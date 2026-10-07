"""Fork one dimension or local topology variant from an existing native model."""

import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, sculpt, attachments

VARIANTS = {
    "grip-width": {"grip_width": 2},
    "grip-length": {"grip_length": 5},
    "split-shift": {"split_shift": 1},
}


def generate(source, output, variant):
    source = Path(source).resolve()
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    state = nested.load()
    before = {
        k: attachments.revision(bpy.data.objects[r["object"]])
        for k, r in state["outputs"].items()
    }
    try:
        if variant == "remesh":
            report = nested.update(
                remesh_request={
                    "part": "master",
                    "query": {
                        "box": [[-35, -30, 74], [-24, -8, 99]],
                        "normal": [0, -1, 0],
                        "normal_min": 0.95,
                        "components": 1,
                    },
                    "options": {"target_length": 4, "iterations": 1, "max_error": 0.09},
                }
            )
            master = bpy.data.objects[report["objects"]["master"]]
            report["remesh"] = json.loads(master["mw_remesh"])["report"]
        else:
            report = nested.update(VARIANTS[variant])
    except Exception as exc:
        sculpt.dump(out / "rejected.json", getattr(exc, "report", {"reason": str(exc)}))
        raise
    current = nested.load()
    checks = {}
    for key in [
        "chuck_body",
        "torque_ring",
        "jaw_cage",
        "jaw_0",
        "jaw_1",
        "jaw_2",
        "bit",
    ]:
        checks[key] = (
            current["outputs"][key]["object"] == state["outputs"][key]["object"]
            and attachments.revision(
                bpy.data.objects[current["outputs"][key]["object"]]
            )
            == before[key]
        )
    if variant != "grip-length":
        for key in [
            "battery",
            "rail_left",
            "rail_right",
            "channel_left",
            "channel_right",
        ]:
            checks[key] = (
                current["outputs"][key]["object"] == state["outputs"][key]["object"]
                and attachments.revision(
                    bpy.data.objects[current["outputs"][key]["object"]]
                )
                == before[key]
            )
    if not all(checks.values()):
        raise AssertionError("Independent geometry changed")
    report["independent_parts_unchanged"] = checks
    sculpt.dump(out / "variant.json", report)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
    print(
        "VARIANT",
        variant,
        "updated",
        len(report["updated"]),
        "unchanged",
        len(report["unchanged"]),
        flush=True,
    )
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    generate(*args)
