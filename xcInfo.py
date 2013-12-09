# Copyright (C) 2011 PSNC
#
# Authors:
#   Damian Parniewicz (PSNC) <damianp_at_man.poznan.pl>

from threading import Thread
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import pprint, copy
import logging
logger = logging.getLogger(__name__)

data_models = None
global_clients = None

#----------------------------------------------

class XCinfoHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        logger.info('incoming HTTP GET request %s', self.path)
        self.nodeId = 0
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            data = self.getXCs()
            logger.info('getting XCs from %s', data_models['data']['node'][self.nodeId]['crossConnections'])
            self.wfile.write('Cross-connections on node %s are:\n' % self.nodeId)

            self.wfile.write(data)
        except:
            import traceback
            logger.error(traceback.format_exc())

    def getXCs(self):
        self.nodeId = 0
        xcs = []
        for nodeId in data_models['data']['node']:
            xcs = copy.deepcopy(data_models['data']['node'][nodeId]['crossConnections'])
            self.nodeId = nodeId
            break
        if len(xcs) == 0:
            return "  No cross-connections."
        for xcId in xcs:
            del xcs[xcId]['__name__']
            resIn = xcs[xcId]['crossConnection']['resourceIn']
            resOut = xcs[xcId]['crossConnection']['resourceOut']
            xcs[xcId]['resourceIn'] = "%s.%s.%s" % (resIn['boardID'], resIn['portID'], resIn['resourceID'])
            xcs[xcId]['resourceOut'] = "%s.%s.%s" % (resOut['boardID'], resOut['portID'], resOut['resourceID'])
            xcs[xcId]['direction'] = xcs[xcId]['crossConnection']['direction']
            del xcs[xcId]['crossConnection']
        logger.debug('data model is %s', xcs)
        return pprint.pformat(xcs)


#===============================================

class xcInfoServer(Thread):  
    def __init__(self, dataModels, config):
        '''contructor method required for access to common data model'''
        Thread.__init__(self)        
        global data_models        
        data_models = dataModels
        global global_clients
        global_clients = dataModels['clients']
        self.config = config
        logger.debug('DataModels are %s', str(data_models))
        
    def run(self):
        """Called when server is starting"""
        server = HTTPServer(('', self.config['port']), XCinfoHandler)
        logger.info('Http server started on port %s', self.config['port'])
        server.serve_forever()