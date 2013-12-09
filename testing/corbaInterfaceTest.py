import sys, os, time
sys.path.append(os.getcwd()+"/../") # add directory with corba stub to python modules path
import TNRC
import TNRC_SP
import _GlobalIDL as glob
from tnrcsp_dm import portIdentifier
del sys.path[-1]

from geysers_psnc_utils.corbaUtils import corbaClient as corbaClient

def test_config():
    tnrcspConfig_ref = corbaClient(TNRC_SP.Config, iorFile='/tmp/tnrcsp_conf.ior')
    tnrcspConfig_ref.init(10)

#tnrcspxc_ref = corbaClient(TNRC_SP.XC, iorFile='/tmp/tnrcsp_xc.ior')
tnrcspxc_ref = corbaClient(TNRC_SP.XC, iorFile='/opt/gmpls_ctrl_edge/var/gmpls/tnrcsp_xc.ior')


def test_XC_make():
    src_endpoint = TNRC.xcEndPoints(
                            resIn    = TNRC.xcResource(portId=portIdentifier(3, 2, 8), lblId=glob.gmplsTypes.labelId(label32=0x22000038)),
                            resOut   = TNRC.xcResource(portId=portIdentifier(3, 2, 14), lblId=glob.gmplsTypes.labelId(label32=0x22000038)))
                         
    return tnrcspxc_ref.make(0, [src_endpoint,],
                            glob.gmplsTypes.XCDIR_BIDIRECTIONAL,
                            True,
                            False, 
                            TNRC.XC_ACTION_ACTIVATE)

def test_XC_destroy(xcId):                         
    return tnrcspxc_ref.destroy(int(xcId),
                            True,
                            False)

#test_config()
#time.sleep(1)
xcId, timeout = test_XC_make()
print xcId, timeout
time.sleep(30)
print 'destroy timeout', test_XC_destroy(xcId)
