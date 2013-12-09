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

import sys, os, logging, time
from optparse import OptionParser
from threading import Lock
from omniORB import CORBA

from geysers_psnc_utils.deamon import Daemon
from geysers_psnc_utils.corbaUtils import CorbaServant, CorbaException
import tnrcspCorbaServant
import tnrcsp_dm
import restInterfaceCCI
import restProxyInfo

try: 
     import cherrypy
     import xcInfo as xcInfo
except:
     import xcInfo


##############################################

MODULE_NAME = 'tnrcsp'
__version__ = '0.1'

##############################################

class ModuleDaemon(Daemon):
    def __init__(self, moduleName, options):
        self.moduleName=moduleName
        self.options = options
        self.logger = logging.getLogger(self.__class__.__name__)
        pidFile = "%s/%s.pid" % (self.options.pidDir, self.moduleName)
        self.initializeDataModel()
        Daemon.__init__(self, pidFile)

    #---------------------
    def initializeDataModel(self):
        self.dataModels = {
            'data':{},
            'lock':Lock(),
            'clients':{},
        }     
        # load configuration to global dictionary
        configFile = '%s/%s.conf' % (self.options.confDir, self.moduleName)
        execfile(configFile, globals())

        # passing clients configuration to servers
        self.dataModels.update(INTERFACES)

    #---------------------
    def run(self):
        """
        Method called when starting the daemon. 
        """
        try:
            # starting interfaces threads
            tnrcspXCServer = CorbaServant(tnrcspCorbaServant.tnrcsp_xc, self.dataModels, self.options.iorDir)
            tnrcspXCServer.start()

            tnrcspConfigServer = CorbaServant(tnrcspCorbaServant.tnrcsp_conf, self.dataModels, self.options.iorDir)
            tnrcspConfigServer.start()
            
            if 'rest-CCI' in self.dataModels['servants']:
                tnrcspServer = restInterfaceCCI.RestCCIServer(self.dataModels, self.dataModels['servants']['rest-CCI'])
                tnrcspServer.start()

            if 'rest-CCI2' in self.dataModels['servants']:
                import botInterface
                tnrcspServer2 = botInterface.RestCCIServer(self.dataModels, self.dataModels['servants']['rest-CCI2'])
                tnrcspServer2.start()

            if 'rest-Info' in self.dataModels['servants']:
                infoServer = restProxyInfo.RestInfoServer(self.dataModels, self.dataModels['servants']['rest-Info'])
                infoServer.start()

            if 'xcInfo' in self.dataModels['servants']:
                xcInfoServer = xcInfo.xcInfoServer(self.dataModels, self.dataModels['servants']['xcInfo'])
                xcInfoServer.start()
            # run any more interface server as a Thread

            # try every 10 sec to register in TNRC-AP until registered succesfully
            #time.sleep(10.0)
            while True:
                try:
                    tnrcsp_dm.registerInTnrcAP(self.dataModels, tnrcspXCServer.servantObject, tnrcspConfigServer.servantObject)
                    return
                except (CORBA.TRANSIENT, CorbaException):
                    self.logger.error("Could not connect to TNRC-AP - waiting 10 sec")
                    time.sleep(10.0)
        except:
            import traceback
            self.logger.error("Exception" + traceback.format_exc())

    def unregister(self):
        try:
            tnrcsp_dm.unregisterInTnrcAP(self.dataModels)
        except:
            import traceback
            self.logger.error("Exception" + traceback.format_exc())

##############################################

if __name__ == "__main__":
    
    # optional command-line arguments processing
    usage="usage: %prog start|stop|restart [options]"
    parser = OptionParser(usage=usage, version="%prog " + __version__)
    parser.add_option("-p", "--pidDir", dest="pidDir", default='/tmp', help="directory for pid file")
    parser.add_option("-l", "--logDir", dest="logDir", default='.', help="directory for log file")
    parser.add_option("-i", "--iorDir", dest="iorDir", default='/tmp', help="directory for ior file")
    parser.add_option("-c", "--confDir", dest="confDir", default='.',    help="directory for config file")
    options, args = parser.parse_args()
    
    # I do a hack if configDir is default - './' could not point to local dir 
    if options.confDir == '.':
        options.confDir = sys.path[0]

    if 'start' in args[0]:
        # clear log file
        try:
            os.remove("%s/%s.log" % (options.logDir, MODULE_NAME))
        except: 
            pass          

    # creation of logging infrastructure
    logging.basicConfig(filename = "%s/%s.log" % (options.logDir, MODULE_NAME),
                        level    = logging.DEBUG,
                        format   = "%(levelname)s - %(asctime)s - %(name)s - %(message)s")
    logger = logging.getLogger(MODULE_NAME)

    # starting module's daemon
    daemon = ModuleDaemon(MODULE_NAME, options)
    
    # mandatory command-line arguments processing
    if len(args) == 0:
        print usage
        sys.exit(2)
    if 'start' == args[0]:
        logger.info('starting the module')
        daemon.start()
    elif 'stop' == args[0]:
        logger.info('stopping the module')
        daemon.unregister()
        daemon.stop()
    elif 'restart' == args[0]:
        logger.info('restarting the module')
        daemon.restart()
    else:
        print "Unknown command"
        print usage
        sys.exit(2)
    sys.exit(0)

