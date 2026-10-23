"""Frozen vent sightlines, sampled open routes and native shield attachment."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=_WORKSPACE
sys.path.insert(0,str(ROOT/"src"))
from mesh_workbench import actuators, assembly, geometry, nested, shells

SPEC_SHA="a1d902c9f47ef03f28b7247f23855f8759cc262709958d3bbd14121f9ebed34a"


def verify(source, output):
    if output.exists():
        raise ValueError("Fresh vent report path required")
    spec_path=ROOT/"examples/drill/realism/recipes/part-01/drill-realism-vent-rays.json"
    if hashlib.sha256(spec_path.read_bytes()).hexdigest()!=SPEC_SHA:
        raise ValueError("Frozen vent ray specification changed")
    spec=json.loads(spec_path.read_text())
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    objects={k:bpy.data.objects[v["object"]] for k,v in state["outputs"].items()
             if state["nodes"][k].get("visible",True)}
    trees={k:assembly._tree(v) for k,v in objects.items()}
    reports={}
    for side,sign in (("left",-1),("right",1)):
        shield="vent_baffle_"+side
        source_key="housing_"+side
        clear=actuators.pair(objects[shield],objects[source_key],minimum=spec["shell_clearance_mm"])
        contacts={}
        for i in range(2):
            key="vent_support_"+side+"_"+str(i)
            contacts[key]={target:shells.intersections(objects[key],objects[target])["triangle_pair_count"]
                           for target in (shield,source_key)}
        failures=[]
        rays=0
        for x in spec["vent_centers_x"]:
            for dx in spec["x_offsets"]:
                for dz in spec["z_offsets"]:
                    origin=Vector([x+dx,sign*spec["sightline_origin_abs_y"],spec["center_z"]+dz])
                    direction=Vector([0,-sign,0])
                    hit=trees[shield].ray_cast(origin,direction)
                    rays+=1
                    if hit[0] is None:
                        failures.append({"ray":rays,"reason":"missing shield"})
                        continue
                    prior=[k for k,t in trees.items() if k!=shield and
                           t.ray_cast(origin,direction,max(0,hit[3]-1e-4))[0] is not None]
                    if prior:
                        failures.append({"ray":rays,"reason":"blocked before shield","parts":prior})
        corridor_failures=[]
        routes=0
        c=spec["corridor"]
        for x in spec["vent_centers_x"]:
            for dx in spec["corridor_offsets_xz"]:
                for dz in spec["corridor_offsets_xz"]:
                    z=spec["center_z"]
                    points=[[x,sign*c["outside_abs_y"],z],[x,sign*c["gap_abs_y"],z],
                            [x,sign*c["gap_abs_y"],c["bypass_z"]],
                            [c["front_edge_x"],sign*c["gap_abs_y"],c["bypass_z"]],
                            [c["front_edge_x"],sign*c["inside_abs_y"],c["bypass_z"]]]
                    points=[Vector([p[0]+dx,p[1],p[2]+dz]) for p in points]
                    routes+=1
                    for segment,(a,b) in enumerate(zip(points,points[1:])):
                        delta=b-a
                        blockers=[k for k,t in trees.items() if t.ray_cast(a,delta.normalized(),delta.length)[0] is not None]
                        if blockers:
                            corridor_failures.append({"route":routes,"segment":segment,"parts":blockers})
        reports[side]={"rays":rays,"ray_failures":failures,"routes":routes,
                       "route_failures":corridor_failures,"clearance":clear,"contacts":contacts}
        reports[side]["passed"]=(clear["passed"] and not failures and not corridor_failures
                                 and all(n>0 for row in contacts.values() for n in row.values()))
    new_parts=[k for k in objects if k.startswith(("vent_baffle_","vent_support_"))]
    allowed=set()
    for side in ("left","right"):
        for i in range(2):
            support="vent_support_"+side+"_"+str(i)
            for target in ("housing_"+side,"vent_baffle_"+side):
                allowed.add(tuple(sorted((support,target))))
    checked=set()
    interference=[]
    for key in new_parts:
        for other in objects:
            pair=tuple(sorted((key,other)))
            if key==other or pair in allowed or pair in checked:
                continue
            checked.add(pair)
            report=actuators.pair(objects[key],objects[other],minimum=.2)
            if not report["passed"]:
                interference.append({"parts":list(pair),"report":report})
    topology={k:geometry.inspect(objects[k]) for k in new_parts}
    result={"blender":bpy.app.version_string,"source_sha256":digest,"spec_sha256":SPEC_SHA,
            "scope":spec["scope"],"sides":reports,
            "other_part_pairs_checked":len(checked),"other_part_minimum_clearance_mm":.2,
            "other_part_failures":interference,
            "topology":{k:{"finite":v["finite"],"nonmanifold_edges":v["nonmanifold_edges"]} for k,v in topology.items()},
            "source_preserved":digest==hashlib.sha256(source.read_bytes()).hexdigest()}
    result["passed"]=(result["source_preserved"] and not interference and all(r["passed"] for r in reports.values())
                      and len(new_parts)==6 and all(v["finite"] and not v["nonmanifold_edges"] for v in topology.values()))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n")
    print("VENT_CHECK",result["passed"],flush=True)
    if not result["passed"]:
        raise ValueError("Native vent shield or open-route checks failed")


if __name__=="__main__":
    verify(*map(Path,sys.argv[sys.argv.index("--")+1:]))
