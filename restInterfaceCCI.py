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
import wsgiservice
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
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}')
class Node(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId):
        logger.info('NodeResource %s requested', nodeId)
        return extendingLocalizator(data_models['data']['node'], nodeId)

    def PUT(self, nodeId):
        logger.info('*'*20 +' NodeResource %s updating with %s', nodeId, self.request.body)
        data = data_models['data']['node']
        body = process_request(self.request, nodeId)
        if body is False:
            return
        if 'node' in body:
            attributes = body['node']
        else:
            attributes = body
            if 'boardID' in attributes and len(attributes['boardID']) == 1:
                attributes['boardID'] = [attributes['boardID']]
            nodeId, attrName = nodeId.split('/')[0:2]
        with data_models['lock']:
            if nodeId not in data:
                data[nodeId] = {'__attributes__': attributes, '__name__':'node'}
                wsgiservice.raise_201(self, nodeId)
            elif isSomethingNew(data[nodeId]['__attributes__'], attributes):
                data[nodeId]['__attributes__'].update(attributes) 
                tnrcsp_dm.send_node_notification(nodeId, global_clients['tnrcapNotification'], attributes)
                wsgiservice.raise_200(self)
            else:
                logger.debug('Nothing new in node attributes!')
                wsgiservice.raise_200(self)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}')
class Board(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId):
        logger.info('BoardResouce %s.%s requested', nodeId, boardId)
        return extendingLocalizator(data_models['data']['node'][nodeId], boardId)

    def PUT(self, nodeId, boardId):
        logger.info('*'*20 +' BoardResource %s.%s updating with %s', nodeId, boardId, self.request.body)
        body = process_request(self.request, nodeId)
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
                wsgiservice.raise_201(self, boardId)
            elif isSomethingNew(data[nodeId][boardId]['__attributes__'], attributes):
                data[nodeId][boardId]['__attributes__'].update(attributes) 
                wsgiservice.raise_200(self)
            else:
                logger.debug('Nothing new in board attributes!')
                wsgiservice.raise_200(self)
        
    def DELETE(self, nodeId, boardId):
        logger.info('*'*20 +' BoardResoruce %s.%s deleting with %s', nodeId, boardId, self.request.body)
        with data_models['lock']:
            del data_models['data']['node'][nodeId][boardId]
            data_models['data']['node'][nodeId]['__attributes__']['boardID'].remove(boardId)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}/port/{portId}')
class Port(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId, portId):
        logger.info('PortResource %s.%s.%s requested', nodeId, boardId, portId)
        return extendingLocalizator(data_models['data']['node'][nodeId][boardId], portId)

    def PUT(self, nodeId, boardId, portId):
        logger.info('*'*20 +' PortResource %%.%s.%s updating with %s', nodeId, boardId, portId, self.request.body)
        body = process_request(self.request, nodeId)
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
                wsgiservice.raise_201(self, portId)
            elif isSomethingNew(data[nodeId][boardId][portId]['__attributes__'], attributes):
                logger.debug('Port %s found - updating port instance %s', portId, attributes)
                data[nodeId][boardId][portId]['__attributes__'].update(attributes) 
                tnrcsp_dm.send_port_notification(nodeId, boardId, portId, global_clients['tnrcapNotification'], attributes, data[nodeId][boardId][portId]['__attributes__'])
                wsgiservice.raise_200(self)
            else:
                logger.debug('Nothing new in port attributes!')
                wsgiservice.raise_200(self)

        
    def DELETE(self, nodeId, boardId, portId):
        logger.info('*'*20 +' PortResource %s.%s.%s deleting with %s', nodeId, boardId, portId, self.request.body)
        with data_models['lock']:
            del data_models['data']['node'][nodeId][boardId][portId]
            data_models['data']['node'][nodeId][boardId]['__attributes__']['portID'].remove(portId)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}/port/{portId}/resource/{resId}')
class Resource(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId, portId, resId):
        logger.info('ResResource %s.%s.%s.%s requested', nodeId, boardId, portId, resId)
        return extendingLocalizator(data_models['data']['node'][nodeId][boardId][portId], resId)

    def PUT(self, nodeId, boardId, portId, resId):
        logger.info('*'*20 +' ResResource %s.%s.%s.%s updating with %s', nodeId, boardId, portId, resId, self.request.body)
        body = process_request(self.request, nodeId)
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
                    
                    tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
                                                     global_clients['tnrcapNotification'], 
                                                     data[nodeId][boardId][portId][resId]['__attributes__'], 
                                                     data[nodeId][boardId][portId][resId]['__attributes__'])
                    #wsgiservice.raise_201(self, resId)
                    #logger.debug('HTTP response 201 sent')
                elif isSomethingNew(data[nodeId][boardId][portId][resId]['__attributes__'], attributes):
                    logger.debug('Resouce object updated')
                    data[nodeId][boardId][portId][resId]['__attributes__'].update(attributes) 
                    tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
                                                     global_clients['tnrcapNotification'], 
                                                     attributes, 
                                                     data[nodeId][boardId][portId][resId]['__attributes__'])
                    #wsgiservice.raise_200(self)
                    logger.debug('HTTP response 200 sent')
                else:
                    logger.debug('Nothing new in resource attributes!')
                    #wsgiservice.raise_200(self)
                    logger.debug('HTTP response 200 sent')
            except:
                import traceback
                logger.error(traceback.format_exc())

    def POST(self, nodeId, boardId, portId, resId):
        logger.info('*'*20 +' ResResource %s.%s.%s.%s deleting with %s', nodeId, boardId, portId, resId, self.request.body)
        with data_models['lock']:
            data = data_models['data']['node']
            data[nodeId][boardId][portId][resId]['__attributes__']['operationalStatus'] = 'down'
            tnrcsp_dm.send_resource_notification(nodeId, boardId, portId, resId, 
                                                     global_clients['tnrcapNotification'], 
                                                     data[nodeId][boardId][portId][resId]['__attributes__'], 
                                                     data[nodeId][boardId][portId][resId]['__attributes__'])

            del data_models['data']['node'][nodeId][boardId][portId][resId]
            data_models['data']['node'][nodeId][boardId][portId]['__attributes__']['resourceID'].remove(resId)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/crossConnection/{xcId}')
class XC(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, xcId):
        logger.info('node %s xc %s requested', nodeId, xcId)
        return extendingLocalizator(data_models['data']['node'][nodeId]['crossConnections'], xcId)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/crossConnections-{tag}')
class XCs(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, tag):
        logger.info('node %s xc list requested with tag %s', nodeId, tag)
        #logger.info('data model is %s', str(data_models['data']['node'][nodeId]['crossConnections']))
        new_data = []
        for xcId, value in data_models['data']['node'][nodeId]['crossConnections'].items():
            new_data.append(value)
        return new_data

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/crossConnection/{xcId}/status')
class XCstatus(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, xcId):
        logger.info('node %s xc %s status requested', nodeId, xcId)
        return data_models['data']['node'][nodeId]['crossConnections'][xcId]['status']

    def PUT(self, nodeId, xcId):
        logger.info('*'*20 +' node %s xc %s status updated with %s', nodeId, xcId, self.request.body)
        logger.debug('XCs dm: %s', data_models['data']['node'][nodeId]['crossConnections'])
        body = process_request(self.request, nodeId, 'xcAction')
        if body is False:
            return
        if 'status' in body and isinstance(body['status'], str):
            status = body['status']
        else:
            wsgiservice.raise_400(self, 'Unproper request body - lack of root status XML element')
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
@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/crossConnection/{xcId}/failureReason')
class XCfailureReason(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, xcId):
        logger.info('node %s xc %s failureReason requested', nodeId, xcId)
        return data_models['data']['node'][nodeId]['crossConnections'][xcId]['failureReason']

    def PUT(self, nodeId, xcId):
        logger.info('*'*20 +' node %s xc %s failureReason updated with %s', nodeId, xcId, self.request.body)
        body = process_request(self.request, nodeId, 'xcAction')
        if body is False:
            return
        if 'failureReason' in body and isinstance(body['failureReason'], str):
            failureReason = body['failureReason']
        else:
            wsgiservice.raise_400(self, 'Unproper request body - lack of root failureReason XML element')
            return
        with data_models['lock']:
            data = data_models['data']['node']
            data[nodeId]['crossConnections'][xcId]['failureReason'] = failureReason

        if 'status' in data[nodeId]['crossConnections'][xcId]:
            status = data[nodeId]['crossConnections'][xcId]['status']
            tnrcsp_dm.send_corba_xc_notification(xcId, status, failureReason, global_clients['tnrcapNotification'])

####################################
### Corba security

def process_request(request, nodeId, functionality='NodeInfo'):
    body = request.body
    logger.debug('Content type is %s', request.content_type)
    if 'multipart/form-data' in request.content_type or 'multipart/mixed' in request.content_type:
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


#===============================================

app = wsgiservice.get_app(globals())


class RestCCIServer(Thread):  
    """HTTP REST interface server class for CCI interface"""
    def __init__(self, dataModels, config):
        '''contructor method required for access to common data model'''
        Thread.__init__(self)        
        global data_models        
        data_models = dataModels
        global global_clients
        global_clients = dataModels['clients']
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
        restUtils.startServer(app, self.config)

if __name__ == '__main__':
    # processed when module is started as a standlone application
    restUtils.startServer(app, {
            'port': 8010,
            'ssl': False,
            'certFilesDir':'/home/user/geysers-wp4/branches/python_modules/myModule/ssl/'
        },)
