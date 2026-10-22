"""Rounded transverse trigger grooves, retaining the stock and travel frame."""
import copy


def add_trigger_grooves(nodes):
    original = copy.deepcopy(nodes['trigger'])
    previous = 'trigger_stock'
    for index, z in enumerate((121.5, 124.5, 127.5)):
        name = 'trigger' if index == 2 else 'trigger_groove_' + str(index)
        nodes[name] = {
            'kind': 'cut_box', 'visible': index == 2,
            'deps': [{'id': previous, 'use': 'geometry'}],
            'args': {'dimensions': [1, 12, .8], 'center': [11.25, 0, z], 'radius': .15},
            'frame': copy.deepcopy(original['frame']),
            'material': copy.deepcopy(original['material']),
        }
        previous = name
