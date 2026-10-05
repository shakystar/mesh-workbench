"""Reopen the product studies and collect evaluated geometry and pixel evidence."""

import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import surface
from mesh_workbench.runner import camera

root = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
report = {}
for name in ["field-robot", "work-lantern"]:
    folder = root / name
    bpy.ops.wm.open_mainfile(
        filepath=str(folder / "model.blend"), load_ui=False, use_scripts=False
    )
    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name.startswith("Studio floor"):
            continue
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        coords = np.array([obj.matrix_world @ v.co for v in mesh.vertices])
        rows.append(
            {
                "object": obj.name,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.polygons),
                "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                "finite": bool(np.isfinite(coords).all()),
                "bounds": [coords.min(axis=0).tolist(), coords.max(axis=0).tolist()],
            }
        )
        bm.free()
        evaluated.to_mesh_clear()
    entry = {"parts": rows, "pixel_samples": []}
    assert all(r["finite"] and r["nonmanifold_edges"] == 0 for r in rows)
    if name == "field-robot":
        shell = bpy.data.objects["Vented shell"]
        graph = bpy.context.evaluated_depsgraph_get()
        hits = []
        for y in [0.03, 0.115]:
            hit, point, normal, face = shell.ray_cast(
                shell.matrix_world.inverted() @ Vector((2, y, 1.97)),
                Vector((-1, 0, 0)),
                depsgraph=graph,
            )
            assert hit
            hits.append(list(shell.matrix_world @ point))
        assert hits[1][0] - hits[0][0] > 0.1, hits
        entry["vent_recess_depth"] = hits[1][0] - hits[0][0]
    scale = 5.6 if name == "field-robot" else 4.5
    for view, pos in [
        ("coordinate-front", (4, -6, 3.7)),
        ("coordinate-side", (6, 0, 2.5)),
    ]:
        camera(pos, (0, 0, 1.45), scale, (320, 320))
        dest = folder / view
        info = surface.capture(dest, render=True)
        with np.load(dest / "surface.npz") as data:
            for ident, objname in info["objects"].items():
                if objname.startswith(
                    ("Vented shell", "Lens_", "Diffuser_", "Battery housing")
                ):
                    ys, xs = np.where(data["object_id"] == int(ident))
                    if len(xs):
                        i = len(xs) // 2
                        entry["pixel_samples"].append(
                            surface.read_pixel(dest, [int(xs[i]), int(ys[i])])
                        )
    report[name] = entry
(root / "evaluated-review.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("EVALUATED_REVIEW_OK", {k: len(v["parts"]) for k, v in report.items()})
