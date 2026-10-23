"""Authored cross-body direction control and its rounded clearance slot."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import copy


def add_direction_switch(nodes):
    for side in ("left", "right"):
        key = "direction_slot_"+side
        nodes[key] = {
            "kind":"cut_box", "visible":False,
            "deps":[{"id":"trigger_cut_"+side,"use":"geometry"}],
            "args":{"dimensions":[8.6,80,5.6],"center":[5,0,136.5],"radius":.5}}
        nodes["front_bore_"+side]["deps"] = [{"id":key,"use":"geometry"}]
    nodes["direction_switch"] = {
        "kind":"box", "visible":True,
        "deps":[{"id":"housing_left","use":"frame"}],
        "args":{"dimensions":[8,52,5],"center":[5,0,136.5],"radius":.4},
        "frame":{"origin":[5,0,136.5],"x":[1,0,0],"y":[0,1,0],"z":[0,0,1]},
        "material":copy.deepcopy(nodes["battery"]["material"])}
