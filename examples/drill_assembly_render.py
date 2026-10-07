"""Native Blender review renders; input geometry and rest transforms preserved."""

import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, joints
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


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    bpy.ops.wm.open_mainfile(filepath=str(Path(args[0]).resolve()))
    render(args[1])
