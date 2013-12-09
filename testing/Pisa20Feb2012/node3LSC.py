from genericNode import node, addPort
from copy import deepcopy

node = deepcopy(node)
nodeId = '3'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'LSC', 
                                                'encodingType':'Fiber',
                                                'parameteresLSC': {
                                                    'channelSpacing':'4',
                                                    'grid':'1',
                                                },
                                            }
# UNI
addPort(board=node['1'], portId='5', resIds=['1'])
addPort(board=node['1'], portId='6', resIds=['10'])

# towards Node-1
addPort(board=node['1'], portId='1', resIds=['10', '20', '30', '31', '32'])
addPort(board=node['1'], portId='3', resIds=['1', '2', '3', '4'])

# towards Node-2
addPort(board=node['1'], portId='2', resIds=['1', '2', '3', '4'])
addPort(board=node['1'], portId='4', resIds=['10', '20', '30', '31', '32'])

if __name__ == "__main__":
    import pprint
    f = file('node3_LSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
