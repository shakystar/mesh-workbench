"""Rounded transverse trigger grooves, retaining the stock and travel frame."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
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
