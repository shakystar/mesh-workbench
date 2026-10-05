"""Reopen the attachment study and verify update/undo attachment behavior."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import attachments, fairing, geometry, patterns, sculpt

folder = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(
    filepath=str(folder / "ray.blend"), load_ui=False, use_scripts=False
)
body = bpy.data.objects["Ray body"]
old = bpy.data.objects["Bound spots"]
new = bpy.data.objects["Refreshed spots"]
report = json.loads((folder / "report.json").read_text())
assert attachments.status(body, old)["status"] == "needs_refresh"
assert attachments.status(body, new)["status"] == "current"
binding = json.loads(new["mw_surface_binding"])
hits = attachments.resolve(body, binding)
projected = patterns.project(body, [h["position"] for h in hits], 0.05)
anchors = np.array(new["mw_relief_anchors"]).reshape(-1, 3)
error = float(
    np.linalg.norm(anchors - np.array([h["position"] for h in projected]), axis=1).max()
)
assert error < 1e-5
old_coords = sculpt.coordinates(old).copy()
sculpt.set_layer(body, report["edit"]["layer"], 0)
assert attachments.status(body, old)["status"] == "current"
assert attachments.status(body, new)["status"] == "needs_refresh"
restored = attachments.refresh_relief(body, new, "Restored check")
restore_error = float(
    np.linalg.norm(sculpt.coordinates(restored) - old_coords, axis=1).max()
)
assert restore_error < 1e-4
bpy.data.objects.remove(restored, do_unlink=True)
sculpt.set_layer(body, report["edit"]["layer"], 1)
assert attachments.status(body, new)["status"] == "current"
assert (
    fairing.overlap_candidates(new) == 0
    and geometry.inspect(new)["nonmanifold_edges"] == 0
)
result = {
    "reopened_statuses_verified": True,
    "anchor_projection_max_error": error,
    "undo_regeneration_max_vertex_error": restore_error,
    "old_pattern_unchanged": bool(np.array_equal(old_coords, sculpt.coordinates(old))),
}
(folder / "reopen-verification.json").write_text(json.dumps(result, indent=2))
print("ATTACHMENT_REOPEN_OK", result)
