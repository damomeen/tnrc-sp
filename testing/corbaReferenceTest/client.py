# Copyright (C) 2011 PSNC
#
# Authors:
#   Damian Parniewicz (PSNC) <damianp_at_man.poznan.pl>

import uuid, httplib, sys, os, thread, time

#from omniORB import CORBA, PortableServer
import CORBA
import CLIENT__POA
import SERVER

class Config (CLIENT__POA.Config):
    def init(self):
        print 'Config::init() called'

def register(name, configServant): 
    time.sleep(2)      
    print 'Registering in server...'
    orb = CORBA.ORB_init([], CORBA.ORB_ID)
    ior = file('/tmp/server.ior').readline()
    obj = orb.string_to_object(ior)
    presence = obj._narrow(SERVER.Presence)
    presence.register(name, configServant)

if __name__ == '__main__':
    # processed when module is started as a standlone application
    orb = CORBA.ORB_init([], CORBA.ORB_ID)
    rootPoa = orb.resolve_initial_references("RootPOA")
    poaManager = rootPoa._get_the_POAManager()
    poaManager.activate()

    servant = Config()
    servantObject = servant._this()
    thread.start_new_thread(register, ('test_client', servantObject))
    orb.run()

