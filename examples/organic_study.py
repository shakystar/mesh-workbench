"""Organic ray study and reversible coordinate sculpt. Run with -- NEW_OUTPUT."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import geometry, models, sculpt, surface
from mesh_workbench.runner import camera
from mesh_workbench.sweep import sweep

OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, metal=0, rough=0.4):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return m


def finish(ob, material):
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def subdivide(ob, level=2):
    models.activate(ob)
    mod = ob.modifiers.new("Section fairing", "SUBSURF")
    mod.levels = level
    bpy.ops.object.modifier_apply(modifier=mod.name)


teal = mat("Deep teal ceramic", (0.018, 0.22, 0.23), 0.3, 0.3)
cream = mat("Warm porcelain underside", (0.6, 0.68, 0.61), 0.12, 0.45)
black = mat("Eye obsidian", (0.008, 0.018, 0.023), 0.4, 0.14)
gold = mat("Iris copper", (0.8, 0.31, 0.075), 0.65, 0.26)
# Sections describe the swept wing planform; camber is built into the base mesh.
rows = [
    (-1.5, 0.06, 0.07),
    (-1.43, 0.4, 0.12),
    (-1.25, 0.78, 0.2),
    (-1.03, 1.0, 0.25),
    (-0.72, 1.35, 0.28),
    (-0.35, 1.9, 0.27),
    (0, 2.5, 0.24),
    (0.25, 2.64, 0.19),
    (0.47, 2.15, 0.17),
    (0.7, 1.5, 0.15),
    (0.95, 0.87, 0.13),
    (1.2, 0.4, 0.1),
    (1.4, 0.14, 0.07),
    (1.48, 0.045, 0.035),
]
continuous = "--continuous" in sys.argv
centers = [(0, y, 1.0) for y, w, h in rows]
sizes = [(w, h) for y, w, h in rows]
if continuous:
    rows = rows[:-1]
    centers = [(0, y, 1.0) for y, w, h in rows] + [
        (0, 1.65, 1),
        (0, 2.05, 1.04),
        (0.25, 2.48, 1.17),
        (0.38, 2.86, 1.39),
        (0.48, 3.12, 1.6),
    ]
    sizes = [(w, h) for y, w, h in rows] + [
        (0.06, 0.04),
        (0.044, 0.029),
        (0.033, 0.024),
        (0.023, 0.018),
        (0.008, 0.008),
    ]
body = finish(
    sweep("Ray body", centers, sizes, 64),
    teal,
)
body.data.materials.append(cream)
for i, (y, w, h) in enumerate(rows):
    for j in range(64):
        v = body.data.vertices[i * 64 + j]
        v.co.z += 0.16 * min(1.0, w) ** 2 * (abs(v.co.x) / w) ** 4
for p in body.data.polygons:
    if p.index < (len(centers) - 1) * 64 and p.index % 64 < 32:
        p.material_index = 1
    elif p.index >= (len(centers) - 1) * 64:
        center = sum((body.data.vertices[i].co for i in p.vertices), Vector()) / len(
            p.vertices
        )
        if center.z < 1.0:
            p.material_index = 1
subdivide(body, 2)
# A thin tapering tail curves upward instead of remaining a straight cylinder.
if not continuous:
    tail = finish(
        sweep(
            "Tail",
            [
                (0, 1.42, 1),
                (0.03, 1.65, 1.0),
                (0.13, 2.05, 1.04),
                (0.25, 2.48, 1.17),
                (0.38, 2.86, 1.39),
                (0.48, 3.12, 1.6),
            ],
            [
                (0.054, 0.039),
                (0.05, 0.032),
                (0.044, 0.029),
                (0.033, 0.024),
                (0.023, 0.018),
                (0.008, 0.008),
            ],
            24,
        ),
        teal,
    )
    subdivide(tail, 2)
for sign in [-1, 1]:
    finish(
        models.primitive(
            "sphere",
            "Eye " + str(sign),
            location=(sign * 0.43, -1.10, 1.214),
            scale=(0.15, 0.16, 0.11),
            segments=32,
            rings=16,
        ),
        black,
    )
    finish(
        models.primitive(
            "sphere",
            "Iris " + str(sign),
            location=(sign * 0.43, -1.202, 1.255),
            scale=(0.071, 0.038, 0.066),
        ),
        gold,
    )
    finish(
        models.primitive(
            "sphere",
            "Pupil " + str(sign),
            location=(sign * 0.43, -1.227, 1.26),
            scale=(0.022, 0.016, 0.047),
        ),
        black,
    )
# Neutral display stand makes the intentional airborne pose explicit.
standmat = mat("Stand graphite", (0.027, 0.04, 0.053), 0.5, 0.4)
finish(
    models.primitive(
        "cylinder",
        "Display plinth",
        location=(0, 0.1, 0.08),
        scale=(1.0, 0.8, 0.08),
        segments=64,
    ),
    standmat,
)
finish(
    models.primitive(
        "cylinder",
        "Support",
        location=(0, 0.1, 0.51),
        scale=(0.11, 0.11, 0.42),
        segments=32,
    ),
    standmat,
)
finish(
    models.primitive("plane", "Floor", scale=(200, 200, 200)),
    mat("Studio", (0.065, 0.09, 0.105), 0, 0.7),
)
for name, pos, power, size in [
    ("Key", (-4, -3, 7), 1300, 5),
    ("Rim", (4, 4, 6), 1700, 4),
    ("Fill", (2, -5, 2), 350, 3),
]:
    light = bpy.data.lights.new(name, "AREA")
    light.energy = power
    light.size = size
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (
        (Vector((0, 0, 1)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def shot(folder, pos, target=(0, 0.6, 1), scale=7, size=640, mapping=False):
    camera(pos, target, scale, (size, size))
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.use_denoising = True
    if mapping:
        return surface.capture(OUT / folder, render=True)
    (OUT / folder).mkdir()
    bpy.context.scene.render.filepath = str(OUT / folder / "render.png")
    bpy.ops.render.render(write_still=True)


shot("before", (4, -6, 5))
# Pixel selection uses the saved geometry map, never a screen guess.
info = shot("map-before", (0, -5, 6), scale=6.6, size=384, mapping=True)
with np.load(OUT / "map-before" / "surface.npz") as data:
    ident = next(int(k) for k, v in info["objects"].items() if v == body.name)
    target = np.array([1.95, 0.12, 1.22])
    valid = data["object_id"] == ident
    distances = np.where(valid, np.linalg.norm(data["world"] - target, axis=2), np.inf)
    y, x = np.unravel_index(np.argmin(distances), distances.shape)
    pixel = [int(x), int(y)]
before = sculpt.coordinates(body).copy()
sample = surface.read_pixel(OUT / "map-before", pixel)
command = {
    "object": body.name,
    "mode": "grab",
    "points": [pixel, [pixel[0] + 8, pixel[1] - 24]],
    "radius": 1.6,
    "strength": 0.7,
    "metric": "sphere",
    "symmetry_x": True,
    "label": "Raised wing tips",
}
edit = sculpt.path_stroke(OUT / "map-before", command)
after = sculpt.coordinates(body).copy()
assert edit["changed_vertices"] > 100 and edit["max_displacement"] > 0.1
sculpt.set_layer(body, edit["layer"], 0)
assert np.allclose(sculpt.coordinates(body), before, atol=1e-6)
sculpt.set_layer(body, edit["layer"], 1)
assert np.allclose(sculpt.coordinates(body), after, atol=1e-6)
# Old revision must become unusable after the edit.
try:
    sculpt.Surface(OUT / "map-before").point(pixel, body.name)
except ValueError:
    stale_rejected = True
else:
    raise AssertionError("Stale capture accepted")
shot("after", (4, -6, 5))
shot("junction", (3, 4, 3), (0, 1.38, 1.03), 1.65)
shot("side", (6, -0.5, 2.2))
shot("map-after", (0, -5, 6), scale=6.6, size=384, mapping=True)
camera((4, -6, 5), (0, 0.6, 1), 7, (640, 640))
np.savez_compressed(OUT / "deformation.npz", before=before, after=after)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "ray.blend"))
report = {
    "blender": bpy.app.version_string,
    "continuous": continuous,
    "hit": sample,
    "edit": edit,
    "stale_rejected": stale_rejected,
    "layer_restore_verified": True,
    "mesh": geometry.inspect(body),
    "changed_max": float(np.linalg.norm(after - before, axis=1).max()),
    "limitations": [
        "static decorative study",
        "continuous tail" if continuous else "tail is separate overlapping mesh",
        "no self-intersection or rig clearance proof",
    ],
}
(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
(OUT / "source.py").write_text(Path(__file__).read_text(), encoding="utf-8")
print("ORGANIC_STUDY_OK", edit["changed_vertices"])
