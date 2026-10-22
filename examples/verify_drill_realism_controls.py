"""Native seating clearance for the authored direction selector."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from mesh_workbench import actuators, geometry, nested


def verify(source, output):
    if output.exists():
        raise ValueError("Fresh control report path required")
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    control=bpy.data.objects[state["outputs"]["direction_switch"]["object"]]
    info=geometry.inspect(control)
    pairs={side:actuators.pair(control,bpy.data.objects[state["outputs"]["housing_"+side]["object"]],
                              minimum=.2) for side in ("left","right")}
    report={"blender":bpy.app.version_string,"source_sha256":digest,
            "geometry":{"finite":info["finite"],"nonmanifold_edges":info["nonmanifold_edges"]},
            "clearance":pairs,"required_clearance_mm":.2,
            "scope":"Static selector-to-shell fit; selector actuation and internal retention not certified",
            "source_preserved":digest==hashlib.sha256(source.read_bytes()).hexdigest()}
    report["passed"]=(report["source_preserved"] and info["finite"] and not info["nonmanifold_edges"]
                      and all(r["passed"] for r in pairs.values()))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("Direction selector fit failed")


if __name__=="__main__":
    verify(*map(Path,sys.argv[sys.argv.index("--")+1:]))
