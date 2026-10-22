"""Authored cross-body direction control and its rounded clearance slot."""

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
