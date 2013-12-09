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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USAA

import uuid, copy, time
import httplib
import thread
from threading import Thread
import wsgiservice
import geysers_psnc_utils.restUtils as restUtils
from geysers_psnc_utils.restUtils import extendingLocalizator, decode_multipart, encode_multipart_mime
from geysers_psnc_utils.wsgiservice.xmlserializer import dumps, xml2obj

import logging
logger = logging.getLogger(__name__)

BASE_SCHEMA = '/cxf/vi-cam/cci'
ACTION_TIMEOUT = 60 #sec

data_models = None

#----------------------------------------------
#@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}')
@wsgiservice.mount(BASE_SCHEMA+'/node-synchronization/node/{nodeId}')
class Node(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId):
        return self.POST(nodeId)
    # GETTING
    def POST(self, nodeId):
        # testing notifications
        #thread.start_new_thread(send_node_notification2, ())
        #thread.start_new_thread(send_port_notification, ())
        #thread.start_new_thread(send_port_notification2, ())
        #thread.start_new_thread(send_resource_notification, ())
        return extendingLocalizator(data_models['data']['node'], nodeId)

@wsgiservice.mount(BASE_SCHEMA+'/node-monitoring/node/{nodeId}')
class NodeMonitoring(Node):
    pass

#----------------------------------------------
#@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}')
@wsgiservice.mount(BASE_SCHEMA+'/node-synchronization/node/{nodeId}/board/{boardId}')
class Board(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId):
        return self.POST(nodeId, boardId)
    # GETTING
    def POST(self, nodeId, boardId):
        logger.debug(extendingLocalizator(data_models['data']['node'][nodeId], boardId))
        return extendingLocalizator(data_models['data']['node'][nodeId], boardId)

@wsgiservice.mount(BASE_SCHEMA+'/node-monitoring/node/{nodeId}/board/{boardId}')
class BoardMonitoring(Board):
    pass
#----------------------------------------------
#@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}/port/{portId}')
@wsgiservice.mount(BASE_SCHEMA+'/node-synchronization/node/{nodeId}/board/{boardId}/port/{portId}')
class Port(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId, portId):
        return self.POST(nodeId, boardId, portId)

    # GETTING
    def POST(self, nodeId, boardId, portId):
        return extendingLocalizator(data_models['data']['node'][nodeId][boardId], portId)

@wsgiservice.mount(BASE_SCHEMA+'/node-monitoring/node/{nodeId}/board/{boardId}/port/{portId}')
class PortMonitoring(Port):
    pass
#----------------------------------------------
#@wsgiservice.mount(BASE_SCHEMA+'/node/{nodeId}/board/{boardId}/port/{portId}/resource/{resId}')
@wsgiservice.mount(BASE_SCHEMA+'/node-synchronization/node/{nodeId}/board/{boardId}/port/{portId}/resource/{resId}')
class Resource(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, boardId, portId, resId):
        return self.POST(nodeId, boardId, portId, resId)

    # GETTING
    def POST(self, nodeId, boardId, portId, resId):
        return extendingLocalizator(data_models['data']['node'][nodeId][boardId][portId], resId)

@wsgiservice.mount(BASE_SCHEMA+'/node-monitoring/node/{nodeId}/board/{boardId}/port/{portId}/resource/{resId}')
class ResourceMonitoring(Resource):
    pass
#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/xc-configuration/node/{nodeId}/crossConnection/{xcId}')
class XC(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, nodeId, xcId):
        return self.POST(nodeId, xcId)

    # GETTING
    def POST(self, nodeId, xcId):
        return extendingLocalizator(data_models['data']['node'][nodeId]['crossConnections'], xcId)

    # DELETION
    def PUT(self, nodeId, xcId):
        logger.debug('XC deletion request received')
        del data_models['data']['node'][nodeId]['crossConnections'][xcId]
        logger.debug('XC deleted from datamodel')
        self.response.expires = time.time() + ACTION_TIMEOUT
        logger.debug('Notify about destroying')
        thread.start_new_thread(send_xc_status, (xcId, nodeId, 'Deleted'))
        wsgiservice.raise_202(self)

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/xc-configuration/node/{nodeId}/crossConnection')
class XC_Creator(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    # CREATION
    def POST(self, nodeId):
        logger.info('New XC request for node %s with body %s', nodeId, self.request.body)
        try:
            parts = decode_multipart(self.request.body)
            body = xml2obj(parts['content'])
        except:
            import traceback
            logger.error("Exception" + traceback.format_exc())
            wsgiservice.raise_500(self, 'XML parsing failure')
        logger.debug('POST XC body %s', str(body))
        if 'crossConnection' in body:
            attributes = body['crossConnection']
        else:
            wsgiservice.raise_400(self, 'Unproper request body - lack of root crossConnection XML element')
            return
        xcId = str(uuid.uuid4().time_low)
        attributes['__name__'] = 'crossConnection'
        data_models['data']['node'][nodeId]['crossConnections'][xcId] = attributes
        self.response.expires = time.time() + ACTION_TIMEOUT
        thread.start_new_thread(send_xc_status, (xcId, nodeId, 'Working'))
        #thread.start_new_thread(send_xc_failureReason, (xcId, nodeId, 'Generic Error'))
        #thread.start_new_thread(send_xc_status, (xcId, nodeId, 'Failed'))
        wsgiservice.raise_202(self, xcId)

#===============================================

def send_xc_status(xcId, nodeId, status):
    time.sleep(1)
    try:
        logger.debug('Sending new xc status request')
        conn = httplib.HTTPConnection('localhost:8010')
        uri = '/cci/node/%s/crossConnection/%s/status' % (nodeId, xcId)
        logger.debug('Sending XC status request - %s', status)
        body = dumps(obj=status, root_tag='status')
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type':content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

#===============================================

def send_xc_failureReason(xcId, failureReason):
    time.sleep(1)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/crossConnection/%s/failureReason' % (nodeId, xcId)
        logger.debug('Sending XC failureReason - %s', failureReason)
        body = dumps(obj=failureReason, root_tag='failureReason')
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type':content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())


#===============================================

def send_node_notification():
    time.sleep(5)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/powerConsumption/currentPowerConsumption' % nodeId
        logger.debug('Sending Node notification: %s', uri)
        body = dumps(obj=300.0, root_tag='currentPowerConsumption')
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type': content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

def send_node_notification2():
    time.sleep(4)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/operationalStatus' % nodeId
        logger.debug('Sending Node notification: %s', uri)
        body = dumps(obj='up', root_tag='operationalStatus')
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type': content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

def send_port_notification2():
    time.sleep(7)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        attrName, attrValue = 'currentPowerConsumption', 300.0
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/board/1/port/%s/powerConsumption/currentPowerConsumption' % (nodeId, portId)
        logger.debug('Sending Port notification: %s', uri)
        body = dumps(obj=attrValue, root_tag=attrName)
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type':content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

def send_port_notification():
    time.sleep(8)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        attrName, attrValue = 'maxBwUpgrade', 300.0
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/board/1/port/%s/%s' % (nodeId, portId, attrName)
        logger.debug('Sending Port notification: %s', uri)
        body = dumps(obj=attrValue, root_tag=attrName)
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type':content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

def send_resource_notification():
    time.sleep(5)
    try:
        conn = httplib.HTTPConnection('localhost:8010')
        attrName, attrValue = 'operationalStatus', 'down'
        nodeId, portId, resId = data_models['testingNode'], data_models['testingPort'], data_models['testingResource']
        uri = '/cci/node/%s/board/1/port/%s/resource/%s/%s' % (nodeId, portId, resId, attrName)
        logger.debug('Sending resource notification: %s', uri)
        body = dumps(obj=attrValue, root_tag=attrName)
        content_type, body = encode_multipart_mime([('token', 'text/plain', ''), ('content', 'application/xml', body)], 'boundary')
        conn.request('PUT', uri, body, {'Content-type':content_type})
    except:
        import traceback
        logged.debug(traceback.format_exc())

#===============================================
app = wsgiservice.get_app(globals())

class RestCCIServer(Thread):  
    """HTTP REST interface server class for CCI interface"""
    def __init__(self, dataModels, config):
        '''contructor method required for access to common data model'''
        Thread.__init__(self)        
        global data_models        
        data_models = dataModels
        self.initData()
        self.config = config

    def initData(self):  
        nodeConfigFiles = data_models['nodes']
        data_models['data'] = {'node':{}}
        for configFile in nodeConfigFiles:  
            exec "from %s import node, nodeId" % configFile
            data_models['data']['node'][nodeId] = node
        logger.debug('Nodes are: %s', data_models['data']['node'].keys())
        
    def run(self):
        """Called when server is starting"""
        restUtils.startServer(app, self.config)

if __name__ == '__main__':
    # processed when module is started as a standlone application
    restUtils.startServer(app, config)


