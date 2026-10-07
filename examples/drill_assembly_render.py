"""Native Blender review renders; input geometry and rest transforms preserved."""

import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    nested,
    joints,
    sections,
    materials,
    actuators,
    assembly,
    sculpt,
)
from mesh_workbench.runner import camera


def render(out, views=("hero", "side", "exploded")):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new("DA studio")
    scene.world.color = (0.18, 0.18, 0.18)
    for name, pos, power, size in [
        ("DA Key", [-180, -220, 340], 2200000, 200),
        ("DA Fill", [230, -60, 180], 1600000, 150),
        ("DA Rim", [0, 200, 290], 2400000, 180),
    ]:
        lamp = bpy.data.objects.get(name)
        if lamp is None:
            lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
            scene.collection.objects.link(lamp)
        lamp.location = pos
        lamp.data.energy = power
        lamp.data.size = size
        lamp.rotation_euler = (
            (Vector([0, 0, 100]) - lamp.location).to_track_quat("-Z", "Y").to_euler()
        )
    state = nested.load()
    objects = {k: bpy.data.objects[r["object"]] for k, r in state["outputs"].items()}
    snapshot = joints.snapshot([o.name for o in objects.values()])
    try:
        for view in views:
            joints.restore(snapshot)
            if view == "exploded":
                for key, o in objects.items():
                    if key in [
                        "housing_left",
                        "grip_left",
                        "texture_left",
                    ] or key.startswith("boss_"):
                        o.location.y -= 30
                    if key in ["housing_right", "grip_right", "texture_right"]:
                        o.location.y += 30
                    if key in [
                        "battery",
                        "battery_latch",
                        "channel_left",
                        "channel_right",
                    ]:
                        o.location.x -= 45
                        o.location.z -= 10
                    if key in ["chuck_body", "jaw_cage", "bit"] or key.startswith(
                        "jaw_"
                    ):
                        o.location.x += 20
            position, target, scale = (
                ([0, -500, 105], [12, 0, 102], 265)
                if view == "side"
                else (
                    [270, -400, 230],
                    [15, 0, 100],
                    320 if view == "exploded" else 280,
                )
            )
            camera(position=position, target=target, scale=scale, size=[1000, 850])
            scene.camera.data.clip_end = 10000
            scene.cycles.samples = 24
            scene.render.filepath = str(out / (view + ".png"))
            bpy.ops.render.render(write_still=True)
    finally:
        joints.restore(snapshot)
    nested.load()


def render_clearance(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = nested.load()
    objects = {k: bpy.data.objects[r["object"]] for k, r in state["outputs"].items()}
    rail, channel = objects["rail_left"], objects["channel_left"]
    measurement = actuators.pair(rail, channel)
    if not measurement["passed"]:
        raise ValueError("Measured rail interface required")
    length = state["parameters"]["grip_length"]
    seed = Vector((-32, -14.5, 36 - length))
    first, _, _, residual = assembly._tree(rail).find_nearest(seed)
    second = assembly._tree(channel).find_nearest(first)[0]
    distance = (first - second).length
    if residual > 1e-4 or distance < 0.2:
        raise ValueError("Declared section probe does not match actual geometry")
    visibility = {
        o: (o.hide_get(), o.hide_render) for o in bpy.data.objects if o.type == "MESH"
    }
    created = []

    def lines(name, segments, color, radius=0.025):
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = radius
        curve.bevel_resolution = 2
        for a, b in segments:
            spline = curve.splines.new("POLY")
            spline.points.add(1)
            spline.points[0].co = (*a, 1)
            spline.points[1].co = (*b, 1)
        obj = bpy.data.objects.new(name, curve)
        bpy.context.collection.objects.link(obj)
        created.append(obj)
        materials.assign([obj], name + " color", color)

    try:
        for obj in visibility:
            obj.hide_set(True)
            obj.hide_render = True
        lines(
            "Rail section", sections.cut(rail, 0, -32)["segments"], [0.95, 0.4, 0.02, 1]
        )
        lines(
            "Channel section",
            sections.cut(channel, 0, -32)["segments"],
            [0.04, 0.3, 0.8, 1],
        )
        q1 = first.copy()
        q2 = second.copy()
        q1.z = q2.z = 31.8 - length
        lines(
            "Measured gap",
            [(first, second), (first, q1), (second, q2), (q1, q2)],
            [0.9, 0.03, 0.02, 1],
            0.02,
        )
        target = Vector((-32, -11, 36.5 - length))
        camera(
            position=target + Vector((-100, 0, 0)),
            target=target,
            scale=19,
            size=[1000, 750],
        )
        scene = bpy.context.scene
        scene.camera.data.clip_end = 10000
        font = bpy.data.curves.new("Clearance label", "FONT")
        font.body = f"{distance:.3f} mm"
        font.size = 0.85
        label = bpy.data.objects.new("Clearance label", font)
        bpy.context.collection.objects.link(label)
        created.append(label)
        label.location = (-32.1, -9, 30.5 - length)
        label.rotation_euler = scene.camera.rotation_euler
        materials.assign([label], "Clearance label color", [0.04, 0.04, 0.04, 1])
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.background_type = "VIEWPORT"
        scene.display.shading.background_color = (0.8, 0.8, 0.8)
        scene.render.filepath = str(out / "clearance.png")
        bpy.ops.render.render(write_still=True)
        sculpt.dump(
            out / "clearance.json",
            {
                "pair": ["rail_left", "channel_left"],
                "section_x": -32,
                "measurement": measurement,
                "segment": [list(first), list(second)],
                "segment_length": distance,
                "probe_surface_residual": residual,
            },
        )
    finally:
        for obj in created:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)
        for obj, (hidden, render_hidden) in visibility.items():
            obj.hide_set(hidden)
            obj.hide_render = render_hidden
    nested.load()


def render_sections(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = nested.load()
    objects = {k: bpy.data.objects[r["object"]] for k, r in state["outputs"].items()}
    visibility = {
        o: (o.hide_get(), o.hide_render) for o in bpy.data.objects if o.type == "MESH"
    }
    created = []
    try:
        for obj in visibility:
            obj.hide_set(True)
            obj.hide_render = True
        for z in [85, 165]:
            for obj in created:
                obj.hide_render = True
            for side, color in [
                ("left", [0.9, 0.38, 0.03, 1]),
                ("right", [0.08, 0.4, 0.8, 1]),
            ]:
                section = sections.cut(objects["housing_" + side], 2, z)
                curve = bpy.data.curves.new("Measured section " + side, "CURVE")
                curve.dimensions = "3D"
                curve.bevel_depth = 0.12
                curve.bevel_resolution = 2
                for a, b in section["segments"]:
                    spline = curve.splines.new("POLY")
                    spline.points.add(1)
                    spline.points[0].co = (*a, 1)
                    spline.points[1].co = (*b, 1)
                obj = bpy.data.objects.new("Measured section " + side, curve)
                bpy.context.collection.objects.link(obj)
                created.append(obj)
                mat = bpy.data.materials.new("Section " + side)
                mat.diffuse_color = color
                curve.materials.append(mat)
            bounds = section["bounds"]
            center_x = (bounds[0][0] + bounds[1][0]) / 2
            width = bounds[1][0] - bounds[0][0]
            height = max(abs(bounds[0][1]), abs(bounds[1][1])) * 2
            camera(
                position=[center_x, 0, 400],
                target=[center_x, 0, z],
                scale=max(width, height * 1000 / 600) * 1.25,
                size=[1000, 600],
            )
            bpy.context.scene.camera.data.clip_end = 10000
            bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
            bpy.context.scene.display.shading.light = "STUDIO"
            bpy.context.scene.display.shading.color_type = "MATERIAL"
            bpy.context.scene.display.shading.show_shadows = False
            bpy.context.scene.render.filepath = str(
                out / ("section-" + str(z) + ".png")
            )
            bpy.ops.render.render(write_still=True)
    finally:
        for obj in created:
            curve = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.curves.remove(curve)
        for obj, (hidden, render_hidden) in visibility.items():
            obj.hide_set(hidden)
            obj.hide_render = render_hidden
    nested.load()


def render_topology(out):
    import json

    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = nested.load()
    after = bpy.data.objects[state["outputs"]["master"]["object"]]
    if "mw_remesh" not in after:
        raise ValueError("Root remesh trial required")
    before = bpy.data.objects[json.loads(after["mw_remesh"])["source"]]
    visibility = {
        o: (o.hide_get(), o.hide_render) for o in bpy.data.objects if o.type == "MESH"
    }
    try:
        for obj in visibility:
            obj.hide_set(True)
            obj.hide_render = True
        for label, obj in [("before", before), ("after", after)]:
            obj.hide_set(False)
            obj.hide_render = False
            wire = obj.copy()
            wire.data = obj.data.copy()
            wire.name = "Measured wire " + label
            bpy.context.collection.objects.link(wire)
            wire.hide_set(False)
            wire.hide_render = False
            try:
                materials.assign(
                    [wire], "Topology wire " + label, [0.01, 0.02, 0.025, 1]
                )
                mod = wire.modifiers.new("Actual mesh edges", "WIREFRAME")
                mod.thickness = 0.045
                mod.use_replace = True
                mod.use_even_offset = False
                camera(
                    position=[-29, -150, 86.5],
                    target=[-29, 0, 86.5],
                    scale=38,
                    size=[800, 800],
                )
                bpy.context.scene.camera.data.clip_end = 10000
                bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
                bpy.context.scene.display.shading.light = "STUDIO"
                bpy.context.scene.display.shading.color_type = "MATERIAL"
                bpy.context.scene.render.filepath = str(
                    out / ("topology-" + label + ".png")
                )
                bpy.ops.render.render(write_still=True)
            finally:
                mesh = wire.data
                bpy.data.objects.remove(wire, do_unlink=True)
                bpy.data.meshes.remove(mesh)
                obj.hide_set(True)
                obj.hide_render = True
    finally:
        for obj, (hidden, render_hidden) in visibility.items():
            obj.hide_set(hidden)
            obj.hide_render = render_hidden
    nested.load()


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    bpy.ops.wm.open_mainfile(filepath=str(Path(args[0]).resolve()))
    mode = args[2] if len(args) > 2 else "review"
    if mode == "clearance":
        render_clearance(args[1])
    elif mode == "sections":
        render_sections(args[1])
    elif mode == "topology":
        render_topology(args[1])
    elif mode in ("hero", "side", "exploded"):
        render(args[1], views=(mode,))
    else:
        render(args[1])
