from genericNode import node, addPort
from copy import deepcopy

node = deepcopy(node)
nodeId = '2'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'FSC', 
                                                'encodingType':'Fiber',
                                            }

# towards Node-1
addPort(node['1'], portId='2', resIds=['1'])
addPort(node['1'], portId='4', resIds=['1'])

# towards Node-3
addPort(node['1'], portId='1', resIds=['1'])
addPort(node['1'], portId='3', resIds=['1'])

if __name__ == "__main__":
    import pprint
    f = file('node2_FSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
