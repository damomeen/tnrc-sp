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

import uuid, httplib, datetime

import TNRC_SP__POA
import TNRC_SP
import TNRC
import _GlobalIDL as glob

import tnrcsp_dm
from geysers_psnc_utils.wsgiservice.xmlserializer import dumps, xml2obj

import logging
logger = logging.getLogger(__name__)

class tnrcsp_xc (TNRC_SP__POA.XC):
    
    def __init__(self, dataModels):
        '''contructor method required for access to common data model'''
        self.dataModels = dataModels
        self.defaultTimeout = 10
  
    @tnrcsp_dm.corba_exception_handler
    def make(self, handle, inOutRes, direction, isVirtual, activate, action):
        logger.info('\n\n\t\t\t\t\t\t\t\t\tXC.make() called\n')
        logger.info('--> Handle', handle)
        logger.info('--> Ingress portId %d, labelId %d', inOutRes[0].resIn.portId, inOutRes[0].resIn.lblId.label32)
        logger.info('--> Egress portId %d, labelId %d', inOutRes[0].resOut.portId, inOutRes[0].resOut.lblId.label32)
        logger.info('--> direction %s, isVirtual %s, action %s', str(direction), str(isVirtual), str(action))
        
        xc = {
            'crossConnection':{
                'resourceIn':{
                    'boardID': str((inOutRes[0].resIn.portId & 0x03FF0000) >> 16),
                    'portID': str(inOutRes[0].resIn.portId & 0x0000FFFF),
                    'resourceID': str(tnrcsp_dm.label2channel(inOutRes[0].resIn.lblId.label32)),
                },
                'resourceOut':{
                    'boardID': str((inOutRes[0].resOut.portId & 0x03FF0000) >> 16),
                    'portID':  str(inOutRes[0].resOut.portId & 0x0000FFFF),
                    'resourceID': str(tnrcsp_dm.label2channel(inOutRes[0].resOut.lblId.label32)),
                },
                'direction': tnrcsp_dm.parse_corba_direction(direction),
                'status': 'Creation',
            }
        }

        if action is not TNRC.XC_ACTION_ACTIVATE:
            raise TNRC_SP.NotCapable("Not implemented")

        response = tnrcsp_dm.send_xc_creation_rest_req(xc, self.dataModels['clients'])
        logger.debug('XC req response is %s', response.status)
        if response.status in [httplib.CREATED, httplib.ACCEPTED]:
            xcId = tnrcsp_dm.parse_rest_xcId(response)
            logger.info('The xc handle genarated by LICL is %i', xcId)
            expires = self.defaultTimeout
            if response.status == httplib.ACCEPTED:
                xc['status'] = 'Creation'
                expires = tnrcsp_dm.parseExpires(response)
                logger.info('XC creation timeout is %s', str(expires))
            xc['__name__'] = 'crossConnection'
            with self.dataModels['lock']:
                nodeId = self.dataModels['clients']['rest-CCI']['nodeId']
                self.dataModels['data']['node'][nodeId]['crossConnections'][str(xcId)] = xc
            expires = (datetime.datetime.now()-expires).seconds
            return xcId, expires
        else:
            raise TNRC_SP.GenericError("LICL doesn't accepted the request")
            # TODO: analyse and forward proper exception/response to LICL
    
    @tnrcsp_dm.corba_exception_handler 
    def destroy(self, handle, isVirtual, deactivate):
        logger.info('\n\n\t\t\t\t\t\t\t\t\tXC.destroy() called\n')
        logger.info('--> handle %i, isVirtual %d, deactivate %s', handle, str(isVirtual), str(deactivate))

        response = tnrcsp_dm.send_xc_deletion_rest_req(handle, self.dataModels['clients'])
        xcId = handle
        expires = self.defaultTimeout
        logger.debug('XC deletion response is %s', response.status)
        if response.status in [httplib.CREATED, httplib.ACCEPTED]:
            #xcId = tnrcsp_dm.parse_rest_xcId(response)
            expires = tnrcsp_dm.parseExpires(response)
            logger.info('XC deletion timeout is %s', str(expires))
            expires = (datetime.datetime.now()-expires).seconds

        with self.dataModels['lock']:
            nodeId = self.dataModels['clients']['rest-CCI']['nodeId']
            self.dataModels['data']['node'][nodeId]['crossConnections'][str(handle)]['status'] = 'Deletion'

        return expires
        
    def reserve(self, inOutRes, direction, isVirtual, action):
        logger.info('\n\n\t\t\t\t\t\t\t\t\XC.reserve() called\n')
        raise TNRC_SP.NotCapable("Not implemented")

    def unreserve(self, handle, isVirtual):
        logger.info('\n\n\t\t\t\t\t\t\t\t\XC.unreserve() called\n')
        raise TNRC_SP.NotCapable("Not implemented")

    def protect(self, port_xc, label_xc, port_prot, label_prot, direction, isVirtual):
        logger.info('\n\n\t\t\t\t\t\t\t\t\XC.protect() called\n')
        raise TNRC_SP.NotCapable("Not implemented")

    def unprotect(self, handle, isVirtual):
        logger.info('\n\n\t\t\t\t\t\t\t\t\XC.unprotect() called\n')
        raise TNRC_SP.NotCapable("Not implemented")

class tnrcsp_conf (TNRC_SP__POA.Config):
    def __init__(self, dataModels):
        '''contructor method required for access to common data model'''
        self.dataModels = dataModels

    @tnrcsp_dm.corba_exception_handler
    def init(self, max_timeout):
        logger.info('\n\n\t\t\t\t\t\t\t\tConfig.init() called\n')
        logger.info('--> max_timeout %d', max_timeout)
        import thread
        thread.start_new_thread(tnrcsp_dm.configureResources, (self.dataModels,))
        return max_timeout
