"""Probe authored shallow screw seats on the unbored native left shell."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT=_WORKSPACE
sys.path.insert(0,str(ROOT/"src"))
from mesh_workbench import attachments, mechanical, nested, seams


def add_front_seat(nodes):
    """Recess the front screw on its verified planar housing chart.

    Rear and grip seats require reshaped mounting lands; they are not implied
    by this single seat. Keep the original screw axis and mating frame.
    """
    nodes["screw_seat_left_0"] = {
        "kind": "recess_seat", "visible": False,
        "deps": [{"id": "front_bore_left", "use": "geometry"}],
        "args": {"point": copy.deepcopy(nodes["head_0"]["args"]["end"]),
                 "outward": [0,-1,0], "query": {"materials": [0], "components": 1},
                 "radius": 3.6, "depth": .2}}
    nodes["fastener_bore_left_0"]["deps"] = [
        {"id": "screw_seat_left_0", "use": "geometry"}]
    # Move both ends and slot together so the head rests on the new floor.
    for key in ("start", "end"):
        value = nodes["head_0"]["args"][key][1]
        offset = value.get("offset", 0) if isinstance(value, dict) else value
        nodes["head_0"]["args"][key][1] = {
            "param": "head_width", "scale": -.5, "offset": offset + .2}
    value = nodes["slotted_head_0"]["args"]["center"][1]
    offset = value.get("offset", 0) if isinstance(value, dict) else value
    nodes["slotted_head_0"]["args"]["center"][1] = {
        "param": "head_width", "scale": -.5, "offset": offset + .2}
    value = nodes["shaft_0"]["args"]["start"][1]
    offset = value.get("offset", 0) if isinstance(value, dict) else value
    nodes["shaft_0"]["args"]["start"][1] = {
        "param": "head_width", "scale": -.5, "offset": offset}


def add_supported_seats(nodes):
    """Counterbore the existing rear/grip supports behind shell access holes.

    Preserve coaxial part frames. Trim the support front inside the curved
    envelope rather than flattening the shell or thickening its outer skin.
    """
    for index, shift, front, length in (
        (1, 3.4, {"param":"head_width","offset":-24.4,"scale":-.5},
         {"param":"head_width","offset":23.7,"scale":.5}),
        (2, 6.2, {"param":"grip_width","offset":-9.1,"scale":-.5},
         {"param":"grip_width","offset":8.4,"scale":.5}),
    ):
        key=str(index)
        for part, coordinates in (("head_"+key,("start","end")),
                                  ("shaft_"+key,("start",)),
                                  ("slotted_head_"+key,("center",))):
            for coordinate in coordinates:
                value=nodes[part]["args"][coordinate][1]
                offset=value.get("offset",0) if isinstance(value,dict) else value
                if index==1:
                    value={"param":"head_width","offset":offset+shift,"scale":-.5}
                elif isinstance(value,dict):
                    value=copy.deepcopy(value)
                    value["offset"]=offset+shift
                else:
                    value+=shift
                nodes[part]["args"][coordinate][1]=value
        bore="fastener_bore_left_1" if index==1 else "housing_left"
        floor=copy.deepcopy(nodes["head_"+key]["args"]["end"])
        start=copy.deepcopy(floor)
        start[1]=-40
        access="screw_access_left_"+key
        access_end=copy.deepcopy(floor)
        if isinstance(access_end[1],dict):
            access_end[1]["offset"]+=.3
        else:
            access_end[1]+=.3
        # Cut the shell 0.3 mm behind the separate support floor so the head
        # seats on its boss, not a coplanar shell cap. Retain the shaft bore.
        nodes[access]={"kind":"cut_cylinder","visible":False,
            "deps":copy.deepcopy(nodes[bore]["deps"]),
            "args":{"start":copy.deepcopy(start),"end":access_end,
                    "radius":3.6,"segments":64}}
        if index == 2:
            cutter = access + "_cutter"
            nodes[cutter] = {"kind":"revolve", "visible":False,
                "args":{"profile":[[15.825,-16],[3.6,.3]],"segments":64,
                        "location":copy.deepcopy(floor),"axis":[0,1,0]}}
            nodes[access] = {"kind":"difference", "visible":False,
                "deps":copy.deepcopy(nodes[bore]["deps"])+[
                    {"id":cutter,"use":"geometry"}], "args":{"cut_material_index":2}}
        nodes[bore]["deps"]=[{"id":access,"use":"geometry"}]
        boss="boss_"+key
        stock=copy.deepcopy(nodes[boss])
        stock["visible"]=False
        stock["args"]["start"][1]=front
        stock["args"]["length"]=length
        nodes[boss+"_stock"]=stock
        nodes[boss]={"kind":"cut_cylinder","visible":True,
            "deps":[{"id":boss+"_stock","use":"geometry"}],
            "args":{"start":start,"end":floor,"radius":3.6,"segments":64},
            "frame":copy.deepcopy(stock["frame"]),
            "material":copy.deepcopy(stock["material"])}


def probe(source, output):
    if output.exists():
        raise ValueError("Fresh seat report path required")
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    shell=bpy.data.objects[state["outputs"]["front_bore_left"]["object"]]
    revision=attachments.revision(shell)
    reports={}
    for index in range(3):
        end=nested._resolve(state["nodes"]["head_"+str(index)]["args"]["end"],state["parameters"])
        try:
            result=seams.recess_seat(shell,"Seat probe "+str(index),end,[0,-1,0],
                                    {"materials":[0],"components":1},radius=3.6,depth=.2)
            reports[str(index)]={"passed":True,"seat":json.loads(result["mw_recess_seat"])}
            mechanical.remove(result)
        except ValueError as exc:
            reports[str(index)]={"passed":False,"reason":str(exc),"point":end}
        print("SCREW_SEAT",index,reports[str(index)]["passed"],flush=True)
    report={"blender":bpy.app.version_string,"seats":reports,
            "source_preserved":digest==hashlib.sha256(source.read_bytes()).hexdigest(),
            "shell_preserved":revision==attachments.revision(shell),
            "passed":all(r["passed"] for r in reports.values())}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("Native screw seat probe rejected")


if __name__=="__main__":
    probe(*map(Path,sys.argv[sys.argv.index("--")+1:]))
