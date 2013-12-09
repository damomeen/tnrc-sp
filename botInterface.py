#
# The Geysers project (work funded by European Commission).
#
# Copyright (C) 2012  Poznan Supercomputing and Network Center
# Authors:
#   Damian Parniewicz (PSNC) <damianp_at_man.poznan.pl>
# 
# This software is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import uuid, copy
import bottle
from bottle import request, response
from threading import Thread
import geysers_psnc_utils.restUtils as restUtils
from geysers_psnc_utils.restUtils import extendingLocalizator, decode_multipart
from geysers_psnc_utils.wsgiservice.xmlserializer import dumps, xml2obj
import tnrcsp_dm
import pprint

import logging
logger = logging.getLogger(__name__)

BASE_SCHEMA = '/cci'

data_models = None
global_clients = None
global_nodeId = 1


#----------------------------------------------

def isSomethingNew(old, new):
    for k in new:
        if isinstance(new[k], dict) and k in old:
            if isSomethingNew(old[k], new[k]):
                return True
        if new[k] != old.get(k):
            logger.debug('There is a new value of %s: %s->%s', k, old.get(k), new[k])
            return True
    return False

#----------------------------------------------

@bottle.get(BASE_SCHEMA+'/node/<nodeId>')
def node_GET(nodeId):
    logger.info('NodeResource %s requested', nodeId)
    response.headers['Content-Type'] = 'xml/application'
    return dumps(extendingLocalizator(data_models['data']['node'], nodeId))

@bottle.put(BASE_SCHEMA+'/node/<nodeId>')
def node_PUT(nodeId):
    logger.info('*'*20 +' NodeResource %s updating with %s', nodeId, request.body)
    data = data_models['data']['node']
    body = process_request(request, nodeId)
    if body is False:
        return
    if 'node' in body:
        attributes = body['node']
    else:
        attributes = body
        if 'boardID' in attributes and len(attributes['boardID']) == 1:
            attributes['boardID'] = [attributes['boardID']]
            nodeId, attrName = nodeId.split('/')[0:2]
            data[nodeId] = {'__attributes__': attributes, '__name__':'node'}
            bottle.redirect(nodeId, "201")
        elif isSomethingNew(data[nodeId]['__attributes__'], attributes):
            data[nodeId]['__attributes__'].update(attributes) 
            tnrcsp_dm.send_node_notification(nodeId, global_clients['tnrcapNotification'], attributes)
        else:
            logger.debug('Nothing new in node attributes!')

#----------------------------------------------

@bottle.get(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/<rubbish>')
def board_GET(nodeId, boardId, rubbish):
    logger.info('BoardResouce %s.%s requested', nodeId, boardId)
    response.headers['Content-Type'] = 'text/plain'
    logger.debug(extendingLocalizator(data_models['data']['node'][nodeId], boardId))
    return pprint.pformat(extendingLocalizator(data_models['data']['node'][nodeId], boardId))

@bottle.put(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>')
def board_PUT(nodeId, boardId):
    logger.info('*'*20 +' BoardResource %s.%s updating with %s', nodeId, boardId, request.body)
    body = process_request(request, nodeId)
    if body is False:
        return
    if 'board' in body:
        attributes = body['board']
    else:
        attributes = body
        if 'portID' in attributes and len(attributes['portID']) == 1:
            attributes['portID'] = [attributes['portID']]
        boardId, attrName = boardId.split('/')[0:2]
    with data_models['lock']:
        data = data_models['data']['node']
        if boardId not in data[nodeId]:
            data[nodeId][boardId] = {'__attributes__': attributes, '__name__':'board'}
            bottle.redirect(boardId, "201")
        elif isSomethingNew(data[nodeId][boardId]['__attributes__'], attributes):
            data[nodeId][boardId]['__attributes__'].update(attributes) 
        else:
            logger.debug('Nothing new in board attributes!')

@bottle.delete(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>')
def board_DELETE(nodeId, boardId):
    logger.info('*'*20 +' BoardResoruce %s.%s deleting with %s', nodeId, boardId, request.body)
    with data_models['lock']:
        del data_models['data']['node'][nodeId][boardId]
        data_models['data']['node'][nodeId]['__attributes__']['boardID'].remove(boardId)

#----------------------------------------------

@bottle.get(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>/<rubbish>')
def port_GET(nodeId, boardId, portId, rubbish):
    logger.info('PortResource %s.%s.%s requested', nodeId, boardId, portId)
    response.headers['Content-Type'] = 'text/plain'
    logger.debug(extendingLocalizator(data_models['data']['node'][nodeId][boardId], portId))
    return pprint.pformat(extendingLocalizator(data_models['data']['node'][nodeId][boardId], portId))

@bottle.put(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>')
def port_PUT(nodeId, boardId, portId):
    logger.info('*'*20 +' PortResource %%.%s.%s updating', nodeId, boardId, portId)
    body = process_request(request, nodeId)
    if body is False:
        return
    if 'port' in body:
        attributes = body['port']
    else:
        attributes = body
        if 'resourceID' in attributes and len(attributes['resourceID']) == 1:
            attributes['resourceID'] = [attributes['resourceID']]
        portId, attrName = portId.split('/')[0:2]
    with data_models['lock']:
        data = data_models['data']['node']
        if portId not in data[nodeId][boardId]:
            logger.debug('Port %s not found - creating a new port instance %s', portId, attributes)
            data[nodeId][boardId][portId] = {'__attributes__': attributes, '__name__':'port'}
            bottle.redirect(portId, "201")
        elif isSomethingNew(data[nodeId][boardId][portId]['__attributes__'], attributes):
            logger.debug('Port %s found - updating port instance %s', portId, attributes)
            data[nodeId][boardId][portId]['__attributes__'].update(attributes) 
            tnrcsp_dm.send_port_notification(nodeId, boardId, portId, global_clients['tnrcapNotification'], attributes, data[nodeId][boardId][portId]['__attributes__'])
        else:
            logger.debug('Nothing new in port attributes!')


@bottle.put(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>/<rubbish>')
def portOperationalStaus_PUT(nodeId, boardId, portId, rubbish):
    try:
        logger.info('*'*20 +' PortResource operational status %%.%s.%s updating', nodeId, boardId, portId)
        body = process_request(request, nodeId)
        if body is False:
            return
        if 'port' in body:
            attributes = body['port']
        else:
            attributes = body
            if 'resourceID' in attributes and len(attributes['resourceID']) == 1:
                attributes['resourceID'] = [attributes['resourceID']]
            #portId, attrName = portId.split('/')[0:2]
            attrName = 'operationalStatus'
        with data_models['lock']:
            data = data_models['data']['node']
            if portId not in data[nodeId][boardId]:
                logger.debug('Port %s not found - creating a new port instance %s', portId, attributes)
                data[nodeId][boardId][portId] = {'__attributes__': attributes, '__name__':'port'}
                bottle.redirect(portId, "201")
            elif isSomethingNew(data[nodeId][boardId][portId]['__attributes__'], attributes):
                logger.debug('Port %s found - updating port instance %s', portId, attributes)
                data[nodeId][boardId][portId]['__attributes__'].update(attributes) 
                tnrcsp_dm.send_port_notification(nodeId, boardId, portId, global_clients['tnrcapNotification'], attributes, data[nodeId][boardId][portId]['__attributes__'])
            else:
                logger.debug('Nothing new in port attributes!')
    except:
        import traceback
        logger.debug(traceback.format_exc())


@bottle.delete(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>')
def port_DELETE(nodeId, boardId, portId):
    logger.info('*'*20 +' PortResource %s.%s.%s deleting with %s', nodeId, boardId, portId, request.body)
    with data_models['lock']:
        del data_models['data']['node'][nodeId][boardId][portId]
        data_models['data']['node'][nodeId][boardId]['__attributes__']['portID'].remove(portId)

#----------------------------------------------

@bottle.get(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>/resource/<resId>/<rubbish>')
def res_GET(nodeId, boardId, portId, resId, rubbish):
    logger.info('ResResource %s.%s.%s.%s requested', nodeId, boardId, portId, resId)
    response.headers['Content-Type'] = 'xml/application'
    return dumps(extendingLocalizator(data_models['data']['node'][nodeId][boardId][portId], resId))

@bottle.put(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>/resource/<resId>')
def res_PUT(nodeId, boardId, portId, resId):
    logger.info('*'*20 +' ResResource %s.%s.%s.%s updating', nodeId, boardId, portId, resId)
    body = process_request(request, nodeId)
    if body is False:
        return
    if 'resource' in body:
        attributes = body['resource']
    else:
        attributes = body
        resId, attrName = resId.split('/')[0:2]
    with data_models['lock']:
        try:
            data = data_models['data']['node']
            if resId not in data[nodeId][boardId][portId]:
                logger.debug('New resource object created')
                data[nodeId][boardId][portId][resId] = {'__attributes__': attributes, '__name__':'resource'}
                data_models['data']['node'][nodeId][boardId][portId]['__attributes__']['resourceID'].append(resId)
                
                #tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
                #                                 global_clients['tnrcapNotification'], 
                #                                 data[nodeId][boardId][portId][resId]['__attributes__'], 
                #                                 data[nodeId][boardId]['__attributes__']['techParams'])
                tnrcsp_dm.addResource(nodeId, boardId, portId, resId, 
                                                 global_clients['tnrcapConfig'], 
                                                 data[nodeId][boardId][portId][resId]['__attributes__'], 
                                                 data[nodeId][boardId]['__attributes__']['techParams'])
                
                data[nodeId][boardId][portId]['__attributes__']['maxBw'] = float(data[nodeId][boardId][portId]['__attributes__']['maxResvBw']) * len(data[nodeId][boardId][portId]['__attributes__']['resourceID'])
                data[nodeId][boardId][portId]['__attributes__']['maxBw'] = "{0:.1E}".format(data[nodeId][boardId][portId]['__attributes__']['maxBw']).replace('+0', '')
                #wsgiservice.raise_201(self, resId)
                #logger.debug('HTTP response 201 sent')
            elif isSomethingNew(data[nodeId][boardId][portId][resId]['__attributes__'], attributes):
                logger.debug('Resouce object updated')
                data[nodeId][boardId][portId][resId]['__attributes__'].update(attributes) 
                tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
                                                 global_clients['tnrcapNotification'], 
                                                 attributes, 
                                                 data[nodeId][boardId][portId][resId]['__attributes__'])
                logger.debug('HTTP response 200 sent')
                data[nodeId][boardId][portId]['__attributes__']['maxBw'] = float(data[nodeId][boardId][portId]['__attributes__']['maxResvBw']) * len(data[nodeId][boardId][portId]['__attributes__']['resourceID'])
                data[nodeId][boardId][portId]['__attributes__']['maxBw'] = "{0:.1E}".format(data[nodeId][boardId][portId]['__attributes__']['maxBw']).replace('+0', '')
            else:
                logger.debug('Nothing new in resource attributes!')
                logger.debug('HTTP response 200 sent')
        except:
            import traceback
            logger.error(traceback.format_exc())

@bottle.post(BASE_SCHEMA+'/node/<nodeId>/board/<boardId>/port/<portId>/resource/<resId>')
def res_POST(nodeId, boardId, portId, resId):
    logger.info('*'*20 +' ResResource %s.%s.%s.%s deleting with %s', nodeId, boardId, portId, resId, request.body.read())
    with data_models['lock']:
        data = data_models['data']['node']
        #data[nodeId][boardId][portId][resId]['__attributes__']['operationalStatus'] = 'down'
        #tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
        #                                         global_clients['tnrcapNotification'], 
        #                                         data[nodeId][boardId][portId][resId]['__attributes__'], 
        #                                         data[nodeId][boardId][portId][resId]['__attributes__'])

        tnrcsp_dm.removeResource(nodeId, boardId, portId, resId, global_clients['tnrcapConfig'], 
                                                 data[nodeId][boardId]['__attributes__']['techParams'])

        del data_models['data']['node'][nodeId][boardId][portId][resId]
        data_models['data']['node'][nodeId][boardId][portId]['__attributes__']['resourceID'].remove(resId)
        data[nodeId][boardId][portId]['__attributes__']['maxBw'] = float(data[nodeId][boardId][portId]['__attributes__']['maxResvBw']) * len(data[nodeId][boardId][portId]['__attributes__']['resourceID'])
        data[nodeId][boardId][portId]['__attributes__']['maxBw'] = "{0:.1E}".format(data[nodeId][boardId][portId]['__attributes__']['maxBw']).replace('+0', '')

#----------------------------------------------
@bottle.get(BASE_SCHEMA+'/node/<nodeId>/crossConnection/<xcId>')
def xc_GET(nodeId, xcId):
    logger.info('node %s xc %s requested', nodeId, xcId)
    return dumps(extendingLocalizator(data_models['data']['node'][nodeId]['crossConnections'], xcId))

#----------------------------------------------
@bottle.get(BASE_SCHEMA+'/node/<nodeId>/crossConnections-{tag}')
def xcs_GET(nodeId, tag):
    logger.info('node %s xc list requested with tag %s', nodeId, tag)
    response.headers['Content-Type'] = 'xml/application'
    #logger.info('data model is %s', str(data_models['data']['node'][nodeId]['crossConnections']))
    new_data = []
    for xcId, value in data_models['data']['node'][nodeId]['crossConnections'].items():
        new_data.append(value)
    return dumps(new_data)

#----------------------------------------------
@bottle.get(BASE_SCHEMA+'/node/<nodeId>/crossConnection/<xcId>/status')
def xc_status_GET(nodeId, xcId):
    logger.info('node %s xc %s status requested', nodeId, xcId)
    response.headers['Content-Type'] = 'xml/application'
    return dumps(data_models['data']['node'][nodeId]['crossConnections'][xcId]['status'])

@bottle.put(BASE_SCHEMA+'/node/<nodeId>/crossConnection/<xcId>/status')
def xc_status_PUT(nodeId, xcId):
    logger.info('*'*20 +' node %s xc %s status updated', nodeId, xcId)
    logger.debug('XCs dm: %s', data_models['data']['node'][nodeId]['crossConnections'])
    body = process_request(request, nodeId, 'xcAction')
    if body is False:
        return
    if 'status' in body and isinstance(body['status'], str):
        status = body['status']
    else:
        bottle.abort("400", 'Unproper request body - lack of root status XML element')
        return
    with data_models['lock']:
        data = data_models['data']['node']
        data[nodeId]['crossConnections'][xcId]['status'] = status
    if status in ('Working', 'Deleted'): 
        tnrcsp_dm.send_corba_xc_notification(xcId, status, None, global_clients['tnrcapNotification'])
    elif 'failureReason' in data[nodeId]['crossConnections'][xcId]:
        failureReason = data[nodeId]['crossConnections'][xcId]['failureReason']
        tnrcsp_dm.send_corba_xc_notification(xcId, status, failureReason, global_clients['tnrcapNotification'])

    if status in ('Deletion', 'Deleted'):
        with data_models['lock']:
            del data[nodeId]['crossConnections'][xcId]

#----------------------------------------------
@bottle.get(BASE_SCHEMA+'/node/<nodeId>/crossConnection/<xcId>/failureReason')
def XCfailureReason_GET(nodeId, xcId):
    logger.info('node %s xc %s failureReason requested', nodeId, xcId)
    response.headers['Content-Type'] = 'xml/application'
    return dumps(data_models['data']['node'][nodeId]['crossConnections'][xcId]['failureReason'])

@bottle.put(BASE_SCHEMA+'/node/<nodeId>/crossConnection/<xcId>/failureReason')
def XCfailureReason_PUT(nodeId, xcId):
    logger.info('*'*20 +' node %s xc %s failureReason updated', nodeId, xcId)
    body = process_request(request, nodeId, 'xcAction')
    if body is False:
        return
    if 'failureReason' in body and isinstance(body['failureReason'], str):
        failureReason = body['failureReason']
    else:
        bottle.abort("400", 'Unproper request body - lack of root status XML element')
        return
    with data_models['lock']:
        data = data_models['data']['node']
        data[nodeId]['crossConnections'][xcId]['failureReason'] = failureReason

    if 'status' in data[nodeId]['crossConnections'][xcId]:
        status = data[nodeId]['crossConnections'][xcId]['status']
        tnrcsp_dm.send_corba_xc_notification(xcId, status, failureReason, global_clients['tnrcapNotification'])

#----------------------------------------------
@bottle.get('/info/node')
def  node_GET():
    logger.info('Virtual node id requested')
    return dumps({'info': global_nodeId})

#----------------------------------------------
@bottle.get('/into/ctrl')
def controller_GET():
    logger.info('Controller id requested')
    nodeId = getControllerId()
    logger.info('Controller Id retrieved: %s', nodeId)
    return dumps({'info': nodeId})

#----------------------------------------------
@bottle.get('/info/te-link/{teLinkId}')
def teLink_GET(teLinkId):
    logger.info('datalinks within Te-Link %s requested', teLinkId)
    dataLink = getDataLinks(teLinkId)
    logger.info('datalinks retrieved: %s', dataLink)
    return dumps({'info': dataLink})
    
    
    
#----------------------------------------------
@bottle.get('/xc-info/<rubbish>')
def xcInfo_GET(rubbish):
    logger.info('incoming HTTP GET request %s', request.path)
    try:
        data, nodeId = xcInfo_getXCs()
        logger.info('getting XCs from %s', data_models['data']['node'][nodeId]['crossConnections'])
        return 'Cross-connections on node %s are:\n %s' % (nodeId, data)
    except:
        import traceback
        logger.error(traceback.format_exc())

def xcInfo_getXCs():
    nodeId = 0
    xcs = []
    for nodeId in data_models['data']['node']:
        xcs = copy.deepcopy(data_models['data']['node'][nodeId]['crossConnections'])
        break
    if len(xcs) == 0:
        return "  No cross-connections.", nodeId
    for xcId in xcs:
        del xcs[xcId]['__name__']
        resIn = xcs[xcId]['crossConnection']['resourceIn']
        resOut = xcs[xcId]['crossConnection']['resourceOut']
        xcs[xcId]['resourceIn'] = "%s.%s.%s" % (resIn['boardID'], resIn['portID'], resIn['resourceID'])
        xcs[xcId]['resourceOut'] = "%s.%s.%s" % (resOut['boardID'], resOut['portID'], resOut['resourceID'])
        xcs[xcId]['direction'] = xcs[xcId]['crossConnection']['direction']
        del xcs[xcId]['crossConnection']
    logger.debug('data model is %s', xcs)
    return pprint.pformat(xcs), nodeId

####################################
### Corba security

def process_request(request, nodeId, functionality='NodeInfo'):
    body = request.body.read()
    content_type = request.headers.get("Content-Type")
    logger.debug('Content type is %s', content_type)
    if 'multipart/form-data' in content_type or 'multipart/mixed' in content_type:
        parts = decode_multipart(body)
        #logger.debug('HTTP parts are %s', parts)
        body = parts.get('content', "")
        token = parts.get('token')
        returned = True # authorizeXcAction(token, nodeId, functionality)
        if returned is False:
            logger.info('Request not authorized')
            return False
    #logger.debug('Body(xml) is %s', body)
    body = xml2obj(body)
    logger.debug('Body(obj) is:\n %s \n', pprint.pformat(body))
    return body


def authorizeXcAction(authNtoken, nodeId, functionality):
    import sys, os, CORBA
    from geysers_psnc_utils.corbaUtils import corbaClient, CorbaException
    import SecGateway

    if 'AaiAuthentication' not in global_clients:
        return None

    logger.info('Authorize XC action for node %s:\n%s\n', nodeId, str(authNtoken))
    try:
        aaiRef = corbaClient(SecGateway.AaiServer, iorFile=global_clients['AaiAuthentication']['iorName'])
        actor = 'VIP'
        resourceId   = nodeId
        resourceType = 'http://geysers.eu/ncp+/resource/resource-type/VNode-Info'
        if functionality == 'NodeInfo':
            action       = 'CCI:Synch-Update'
        elif functionality == 'xcAction':
            action       = 'CCI:Notify'
        else:
            action       = ''
        permitted = aaiRef.authorizeAction(authNtoken, actor, resourceId, resourceType, action)
        logger.debug('AAI authorization of action %s', str(permitted))
        return permitted
    except (CORBA.TRANSIENT, CorbaException):          
        logger.error('Could not connect to AAI server')
        return None
    except:
        import traceback
        logger.error('Exception: ' + traceback.format_exc())
        return None

####################################
### Corba clients

def getControllerId():
    import sys, os, CORBA
    from geysers_psnc_utils.corbaUtils import corbaClient, CorbaException
    import LRM

    try:
        lrmGlobalRef = corbaClient(LRM.Info, iorFile=global_clients['LRM']['iorName'])
        nodeId = lrmGlobalRef.nodeId()
        return itoa(nodeId)
    except (CORBA.TRANSIENT, CorbaException):
        import traceback
        traceback.print_exc()
        logger.error('Could not connect to LRM')
        return None
    except:
        import traceback
        traceback.print_exc()
        logger.error('Exception: ' + traceback.format_exc())
        return None


def atoi(aa):
    "convert dotted IPv4 string into long int"
    aa = aa.split('.')
    ia = int(aa[0])<<24 | int(aa[1])<<16 | int(aa[2])<<8 | int(aa[3])
    logger.debug('convetint %s into %s', aa, str(ia))
    return ia
    
def itoa(ia):
    "convert long int to dotted IPv4 string"
    r = ia>>24, ((ia&0xFF0000)>>16), ((ia&0xFF00)>>8), ia&0xFF
    return '.'.join([str(s) for s in r])

def getDataLinks(teLink):
    import sys, os, CORBA
    from geysers_psnc_utils.corbaUtils import corbaClient, CorbaException
    import _GlobalIDL as glob
    import LRM

    try:
        lrmInfoRef = corbaClient(LRM.Info, iorFile=global_clients['LRM']['iorName'])
        dataLink = lrmInfoRef.DLinkFromTELink(glob.gmplsTypes.linkId(ipv4=atoi(teLink)))
        logger.debug("DataLink %s is %s", str(dataLink), str(dataLink.__dict__))
        return int(dataLink.unnum)
    except (CORBA.TRANSIENT, CorbaException):
        logger.error('Could not connect to LRM')
        return None
    except:
        import traceback
        logger.error('Exception: ' + traceback.format_exc())
        return None

#===============================================

class RestCCIServer(Thread):  
    """HTTP REST interface server class for CCI interface"""
    def __init__(self, dataModels, config):
        '''contructor method required for access to common data model'''
        Thread.__init__(self)        
        global data_models        
        data_models = dataModels
        global global_clients
        global_clients = dataModels['clients']
        global global_nodeId
        global_nodeId = dataModels['clients']['rest-CCI']['nodeId']
        self.config = config
        self.initData()
        logger.debug('DataModels are %s', str(data_models))


    def initData(self):       
        with data_models['lock']:
            nodeId = global_clients['rest-CCI']['nodeId']
            data_models['data'] = {
                'node':{
                    nodeId:{
                        '__name__':'node',
                        'crossConnections':{},
                    },
                },
            }
        
    def run(self):
        """Called when server is starting"""
        logger.info('Running CherryPy HTTP server on port %s', self.config['port'])
        bottle.run(host='0.0.0.0', port=self.config['port'], debug=True, server='cherrypy')


if __name__ == '__main__':
    # processed when module is started as a standlone application
    restUtils.startServer(app, {
            'port': 8010,
            'ssl': False,
            'certFilesDir':'/home/user/geysers-wp4/branches/python_modules/myModule/ssl/'
        },)
