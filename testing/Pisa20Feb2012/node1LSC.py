from genericNode import node, addPort
from copy import deepcopy

node = deepcopy(node)
nodeId = '1'
node['1']['__attributes__']['techParams'] = {
                                                'switchingCapability':'LSC', 
                                                'encodingType':'Fiber',
                                                'parameteresLSC': {
                                                    'channelSpacing':'4',
                                                    'grid':'1',
                                                },
                                            }
# UNI
addPort(board=node['1'], portId='4357', resIds=['1', '20'])
addPort(board=node['1'], portId='4358', resIds=['10', '4'])

# towards Node-2
addPort(board=node['1'], portId='4353', resIds=['1', '2', '3', '4'])
addPort(board=node['1'], portId='4355', resIds=['10', '20', '30', '31', '32'])

# towards Node-3
addPort(board=node['1'], portId='4354', resIds=['1', '2', '3', '4'])
addPort(board=node['1'], portId='4356', resIds=['10', '20', '30', '31', '32'])

if __name__ == "__main__":
    import pprint
    f = file('node1_LSC_overview.txt', 'w')
    f.write(pprint.pformat(node))
    f.close()

    
