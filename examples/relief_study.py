"""Compare dense/sparse conforming relief patterns on the saved ray."""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import fairing, geometry, relief, sculpt
from mesh_workbench.runner import camera

args = sys.argv[sys.argv.index("--") + 1 :]
source = Path(args[0]).resolve()
out = Path(args[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
body = bpy.data.objects["Ray body"]
before = sculpt.coordinates(body).copy()
mat = bpy.data.materials.new("Porcelain spots")
mat.diffuse_color = (0.62, 0.78, 0.69, 1)
mat.use_nodes = True
bs = mat.node_tree.nodes.get("Principled BSDF")
bs.inputs["Base Color"].default_value = (0.62, 0.78, 0.69, 1)
bs.inputs["Roughness"].default_value = 0.34
report = {"source_sha256": source_hash, "designs": {}}
for variant, rows, step, radius in [
    ("dense", 3, 0.17, 0.061),
    ("sparse", 2, 0.21, 0.045),
]:
    points = []
    radii = []
    for sign in [-1, 1]:
        for row in range(rows):
            for i in range(8):
                x = 0.6 + i * step
                y = -0.74 + i * 0.12 + row * 0.19
                points.append((sign * x, y, 2))
                radii.append(radius * (0.65 + 0.35 * math.sin((i + 1) * math.pi / 9)))
    obj = relief.dots(
        body,
        points,
        "Pattern " + variant,
        radii,
        height=0.003,
        embed=0.0015,
        max_distance=2,
        direction=(0, 0, -1),
        gap=0.01,
    )
    obj.data.materials.append(mat)
    stats = geometry.inspect(obj)
    components = fairing.components(obj)
    assert stats["nonmanifold_edges"] == 0 and len(components) == len(points)
    assert fairing.overlap_candidates(obj) == 0
    np.testing.assert_array_equal(before, sculpt.coordinates(body))
    report["designs"][variant] = {
        "count": len(points),
        "minimum_sampled_clearance": obj["mw_relief_sampled_clearance"],
        "geometry": stats,
        "components": len(components),
        "overlap_candidates": 0,
    }
    for name, pos, target, scale in [
        ("whole", (4, -6, 5), (0, 0.6, 1), 7),
        ("detail", (2, -3, 4), (1.1, -0.05, 1.15), 2.9),
    ]:
        camera(pos, target, scale, (640, 640))
        bpy.context.scene.cycles.samples = 32
        bpy.context.scene.cycles.use_denoising = True
        bpy.context.scene.render.filepath = str(out / (variant + "-" + name + ".png"))
        bpy.ops.render.render(write_still=True)
    camera((4, -6, 5), (0, 0.6, 1), 7, (640, 640))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / (variant + ".blend")))
    obj.hide_render = True
    obj.hide_set(True)
assert source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
report["body_unchanged"] = True
(out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("RELIEF_STUDY_OK")
