"""Asset-free product studies. Run inside factory-startup Blender; -- OUTPUT_DIR."""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import construction as c
from mesh_workbench import geometry as g
from mesh_workbench import models as m
from mesh_workbench.runner import camera

OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.mkdir(parents=True, exist_ok=False)


def material(name, color, metallic=0, roughness=0.38, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    if emission:
        bs.inputs["Emission Color"].default_value = (*color, 1)
        bs.inputs["Emission Strength"].default_value = emission
    return mat


def finish(obj, mat):
    obj.data.materials.append(mat)
    return obj


def unique(name):
    i = 1
    while name + f"_{i:03}" in bpy.data.objects:
        i += 1
    return name + f"_{i:03}"


def box(name, dims, pos, mat, r=0.04):
    return finish(c.rounded_box(unique(name), dims, pos, r), mat)


def rod(name, a, b, r, mat):
    return finish(c.strut(unique(name), a, b, r), mat)


def lathe(name, profile, pos, mat, closed=False):
    return finish(c.revolve(unique(name), profile, location=pos, closed=closed), mat)


def ring(name, r, w, depth, pos, mat, axis=(0, 0, 1)):
    ob = lathe(
        name,
        [(r - w, -depth / 2), (r, -depth / 2), (r, depth / 2), (r - w, depth / 2)],
        pos,
        mat,
        True,
    )
    ob.rotation_euler = Vector(axis).to_track_quat("Z", "Y").to_euler()
    return ob


def label(text, pos, size, mat, rotation=(math.pi / 2, 0, 0)):
    data = bpy.data.curves.new(text, "FONT")
    data.body = text
    data.size = size
    data.extrude = 0.0005
    ob = bpy.data.objects.new(text, data)
    bpy.context.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = rotation
    data.materials.append(mat)


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    global ivory, black, metal, orange, glass, light
    ivory = material("Ceramic enamel", (0.66, 0.73, 0.69), 0.25)
    black = material("Graphite elastomer", (0.021, 0.031, 0.038), 0.05, 0.6)
    metal = material("Machined aluminium", (0.27, 0.33, 0.35), 0.85, 0.25)
    orange = material("Safety orange", (0.95, 0.18, 0.035), 0.18)
    glass = material("Optical coating", (0.014, 0.085, 0.11), 0.7, 0.15)
    light = material("LED", (0.2, 0.75, 1), 0.2, 0.2, 3)
    floor = material("Backdrop", (0.075, 0.105, 0.13), 0, 0.65)
    box("Studio floor", (200, 200, 0.2), (0, 0, -0.1), floor, 0.02)
    for name, pos, power, size in [
        ("Key", (-3, -4, 7), 1100, 5),
        ("Rim", (4, 3, 6), 1500, 4),
        ("Fill", (4, -3, 2), 500, 3),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "DISK"
        data.size = size
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = pos
        ob.rotation_euler = (
            (Vector((0, 0, 1)) - ob.location).to_track_quat("-Z", "Y").to_euler()
        )


def robot():
    setup()
    box("Structural belly", (2.15, 2.55, 0.45), (0, 0, 1.28), black, 0.18)
    shell = box("Upper shell", (2.2, 2.65, 0.83), (0, 0, 1.91), ivory, 0.24)
    box("Gasket", (2.18, 2.63, 0.085), (0, 0, 1.51), orange, 0.035)
    box("Top service hatch", (1.32, 1.62, 0.08), (0, 0.12, 2.337), metal, 0.035)
    box("Sensor fascia", (1.48, 0.15, 0.49), (0, -1.31, 1.96), black, 0.065)
    for x in [-0.42, 0.42]:
        ring("Lens bezel", 0.205, 0.043, 0.11, (x, -1.42, 1.98), metal, (0, -1, 0))
        lens = lathe(
            "Lens",
            [(0.154, -0.018), (0.161, 0), (0.154, 0.025)],
            (x, -1.48, 1.98),
            glass,
        )
        lens.rotation_euler = (math.pi / 2, 0, 0)
        rod(
            "Lens glint",
            (x - 0.035, -1.506, 2.02),
            (x - 0.035, -1.513, 2.02),
            0.018,
            light,
        )
    for x in [-1, 1]:
        for y in [-0.88, 0.9]:
            hip = (x * 1.07, y, 1.38)
            knee = (x * 1.59, y * 1.23, 0.85)
            ankle = (x * 1.49, y * 1.43, 0.32)
            rod("Hip axle", (x * 0.98, y, 1.38), (x * 1.3, y, 1.38), 0.23, metal)
            rod("Upper leg", hip, knee, 0.16, ivory)
            rod("Lower piston", knee, ankle, 0.11, metal)
            ring("Knee collar", 0.205, 0.065, 0.17, knee, orange, (1, 0, 0))
            rod(
                "Knee axle",
                (knee[0] - 0.1, knee[1], knee[2]),
                (knee[0] + 0.1, knee[1], knee[2]),
                0.13,
                black,
            )
            rod(
                "Knee bolt",
                (knee[0] - 0.111, knee[1], knee[2]),
                (knee[0] + 0.111, knee[1], knee[2]),
                0.06,
                metal,
            )
            box("Foot", (0.57, 0.7, 0.25), (ankle[0], ankle[1], 0.13), black, 0.095)
            for j in range(4):
                box(
                    "Foot tread",
                    (0.59, 0.055, 0.045),
                    (ankle[0], ankle[1] - 0.23 + j * 0.15, 0.055),
                    metal,
                    0.018,
                )
    cutters = []
    for x in [-1, 1]:
        for j in range(7):
            cutters.append(
                box(
                    "Vent cutter",
                    (0.27, 0.085, 0.22),
                    (x * 1.105, -0.48 + j * 0.17, 1.97),
                    black,
                    0.018,
                )
            )
        box("Vent backing", (0.018, 1.24, 0.29), (x * 0.975, 0.03, 1.97), black, 0.008)
    cutter = m.combine(cutters, "Vent tool")
    m.boolean(shell, cutter, "DIFFERENCE", "Vented shell")
    for ob in [shell, cutter] + cutters:
        ob.hide_render = True
        ob.hide_set(True)
    box("Rear service gasket", (1.22, 0.035, 0.48), (0, 1.328, 1.92), black, 0.014)
    box("Rear service cover", (1.13, 0.045, 0.39), (0, 1.355, 1.92), metal, 0.02)
    for x in [-0.4, 0.4]:
        ring("Rear port bezel", 0.094, 0.023, 0.05, (x, 1.394, 1.94), black, (0, 1, 0))
    label("POWER / DATA", (0.29, 1.402, 1.82), 0.066, ivory, (math.pi / 2, 0, math.pi))
    for x in [-0.51, 0.51]:
        for y in [-0.49, 0.74]:
            rod("Hatch screw", (x, y, 2.376), (x, y, 2.391), 0.039, black)
            box("Screw slot", (0.045, 0.008, 0.003), (x, y, 2.394), metal, 0.001)
    rod("Antenna", (0, 0.94, 2.3), (0, 1.03, 3.0), 0.027, metal)
    rod("Antenna boot", (0, 0.93, 2.29), (0, 0.96, 2.54), 0.064, black)
    label("FIELD / 04", (-0.51, -1.333, 1.64), 0.105, ivory)
    return (0, 0, 1.45), 5.6


def lantern():
    setup()
    lathe(
        "Base profile",
        [(0.67, 0.03), (0.77, 0.13), (0.77, 0.28), (0.72, 0.35), (0.64, 0.39)],
        (0, 0, 0),
        black,
    )
    lathe(
        "Battery housing",
        [(0.64, 0.35), (0.68, 0.42), (0.68, 0.83), (0.60, 0.94)],
        (0, 0, 0),
        orange,
    )
    lathe(
        "Diffuser",
        [(0.53, 0.92), (0.56, 1.03), (0.56, 2.02), (0.51, 2.12)],
        (0, 0, 0),
        material("Warm diffuser", (0.9, 0.77, 0.46), 0, 0.38, 0.7),
    )
    lathe(
        "Roof profile",
        [(0.55, 2.05), (0.74, 2.1), (0.76, 2.18), (0.64, 2.3), (0.35, 2.36)],
        (0, 0, 0),
        ivory,
    )
    for j in range(8):
        a = 2 * math.pi * j / 8
        x, y = 0.605 * math.cos(a), 0.605 * math.sin(a)
        rod("Protective cage", (x, y, 0.86), (x, y, 2.14), 0.032, metal)
    for z in [0.4, 0.43, 0.81, 0.84]:
        ring("Housing seam", 0.685, 0.014, 0.012, (0, 0, z), black)
    for j in range(32):
        a = 2 * math.pi * j / 32
        if math.sin(a) < -0.88:
            continue
        rod(
            "Battery grip rib",
            (0.682 * math.cos(a), 0.682 * math.sin(a), 0.49),
            (0.682 * math.cos(a), 0.682 * math.sin(a), 0.75),
            0.013,
            black,
        )
    for z in [0.96, 1.16, 1.82, 2.06]:
        ring("Diffuser band", 0.582, 0.027, 0.025, (0, 0, z), metal)
    for x in [-0.73, 0.73]:
        rod("Handle pivot", (x - 0.06, 0, 2.17), (x + 0.06, 0, 2.17), 0.1, metal)
        rod("Handle upright", (x, 0, 2.17), (x, 0, 2.94), 0.045, metal)
    rod("Handle grip", (-0.73, 0, 2.94), (0.73, 0, 2.94), 0.085, black)
    for j in range(11):
        ring(
            "Grip rib", 0.092, 0.012, 0.025, (-0.5 + j * 0.1, 0, 2.94), metal, (1, 0, 0)
        )
    knob = lathe(
        "Switch",
        [(0.12, -0.05), (0.14, 0), (0.14, 0.09), (0.12, 0.11)],
        (0, -0.69, 0.64),
        black,
    )
    knob.rotation_euler = (math.pi / 2, 0, 0)
    box("Switch mark", (0.02, 0.01, 0.07), (0, -0.803, 0.67), ivory, 0.004)
    label("LUMA / 02", (-0.28, -0.672, 0.43), 0.075, black)
    return (0, 0, 1.45), 4.5


report = {"blender": bpy.app.version_string, "designs": {}}
for name, builder in [("field-robot", robot), ("work-lantern", lantern)]:
    target, scale = builder()
    folder = OUT / name
    folder.mkdir()
    details = [
        g.inspect(o)
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and not o.hide_render
        and not o.name.startswith("Studio floor")
    ]
    report["designs"][name] = {"parts": len(details), "geometry": details}
    for view, pos in [("front", (4, -6, 3.7)), ("rear", (-4, 6, 3.4))]:
        camera(pos, target, scale, (640, 640))
        bpy.context.scene.cycles.samples = 32
        bpy.context.scene.cycles.use_denoising = True
        bpy.context.scene.render.filepath = str(folder / (view + ".png"))
        bpy.ops.render.render(write_still=True)
    camera((4, -6, 3.7), target, scale, (640, 640))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "model.blend"))
(OUT / "source.py").write_text(Path(__file__).read_text(), encoding="utf-8")
(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
