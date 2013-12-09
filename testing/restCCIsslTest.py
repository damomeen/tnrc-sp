from wsgiservice.xmlserializer import dumps
from geysers_psnc_utils.restUtils import encode_multipart_formdata

# HTTPlib2 has a bug! -- I have raised an issue to developers
#import httplib2
#h = httplib2.Http('.cache')
#resp, content = h.request("https://localhost:8001", "GET")

BASE_SCHEMA = '/geysers.eu/cci'

import httplib
conn = httplib.HTTPConnection('localhost:8011')

"""
node = BASE_SCHEMA + '/node/n10'
nodeDesc = {'energyConsumption':20, 
            'operativeStatus':'up', 
            'boardID': [2, 4, 6]}
conn.request('PUT', node, dumps(nodeDesc, 'Node'), {'Content-type':'text/xml'})
res = conn.getresponse()
print res.read() 
conn.request('GET', node)
res = conn.getresponse()
print res.read()

nodeStatus = BASE_SCHEMA + '/node/n10/operativeStatus'
conn.request('PUT', nodeStatus, dumps('down', 'operativeStatus'), {'Content-type':'text/xml'})
res = conn.getresponse()
print res.read() 
conn.request('GET', nodeStatus)
res = conn.getresponse()
print res.read()
"""


nodeStatus = BASE_SCHEMA + '/node/1/xc'
content_type, body = encode_multipart_formdata([('security', 'adsdsfasf'), ('data', 'dsafagsaag')], [], 'boundary')
conn.request('POST', nodeStatus, body, {'Content-type':content_type})


