"""Offset vent shields with two shell-attached stand-offs per side."""

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
