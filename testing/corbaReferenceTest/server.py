import uuid, httplib, sys, os, traceback, thread
from omniORB import CORBA
import SERVER__POA


class Presence (SERVER__POA.Presence):
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
    orb = CORBA.ORB_init([], CORBA.ORB_ID)
    rootPoa = orb.resolve_initial_references("RootPOA")
    poaManager = rootPoa._get_the_POAManager()
    poaManager.activate()

    servant = Presence()
    servantObject = servant._this()
    ior = orb.object_to_string(servantObject) 
    file('/tmp/server.ior','w').write(ior)
    orb.run()

