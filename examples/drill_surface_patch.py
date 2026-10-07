"""Rebuild an actual grip patch and regenerate its dependent surfaces."""

import hashlib, json, sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, sculpt


def run(source, out):
    source = Path(source).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    try:
        report = nested.update(
            remesh_request={
                "part": "master",
                "method": "rebuild",
                "query": {
                    "box": [[-43, -40, 72], [-12, -5, 109]],
                    "normal": [0, -1, 0],
                    "normal_min": 0.8,
                    "components": 1,
                },
                "options": {
                    "target_length": 2,
                    "iterations": 6,
                    "relaxation": 0.5,
                    "max_error": 0.09,
                },
            }
        )
    except Exception as exc:
        sculpt.dump(out / "rejected.json", getattr(exc, "report", {"reason": str(exc)}))
        raise
    obj = bpy.data.objects[report["objects"]["master"]]
    report["patch"] = json.loads(obj["mw_patch_rebuild"])
    report["source_preserved"] = (
        original == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    sculpt.dump(out / "patch.json", report)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
    print("PATCH_SAVED", report["patch"]["report"]["patch_after"], flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    run(args[0], args[1])
