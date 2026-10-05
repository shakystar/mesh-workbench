"""Blender-side recipe executor. Called by the host CLI in a fresh process."""

import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path
import bpy
from mesh_workbench import __version__, surface, sculpt, geometry, models, patterns


def confined(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Output path escapes run directory")
    return path


def camera(position=(0, -6, 2), target=(0, 0, 0), scale=5, size=(256, 256)):
    scene = bpy.context.scene
    obj = scene.camera
    if obj is None:
        obj = bpy.data.objects.new("MW camera", bpy.data.cameras.new("MW camera"))
        scene.collection.objects.link(obj)
        scene.camera = obj
    obj.parent = None
    obj.scale = (1, 1, 1)
    obj.location = geometry.vector(position)
    obj.rotation_euler = (
        (geometry.vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )
    obj.data.type = "ORTHO"
    obj.data.ortho_scale = sculpt.number(scale, 0.001, 10000, "camera scale")
    obj.data.sensor_fit = "HORIZONTAL"
    if len(size) != 2 or any(type(v) != int or not 16 <= v <= 4096 for v in size):
        raise ValueError("Image size must be 16..4096")
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MW world")
    scene.world.color = (0.15, 0.15, 0.15)
    bpy.context.view_layer.update()
    return surface.camera_info(scene)


def run(recipe_path, output):
    recipe_path = Path(recipe_path).resolve()
    output = Path(output).resolve()
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe.get("version") != 1 or not isinstance(recipe.get("operations"), list):
        raise ValueError("Expected recipe version 1 and operations")
    output.mkdir(parents=True, exist_ok=False)
    audit = {
        "version": __version__,
        "blender": bpy.app.version_string,
        "recipe": recipe,
        "operations": [],
        "status": "running",
        "sources": {},
    }
    selections = {}
    sculpt.dump(output / "recipe.json", recipe)

    def source(name):
        path = (recipe_path.parent / name).resolve()
        if not path.is_file():
            raise ValueError("Missing input file")
        audit["sources"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def obj(name):
        if name not in bpy.data.objects:
            raise ValueError("Unknown object " + name)
        return bpy.data.objects[name]

    try:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        if recipe.get("source"):
            bpy.ops.wm.open_mainfile(
                filepath=str(source(recipe["source"])), load_ui=False, use_scripts=False
            )
        camera(**recipe.get("camera", {}))
        for index, c in enumerate(recipe["operations"]):
            op = c["op"]
            result = None
            if op == "primitive":
                result = models.primitive(
                    c["kind"],
                    c["name"],
                    c.get("location", [0, 0, 0]),
                    c.get("scale", [1, 1, 1]),
                    **c.get("options", {}),
                )
            elif op == "load_blend":
                result = [
                    o.name
                    for o in models.load_blend(
                        source(c["path"]), c["objects"], c.get("prefix", "imported_")
                    )
                ]
            elif op == "load_mesh":
                result = [
                    o.name
                    for o in models.load_mesh(
                        source(c["path"]), c.get("prefix", "imported_")
                    )
                ]
            elif op == "transform":
                result = models.transform(obj(c["object"]), **c["transform"])
            elif op == "duplicate":
                result = geometry.fork(obj(c["object"]), c["name"])
            elif op == "bake":
                result = sculpt.bake(obj(c["object"]))
            elif op == "combine":
                result = models.combine(
                    [obj(n) for n in c["objects"]], c["name"], c.get("voxel")
                )
            elif op == "boolean":
                result = models.boolean(
                    obj(c["left"]), obj(c["right"]), c["operation"], c["name"]
                )
            elif op == "blend":
                result = models.blend(
                    obj(c["left"]), obj(c["right"]), c["name"], c.get("weight", 0.5)
                )
            elif op == "select":
                result = geometry.selection(obj(c["object"]), **c.get("selection", {}))
                selections[c["name"]] = result
            elif op == "move":
                result = geometry.move(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["delta"],
                    c.get("label", "vertex move"),
                )
            elif op == "mesh_edit":
                result = geometry.edit_topology(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["operation"],
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "inspect":
                result = geometry.inspect(obj(c["object"]))
            elif op == "capture":
                result = surface.capture(
                    confined(output, c["name"]), c.get("render", True)
                )
            elif op == "views":
                result = sculpt.capture_views(
                    confined(output, c["name"]), c["views"], c.get("render", True)
                )
            elif op == "activate_map":
                result = sculpt.activate_map(confined(output, c["map"]))
            elif op == "query":
                result = sculpt.Surface(confined(output, c["map"])).summary(
                    c.get("pixels")
                )
            elif op == "mesh_export":
                result = sculpt.export_mesh(
                    obj(c["object"]), confined(output, c["name"])
                )
            elif op == "stroke":
                result = sculpt.path_stroke(confined(output, c["map"]), c["command"])
            elif op == "mask":
                result = sculpt.mask(confined(output, c["map"]), c["command"])
            elif op == "layer":
                result = sculpt.set_layer(obj(c["object"]), c["layer"], c["value"])
            elif op == "project":
                result = patterns.project(
                    obj(c["target"]), c["points"], **c.get("options", {})
                )
            elif op == "conform":
                result = patterns.conform(
                    obj(c["object"]),
                    selections[c["selection"]],
                    obj(c["target"]),
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "seam":
                result = patterns.seam(
                    obj(c["target"]), c["points"], c["name"], **c.get("options", {})
                )
            elif op == "scatter":
                result = patterns.scatter(
                    obj(c["target"]),
                    obj(c["motif"]),
                    c["points"],
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "uv":
                result = patterns.cylindrical_uv(
                    obj(c["object"]), c.get("name", "MW cylindrical UV")
                )
            elif op == "weave":
                result = patterns.weave(
                    obj(c["object"]), c["uv"], **c.get("options", {})
                )
            elif op == "visible":
                for name in c["objects"]:
                    obj(name).hide_render = not c["value"]
                result = {"visible": c["value"], "objects": c["objects"]}
            elif op == "light":
                light = bpy.data.objects.new(
                    c["name"], bpy.data.lights.new(c["name"], "AREA")
                )
                bpy.context.collection.objects.link(light)
                light.location = geometry.vector(c["position"])
                light.rotation_euler = (
                    (geometry.vector(c.get("target", [0, 0, 0])) - light.location)
                    .to_track_quat("-Z", "Y")
                    .to_euler()
                )
                light.data.energy = c.get("energy", 700)
                light.data.shape = "DISK"
                light.data.size = c.get("size", 4)
                result = light
            elif op == "camera":
                result = camera(**c["camera"])
            elif op == "checkpoint":
                path = confined(output, c["name"])
                if path.exists():
                    raise ValueError("Checkpoint exists")
                bpy.ops.wm.save_as_mainfile(filepath=str(path))
                result = {"file": c["name"]}
            else:
                raise ValueError("Unknown operation " + op)
            if isinstance(result, bpy.types.Object):
                result = {"object": result.name}
            bpy.context.view_layer.update()
            audit["operations"].append({"index": index, "op": op, "result": result})
            sculpt.dump(output / "audit.json", audit)
            print("MW_OPERATION", index, op, flush=True)
        for path, digest in audit["sources"].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise AssertionError("Input source changed")
        bpy.ops.wm.save_as_mainfile(filepath=str(output / "result.blend"))
        audit["status"] = "complete"
        audit["source_preserved"] = True
    except Exception:
        audit["status"] = "failed"
        audit["error"] = traceback.format_exc()
        raise
    finally:
        sculpt.dump(output / "audit.json", audit)
    print("MESH_WORKBENCH_COMPLETE", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output", required=True)
    a = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    run(a.recipe, a.output)
