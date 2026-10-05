"""Independent saved join and rejected-edit rollback verification."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import fairing, geometry, sculpt

folder = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(
    filepath=str(folder / "ray.blend"), load_ui=False, use_scripts=False
)
obj = bpy.data.objects["Continuous ray"]
report = json.loads((folder / "report.json").read_text())
with np.load(folder / "deformation.npz") as d:
    before = d["before"]
    after = d["after"]
np.testing.assert_allclose(sculpt.coordinates(obj), after, atol=1e-6)
sculpt.set_layer(obj, report["edit"]["layer"], 0)
np.testing.assert_allclose(sculpt.coordinates(obj), before, atol=1e-6)
keys = len(obj.data.shape_keys.key_blocks)
history = obj["mw_layers"]
try:
    fairing.region(obj, [0, 1.43, 1], 0.43, iterations=14)
except ValueError as exc:
    assert "overlaps" in str(exc)
else:
    raise AssertionError("Unsafe fairing was accepted")
np.testing.assert_allclose(sculpt.coordinates(obj), before, atol=1e-6)
assert keys == len(obj.data.shape_keys.key_blocks) and history == obj["mw_layers"]
sculpt.set_layer(obj, report["edit"]["layer"], 1)
np.testing.assert_allclose(sculpt.coordinates(obj), after, atol=1e-6)
assert len(fairing.components(obj)) == 1 and fairing.overlap_candidates(obj) == 0
assert geometry.inspect(obj)["nonmanifold_edges"] == 0
(folder / "reopen-verification.json").write_text(
    json.dumps(
        {
            "saved_arrays_match": True,
            "rejected_edit_preserves_coordinates_keys_history": True,
            "components": 1,
            "overlap_candidates": 0,
        },
        indent=2,
    )
)
print("JOIN_REOPEN_AND_REJECTION_VERIFIED")
