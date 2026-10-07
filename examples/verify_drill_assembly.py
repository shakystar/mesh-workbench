"""Fresh-process nested assembly validation and a subsequent native edit.

Run with factory-startup Blender; output must be a new directory. Motion checks
can be run separately against followup.blend and are not implied by this report.
"""

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, sculpt, attachments, assembly
from drill_assembly import blueprint
from drill_assembly_geometry import verify as geometry_verify


def snapshot():
    return {
        "graph": bpy.context.scene[nested.KEY],
        "objects": sorted(o.name for o in bpy.data.objects),
        "meshes": sorted(m.name for m in bpy.data.meshes),
        "parts": {
            o.name: nested._stamp(o) for o in bpy.data.objects if o.type == "MESH"
        },
        "visibility": {
            o.name: [o.hide_get(), o.hide_render, o.hide_viewport]
            for o in bpy.data.objects
        },
    }


def attributes(state):
    objects = {k: bpy.data.objects[r["object"]] for k, r in state["outputs"].items()}
    master = objects["master"]
    x = sculpt.coordinates(master)
    uv = master.data.uv_layers["DesignXZ"]
    uv_error = max(
        float(
            np.max(
                np.abs(
                    np.asarray(uv.data[l.index].uv)
                    - x[l.vertex_index][[0, 2]] / [120, 200]
                )
            )
        )
        for l in master.data.loops
    )
    group = master.vertex_groups["Grip weight"]
    t = np.clip((x[:, 2] - 100) / 40, 0, 1)
    expected = 1 - t * t * (3 - 2 * t)
    actual = np.zeros(len(x))
    for v in master.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                actual[v.index] = g.weight
    mask_error = float(np.max(np.abs(actual - expected)))
    bindings = {}
    for side in ["left", "right"]:
        parent = objects["housing_" + side]
        insert = objects["grip_" + side]
        pattern = objects["texture_" + side]
        record = json.loads(insert["mw_insert"])
        resolved = attachments.resolve(parent, record["source_binding"])
        bindings["grip_" + side] = (
            record["source_revision"] == attachments.revision(parent)
            and len(resolved) > 0
        )
        bindings["texture_" + side] = (
            attachments.status(insert, pattern)["status"] == "current"
        )
    return {
        "passed": uv_error <= 1e-4 and mask_error <= 1e-5 and all(bindings.values()),
        "master_uv_error": uv_error,
        "master_mask_error": mask_error,
        "current_bindings": bindings,
    }


def verify(source, output, rollback=False):
    source = Path(source).resolve()
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    state = nested.load()
    spec = json.loads(
        (ROOT / "examples/drill-assembly-target.json").read_text(encoding="utf-8")
    )
    nodes, checks = blueprint(spec)
    if state["nodes"] != nodes or state["checks"] != checks:
        raise AssertionError(
            "Saved recipe does not match the frozen brief implementation"
        )
    report = {
        "source_sha256": digest,
        "blender": bpy.app.version_string,
        "parameters_before": state["parameters"],
        "attributes_before": attributes(state),
        "recipe_matches": True,
        "status": "running",
    }
    sculpt.dump(out / "reopen.json", report)
    before = snapshot()
    try:
        nested.update(remesh_request={"part": "unknown", "query": {}, "options": {}})
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown part accepted")
    if snapshot() != before:
        raise AssertionError("Unknown-part rejection changed the assembly")
    report["unknown_part_rejected_unchanged"] = True
    master = bpy.data.objects[state["outputs"]["master"]["object"]]
    uv = master.data.uv_layers["DesignXZ"].data[0]
    original = uv.uv.copy()
    try:
        uv.uv.x += 0.01
        try:
            nested.load()
        except ValueError:
            pass
        else:
            raise AssertionError("External attribute edit was not detected")
    finally:
        master.data.uv_layers["DesignXZ"].data[0].uv = original
    after = snapshot()
    if after != before:
        sculpt.dump(
            out / "stale-diff.json",
            {
                key: {"before": before[key], "after": after[key]}
                for key in before
                if before[key] != after[key]
            },
        )
        raise AssertionError("Stale-attribute fixture restoration failed")
    report["stale_attribute_detected"] = True
    if rollback:

        def fail(phase):
            if phase == "after_commit":
                raise RuntimeError("actual assembly late-commit injection")

        with patch.object(nested, "_checkpoint", side_effect=fail):
            try:
                nested.update({"grip_width": state["parameters"]["grip_width"] + 0.1})
            except assembly.Rejected as exc:
                if not exc.report["rolled_back"]:
                    raise
            else:
                raise AssertionError("Injected commit failure accepted")
        if snapshot() != before:
            raise AssertionError("Actual late commit failed to restore the assembly")
        report["late_commit_rollback"] = True
    sculpt.dump(out / "reopen.json", report)
    edit = {"grip_width": state["parameters"]["grip_width"] + 0.25}
    result = nested.update(edit)
    report["followup"] = result
    report["attributes_after"] = attributes(nested.load())
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "followup.blend"))
    report["geometry_after"] = geometry_verify(out / "geometry")
    report["source_preserved"] = (
        hashlib.sha256(source.read_bytes()).hexdigest() == digest
    )
    report["passed"] = (
        report["attributes_before"]["passed"]
        and report["attributes_after"]["passed"]
        and report["geometry_after"]["passed"]
        and report["source_preserved"]
        and result["passed"]
    )
    report["status"] = "complete" if report["passed"] else "failed"
    sculpt.dump(out / "reopen.json", report)
    print("REOPEN", report["passed"], str(out), flush=True)
    if not report["passed"]:
        raise AssertionError("Fresh-process gates failed")
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    verify(args[0], args[1], "--rollback" in args)
