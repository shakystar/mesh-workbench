"""Exercise invalid real-drill edits through the public host CLI."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify(source, recipe, output, blender):
    source, recipe, output = source.resolve(), recipe.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    document = json.loads(recipe.read_text())
    base = next(op for op in document["operations"] if op["op"] == "nested_initialize")
    cases = {
        "out_of_range": ([{"op": "nested_update", "parameters": {
            "head_width": base["ranges"]["head_width"][1]+1}}], "Invalid head_width"),
        "invalid_camera": ([{"op": "reference_register", "spec": {
            "projection": "unsupported"}}], "Explicit projection model required"),
    }
    for case in ("missing_surface_role", "excessive_seam_depth", "invalid_material_scale",
                 "cage_displacement", "cage_foldover", "missing_marking_anchor"):
        nodes = copy.deepcopy(base["nodes"])
        if case == "missing_surface_role":
            nodes["housing_seam_front_grip"]["args"]["query"] = {
                "materials": [999], "components": 1}
            reason = "Invalid semantic material roles"
        elif case == "excessive_seam_depth":
            nodes["housing_seam_front_grip"]["args"]["overlap"] = 20
            reason = "Lip violates opposing clearance"
        elif case == "invalid_material_scale":
            nodes["direction_switch"]["material"]["finish"] = {
                "role": "plastic", "color": [.4,.4,.4,1], "roughness": .4,
                "variation": .1, "grain_mm": 0, "bump_mm": .01, "seed": 1}
            reason = "Invalid grain size mm"
        elif case == "cage_displacement":
            nodes["master"]["args"]["controls"][1][1][1] = [1e6,0,0]
            reason = "Control offset exceeds displacement limit"
        elif case == "cage_foldover":
            nodes["master"]["args"]["controls"] = [
                [[[0,-180*(j/3-.5),0] for _ in range(4)] for j in range(4)]
                for _ in range(4)]
            nodes["master"]["args"]["max_displacement"] = 100
            reason = "foldover"
        else:
            nodes["texture_left"] = {"kind": "surface_marking", "visible": True,
                "deps": [{"id": "housing_left", "use": "geometry"}],
                "args": {"text": "1", "origin": [10000,-27,160],
                         "horizontal": [1,0,0], "vertical": [0,0,1],
                         "query": {"materials": [0], "components": 1},
                         "projection_axis": 1, "side": -1, "max_distance": 5}}
            reason = "projection"
        cases[case] = ([{"op": "nested_reconfigure", "nodes": nodes}], reason)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    report = {"source_sha256": source_hash,
              "recipe_sha256": hashlib.sha256(recipe.read_bytes()).hexdigest(),
              "scope": "Eight public CLI failures; full in-memory rollback is separately verified",
              "cases": {}}
    for name, (operations, reason) in cases.items():
        path = output / (name+".json")
        path.write_text(json.dumps({"version": 1, "source": os.path.relpath(source, output),
                                    "operations": operations}, indent=2)+"\n")
        destination = output / name
        process = subprocess.run([sys.executable, "-m", "mesh_workbench", "run", str(path),
            "--output", str(destination), "--blender", blender],
            cwd=ROOT, env=env, capture_output=True, text=True)
        (output / (name+"-host.log")).write_text(process.stdout+process.stderr)
        host = json.loads(process.stdout.strip().splitlines()[-1])
        audit = json.loads((destination / "audit.json").read_text())
        row = {"host_exit": process.returncode, "native_exit": host["exit_code"],
               "status": audit["status"], "expected_reason": reason,
               "reason_matched": reason.lower() in audit.get("error", "").lower(),
               "result_created": (destination / "result.blend").exists(),
               "source_preserved": hashlib.sha256(source.read_bytes()).hexdigest() == source_hash,
               "audit": str((destination / "audit.json").relative_to(output))}
        row["passed"] = (row["host_exit"] == 1 and row["native_exit"] == 2
                         and row["status"] == "failed" and row["reason_matched"]
                         and not row["result_created"] and row["source_preserved"])
        report["cases"][name] = row
        (output / "verification.json").write_text(json.dumps(report, indent=2)+"\n")
        print("CLI_REJECTION", name, row["passed"], flush=True)
        if not row["passed"]:
            raise RuntimeError("Unexpected CLI rejection result: "+name)
    report["passed"] = all(r["passed"] for r in report["cases"].values())
    (output / "verification.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--blender", default=os.environ.get("BLENDER_BIN", "blender"))
    args = parser.parse_args()
    verify(args.source, args.recipe, args.output, args.blender)
