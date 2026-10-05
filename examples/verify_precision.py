"""Fresh-process audit of a saved precision study. Use -- SOURCE RUN_DIRECTORY."""

import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    reference,
    regions,
    candidates,
    sculpt,
    geometry,
    fairing,
    attachments,
)

source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
root = Path(sys.argv[sys.argv.index("--") + 2]).resolve()
audit = json.loads((root / "audit.json").read_text())
spec = json.loads((root / "target.json").read_text())
model = root / "refined-speaker.blend"
model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
assert hashlib.sha256(source.read_bytes()).hexdigest() == audit["source_sha256"]
assert reference.fingerprint(spec) == audit["target_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
original = {
    o.name: sculpt.coordinates(o) for o in bpy.context.scene.objects if o.type == "MESH"
}
bpy.ops.wm.open_mainfile(filepath=str(model), load_ui=False, use_scripts=False)
for name, coords in original.items():
    np.testing.assert_array_equal(sculpt.coordinates(bpy.data.objects[name]), coords)
metrics = []
selected = next(c for c in audit["candidates"] if c["name"] == audit["selected"])
for expected in selected["reports"]:
    actual, _, _ = reference.evaluate(
        bpy.data.objects[expected["object"]], spec, expected["component"], supersample=2
    )
    for key in ["iou", "boundary_mean", "boundary_max", "different_pixels"]:
        assert actual[key] == expected[key], (key, actual, expected)
    metrics.append(actual)
for expected in audit["geometry"]:
    o = bpy.data.objects[expected["object"]]
    actual = geometry.inspect(o)
    assert actual["nonmanifold_edges"] == 0 and actual["finite"]
    assert fairing.overlap_candidates(o) == 0
    assert actual["vertices"] == expected["vertices"]
grip = bpy.data.objects["Refined grip"]
ids = regions.resolve(grip, "grip crown")["indices"]
assert len(ids) == len(grip.data.vertices)
key = grip.data.shape_keys.key_blocks[audit["grip_edit"]["layer"]]
after = sculpt.coordinates(grip)
key.value = 0
before = sculpt.coordinates(grip)
# All vertices sharing one sampled cross section must move by one translation.
ring_count = 41 * 48
delta = (after - before)[:ring_count].reshape(41, 48, 3)
section_error = float(np.max(np.abs(delta - delta[:, :1, :])))
assert section_error < 3e-7, section_error
assert float(np.max(np.abs(delta[:, :, :2]))) == 0
key.value = 1
np.testing.assert_array_equal(sculpt.coordinates(grip), after)
seam = bpy.data.objects["Grip seam fitted"]
assert attachments.status(grip, seam)["status"] == "current"
visibility = {o.name: (o.hide_render, o.hide_get()) for o in bpy.context.scene.objects}
snapshot = candidates.restore()
for name, state in snapshot.items():
    assert bpy.data.objects[name].hide_render == state["render"]
    assert bpy.data.objects[name].hide_get() == state["viewport"]
for name in set(visibility) - set(snapshot):
    assert (
        bpy.data.objects[name].hide_render,
        bpy.data.objects[name].hide_get(),
    ) == visibility[name]
assert hashlib.sha256(model.read_bytes()).hexdigest() == model_hash
result = {
    "blender": bpy.app.version_string,
    "model_sha256": model_hash,
    "original_mesh_objects_unchanged": len(original),
    "saved_metrics_match": metrics,
    "visible_parts_checked": len(audit["geometry"]),
    "named_region_persisted": True,
    "profile_section_translation_error": section_error,
    "seam_binding_current": True,
    "candidate_visibility_restored": True,
    "saved_file_unchanged": True,
}
(root / "reopen-verification.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print("PRECISION_REOPEN_OK", json.dumps(result), flush=True)
