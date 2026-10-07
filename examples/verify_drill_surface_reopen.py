"""Reopen current surface models, verify correspondence and perform a new edit."""

import hashlib, json, sys
from pathlib import Path
from unittest.mock import patch
import bpy, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, sculpt, attachments, assembly
from drill_surface import surface_blueprint
from verify_drill_assembly import snapshot


def attributes(state):
    objects = {k: bpy.data.objects[v["object"]] for k, v in state["outputs"].items()}
    master = objects["master"]
    xyz = sculpt.coordinates(master)
    group = master.vertex_groups["Grip weight"]
    actual = np.array(
        [
            next((v.weight for v in vertex.groups if v.group == group.index), 0)
            for vertex in master.data.vertices
        ]
    )
    if "mw_remesh" in master:
        record = json.loads(master["mw_remesh"])
        source = bpy.data.objects[record["source"]]
        source_group = source.vertex_groups["Grip weight"]
        weights = np.array(
            [
                next(
                    (v.weight for v in vertex.groups if v.group == source_group.index),
                    0,
                )
                for vertex in source.data.vertices
            ]
        )
        expected = np.array(
            [weights[a["vertices"]] @ a["weights"] for a in record["mapping"]]
        )
        method = "piecewise-linear source correspondence"
    else:
        t = np.clip((xyz[:, 2] - 100) / 40, 0, 1)
        expected = 1 - t * t * (3 - 2 * t)
        method = "analytic authored field"
    uv_error = max(
        float(
            np.max(
                np.abs(
                    np.array(master.data.uv_layers["DesignXZ"].data[l.index].uv)
                    - xyz[l.vertex_index][[0, 2]] / [120, 200]
                )
            )
        )
        for l in master.data.loops
    )
    report = {
        "master_uv_error": uv_error,
        "master_mask_error": float(np.max(np.abs(actual - expected))),
        "master_mask_reference": method,
        "bindings": {},
    }
    for key, parent_key in [
        ("grip_left", "housing_left"),
        ("grip_right", "housing_right"),
        ("texture_left", "grip_left"),
        ("texture_right", "grip_right"),
        ("trigger", "trigger_stock"),
    ]:
        obj = objects[key]
        parent = objects[parent_key]
        record = json.loads(
            obj["mw_insert"] if key.startswith("grip_") else obj["mw_surface_paths"]
        )
        binding = (
            record["source_binding"] if key.startswith("grip_") else record["binding"]
        )
        resolved = attachments.resolve(parent, binding)
        valid = bool(resolved) and record["source_revision"] == attachments.revision(
            parent
        )
        report["bindings"][key] = {"anchors": len(resolved), "passed": valid}
        if key.startswith("texture_"):
            parent.data.calc_loop_triangles()
            lookup = {tuple(sorted(t.vertices)): t for t in parent.data.loop_triangles}
            errors = []
            for uv in parent.data.uv_layers:
                values = []
                for a in binding["anchors"]:
                    triangle = lookup[tuple(sorted(a["vertices"]))]
                    corner = {
                        v: np.array(uv.data[l].uv)
                        for v, l in zip(triangle.vertices, triangle.loops)
                    }
                    values.append(
                        sum(corner[v] * w for v, w in zip(a["vertices"], a["weights"]))
                    )
                errors.extend(
                    float(
                        np.max(
                            np.abs(
                                np.array(obj.data.uv_layers[uv.name].data[l.index].uv)
                                - values[l.vertex_index % len(values)]
                            )
                        )
                    )
                    for l in obj.data.loops
                )
            report["bindings"][key]["uv_error"] = max(errors, default=0)
            report["bindings"][key]["passed"] &= max(errors, default=0) <= 1e-4
    report["passed"] = (
        uv_error <= 1e-4
        and report["master_mask_error"] <= 1e-5
        and all(v["passed"] for v in report["bindings"].values())
    )
    return report


def verify(source, out, rollback=False):
    source = Path(source).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    state = nested.load()
    spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())
    nodes, checks = surface_blueprint(spec)
    if state["nodes"] != nodes or state["checks"] != checks:
        raise AssertionError("Saved recipe differs from frozen surface specification")
    initial = attributes(state)
    if not initial["passed"]:
        sculpt.dump(out / "rejected.json", initial)
        raise AssertionError("Saved attributes differ")
    old = snapshot()
    try:
        nested.update({"unknown_surface_parameter": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown parameter accepted")
    if snapshot() != old:
        raise AssertionError("Rejected update changed scene")
    did_rollback = False
    if rollback:
        reached = {"commit": False}

        def reject(phase):
            if phase == "after_commit":
                reached["commit"] = True
                raise RuntimeError("Injected surface late commit failure")

        with patch.object(nested, "_checkpoint", side_effect=reject):
            try:
                nested.update({"grip_width": state["parameters"]["grip_width"] + 0.1})
            except assembly.Rejected:
                pass
            else:
                raise AssertionError("Injected failure accepted")
        did_rollback = reached["commit"] and snapshot() == old
        if not did_rollback:
            raise AssertionError("Late commit did not restore scene")
    result = nested.update({"grip_width": state["parameters"]["grip_width"] + 0.25})
    after = attributes(nested.load())
    report = {
        "recipe_matches": True,
        "attributes_before": initial,
        "attributes_after": after,
        "unknown_parameter_rejected_unchanged": True,
        "late_commit_rollback": did_rollback,
        "followup": result,
        "source_preserved": before == hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    report["passed"] = (
        initial["passed"]
        and after["passed"]
        and result["passed"]
        and report["source_preserved"]
    )
    sculpt.dump(out / "reopen.json", report)
    if not report["passed"]:
        raise AssertionError("Follow-up acceptance failed")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "followup.blend"))
    print("SURFACE_REOPEN", report["passed"], flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    verify(args[0], args[1], "--rollback" in args)
