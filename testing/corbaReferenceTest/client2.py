# Copyright (C) 2011 PSNC
#
# Authors:
#   Damian Parniewicz (PSNC) <damianp_at_man.poznan.pl>

import uuid, httplib, sys, os, thread, time

#from omniORB import CORBA, PortableServer
import CORBA
import CLIENT__POA
import SERVER
from geysers_psnc_utils.corbaUtils import CorbaServant, corbaClient

import logging
logging.basicConfig(filename = "/tmp/Client2.log",
                    level    = logging.DEBUG,
                    format   = "%(levelname)s - %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger('Client2')

class Config (CLIENT__POA.Config):
    def __init__(self, d): pass
    def init(self):
        print 'Config::init() called'

def register(name, configServant): 
    time.sleep(2)      
    print 'Registering in server...'
    presence = corbaClient(SERVER.Presence, iorFile='/tmp/server.ior')
    presence.register(name, configServant)

if __name__ == '__main__':
    # processed when module is started as a standlone application
    server = CorbaServant(Config, None, '/tmp/')
    server.start()
    time.sleep(1)
    thread.start_new_thread(register, ('test_client', server.servantObject))


