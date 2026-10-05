"""Verify saved organic edits against recorded vertex arrays in a fresh process."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import geometry, sculpt

folder = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(
    filepath=str(folder / "ray.blend"), load_ui=False, use_scripts=False
)
obj = bpy.data.objects["Ray body"]
report = json.loads((folder / "report.json").read_text())
with np.load(folder / "deformation.npz") as data:
    before = data["before"]
    after = data["after"]
np.testing.assert_allclose(sculpt.coordinates(obj), after, atol=1e-6)
sculpt.set_layer(obj, report["edit"]["layer"], 0)
np.testing.assert_allclose(sculpt.coordinates(obj), before, atol=1e-6)
sculpt.set_layer(obj, report["edit"]["layer"], 1)
np.testing.assert_allclose(sculpt.coordinates(obj), after, atol=1e-6)
center = np.abs(before[:, 0]) < 0.2
assert center.any()
np.testing.assert_array_equal(before[center], after[center])
tree = KDTree(len(before))
for i, co in enumerate(before):
    tree.insert(Vector(co), i)
tree.balance()
errors = []
delta = after - before
for i, co in enumerate(before):
    mirrored = co.copy()
    mirrored[0] *= -1
    _, j, dist = tree.find(Vector(mirrored))
    assert dist < 1e-5
    expected = delta[i].copy()
    expected[0] *= -1
    errors.append(float(np.linalg.norm(delta[j] - expected)))
assert max(errors) < 1e-5
stats = geometry.inspect(obj)
assert stats["finite"] and stats["nonmanifold_edges"] == 0
result = {
    "saved_layer_matches": True,
    "restored_base_matches": True,
    "unaffected_center_vertices": int(center.sum()),
    "mirror_delta_max_error": max(errors),
    "geometry": stats,
}
(folder / "reopen-verification.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print("REOPEN_VERIFIED", result["unaffected_center_vertices"], max(errors))
