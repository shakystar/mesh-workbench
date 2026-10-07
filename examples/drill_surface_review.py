"""Fixed-camera native renders for the surface refinement study."""

import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, quality, sculpt
from mesh_workbench.runner import camera


def render(source, out, views):
    source = Path(source).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())[
        "surface_phase"
    ]
    state = nested.load()
    objects = {k: bpy.data.objects[v["object"]] for k, v in state["outputs"].items()}
    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new("Surface studio")
    scene.world.color = (0.18, 0.18, 0.18)
    for name, pos, power, size in [
        ("Surface key", [-180, -220, 340], 2200000, 200),
        ("Surface fill", [230, -60, 180], 1600000, 150),
        ("Surface rim", [0, 200, 290], 2400000, 180),
    ]:
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        scene.collection.objects.link(lamp)
        lamp.location = pos
        lamp.data.energy = power
        lamp.data.size = size
        lamp.rotation_euler = (
            (Vector([0, 0, 100]) - lamp.location).to_track_quat("-Z", "Y").to_euler()
        )
    scene.cycles.samples = 32
    saved = {
        o: ([m for m in o.data.materials], [f.material_index for f in o.data.polygons])
        for o in objects.values()
    }
    records = []
    try:
        for name in views:
            stripes = name.startswith("stripes-")
            view = name.removeprefix("stripes-")
            if view not in spec["cameras"]:
                raise ValueError("Unknown frozen camera")
            for o, (mats, indices) in saved.items():
                o.data.materials.clear()
                for m in mats:
                    o.data.materials.append(m)
                for f, i in zip(o.data.polygons, indices):
                    f.material_index = i
            if stripes:
                for key in ["housing_left", "housing_right"]:
                    quality.reflection_bands(objects[key], frequency=16)
            camera(**spec["cameras"][view], size=spec["image_size"])
            scene.camera.data.clip_end = 10000
            scene.render.filepath = str(out / (name + ".png"))
            bpy.ops.render.render(write_still=True)
            records.append(
                {
                    "view": name,
                    "camera": spec["cameras"][view],
                    "sha256": hashlib.sha256(
                        (out / (name + ".png")).read_bytes()
                    ).hexdigest(),
                }
            )
    finally:
        for o, (mats, indices) in saved.items():
            o.data.materials.clear()
            for m in mats:
                o.data.materials.append(m)
            for f, i in zip(o.data.polygons, indices):
                f.material_index = i
    nested.load()
    sculpt.dump(
        out / "renders.json",
        {
            "source_sha256": before,
            "source_preserved": before
            == hashlib.sha256(source.read_bytes()).hexdigest(),
            "views": records,
        },
    )


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    render(
        args[0],
        args[1],
        args[2:]
        or ["hero", "left", "right", "front", "rear", "top", "bottom", "stripes-hero"],
    )
