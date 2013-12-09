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

BASE_SCHEMA = '/info'

global_nodeId = 1
global_clients = None


#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/node')
class Node(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self):
        logger.info('Virtual node id requested')
        return {'info': global_nodeId}

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/ctrl')
class Controller(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self):
        logger.info('Controller id requested')
        nodeId = getControllerId()
        logger.info('Controller Id retrieved: %s', nodeId)
        return {'info': nodeId}

#----------------------------------------------
@wsgiservice.mount(BASE_SCHEMA+'/te-link/{teLinkId}')
class TeLink(wsgiservice.Resource):
    NOT_FOUND = (KeyError,)

    def GET(self, teLinkId):
        logger.info('datalinks within Te-Link %s requested', teLinkId)
        dataLink = getDataLinks(teLinkId)
        logger.info('datalinks retrieved: %s', dataLink)
        return {'info': dataLink}

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

app = wsgiservice.get_app(globals())


class RestInfoServer(Thread):  
    """HTTP REST interface server class for getting GMPLS+ controller information"""
    def __init__(self, dataModels, config):
        '''contructor method required for access to common data model'''
        Thread.__init__(self)        
        global global_clients
        global_clients = dataModels['clients']
        global global_nodeId
        global_nodeId = dataModels['clients']['rest-CCI']['nodeId']
        self.config = config
        logger.info("Info-server initialized")

    def run(self):
        """Called when server is starting"""
        restUtils.startServer(app, self.config)

if __name__ == '__main__':
    # processed when module is started as a standlone application
    global_clients = {'LRM':{'iorName':'/opt/gmpls_ctrl_edge/var/gmpls/lrm.ior'}}
    restUtils.startServer(app, {
            'port': 7010,
            'ssl': False,
            'certFilesDir':'/home/user/geysers-wp4/branches/python_modules/myModule/ssl/'
        },)
