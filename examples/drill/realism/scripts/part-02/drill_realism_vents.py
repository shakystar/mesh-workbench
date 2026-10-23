"""Offset vent shields with two shell-attached stand-offs per side."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import copy


def add_vent_baffles(nodes):
    for side,sign in (("left",-1),("right",1)):
        deps=[{"id":"housing_"+side,"use":"geometry"}]
        material=copy.deepcopy(nodes["battery"]["material"])
        nodes["vent_baffle_"+side]={
            "kind":"box","visible":True,"deps":deps,
            "args":{"dimensions":[35,1.2,18],"center":[-35.5,sign*19,162],"radius":.3},
            "material":material}
        for index,x in enumerate((-52,-19)):
            nodes["vent_support_"+side+"_"+str(index)]={
                "kind":"cylinder","visible":True,"deps":copy.deepcopy(deps),
                "args":{"start":[x,sign*19,162],
                        "end":[x,{"param":"head_width","offset":sign*25.2,"scale":sign*.5},162],
                        "radius":.7,"segments":32},
                "material":copy.deepcopy(material)}
