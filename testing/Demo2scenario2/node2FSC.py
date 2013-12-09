import sys, os

sys.path.append(os.getcwd()+"/../")
from genericNode import node, addPort
del sys.path[-1]

from copy import deepcopy

node = deepcopy(node)
nodeId = '2'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'FSC', 
                                                'encodingType':'Fiber',
                                            }

# UNI
addPort(board=node['1'], portId='5', resIds=['1'])

# towards Node-1
addPort(board=node['1'], portId='3', resIds=['1'])

# towards Node-3
addPort(board=node['1'], portId='1', resIds=['1'])

# towards Node-4
addPort(board=node['1'], portId='2', resIds=['1'])

if __name__ == "__main__":
    import pprint
    f = file('node1_FSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
