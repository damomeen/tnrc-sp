node = {
    '__name__':'node',
    '__attributes__': {
        'powerConsumption': {
            'maxPowerConsumption': 30.0,
            'currentPowerConsumption': 25.5,
            'averagePowerConsumption': 27.2,
            'idlePowerConsumption': 12.8,
            'unit':'W',
        },
        'operationalStatus': 'up',
        'maxConfigTime': 'PT30S',
        'boardID': ['1'],
    },
    'crossConnections':{},
    '1': {
        '__name__': 'board',
        '__attributes__': {
            'techParams': {
            },
            'adminStatus': 'enabled',
            'operationalStatus': 'up',
            'portID': [],
        },
    },
} 
    

def addPort(board, portId, resIds):
    board['__attributes__']['portID'].append('in'+portId)
    board['__attributes__']['portID'].append('out'+portId)
    for portDir in ['in'+portId, 'out'+portId]:
        board[portDir] = {  '__name__': 'port',
                            '__attributes__': {
                                'adminStatus': 'enabled',
                                'operationalStatus': 'up',
                                'protectionType': 'Unprotected',
                                'maxBw': 1000000000.0,
                                'maxResvBw': 1000000000.0,
                                'bwMinChunck': 10.0,
                                'powerConsumption': {
                                    'maxPowerConsumption': 10.0,
                                    'currentPowerConsumption': 5.5,
                                    'averagePowerConsumption': 7.2,
                                    'idlePowerConsumption': 2.8,
                                    'unit':'W',
                                },
                                'maxBwUpgrade':2000000000.0,
                                'maxBwDowngrade':800000000.0,
                                'directionality': 'Inbound' if 'in' in portDir else 'Outbound',
                                'resourceID':[]
                            }
                        }
        for resId in resIds:
            board[portDir]['__attributes__']['resourceID'].append(resId)
            board[portDir][resId] = {   '__name__': 'resource',
                                        'operationalStatus':'up',
                                        'adminStatus':'enabled',
                                        'usageStatus':'Free'
                                     }
