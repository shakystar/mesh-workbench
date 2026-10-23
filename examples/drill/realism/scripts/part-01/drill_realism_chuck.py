"""Procedural chuck support and six-millimetre two-flute drill bit."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import copy


def add_nose_support(nodes):
    nose = copy.deepcopy(nodes['jaw_cage'])
    nose['args'].update({'outer_radius':9.7, 'inner_radius':5.4,
                         'start':[96,0,160], 'length':2,
                         'slot_width':2.2, 'slot_radius':12})
    nose['frame']['origin'] = [96,0,160]
    nodes['chuck_nose_support'] = nose


def add_drill_bit(nodes):
    frame = copy.deepcopy(nodes['bit']['frame'])
    nodes.pop('bit_stock', None)
    nodes.pop('bit_top_flat', None)
    nodes['bit'] = {
        'kind':'twist_bit', 'visible':True,
        'deps':[{'id':'chuck_body','use':'frame'}],
        'args':{'start':[83,0,160], 'radius':3, 'shank':22,
                'cutting':38, 'pitch':32, 'segments':96, 'steps':160},
        'frame':frame}
    for index in range(3):
        nodes['jaw_'+str(index)]['args']['diameter'] = 6
