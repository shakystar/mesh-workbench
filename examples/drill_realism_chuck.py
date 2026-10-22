"""Procedural chuck nose support and original 2 mm slotted-driver bit."""
import copy


def add_nose_support(nodes):
    nose = copy.deepcopy(nodes['jaw_cage'])
    nose['args'].update({'outer_radius':9.7, 'inner_radius':5.4,
                         'start':[96,0,160], 'length':2,
                         'slot_width':2.2, 'slot_radius':12})
    nose['frame']['origin'] = [96,0,160]
    nodes['chuck_nose_support'] = nose


def add_driver_tip(nodes):
    # Preserve the round 2 mm shank and jaw contact zone X83..102.
    # Two opposed flats create a 0.6 mm blade beyond X113.5; rounded cutter
    # edges transition into the shaft. The existing bit frame stays fixed.
    stock = copy.deepcopy(nodes['bit'])
    stock['visible'] = False
    nodes['bit_stock'] = stock
    for name, dependency, z, visible in (
        ('bit_top_flat', 'bit_stock', 161.3, False),
        ('bit', 'bit_top_flat', 158.7, True),
    ):
        nodes[name] = {
            'kind':'cut_box', 'visible':visible,
            'deps':[{'id':dependency,'use':'geometry'}],
            'args':{'dimensions':[5,4,2], 'center':[116,0,z], 'radius':.1},
            'material':copy.deepcopy(stock['material']),
            'frame':copy.deepcopy(stock['frame']),
        }
