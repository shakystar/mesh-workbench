"""Change a sculpted wing pose and regenerate its bound reliefs."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import attachments, fairing, geometry, relief, sculpt, surface
from mesh_workbench.runner import camera

args = sys.argv[sys.argv.index("--") + 1 :]
source = Path(args[0]).resolve()
out = Path(args[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
body = bpy.data.objects["Ray body"]
points = []
for sign in [-1, 1]:
    for row in range(2):
        for i in range(8):
            points.append([sign * (0.65 + i * 0.19), -0.65 + i * 0.1 + row * 0.19, 2])
old = relief.dots(
    body,
    points,
    "Bound spots",
    radii=0.038,
    height=0.003,
    embed=0.0015,
    direction=[0, 0, -1],
    max_distance=2,
    clearance=0.002,
    gap=0.01,
)
old.data.materials.append(body.data.materials[1])
original_pattern = sculpt.coordinates(old).copy()
attachments.bind_relief(body, old)
assert attachments.status(body, old)["status"] == "current"


def render(name):
    camera((4, -6, 5), (0, 0.6, 1), 7, (640, 640))
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.use_denoising = True
    bpy.context.scene.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)


render("before")
camera((0, -5, 6), (0, 0.6, 1), 6.6, (384, 384))
info = surface.capture(out / "edit-map", render=True)
with np.load(out / "edit-map" / "surface.npz") as data:
    ident = next(int(k) for k, v in info["objects"].items() if v == body.name)
    d = np.where(
        data["object_id"] == ident,
        np.linalg.norm(data["world"] - [1.85, 0.05, 1.35], axis=2),
        np.inf,
    )
    y, x = np.unravel_index(np.argmin(d), d.shape)
edit = sculpt.path_stroke(
    out / "edit-map",
    {
        "object": body.name,
        "mode": "grab",
        "points": [[int(x), int(y)], [int(x), int(y) - 28]],
        "radius": 1.2,
        "metric": "sphere",
        "strength": 0.65,
        "symmetry_x": True,
        "label": "Second wing pose",
    },
)
assert attachments.status(body, old)["status"] == "needs_refresh"
render("stale")
new = attachments.refresh_relief(body, old, "Refreshed spots")
old.hide_render = True
old.hide_set(True)
assert attachments.status(body, new)["status"] == "current"
np.testing.assert_array_equal(original_pattern, sculpt.coordinates(old))
assert fairing.overlap_candidates(body) == 0 and fairing.overlap_candidates(new) == 0
assert geometry.inspect(new)["nonmanifold_edges"] == 0
render("updated")
bpy.ops.wm.save_as_mainfile(filepath=str(out / "ray.blend"))
report = {
    "source_sha256": source_hash,
    "edit": edit,
    "old_pattern_preserved": True,
    "old_status": attachments.status(body, old),
    "new_status": attachments.status(body, new),
    "clearance": new["mw_relief_sampled_clearance"],
    "components": len(fairing.components(new)),
    "overlap_candidates": 0,
}
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
(out / "report.json").write_text(json.dumps(report, indent=2))
print("ATTACHMENT_STUDY_OK", report)
