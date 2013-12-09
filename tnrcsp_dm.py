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

import httplib
import struct
from functools import wraps
import pprint
import time, thread

import _GlobalIDL as glob
import CORBA
import TNRC_SP
import TNRC_AP
import TNRC
import SecGateway
from geysers_psnc_utils.wsgiservice.xmlserializer import dumps, xml2obj
from geysers_psnc_utils.corbaUtils import corbaClient
from geysers_psnc_utils.restUtils import encode_multipart_mime

import logging
logger = logging.getLogger(__name__)

BASE_SCHEMA = '/cxf/vi-cam/cci'

####################################
### Utils

def corba_exception_handler(f):
    'intercepting all corba calls and checking for exceptions'
    wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (TNRC_SP.EqptLinkDown, TNRC_SP.NotCapable, TNRC_SP.BusyResources, TNRC_SP.GenericError) as e:
            logger.error("Exception:" + str(e))
            raise
        except:
            import traceback
            logger.error("Exception" + traceback.format_exc())
            raise TNRC_SP.InternalError("Exception in TNRC_SP:" + str(traceback.format_exc()))
    return wrapper


def exception_handler(f):
    'intercepting all calls and checking for exceptions'
    wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            import traceback
            logger.error("Exception" + traceback.format_exc())
    return wrapper

####################################
### Rest messages

def send_rest_req(method, uri, body, config):
    configCCI = config.get('rest-CCI')
    configAAI = config.get('AaiAuthentication')
    authNToken = ''
    if configCCI == None:
        raise Exception('Could not find information about LICL-CCI server in configuration file')
    if configAAI:
        authNToken = authenticate(configAAI)

    remote_sock = '%(address)s:%(port)i' % configCCI
    if body:
        body = dumps(body)
    else:
        body = ''
    logger.info('\n\n\n Sending HTTP %s request through CCI interface to %s%s\n', method, remote_sock, uri)
    try:
        if configCCI.get('ssl') is True:
            httpObj = httplib.HTTPSConnection
        else:
            httpObj = httplib.HTTPConnection
        conn = httpObj(remote_sock, timeout=configCCI.get('timeout'))
        content_type, body = encode_multipart_mime([('token', 'text/plain', authNToken), 
                                                    ('content', 'application/xml', body)], 'boundary')
        conn.request(method, uri, body, {'Content-type':content_type, 'Accept':'application/xml'})
        logger.info('HTTP request send with body:\n %s \n', body)
    except:
        logger.error('Could not connect to LICL CCI interface server %s', str(configCCI))
        raise TNRC_SP.EqptLinkDown('Could not connect to LICL CCI interface server %s' % str(configCCI))
    res = conn.getresponse()
    xml = res.read()
    logger.info('Response received in CCI interface: HTTP %s %s with headers %s', res.status, res.reason, res.msg, str(res.getheaders()))
    if len(xml) > 0:
        #logger.info('Response XML is %s', xml)
        res.body = xml2obj(xml)
        logger.info('Response (obj) is:\n %s \n', pprint.pformat(res.body))
    else:
        res.body = {}
    return res 

def send_xc_creation_rest_req(xc, config):
    #from restInterfaceCCI import BASE_SCHEMA
    nodeID = config['rest-CCI']['nodeId']
    uri = "%s/xc-configuration/node/%s/crossConnection" % (BASE_SCHEMA, nodeID)
    return send_rest_req('POST', uri, xc, config)

def send_xc_deletion_rest_req(handle, config):
    #from restInterfaceCCI import BASE_SCHEMA
    nodeID = config['rest-CCI']['nodeId']
    uri = "%s/xc-configuration/node/%s/crossConnection/%i" % (BASE_SCHEMA, nodeID, handle)
    return send_rest_req('PUT', uri, {}, config)

def getHTTPHeaderValue(message, headerName):
    values = [value for header, value in message.getheaders() if header == headerName]
    if len(values) == 0:
        raise Exception('Lack of %s header in HTTP message' % headerName)
    return values[0]

def parse_rest_xcId(response):
    location = getHTTPHeaderValue(response, 'location')
    return int(location.split('/')[-1])

def parseExpires(response):
    expires = getHTTPHeaderValue(response, 'expires')
    import datetime
    return datetime.datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT")


####################################
### Corba Presence client

def XsdPeriod2Seconds(periodXsd):
    import re
    regex = re.compile('PT(?:(?P<hours>\d+)S)?(?:(?P<minutes>\d+)S)?(?:(?P<seconds>\d+)S)')
    period = regex.match(periodXsd).groupdict(0)
    return ((int(period['hours'])*60)+int(period['minutes']))*60+int(period['seconds'])

def registerInTnrcAP(dataModels, tnrcspXCServer, tnrcspConfigServer):
    time.sleep(10)
    thread.start_new_thread(_registerInTnrcAP, (dataModels, tnrcspXCServer, tnrcspConfigServer))

def _registerInTnrcAP(dataModels, tnrcspXCServer, tnrcspConfigServer):
    try:
        get_cci_node(dataModels, dataModels['clients'], onlyNode=True)
    except:
        import traceback
        logger.error("Exception" + traceback.format_exc())

    maxConfigTime = 0
    for nodeId, node in dataModels['data']['node'].items():
        attributes = node.get('__attributes__')
        if attributes:
            maxConfigTime = attributes.get('maxConfigTime', 'PT0S')
            maxConfigTime = XsdPeriod2Seconds(maxConfigTime)
            with dataModels['lock']:
                node['__attributes__']['_maxConfigTime'] = maxConfigTime

    logger.info("Registering to TNRC-AP")
    presenceRef = corbaClient(TNRC_AP.Presence, iorFile=dataModels['clients']['tnrcapPresence']['iorName'])
    logger.debug('tnrcspConfigServer %s', tnrcspConfigServer)
    presenceRef.register('TNRC-LICL-Adapter', maxConfigTime,
                         tnrcspConfigServer, tnrcspXCServer)
    logger.info("Registered in TNRC-AP succesfully")

def unregisterInTnrcAP(dataModels):
    logger.info("Unregistering from TNRC-AP")
    presenceRef = corbaClient(TNRC_AP.Presence, iorFile=dataModels['clients']['tnrcapPresence']['iorName'])
    presenceRef.unregister('TNRC-LICL-Adapter')
    logger.info("Unregistered in TNRC-AP succesfully")

####################################
### Corba Resource configuration clients

def str2ieee754(floatString):
    packed = struct.pack('f', float(floatString))
    return struct.unpack('I', packed)[0]

def parse_corba_direction(direction):
    if direction == glob.gmplsTypes.XCDIR_BIDIRECTIONAL:
        return 'Bidirectional'
    elif direction == glob.gmplsTypes.XCDIR_UNIDIRECTIONAL:
        return 'Unidirectional'
    else:
        return 'XCDIR_BCAST'

def operStatus_str2corba(operStatus):
    if operStatus == 'up':
        return glob.gmplsTypes.OPERSTATE_UP
    else:
        return glob.gmplsTypes.OPERSTATE_DOWN

def adminStatus_str2corba(adminStatus):
    if adminStatus == 'enabled':
        return glob.gmplsTypes.ADMINSTATE_ENABLED
    else:
        return glob.gmplsTypes.ADMINSTATE_DISABLED

def switchCap_str2corba(switchCap):
    switchCaps = {
        'PSC':        glob.gmplsTypes.SWITCHINGCAP_PSC_1,
        'PSC-1':      glob.gmplsTypes.SWITCHINGCAP_PSC_1,
        'PSC-2':      glob.gmplsTypes.SWITCHINGCAP_PSC_2,
        'PSC-3':      glob.gmplsTypes.SWITCHINGCAP_PSC_3,
        'PSC-4':      glob.gmplsTypes.SWITCHINGCAP_PSC_4,
        'EVPL' :      glob.gmplsTypes.SWITCHINGCAP_EVPL,
        '802.1 PBBTE':glob.gmplsTypes.SWITCHINGCAP_8021_PBBTE,
        'L2SC':       glob.gmplsTypes.SWITCHINGCAP_L2SC,
        'TDM':        glob.gmplsTypes.SWITCHINGCAP_TDM,
        'DCSC':       glob.gmplsTypes.SWITCHINGCAP_DCSC,
        'OBSC':       glob.gmplsTypes.SWITCHINGCAP_OBSC,
        'LSC':        glob.gmplsTypes.SWITCHINGCAP_LSC,
        'FSC':        glob.gmplsTypes.SWITCHINGCAP_FSC,
    }
    return switchCaps.get(switchCap, glob.gmplsTypes.SWITCHINGCAP_UNKNOWN)

def encType_str2corba(encType):
    encTypes = {
         'Packet':           glob.gmplsTypes.ENCODINGTYPE_PACKET,
         'Ethernet':         glob.gmplsTypes.ENCODINGTYPE_ETHERNET,
         'ANSI ETSI PDH':    glob.gmplsTypes.ENCODINGTYPE_ANSI_ETSI_PDH,
         'Reserved 1':       glob.gmplsTypes.ENCODINGTYPE_RESERVED_1,
         'SDH/SONET':        glob.gmplsTypes.ENCODINGTYPE_SDH_SONET,
         'Reserved 2':       glob.gmplsTypes.ENCODINGTYPE_RESERVED_2,
         'Digital wrapper':  glob.gmplsTypes.ENCODINGTYPE_DIGITAL_WRAPPER,
         'Lambda':           glob.gmplsTypes.ENCODINGTYPE_LAMBDA,
         'Fiber':            glob.gmplsTypes.ENCODINGTYPE_FIBER,
         'Reserved 3':       glob.gmplsTypes.ENCODINGTYPE_RESERVED_3,
         'Fiber channel':    glob.gmplsTypes.ENCODINGTYPE_FIBERCHANNEL,
         'G.709 ODU':        glob.gmplsTypes.ENCODINGTYPE_G709_ODU,
         'G.709 OC':         glob.gmplsTypes.ENCODINGTYPE_G709_OC,
         'Line 8B10B':       glob.gmplsTypes.ENCODINGTYPE_LINE_8B10B,
         'TSON fixed':       glob.gmplsTypes.ENCODINGTYPE_TSON_FIXED,
    }
    return encTypes.get(encType, glob.gmplsTypes.ENCODINGTYPE_UNKNOWN)

def protectionType_str2corba(protectionType):
    protectionTypes = {
        'None':           glob.gmplsTypes.PROTTYPE_NONE,
        'Extra Traffic':  glob.gmplsTypes.PROTTYPE_EXTRA,
        'Unprotected':    glob.gmplsTypes.PROTTYPE_UNPROTECTED,
        'Shared':         glob.gmplsTypes.PROTTYPE_SHARED, 
        'Dedicated 1:1':  glob.gmplsTypes.PROTTYPE_DEDICATED_1TO1, 
        'Dedicated 1+1':  glob.gmplsTypes.PROTTYPE_DEDICATED_1PLUS1,
        'enhanced':       glob.gmplsTypes.PROTTYPE_ENHANCED,
    }
    return protectionTypes.get(protectionType, glob.gmplsTypes.PROTTYPE_NONE)

def usageStatus_str2corba(usageState):
    usageStatus = {
        'Undefined':     glob.gmplsTypes.LABELSTATE_FREE,
        'Free':          glob.gmplsTypes.LABELSTATE_FREE,
        'Booked':        glob.gmplsTypes.LABELSTATE_BOOKED,
        'XConnected':    glob.gmplsTypes.LABELSTATE_XCONNECTED,
        'Busy':          glob.gmplsTypes.LABELSTATE_BUSY,
    }
    return usageStatus.get(usageState, glob.gmplsTypes.LABELSTATE_BUSY)

def otaniLabel(grid, channelSpacing, channelID):
    'coding channel basing on otani-draft'
    def twos_comp16(val):
        a = struct.pack('h', val)
        return struct.unpack('H', a)[0]

    if grid in ('1', '2'):
        firstByte = (int(grid)<<5) | (int(channelSpacing)<<1)
        value = firstByte<<24 | twos_comp16(int(channelID))
    else:
        value = 0
    logger.debug("\t\t Otani label is %s (grid:%s, channelSpacing:%s, channelId:%s)", hex(value), grid, channelSpacing, channelID)
    return value

def label2channel(label):
    def two_comp16(val):
        return struct.unpack('h', struct.pack('H', val))[0]
    return two_comp16(label&0xFFFF)

def portIdentifier(nodeId, boardId, portId):
    return (int(nodeId)<<26) + (int(boardId)<<16) + int(portId)
       
def configureResources(dataModels):
    try:
        logger.info('configureResources')
        get_cci_node(dataModels, dataModels['clients'])
        pushResourcetoAP(dataModels, dataModels['clients']['tnrcapConfig'])
    except:
        import traceback
        logger.error(traceback.format_exc())

def getMostSuitablePowerConsumption(powerConsumptionInfo):
    priorityList = ['currentPowerConsumption', 'averagePowerConsumption', 'maxPowerConsumption', 'idlePowerConsumption']
    value = None
    for item in priorityList:
        if value is None:
            value = powerConsumptionInfo.get(item)
    if value:
       if powerConsumptionInfo.get('unit') == 'kW':
            value += '000'
       if powerConsumptionInfo.get('unit') == 'MW':
            value += '000000' 
    return value
        

@exception_handler
def pushResourcetoAP(dataModel, config):
    logger.info("Starting pushing resource info to TNRC-AP")

    import pprint
    logger.info('\n' + pprint.pformat(dataModel['data']['node']))
    ConfigRef = corbaClient(TNRC_AP.Config, iorFile=config['iorName'])

    NODE_ID = '1'
    with dataModel['lock']:
        for nodeId, node in dataModel['data']['node'].items():
            if '__attributes__' not in node:
                continue
            attributes = node['__attributes__']
            operStatus = attributes.get('operationalStatus', 'up')
            ConfigRef.addEqpt(struct.pack('B', int(NODE_ID)),
                              glob.gmplsTypes.linkId(ipv4=0), 
                              TNRC.EQUIPMENT_VIRTUAL_NODE, 
                              operStatus_str2corba(operStatus), 
                              glob.gmplsTypes.ADMINSTATE_ENABLED, 
                              "")
            if 'powerConsumption' in attributes:
                ConfigRef.setEqptPowerConsumption(struct.pack('B', int(NODE_ID)), 
                                                  str2ieee754(getMostSuitablePowerConsumption(attributes['powerConsumption'])))
            
            for boardId in attributes.get('boardID', []):
                if boardId not in node:
                    raise Exception("Database is not consistent - board object is declared but its content is missing ")
                board            = node[boardId]
                board_attributes = attributes = board['__attributes__']
                operStatus       = attributes.get('operationalStatus', 'up')
                adminStatus      = attributes.get('adminStatus', 'enabled')
                switchingCapability, encodingType, techParams = 'Unknown', 'Unknown', []
                if 'techParams' in attributes:
                    techParams          = attributes.get('techParams')
                    switchingCapability = techParams.get('switchingCapability')
                    encodingType        = techParams.get('encodingType')

                ConfigRef.addBoard(struct.pack('B', int(NODE_ID)),
                                   int(boardId), 
                                   switchCap_str2corba(switchingCapability),
                                   encType_str2corba(encodingType), 
                                   operStatus_str2corba(operStatus),
                                   adminStatus_str2corba(adminStatus))

            
                for portIdIn in attributes.get('portID', []):
                    if 'out' in portIdIn: # skip outbound port ids
                        continue
                    if portIdIn not in board:
                        raise Exception("Database is not consistent - port object is declared but its content is missing ")
                    port       = board[portIdIn]
                    portId     = portIdIn.replace('in', '')    # port id of pack of inbound and outbound ports
                    portIdOut  = 'out' + portId   # Outbound port id
                    attributes = port['__attributes__']
                    resources  = attributes.get('resourceID', [])
                    resources = [int(resId) for resId in resources]
                    resources.sort() # if not ordered already
                    operStatus     = attributes.get('operationalStatus', 'up')
                    adminStatus    = attributes.get('adminStatus', 'enabled')
                    maxBw          = attributes.get('maxResvBw', '0')
                    protectionType = attributes.get('protectionType', 'Unprotected')

                    if portIdOut in board:
                        # modify statuses if 'bad' outbound statuses
                        outAttr    = board[portIdOut]['__attributes__']
                        if outAttr.get('operationalStatus') == 'down':
                            operStatus = 'down'
                        if outAttr.get('adminStatus') == 'disabled':
                            operStatus = 'disabled'
                    
                    lambdaBase, lambdaCount = 0, 0

                    # if technology is LSC
                    #logger.debug("%s %s %s", switchingCapability, techParams, len(resources))
                    if switchingCapability == 'LSC' and 'parametersLSC' in techParams and len(resources) > 0:
                        grid           = techParams['parametersLSC'].get('gridLSC', '1')
                        channelSpacing = techParams['parametersLSC'].get('channelSpacingLSC', '1')
                        if len(resources) > 0:
                            lambdaBase     = otaniLabel(grid, channelSpacing, 20) #resources[0])
                            lambdaCount    = 40  # value hardcoded instead of int(resources[-1]) - int(resources[0]) + 1


                    logger.debug('Config::addPort for %s.%s.%s', nodeId, boardId, portId)
                    logger.debug('\t\t Port bandwidth is %s', int(float(maxBw)/1e6))
                    logger.debug('\t\t Lambda base is 0x%x, count is %s', lambdaBase, lambdaCount)
 
                    ConfigRef.addPort(struct.pack('B', int(NODE_ID)),            # equipId
                                      int(boardId),                             # boardId
                                      int(portId),                              # portId
                                      glob.gmplsTypes.linkId(ipv4=0),           # remEqAddr
                                      0,                                        # remPortId
                                      operStatus_str2corba(operStatus),         # opSt
                                      adminStatus_str2corba(adminStatus),       # admSt
                                      lambdaBase,                               # lambdaBase
                                      lambdaCount,                              # lambdaCount
                                      int(float(maxBw)/1e6),                    # bw
                                      [],                                       # subwavInfo
                                      protectionType_str2corba(protectionType)) # prot

                    if 'powerConsumption' in attributes:
                        ConfigRef.setPortPowerConsumption(struct.pack('B', int(NODE_ID)), 
                                                          int(boardId), 
                                                          int(portId), 
                                                          str2ieee754(getMostSuitablePowerConsumption(attributes['powerConsumption'])))

                    attributes['maxBwUpgrade'] = '1.0E8'  # temporary fix to have replaning attributes
                    attributes['maxBwDowngrade'] = '1.0E8'
                    if 'maxBwUpgrade' in attributes or 'maxBwDowngrade' in attributes:
                        ConfigRef.setPortBwReplanning(struct.pack('B', int(NODE_ID)),
                                                      int(boardId), 
                                                      int(portId), 
                                                      glob.gmplsTypes.vlinkBwReplanInfo(str2ieee754(attributes.get('maxBwUpgrade', '0')),
                                                                                        str2ieee754(attributes.get('maxBwDowngrade', '0'))))

                    for resId in attributes.get('resourceID', []):
                        if resId not in port:
                            raise Exception("Database is not consistent - res object is declared but its content is missing ")
                        res         = port[resId]
                        attributes  = res['__attributes__']
                        label       = int(resId)
                        operStatus  = attributes.get('operationalStatus', 'up')
                        adminStatus = attributes.get('adminStatus', 'enabled')
                        usageStatus = attributes.get('usageStatus', 'Undefined')
                	if switchingCapability == 'FSC':
                	    break
                        if switchingCapability == 'LSC' and 'parametersLSC' in techParams:
                            label   = otaniLabel(grid, channelSpacing, resId)
                            attributes['parameteresLSC'] = {'gridLSC': grid, 'channelSpacingLSC':channelSpacing}
		            try:
                                out_attr = board[portId][resId]['__attributes__']
				out_attr['parameteresLSC'] = {'gridLSC': grid, 'channelSpacingLSC':channelSpacing}
			    except:
				import traceback
                                logger.error(traceback.format_exc())

                        logger.debug('Config::addResource for %s.%s.%s.%s with:', nodeId, boardId, portId, resId)
                        logger.debug('\t\t label: 0x%x, operStatus: %s, adminStatus: %s, usageStatus: %s', label, operStatus, adminStatus, usageStatus)
                        ConfigRef.addResource(struct.pack('B', int(NODE_ID)),
                                              int(boardId),
                                              int(portId),
                                              glob.gmplsTypes.labelId(label32=label),
                                              operStatus_str2corba(operStatus),
                                              adminStatus_str2corba(adminStatus),
                                              usageStatus_str2corba(usageStatus))

    #logger.info(pprint.pformat(dataModel['data']['node']))

####################################
### Rest Resource configuration clients

def get_cci_node(dataModel, config, onlyNode=False):
    #from restInterfaceCCI import BASE_SCHEMA
    nodeID = config['rest-CCI']['nodeId']
    uri = "%s/node-synchronization/node/%s" % (BASE_SCHEMA, str(nodeID))
    res = send_rest_req('POST', uri, {}, config)
    if res.status is not httplib.OK:
        logger.debug('Response is %s', res.status)
        return
    
    node = res.body.get('node', {})
    if not isinstance(node['boardID'], list):
        node['boardID'] = [node['boardID']]
    with dataModel['lock']:
        dataModel['data']['node'][str(nodeID)]['__attributes__'] = node
    
    if onlyNode == True:
        return

    for boardId in node.get("boardID", []):
        get_cci_board(dataModel['data']['node'][str(nodeID)], dataModel['lock'], boardId, uri, config)

def get_cci_board(data, lock, boardId, uri, config):
    if not isinstance(boardId, str):
        logger.error("Bad boardId type %s", type(boardId))
    uri = '%s/board/%s' %(uri, boardId) 
    res = send_rest_req('POST', uri, {}, config)
    if res.status is not httplib.OK:
        return
    board = res.body.get('board', {})
    if not isinstance(board['portID'], list):
        board['portID'] = [board['portID']]
    board['portID'] = list(set(board['portID'])) # remove duplicated ports
    with lock:
        data[boardId] = {'__name__':'board', '__attributes__': board}

    for portId in board.get("portID", []):  
        get_cci_port(data[boardId], lock, portId, uri, config)

    
def get_cci_port(data, lock, portId, uri, config):
    if not isinstance(portId, str):
        logger.error("Bad portId type %s", type(portId))
    uri = '%s/port/%s' %(uri, portId) 
    res = send_rest_req('POST', uri, {}, config)
    if res.status is not httplib.OK:
        return     
    port = res.body.get('port', {})
    if not isinstance(port['resourceID'], list):
        port['resourceID'] = [port['resourceID']]
    port['resourceID'] = list(set(port['resourceID'])) # remove duplicated boards
    with lock:
        data[portId] = {'__name__':'port', '__attributes__': port}
    for resId in port.get("resourceID", []):
        get_cci_resource(data[portId], lock, resId, uri, config)


def get_cci_resource(data, lock, resId, uri, config):
    if not isinstance(resId, str):
        logger.error("Bad resourceId type %s", type(resId))
    uri = '%s/resource/%s' %(uri, resId) 
    res = send_rest_req('POST', uri, {}, config)
    if res.status is not httplib.OK:
        return   
    resource = res.body.get('resource', {})
    with lock:
        data[resId] = {'__name__':'resource', '__attributes__': resource}

####################################
### Corba Notification clients

def send_corba_xc_notification(xcId, xcStatus, failureReason, config):
    if xcStatus in ('Working', 'Deleted'):    
        result = TNRC.XC_RESULT_SUCCESS
        error = TNRC.XC_ERROR_NONE
    else:
        result = TNRC.XC_RESULT_FAILURE
        reasons = {
            "Virtual Node Down": TNRC.XC_ERROR_EQPTLINKDOWN,
            "Param Err":         TNRC.XC_ERROR_PARAMERROR,
            "Not Capable":       TNRC.XC_ERROR_NOTCAPABLE,
            "Busy Resource":     TNRC.XC_ERROR_BUSYRESOURCES,
            "Generic Error":     TNRC.XC_ERROR_GENERICERROR,
        }
        error = reasons.get(failureReason, TNRC.XC_ERROR_INTERNALERROR)
          
    logger.info('Sending corba notification to tnrc-ap for xc %i with result %s and error %s', int(xcId), str(result), str(error))
    try:
        TNRCSPNotifyRef = corbaClient(TNRC_AP.Notifications, iorFile=config['iorName'])        
        TNRCSPNotifyRef.xcResult(int(xcId), result, error, [])
    except CORBA.TRANSIENT:
        logger.error('Could not connect to TNRC-AP Notification servant')
    
def send_node_notification(nodeId, config, attributes):
    logger.debug('Sending node notification %s, %s, %s', nodeId, config, attributes)
    if 'powerConsumption' in attributes:
        power = getMostSuitablePowerConsumption(attributes['powerConsumption'])
        if power:
            power = str2ieee754(power)
            notification = TNRC.notificationDetails(nodeUpd = TNRC.nodeUpdateInfo(nodeId=struct.pack('B', 1),
                                                                              updParms=TNRC.nodeUpdateParms(powerCons=power)))
            send_corba_notification(config, [notification])

def send_port_notification(nodeId, boardId, portId, config, attributes, allAttributes):
    logger.debug('Sending port notification %s, %s, %s, %s, %s', nodeId, boardId, portId, config, attributes)
    portId = portId.replace('in', '').replace('out', '')
    notifications = []
    if 'operationalStatus' in attributes:
        notifications.append(TNRC.notificationDetails(alarm = TNRC.alarmInfo(portId   = portIdentifier('1', boardId, portId),
                                                                             lblId    = glob.gmplsTypes.labelId(label32=1),
                                                                             event    = operStatus_str2corba(attributes['operationalStatus']))))
    if 'powerConsumption' in attributes:
        power = getMostSuitablePowerConsumption(attributes['powerConsumption'])
        if power:                                                                         
            power = str2ieee754(power)
            notifications.append(TNRC.notificationDetails(portUpd = TNRC.portUpdateInfo(portId   = portIdentifier('1', boardId, portId),
                                                                                        updParms = TNRC.portUpdateParms(powerCons=power))))
    if 'maxBwUpgrade' in attributes or 'maxBwUpgrade' in attributes:
        maxBw          = float(allAttributes.get('maxBw', 0.0))/1e6
        maxBwUpgrade   = str2ieee754(allAttributes.get('maxBwUpgrade', maxBw))
        maxBwDowngrade = str2ieee754(allAttributes.get('maxBwDowngrade', maxBw))
        bandwidthInfo  = glob.gmplsTypes.vlinkBwReplanInfo(maxBwUpgrade = maxBwUpgrade, maxBwDowngrade = maxBwDowngrade)
        notifications.append(TNRC.notificationDetails(portUpd = TNRC.portUpdateInfo(portId   = portIdentifier('1', boardId, portId),
                                                                                    updParms = TNRC.portUpdateParms(bwInfo=bandwidthInfo))))
    send_corba_notification(config, notifications)


def send_resource_notification(nodeId, boardId, portId, resId, config, attributes, allAttributes):
    logger.debug('Sending resource notification %s, %s, %s, %s, %s, %s, %s', nodeId, boardId, portId, resId, config, attributes, allAttributes)
    portId = portId.replace('in', '').replace('out', '')
    notifications = []
    if 'operationalStatus' in attributes:
        label       = int(resId)
        operStatus  = attributes.get('operationalStatus', 'up')
        adminStatus = attributes.get('adminStatus', 'enabled')
        if'parametersLSC' in allAttributes:
            grid           = allAttributes['parametersLSC'].get('gridLSC', '1')
            channelSpacing = allAttributes['parametersLSC'].get('channelSpacingLSC', '4')
            label          = otaniLabel(grid, channelSpacing, resId)
            logger.debug("Label used is %s", hex(label))
        notifications.append(TNRC.notificationDetails(alarm = TNRC.alarmInfo(portId   = portIdentifier('1', boardId, portId),
                                                                             lblId    = glob.gmplsTypes.labelId(label32=label),
                                                                             event    = operStatus_str2corba(operStatus))))
    send_corba_notification(config, notifications)

def send_corba_notification(config, notifications):
    logger.info('Sending corba notification to tnrc-ap')
    try:
        tnrcspNotifyRef = corbaClient(TNRC_AP.Notifications, iorFile=config['iorName'])     
        tnrcspNotifyRef.asyncNotification(notifications)
        logger.debug('Notification sent to TNRC-AP %s', notifications)
    except CORBA.TRANSIENT:
        logger.error('Could not connect to TNRC-AP Notification servant')


def addResource(nodeId, boardId, portId, resId, config, attributes, techParams):
    NODE_ID = '1'
    label       = int(resId)
    operStatus  = attributes.get('operationalStatus', 'up')
    adminStatus = attributes.get('adminStatus', 'enabled')
    usageStatus = attributes.get('usageStatus', 'Undefined')
    if techParams['switchingCapability'] == 'FSC':
        return
    if techParams['switchingCapability'] == 'LSC' and 'parametersLSC' in techParams:
        grid = techParams['parametersLSC']['gridLSC']
        channelSpacing = techParams['parametersLSC']['channelSpacingLSC']
        label   = otaniLabel(grid, channelSpacing, resId)
        attributes['parametersLSC'] = {'gridLSC': grid, 'channelSpacingLSC':channelSpacing}

    logger.debug('Config::addResource for %s.%s.%s.%s with:', nodeId, boardId, portId, resId)
    logger.debug('\t\t label: 0x%x, operStatus: %s, adminStatus: %s, usageStatus: %s', label, operStatus, adminStatus, usageStatus)

    try:
        configRef = corbaClient(TNRC_AP.Config, iorFile=config['iorName'])
        configRef.addResource(struct.pack('B', int(NODE_ID)),
                                              int(boardId),
                                              int(portId),
                                              glob.gmplsTypes.labelId(label32=label),
                                              operStatus_str2corba(operStatus),
                                              adminStatus_str2corba(adminStatus),
                                              usageStatus_str2corba(usageStatus))
        logger.debug('Request sent to TNRC-AP')
    except CORBA.TRANSIENT:
        logger.error('Could not connect to TNRC-AP Config servant')


                                             
def removeResource(nodeId, boardId, portId, resId, config, techParams):
    NODE_ID = '1'
    label       = int(resId)
    if techParams['switchingCapability'] == 'LSC' and 'parametersLSC' in techParams:
        grid = techParams['parametersLSC']['gridLSC']
        channelSpacing = techParams['parametersLSC']['channelSpacingLSC']
        label   = otaniLabel(grid, channelSpacing, resId)

    logger.debug('Config::removeResource for %s.%s.%s.%s', nodeId, boardId, portId, resId)
    logger.debug('\t\t label: 0x%x', label)

    try:
        configRef = corbaClient(TNRC_AP.Config, iorFile=config['iorName'])
        configRef.removeResource(struct.pack('B', int(NODE_ID)),
                                              int(boardId),
                                              int(portId),
                                              glob.gmplsTypes.labelId(label32=label))
        logger.debug('Request sent to TNRC-AP')
    except CORBA.TRANSIENT:
        logger.error('Could not connect to TNRC-AP Config servant')


####################################
### Corba security

def authenticate(config):
    logger.info('Authenticate in AAI')
    try:
        aaiRef = corbaClient(SecGateway.AaiServer, iorFile=config['iorName'])
        authNtoken = aaiRef.authenticate(config['user'], config['passwd'])
        logger.debug('AAI authentication authNtoken is', authNtoken)
        return authNtoken
    except CORBA.TRANSIENT:          
        logger.error('Could not connect to AAI server %s', str(config))

