"""Fresh-process verification of the saved mouse, not just its construction log.

Factory Blender: -- RUN_DIRECTORY. Does not overwrite the saved model.
"""

import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    geometry,
    sculpt,
    reference,
    sections,
    shells,
    regions,
    attachments,
    fairing,
    patterns,
    candidates,
    precision,
)

root = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
audit = json.loads((root / "audit.json").read_text())
spec = json.loads((root / "target.json").read_text())
ref = json.loads((root / "reference.json").read_text())
model = root / "mouse.blend"
file_hash = hashlib.sha256(model.read_bytes()).hexdigest()
assert file_hash == audit["model_sha256"]
assert reference.fingerprint(spec) == audit["target_sha256"]
assert reference.fingerprint(ref) == audit["reference_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(model), load_ui=False, use_scripts=False)
master = bpy.data.objects["Mouse master"]
expected = np.load(root / "master-after.npy")
original = np.load(root / "master-before.npy")
np.testing.assert_array_equal(sculpt.coordinates(master), expected)
selected = regions.resolve(master, spec["local_edit"]["name"])
outside = sorted(set(range(len(expected))) - set(selected["indices"]))
np.testing.assert_array_equal(expected[outside], original[outside])
np.testing.assert_array_equal(expected[:, 1:], original[:, 1:])
key = master.data.shape_keys.key_blocks[audit["local_edit"]["layer"]]
key.value = 0
undo_error = float(np.max(np.abs(sculpt.coordinates(master) - original)))
assert undo_error < 1e-6
pattern = bpy.data.objects["Grip fitted"]
assert attachments.status(master, pattern)["status"] == "needs_refresh"
key.value = 1
np.testing.assert_array_equal(sculpt.coordinates(master), expected)
assert attachments.status(master, pattern)["status"] == "current"
palm = master.data.shape_keys.key_blocks[audit["palm_edit"]["layer"]]
assert palm.value == 0
palm_ids = regions.resolve(master, "palm support")["indices"]
accent = bpy.data.objects["Crown accent"]
accent_original = sculpt.coordinates(accent).copy()
palm.value = 1
assert attachments.status(master, accent)["status"] == "needs_refresh"
refreshed_accent = precision.refresh_seam(master, accent, "Reopened palm seam trial")
assert attachments.status(master, refreshed_accent)["status"] == "current"
assert geometry.inspect(refreshed_accent)["nonmanifold_edges"] == 0
assert fairing.overlap_candidates(refreshed_accent) == 0
accent_shift = float(
    np.linalg.norm(sculpt.coordinates(refreshed_accent) - accent_original, axis=1).max()
)
assert accent_shift > 0.5
np.testing.assert_array_equal(sculpt.coordinates(accent), accent_original)
palm_changed = sculpt.coordinates(master)
palm_outside = sorted(set(range(len(expected))) - set(palm_ids))
np.testing.assert_array_equal(palm_changed[palm_outside], expected[palm_outside])
assert float(np.max(palm_changed[:, 2] - expected[:, 2])) > 1
palm.value = 0
np.testing.assert_array_equal(sculpt.coordinates(master), expected)
old_pattern = bpy.data.objects["Grip before"]
shift = float(
    np.linalg.norm(
        np.asarray(pattern["mw_relief_anchors"]).reshape(-1, 3)
        - np.asarray(old_pattern["mw_relief_anchors"]).reshape(-1, 3),
        axis=1,
    ).max()
)
assert shift > 0.5
metrics = []
for expected_report in audit["candidates"][-1]["reports"]:
    result, _, _ = reference.evaluate(master, ref, expected_report["component"])
    for key in ["iou", "boundary_mean", "different_pixels"]:
        assert result[key] == expected_report[key]
    metrics.append(result)
sections_report = []
for c in ref["section_bounds"]:
    report = sections.compare(sections.cut(master, 1, c["y"]), c["bounds"])
    assert report["bound_error_max"] <= spec["acceptance"]["section_bound_error_max_mm"]
    sections_report.append(report)
gauges = []
for report in audit["thickness"]:
    actual = shells.thickness(
        bpy.data.objects[report["object"]], method=report["method"]
    )
    for key in ["min", "max", "samples", "missing", "passed"]:
        assert actual[key] == report[key], (key, actual, report)
    gauges.append({k: v for k, v in actual.items() if k != "violations"})
for report in audit["gaps"]:
    actual = shells.gap(*(bpy.data.objects[n] for n in report["objects"]))
    for key in ["min", "max", "samples", "passed"]:
        assert actual[key] == report[key]
for report in audit["assembly_intersections"]:
    actual = shells.intersections(*(bpy.data.objects[n] for n in report["objects"]))
    assert actual["triangle_pair_count"] == 0
for report in audit["geometry"]:
    obj = bpy.data.objects[report["object"]]
    assert geometry.inspect(obj)["nonmanifold_edges"] == 0
    assert fairing.overlap_candidates(obj) == 0

# Test the relief against the final split housing, not only its hidden master.
settings = json.loads(pattern["mw_relief_settings"])
top_count = 1 + settings["segments"] * settings["rings"]
coords = sculpt.coordinates(pattern)
top_faces = [
    tuple(p.vertices)
    for p in pattern.data.polygons
    if all(i % (2 * top_count) < top_count for i in p.vertices)
]
vertices = sorted({i for f in top_faces for i in f})
edges = {tuple(sorted((a, b))) for f in top_faces for a, b in zip(f, f[1:] + f[:1])}
probes = (
    [coords[i] for i in vertices]
    + [(coords[a] + coords[b]) / 2 for a, b in edges]
    + [coords[list(f)].mean(0) for f in top_faces]
)
tree = patterns.tree(bpy.data.objects["Upper housing"])
clearances = []
for p in probes:
    hit, n, _, distance = tree.find_nearest(Vector(p), 1.0)
    assert hit is not None, "Grip sample outside final shell"
    clearances.append((Vector(p) - hit).dot(n))
assert min(clearances) >= -1e-5, min(clearances)
# Candidate visibility restoration preserves both viewport and render flags.
names = [
    "Baseline master",
    "Mouse master",
    "Upper housing",
    "Lower housing",
    "Left button",
    "Right button",
]
snapshot = candidates.activate(["Baseline master"], names)
candidates.restore()
for name, state in snapshot.items():
    o = bpy.data.objects[name]
    assert o.hide_render == state["render"] and o.hide_get() == state["viewport"]
assert hashlib.sha256(model.read_bytes()).hexdigest() == file_hash
result = {
    "blender": bpy.app.version_string,
    "model_sha256": file_hash,
    "saved_coordinates_match": True,
    "independent_palm_layer_verified": True,
    "palm_seam_refresh_max_shift": accent_shift,
    "unchanged_vertices": len(outside),
    "undo_max_error": undo_error,
    "attachment_anchor_max_shift": shift,
    "grip_probe_count": len(probes),
    "grip_minimum_final_shell_clearance": min(clearances),
    "metrics": metrics,
    "section_error_max": max(r["bound_error_max"] for r in sections_report),
    "thickness": gauges,
    "saved_gap_reports_match": True,
    "assembly_intersections_zero": True,
    "closed_parts_checked": len(audit["geometry"]),
    "candidate_restore_verified": True,
    "saved_file_unchanged": True,
}
(root / "reopen-verification.json").write_text(json.dumps(result, indent=2))
print("MOUSE_REOPEN_OK", json.dumps(result), flush=True)
