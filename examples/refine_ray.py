"""Source-preserving union and local fairing of the organic ray tail."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import fairing, geometry, models, sculpt
from mesh_workbench.runner import camera

args = sys.argv[sys.argv.index("--") + 1 :]
source = Path(args[0]).resolve()
out = Path(args[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
body = bpy.data.objects["Ray body"]
tail = bpy.data.objects["Tail"]
body_before = sculpt.coordinates(body).copy()
tail_before = sculpt.coordinates(tail).copy()
print(
    "INPUT_OVERLAPS",
    fairing.overlap_candidates(body),
    fairing.overlap_candidates(tail),
    flush=True,
)


def render(name, pos=(3, 4, 3), target=(0, 1.38, 1.03), scale=1.65):
    camera(pos, target, scale, (640, 640))
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.use_denoising = True
    bpy.context.scene.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)


render("before")
joined = models.boolean(body, tail, "UNION", "Continuous ray")
for ob in [body, tail]:
    ob.hide_render = True
    ob.hide_set(True)
assert len(fairing.components(joined)) == 1
assert geometry.inspect(joined)["nonmanifold_edges"] == 0
render("union")
before = sculpt.coordinates(joined).copy()
attempts = []
for steps, positive, negative in [
    (14, 0.5, -0.53),
    (8, 0.25, -0.26),
    (4, 0.15, -0.151),
    (2, 0.08, -0.081),
]:
    try:
        edit = fairing.region(
            joined,
            [0, 1.43, 1],
            0.43,
            iterations=steps,
            positive=positive,
            negative=negative,
        )
        attempts.append({"iterations": steps, "positive": positive, "accepted": True})
        break
    except ValueError as exc:
        attempts.append(
            {
                "iterations": steps,
                "positive": positive,
                "accepted": False,
                "reason": str(exc),
            }
        )
        np.testing.assert_allclose(sculpt.coordinates(joined), before, atol=1e-6)
else:
    raise ValueError("No intersection-free fairing candidate")
after = sculpt.coordinates(joined).copy()
sculpt.set_layer(joined, edit["layer"], 0)
np.testing.assert_allclose(sculpt.coordinates(joined), before, atol=1e-6)
sculpt.set_layer(joined, edit["layer"], 1)
np.testing.assert_allclose(sculpt.coordinates(joined), after, atol=1e-6)
np.testing.assert_array_equal(body_before, sculpt.coordinates(body))
np.testing.assert_array_equal(tail_before, sculpt.coordinates(tail))
outside = np.linalg.norm(before - [0, 1.43, 1], axis=1) >= 0.43
np.testing.assert_array_equal(before[outside], after[outside])
render("after")
render("whole", (4, -6, 5), (0, 0.6, 1), 7)
np.savez_compressed(out / "deformation.npz", before=before, after=after)
bpy.ops.wm.save_as_mainfile(filepath=str(out / "ray.blend"))
assert source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
report = {
    "fairing_attempts": attempts,
    "source_sha256": source_hash,
    "edit": edit,
    "components": fairing.components(joined),
    "geometry": geometry.inspect(joined),
    "unchanged_outside_region": int(outside.sum()),
    "source_meshes_unchanged": True,
    "overlap_candidates": fairing.overlap_candidates(joined),
}
(out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("TAIL_JOIN_OK", report)
