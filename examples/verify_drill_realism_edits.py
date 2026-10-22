"""Reopen the drill and exercise independent head/grip edits with bound details."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"examples"))
from mesh_workbench import actuators, attachments, nested


def verify(source, output):
    output.mkdir(parents=True,exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    reports = {}
    for parameter,delta in (("head_width",.25),("grip_length",1)):
        bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
        state = nested.load()
        expected_lips = {key for key,row in state["outputs"].items()
                         if "mw_seam_lip" in bpy.data.objects[row["object"]]}
        stationary = ["bit","chuck_body","torque_ring"] + (["battery"] if parameter=="head_width" else [])
        if "direction_switch" in state["outputs"]:
            stationary.append("direction_switch")
        before = {key:(state["outputs"][key]["object"],
                   attachments.revision(bpy.data.objects[state["outputs"][key]["object"]])) for key in stationary}
        try:
            update = nested.update({parameter:state["parameters"][parameter]+delta})
            after = nested.load()
            unchanged = all(before[key] == (after["outputs"][key]["object"],
                        attachments.revision(bpy.data.objects[after["outputs"][key]["object"]])) for key in stationary)
            bindings, lips = {}, {}
            for key,row in after["outputs"].items():
                obj = bpy.data.objects[row["object"]]
                for tag,binding_key in (("mw_insert","source_binding"),("mw_surface_paths","binding")):
                    if tag in obj:
                        meta = json.loads(obj[tag])
                        parent = bpy.data.objects[meta["source"]]
                        bindings[key] = (meta["source_revision"] == attachments.revision(parent)
                                         and bool(attachments.resolve(parent,meta[binding_key])))
                if "mw_seam_lip" in obj:
                    meta = json.loads(obj["mw_seam_lip"])
                    lips[key] = {"clearance":meta["minimum_sampled_clearance"],
                                 "contacts":meta["source_contact_candidates"],
                                 "current":meta["source_revision"] == attachments.revision(bpy.data.objects[meta["source"]])}
            passed = (update["passed"] and unchanged and bool(bindings) and all(bindings.values())
                      and bool(expected_lips) and set(lips)==expected_lips
                      and all(r["clearance"]>=.2-1e-6 and r["contacts"]>0 and r["current"] for r in lips.values()))
            controls = {}
            if "direction_switch" in after["outputs"]:
                control = bpy.data.objects[after["outputs"]["direction_switch"]["object"]]
                controls = {side:actuators.pair(control,
                    bpy.data.objects[after["outputs"]["housing_"+side]["object"]],minimum=.2)
                    for side in ("left","right")}
                passed = passed and all(r["passed"] for r in controls.values())
            reports[parameter] = {"passed":passed,"unrelated_unchanged":unchanged,
                "stationary_parts":stationary,"bindings":bindings,"lips":lips,
                "controls":controls,"update":update}
            if passed:
                followup=output/(parameter+".blend")
                bpy.ops.wm.save_as_mainfile(filepath=str(followup.resolve()))
                if "vent_baffle_left" in after["outputs"]:
                    from verify_drill_realism_vents import verify as verify_vents
                    vent_report=output/(parameter+"-vents.json")
                    verify_vents(followup,vent_report)
                    reports[parameter]["vent_verification"]=json.loads(vent_report.read_text())
                if "screw_seat_left_0" in after["outputs"]:
                    from verify_drill_realism_seats import verify as verify_seats
                    seat_report=output/(parameter+"-seats.json")
                    verify_seats(followup,seat_report)
                    reports[parameter]["seat_verification"]=json.loads(seat_report.read_text())
                if "grip_rear_left" in after["nodes"]:
                    from verify_drill_realism_grip import verify as verify_grip
                    grip_report=output/(parameter+"-grip.json")
                    verify_grip(followup,grip_report)
                    reports[parameter]["grip_verification"]=json.loads(grip_report.read_text())
                if any("finish" in node.get("material", {}) for node in after["nodes"].values()):
                    from verify_drill_realism_finishes import verify as verify_finishes
                    finish_report=output/(parameter+"-finishes.json")
                    verify_finishes(followup,finish_report)
                    reports[parameter]["finish_verification"]=json.loads(finish_report.read_text())
        except Exception as exc:
            reports[parameter] = {"passed":False,"reason":str(exc),"detail":getattr(exc,"report",None)}
        print("EDIT_CHECK",parameter,reports[parameter]["passed"],flush=True)
        (output/"verification.json").write_text(json.dumps(reports,indent=2)+"\n")
    result = {"blender":bpy.app.version_string,"edits":reports,
              "source_preserved":digest==hashlib.sha256(source.read_bytes()).hexdigest()}
    result["passed"] = result["source_preserved"] and all(r["passed"] for r in reports.values())
    (output/"verification.json").write_text(json.dumps(result,indent=2)+"\n")
    if not result["passed"]:
        raise ValueError("Native editing checks failed")


if __name__ == "__main__":
    verify(*map(Path,sys.argv[sys.argv.index("--")+1:]))
