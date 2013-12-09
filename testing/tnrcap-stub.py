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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USASA

import uuid, httplib, sys, os, thread

sys.path.append(os.getcwd()+"/../") # add directory with corba stub to python modules path
import TNRC_AP__POA as TNRC_AP
import TNRC_AP as TNRC
import _GlobalIDL as glob
del sys.path[-1]

from geysers_psnc_utils.corbaUtils import CorbaServant, corbaClient

import logging

logging.basicConfig(filename = "tnrcap-stub.log", level = logging.DEBUG, 
                    format = "%(levelname)s - %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger('tnrcap-stub')


class tnrc_presence (TNRC_AP.Presence):
    
    def __init__(self, dataModel):
        pass
     
    def register(self, spName, maxTimeout, spConfigRef, spXCRef):
        print 'Presence.register() called'
        print '--> spName %s, maxTimeout %d' % (spName, maxTimeout)
        print '--> ConfigRef', spConfigRef
        print '--> XCRef', spXCRef
        thread.start_new_thread(call_init, (spConfigRef,))

    def unregister(self, spName):
        print 'Presence.unregister() called'
        print '--> spName', spName

def call_init(spConfigRef):
    try:
        spConfigRef.init(10)
    except:
        import traceback
        traceback.print_exc()

class tnrc_conf (TNRC_AP.Config):

    def __init__(self, dataModel):
        pass

    def instanceStart(self):
        print 'Config.instanceStart() called'

    def instanceStop(self):
        print 'Config.instanceStop() called'

    def setEquipment(self, details):
        print 'Config.setEquipment() called'

    def addEqpt(self, eId, addr, eType, opSt, admSt, location):
        print 'Config.addEqpt() called', eId, addr, eType, opSt, admSt, location

    def addBoard(self, eId, bId, sCap, eType, opSt, admSt):
        print 'Config.addBoard() called', eId, bId, sCap, eType, opSt, admSt

    def addPort(self, eId, bId, pId, remEqAddr, remPortId, opSt, admSt, lambdaBase, lambdaCount, bw, subwavInfo, prot):
        print 'Config.addPort() called', eId, bId, pId, remEqAddr, remPortId, opSt, admSt, hex(lambdaBase), hex(lambdaCount), bw, subwavInfo, prot

    def addResource(self, eId, bId, pId, label, opSt, admSt, labelState):
        print 'Config.addResource() called', eId, bId, pId, label, opSt, admSt, labelState

    def setEqptPowerConsumption(self, eId, powerCons):
        print 'Config.setEqptPowerConsumption() called', eId, powerCons

    def setPortPowerConsumption(self, eId, bId, pId, powerCons):
        print 'Config.setPortPowerConsumption() called', eId, bId, pId, powerCons

    def setPortBwReplanning(self, eId, bId, pId, bwInfo):
        print 'Config.setPortBwReplanning() called', eId, bId, pId, bwInfo
  
class tnrc_notif (TNRC_AP.Notifications):

    def __init__(self, dataModel):
        pass

    def xcResult(self, handle, result, error, selectedRes):
        print 'Notification.xcResult() called', handle, result, error, selectedRes

    def asyncNotification(self, events):
        print 'Notification.asyncNotification() called', events


if __name__ == '__main__':
    # processed when module is started as a standlone application
    for servant in [tnrc_presence, tnrc_conf, tnrc_notif]:
        server = CorbaServant(servant, None, '/opt/gmpls_ctrl_core/var/gmpls')
        server.start()

