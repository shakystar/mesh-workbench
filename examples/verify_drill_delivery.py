"""Inspect every delivered native variant against the frozen specification."""

import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, sculpt
from drill_assembly import blueprint
from drill_assembly_geometry import verify as geometry_verify
from drill_assembly_motion import verify_interfaces

NAMES = ["baseline", "grip-width", "grip-length", "split-shift", "remesh"]


def verify(root, mode):
    root = Path(root).resolve()
    if mode not in ["native", "followup"]:
        raise ValueError("Expected native or followup")
    spec_path = ROOT / "examples/drill-assembly-target.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    nodes, checks = blueprint(spec)
    records = {}
    destination = root / ("delivery-" + mode + ".json")
    for name in NAMES:
        folder = root / name if mode == "native" else root / ("reopen-" + name)
        source = folder / ("drill.blend" if mode == "native" else "followup.blend")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        print("DELIVERY", mode, name, flush=True)
        bpy.ops.wm.open_mainfile(filepath=str(source))
        state = nested.load()
        if state["nodes"] != nodes or state["checks"] != checks:
            raise AssertionError("Recipe does not match current frozen brief")
        frames = {}
        for part in spec["parts"]:
            record = state["outputs"][part]
            obj = bpy.data.objects[record["object"]]
            expected = nested._resolve(nodes[part]["frame"], state["parameters"])
            frames[part] = (
                json.loads(obj["mw_part_frame"]) == expected
                and record["frame"] == expected
                and obj["mw_part_id"] == part
            )
        if not all(frames.values()):
            raise AssertionError("Missing or mismatched declared part frame")
        out = folder / "delivery"
        out.mkdir(parents=True, exist_ok=False)
        geometry = geometry_verify(out)
        interfaces = verify_interfaces(out)
        record = {
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "sha256": digest,
            "parameters": state["parameters"],
            "declared_frames": frames,
            "geometry": geometry,
            "interfaces": interfaces,
            "source_preserved": hashlib.sha256(source.read_bytes()).hexdigest()
            == digest,
        }
        record["passed"] = (
            geometry["passed"] and interfaces["passed"] and record["source_preserved"]
        )
        records[name] = record
        sculpt.dump(
            destination, {"status": "running", "mode": mode, "records": records}
        )
        if not record["passed"]:
            raise AssertionError(
                "Delivered variant failed geometric acceptance: " + name
            )
    result = {
        "status": "complete",
        "passed": all(r["passed"] for r in records.values()),
        "mode": mode,
        "specification_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "blender": bpy.app.version_string,
        "records": records,
    }
    sculpt.dump(destination, result)
    print("DELIVERY_COMPLETE", mode, result["passed"], flush=True)


if __name__ == "__main__":
    verify(*sys.argv[sys.argv.index("--") + 1 :])
