from genericNode import node, addPort
from copy import deepcopy

node = deepcopy(node)
nodeId = '3'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'FSC', 
                                                'encodingType':'Fiber',
                                            }
# UNI
addPort(node['1'], portId='5', resIds=['1'])
addPort(node['1'], portId='6', resIds=['1'])

# towards Node-1
addPort(node['1'], portId='1', resIds=['1'])
addPort(node['1'], portId='3', resIds=['1'])

# towards Node-2
addPort(node['1'], portId='2', resIds=['1'])
addPort(node['1'], portId='4', resIds=['1'])

if __name__ == "__main__":
    import pprint
    f = file('node3_LSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
