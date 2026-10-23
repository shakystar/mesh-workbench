"""Reopen the drill and measure the front seat after its through-bore cut."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import actuators, assembly, geometry, nested


def supported_seats(state, obj):
    present=["boss_"+str(i)+"_stock" in state["outputs"] for i in (1,2)]
    if not any(present):
        return {}
    if not all(present):
        raise ValueError("Incomplete rear/grip seat construction")
    housing=obj("housing_left")
    shell_tree=assembly._tree(housing)
    visible={key:assembly._tree(obj(key)) for key,node in state["nodes"].items()
             if node.get("visible",True) and not obj(key).hide_render}
    reports={}
    for index in (1,2):
        boss="boss_"+str(index)
        head="head_"+str(index)
        floor=Vector(nested._resolve(state["nodes"][head]["args"]["end"],state["parameters"]))
        tree=assembly._tree(obj(boss))
        samples=[]
        for radius in (2.2,2.8,3.4):
            for i in range(32):
                angle=math.tau*i/32
                origin=Vector((floor.x+radius*math.cos(angle),-50,floor.z+radius*math.sin(angle)))
                hit,normal,_,_=tree.ray_cast(origin,Vector((0,1,0)),80)
                samples.append(hit is not None and abs(hit.y-floor.y)<=1e-4 and normal.y<=-.95)
        first_hits=[]
        for i in range(64):
            angle=math.tau*i/64
            origin=Vector((floor.x+3.4*math.cos(angle),-50,floor.z+3.4*math.sin(angle)))
            hits=[]
            for key,other in visible.items():
                hit,_,_,distance=other.ray_cast(origin,Vector((0,1,0)),100)
                if hit is not None:
                    hits.append((distance,key))
            first_hits.append(min(hits)[1] if hits else None)
        contacts=len(tree.overlap(shell_tree))
        pairs={side:actuators.pair(obj("fastener_"+str(index)),obj("housing_"+side),minimum=.2)
               for side in ("left","right")}
        info=geometry.inspect(obj(boss))
        report={"floor_y_mm":floor.y,"floor_samples":len(samples),
                "floor_failures":samples.count(False),"annular_visibility_first_hits":first_hits,
                "shell_contact_candidates":contacts,"fastener_shell_clearance":pairs,
                "finite":info["finite"],"nonmanifold_edges":info["nonmanifold_edges"],
                "scope":"Counterbored internal support with intentional shell contact; not a thin-shell blind floor"}
        report["passed"]=(all(samples) and all(k==boss for k in first_hits) and contacts>0
                          and info["finite"] and not info["nonmanifold_edges"]
                          and all(p["passed"] for p in pairs.values()))
        reports[boss]=report
    return reports


def verify(source, output):
    if output.exists():
        raise ValueError("Fresh screw seat report required")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    def obj(key):
        return bpy.data.objects[state["outputs"][key]["object"]]
    seat = json.loads(obj("screw_seat_left_0")["mw_recess_seat"])
    point, axis = Vector(seat["point"]), Vector(seat["outward"])
    shell = assembly._tree(obj("housing_left"))
    samples = []
    # The radius-2 through bore deliberately removes the seat center.
    # Measure only the remaining annular floor, independently of metadata.
    for radius in (2.2, 2.8, 3.4):
        for i in range(32):
            angle = math.tau * i / 32
            start = point + Vector((radius*math.cos(angle), 0, radius*math.sin(angle)))
            hit, normal, _, _ = shell.ray_cast(start + axis, -axis, 3)
            depth = None if hit is None else (start-hit).dot(axis)
            samples.append({"radius": radius, "angle": i*360/32, "depth": depth,
                            "passed": depth is not None and abs(depth-.2) <= 1e-4
                            and normal.dot(axis) >= .95})
    end = Vector(nested._resolve(state["nodes"]["head_0"]["args"]["end"], state["parameters"]))
    contact_error = abs((end - (point-axis*.2)).dot(axis))
    geometry_checks = {}
    for key in ("housing_left", "fastener_0"):
        info = geometry.inspect(obj(key))
        geometry_checks[key] = {"finite": info["finite"], "nonmanifold_edges": info["nonmanifold_edges"]}
    report = {"blender": bpy.app.version_string, "source_sha256": digest,
              "source_preserved": digest == hashlib.sha256(source.read_bytes()).hexdigest(),
              "scope": "Front screw only; rear and grip mounting lands remain unresolved",
              "seat_floor_minimum_mm": seat["floor_minimum"], "annular_floor_samples": samples,
              "head_floor_contact_error_mm": contact_error,
              "radial_clearance_mm": seat["radius"] - state["nodes"]["head_0"]["args"]["radius"],
              "geometry": geometry_checks}
    supports=supported_seats(state,obj)
    report["supported_seats"]=supports
    if supports:
        report["scope"]="Front blind recess plus rear/grip counterbored internal supports"
    report["passed"] = (report["source_preserved"] and all(s["passed"] for s in samples)
                        and contact_error <= 1e-4 and report["radial_clearance_mm"] >= .39
                        and seat["floor_minimum"] >= 1.6
                        and all(g["finite"] and not g["nonmanifold_edges"] for g in geometry_checks.values()))
    report["passed"]=report["passed"] and all(r["passed"] for r in supports.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print("FRONT_SEAT", report["passed"], flush=True)
    if not report["passed"]:
        raise ValueError("Native front screw seat failed")


if __name__ == "__main__":
    verify(*map(Path, sys.argv[sys.argv.index("--")+1:]))
