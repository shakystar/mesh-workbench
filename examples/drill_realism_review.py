"""Capture a preserved native drill under versioned, reproducible settings."""

import argparse
import copy
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, quality, visualaudit
from mesh_workbench.runner import camera


def render(source, output, target, views, mode="beauty", preview=False, views_config=None):
    source, output, target = map(lambda p: Path(p).resolve(), (source, output, target))
    if output.exists():
        raise ValueError("Use a fresh capture directory")
    spec = json.loads(target.read_text(encoding="utf-8"))
    if views_config:
        extra_path = Path(views_config).resolve()
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
        if (extra.get("schema") != 1 or not isinstance(extra.get("views"), dict)
                or set(extra["views"]) & set(spec["capture"]["views"])):
            raise ValueError("Additional cameras cannot replace frozen evaluation views")
        spec["capture"]["views"].update(extra["views"])
        spec["supplemental_capture_sha256"] = visualaudit.file_hash(extra_path)
    view_spec = spec["capture"]
    if (
        mode not in ("beauty", "clay", "stripes", "backlit")
        or not views
        or len(set(views)) != len(views)
        or any(v not in view_spec["views"] for v in views)
    ):
        raise ValueError("Explicit valid unique views and mode required")
    size = [384, 384] if preview else view_spec["final_size"]
    samples = 16 if preview else view_spec["samples"]
    lights = [
        {"name": "Key", "position": [-180, -220, 340], "power": 2200000, "size": 200},
        {"name": "Fill", "position": [230, -60, 180], "power": 1600000, "size": 150},
        {"name": "Rim", "position": [0, 200, 290], "power": 2400000, "size": 180},
    ]
    if mode == "backlit":
        lights = []
    settings = {
        "schema": 1,
        "mode": mode,
        "preview_only": preview,
        "size": size,
        "samples": samples,
        "denoising": False,
        "engine": "CYCLES",
        "device": "CPU",
        "view_transform": "AgX",
        "exposure": 0,
        "gamma": 1,
        "world_strength": 0 if mode == "backlit" else 0.18,
        "lights": lights,
        "views": {v: view_spec["views"][v] for v in views},
        "required_captures": [mode + "-" + v for v in views],
    }
    if mode == "backlit":
        settings["emissive_background"] = {"distance_behind_target":500,
            "plane_width_in_camera_scales":4,"strength":3,"color":[1,1,1,1]}
    digest = visualaudit.fingerprint(settings)
    original_hash = visualaudit.file_hash(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    state = nested.load()
    visible = [
        bpy.data.objects[item["object"]]
        for key, item in state["outputs"].items()
        if state["nodes"][key].get("visible", True)
    ]
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new("Realism world")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
    background.inputs["Strength"].default_value = settings["world_strength"]
    for light in lights:
        data = bpy.data.lights.new("Realism " + light["name"], "AREA")
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = light["position"]
        data.energy = light["power"]
        data.size = light["size"]
        obj.rotation_euler = (
            (Vector((0, 0, 95)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
    if mode in ("clay", "backlit"):
        material = bpy.data.materials.new("Realism diagnostic clay")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.35, 1)
        bsdf.inputs["Roughness"].default_value = 0.38
        for obj in visible:
            for slot in range(len(obj.data.materials)):
                obj.data.materials[slot] = material
    backdrop = None
    if mode == "backlit":
        bpy.ops.mesh.primitive_plane_add(size=2)
        backdrop = bpy.context.object
        backdrop.name = "Diagnostic emissive background"
        material = bpy.data.materials.new("Diagnostic background emission")
        material.use_nodes = True
        material.node_tree.nodes.clear()
        emission = material.node_tree.nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = (1,1,1,1)
        emission.inputs["Strength"].default_value = 3
        surface = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(emission.outputs[0],surface.inputs["Surface"])
        backdrop.data.materials.append(material)
    if mode == "stripes":
        for key in ("housing_left", "housing_right"):
            obj = bpy.data.objects[state["outputs"][key]["object"]]
            quality.reflection_bands(obj, frequency=16)
    output.mkdir(parents=True)
    captures = []
    for view in views:
        camera(**view_spec["views"][view], size=size)
        if backdrop is not None:
            view_data = view_spec["views"][view]
            toward_camera = (Vector(view_data["position"])-Vector(view_data["target"])).normalized()
            backdrop.location = Vector(view_data["target"])-toward_camera*500
            backdrop.rotation_euler = toward_camera.to_track_quat("Z","Y").to_euler()
            backdrop.scale = [view_data["scale"]*2]*3
        scene.camera.data.clip_end = 10000
        scene.cycles.samples = samples
        scene.cycles.use_denoising = False
        scene.cycles.seed = 0
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
        path = output / (mode + "-" + view + ".png")
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        captures.append(
            {
                "id": mode + "-" + view,
                "path": path.name,
                "sha256": visualaudit.file_hash(path),
                "settings_sha256": digest,
                "native_renderer": "Blender Cycles",
                "blender_version": bpy.app.version_string,
            }
        )
    if visualaudit.file_hash(source) != original_hash:
        raise ValueError("Input native file changed")
    defects = copy.deepcopy(
        json.loads((ROOT / "docs/audits/DRILL_REALISM_BASELINE.json").read_text())[
            "defects"
        ]
    )
    manifest = {
        "schema": 1,
        "source_sha256": original_hash,
        "source_preserved": True,
        "reference_sha256": visualaudit.fingerprint(spec),
        "settings": settings,
        "settings_sha256": digest,
        "captures": captures,
        "defects": defects,
        "blender_version": bpy.app.version_string,
    }
    manifest["validation"] = visualaudit.validate(manifest, output, spec)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8"
    )
    print("REALISM_CAPTURE", json.dumps(manifest["validation"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument(
        "views",
        nargs="+",
        choices=[
            "hero",
            "left",
            "right",
            "front",
            "rear",
            "top",
            "bottom",
            "chuck-detail",
            "grip-detail",
            "trigger-detail",
            "battery-detail",
            "vent-detail",
            "seam-detail",
            "screw-detail",
            "rear-screw-detail",
            "grip-screw-detail",
        ],
    )
    parser.add_argument(
        "--target", default=str(ROOT / "examples/drill-realism-target.json")
    )
    parser.add_argument(
        "--mode", choices=["beauty", "clay", "stripes", "backlit"], default="beauty"
    )
    parser.add_argument("--views-config")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    render(args.source, args.output, args.target, args.views, args.mode, args.preview, args.views_config)
