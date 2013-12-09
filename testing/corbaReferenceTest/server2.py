import uuid, httplib, sys, os, traceback, thread
from omniORB import CORBA
import SERVER__POA

import logging
logging.basicConfig(filename = "/tmp/Client2.log",
                    level    = logging.DEBUG,
                    format   = "%(levelname)s - %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger('Client2')
from geysers_psnc_utils.corbaUtils import CorbaServant, corbaClient

class server (SERVER__POA.Presence):
    def __init__(self, d): pass
    def register(self, name, configRef):
        print 'Presence::register() called'
        print '--> spName %s' % name
        print '--> ConfigRef', configRef
        thread.start_new_thread(call_init, (configRef,))

def call_init(configRef):
    try:
        configRef.init()
        print 'Servant reference successfully used'
    except:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    server = CorbaServant(server, None, '/tmp/')
    server.start()

