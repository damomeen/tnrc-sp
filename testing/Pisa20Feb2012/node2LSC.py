from genericNode import node, addPort
from copy import deepcopy

node = deepcopy(node)
nodeId = '2'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'LSC', 
                                                'encodingType':'Fiber',
                                                'parameteresLSC': {
                                                    'channelSpacing':'4',
                                                    'grid':'1',
                                                },
                                            }

# towards Node-1
addPort(board=node['1'], portId='2', resIds=['1', '2', '3', '4'])
addPort(board=node['1'], portId='4', resIds=['10', '20', '30', '31', '32'])

# towards Node-3
addPort(board=node['1'], portId='1', resIds=['1', '2', '3', '4'])
addPort(board=node['1'], portId='3', resIds=['10', '20', '30', '31', '32'])

if __name__ == "__main__":
    import pprint
    f = file('node2_LSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
