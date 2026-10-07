"""Blender-side recipe executor. Called by the host CLI in a fresh process."""

import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

import bpy

from mesh_workbench import (
    __version__,
    nested,
    actuators,
    quality,
    detail,
    surfacedetail,
    refinement,
    remesh,
    pathmodel,
    joints,
    assembly,
    motion,
    attachments,
    candidates,
    precision,
    reference,
    regions,
    construction,
    fairing,
    geometry,
    materials,
    loft,
    shells,
    sections,
    models,
    patterns,
    relief,
    sculpt,
    surface,
    sweep,
)


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
    measurements = {}
    current_operation = None
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
        if "units" in recipe:
            scales = {"mm": 0.001, "cm": 0.01, "m": 1.0}
            if recipe["units"] not in scales:
                raise ValueError("Recipe units must be mm, cm or m")
            bpy.context.scene.unit_settings.system = "METRIC"
            bpy.context.scene.unit_settings.scale_length = scales[recipe["units"]]
        camera(**recipe.get("camera", {}))
        for index, c in enumerate(recipe["operations"]):
            op = c["op"]
            current_operation = {"index": index, "op": op}
            result = None
            if op == "curvature":
                result = quality.curvature(obj(c["object"]), **c.get("options", {}))
            elif op == "fair_patch":
                result = quality.fair_patch(
                    obj(c["object"]), selections[c["selection"]], **c.get("options", {})
                )
            elif op == "reflection_bands":
                result = {
                    "material": quality.reflection_bands(
                        obj(c["object"]), **c.get("options", {})
                    ).name
                }
            elif op == "profiled_ring":
                result = detail.profiled_ring(c["name"], **c["options"])
            elif op == "variable_bevel":
                result = detail.variable_bevel(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["name"],
                    **c["options"],
                )
            elif op == "surface_paths":
                result = surfacedetail.paths(
                    obj(c["object"]), c["name"], **c["options"]
                )
            elif op == "rebuild_patch":
                result = remesh.rebuild_patch(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["name"],
                    **c["options"],
                )
            elif op == "remesh":
                result = remesh.remesh(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["name"],
                    **c["options"],
                )
            elif op == "remesh_selection":
                result = remesh.transfer_selection(
                    obj(c["source"]), obj(c["target"]), selections[c["selection"]]
                )
                selections[c["name"]] = result
            elif op == "remesh_pattern":
                result = remesh.transfer_pattern(
                    obj(c["source"]),
                    obj(c["target"]),
                    obj(c["pattern"]),
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "assembly_remesh":
                result = assembly.remesh_source(
                    c["source"], selections[c["selection"]], c["name"], **c["options"]
                )
            elif op == "refine_faces":
                result = refinement.split(
                    obj(c["object"]), selections[c["selection"]], c["name"]
                )
            elif op == "transfer_selection":
                result = refinement.transfer_selection(
                    obj(c["source"]), obj(c["target"]), selections[c["selection"]]
                )
                selections[c["name"]] = result
            elif op == "transfer_pattern":
                result = refinement.transfer_pattern(
                    obj(c["source"]), obj(c["target"]), obj(c["pattern"]), c["name"]
                )
            elif op == "path_create":
                result = pathmodel.create(
                    c["name"], c["centers"], c["radii"], **c.get("options", {})
                )
            elif op == "path_reshape":
                result = pathmodel.reshape(obj(c["object"]), c["centers"], c["name"])
            elif op == "path_sections":
                result = pathmodel.sections(obj(c["object"]))
            elif op == "ring_bridge":
                result = pathmodel.bridge(
                    c["name"],
                    c["start"],
                    c["end"],
                    c["start_tangent"],
                    c["end_tangent"],
                    **c.get("options", {}),
                )
            elif op == "joints_register":
                result = joints.register(c["joints"])
            elif op == "joints_inspect":
                result = joints.inspect(c["angles"], c["fixed"], **c.get("options", {}))
            elif op == "nested_initialize":
                result = nested.initialize(
                    c["name"], c["nodes"], c["parameters"], c["ranges"], c.get("checks")
                )
            elif op == "nested_status":
                result = nested.load()
            elif op == "nested_reconfigure":
                result = nested.reconfigure(c["nodes"], c.get("checks"))
            elif op == "nested_update":
                result = nested.update(c.get("parameters"), c.get("remesh_request"))
            elif op == "actuators_register":
                result = actuators.register(
                    c["parts"], c["channels"], c.get("interlocks")
                )
            elif op == "actuators_sweep":
                result = actuators.sweep(
                    c["channel"],
                    c["start"],
                    c["end"],
                    c["pairs"],
                    **c.get("options", {}),
                )
                if not result["passed"]:
                    raise assembly.Rejected(result)
            elif op == "assembly_register":
                result = assembly.register(c["name"], c["nodes"], c.get("checks"))
            elif op == "assembly_status":
                result = assembly.status()
            elif op == "assembly_update":
                result = assembly.update(c["source"], c["edit"])
            elif op == "assembly_validate":
                result = assembly.validate(assembly.load())
            elif op == "motion_inspect":
                result = motion.inspect(
                    obj(c["object"]),
                    [obj(n) for n in c["obstacles"]],
                    **c.get("options", {}),
                )
            elif op == "primitive":
                result = models.primitive(
                    c["kind"],
                    c["name"],
                    c.get("location", [0, 0, 0]),
                    c.get("scale", [1, 1, 1]),
                    **c.get("options", {}),
                )
            elif op == "guide_loft":
                result = loft.create(c["name"], c["sections"], **c.get("options", {}))
            elif op == "radial_edit":
                result = regions.radial_move(
                    obj(c["object"]),
                    c["region"],
                    c["center"],
                    c["radius"],
                    c["delta"],
                    **c.get("options", {}),
                )
            elif op == "extract_shell":
                result = shells.extract(
                    obj(c["object"]),
                    selections[c["selection"]],
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "measure_thickness":
                result = shells.thickness(obj(c["object"]), **c.get("options", {}))
                measurements[c["name"]] = result
            elif op == "measure_gap":
                result = shells.gap(
                    obj(c["left"]), obj(c["right"]), **c.get("options", {})
                )
                measurements[c["name"]] = result
            elif op == "mark_violations":
                result = shells.markers(
                    c["name"], measurements[c["measurement"]], **c.get("options", {})
                )
            elif op == "section":
                result = sections.cut(obj(c["object"]), c["axis"], c["value"])
                if c.get("expected_bounds") is not None:
                    result = sections.compare(result, c["expected_bounds"])
            elif op == "intersection_candidates":
                result = shells.intersections(obj(c["left"]), obj(c["right"]))
            elif op == "rounded_panel":
                result = precision.rounded_panel(
                    c["name"],
                    c["dimensions"],
                    c["corner_radius"],
                    c["edge_radius"],
                    **c.get("options", {}),
                )
            elif op == "bezier_tube":
                result = precision.bezier_tube(
                    c["name"], c["controls"], **c.get("options", {})
                )
            elif op == "define_region":
                selected = geometry.selection(
                    obj(c["object"]), "VERT", **c.get("selection", {})
                )
                result = regions.define(obj(c["object"]), c["name"], selected)
            elif op == "profile_edit":
                result = regions.profile(
                    obj(c["object"]),
                    c["region"],
                    c["axis"],
                    c["displacement_axis"],
                    c["knots"],
                    **c.get("options", {}),
                )
            elif op == "bound_seam":
                result = precision.bound_seam(
                    obj(c["target"]), c["points"], c["name"], **c.get("options", {})
                )
            elif op == "refresh_seam":
                result = precision.refresh_seam(
                    obj(c["target"]), obj(c["object"]), c["name"]
                )
            elif op == "compare_reference":
                spec = json.loads(source(c["path"]).read_text(encoding="utf-8"))
                result, actual, expected = reference.evaluate(
                    obj(c["object"]),
                    spec,
                    c["component"],
                    supersample=c.get("supersample", 1),
                )
                if c.get("overlay"):
                    destination = confined(output, c["overlay"])
                    if destination.exists():
                        raise ValueError("Overlay exists")
                    reference.save_overlay(destination, actual, expected)
            elif op == "activate_candidate":
                result = candidates.activate(c["objects"], c["alternatives"])
            elif op == "restore_candidate":
                result = candidates.restore()
            elif op == "rounded_box":
                result = construction.rounded_box(
                    c["name"], c["dimensions"], **c.get("options", {})
                )
            elif op == "revolve":
                result = construction.revolve(
                    c["name"], c["profile"], **c.get("options", {})
                )
            elif op == "strut":
                result = construction.strut(
                    c["name"], c["start"], c["end"], **c.get("options", {})
                )
            elif op == "sweep":
                result = sweep.sweep(
                    c["name"], c["centers"], c["radii"], **c.get("options", {})
                )
            elif op == "fair":
                result = fairing.region(
                    obj(c["object"]), c["center"], c["radius"], **c.get("options", {})
                )
            elif op == "relief_dots":
                result = relief.dots(
                    obj(c["target"]), c["points"], c["name"], **c.get("options", {})
                )
            elif op == "bind_relief":
                result = attachments.bind_relief(
                    obj(c["target"]), obj(c["object"]), **c.get("options", {})
                )
            elif op == "attachment_status":
                result = attachments.status(obj(c["target"]), obj(c["object"]))
            elif op == "refresh_relief":
                result = attachments.refresh_relief(
                    obj(c["target"]),
                    obj(c["object"]),
                    c["name"],
                    **c.get("options", {}),
                )
            elif op == "diagnose":
                target = obj(c["object"])
                result = geometry.inspect(target)
                result["components"] = fairing.components(target)
                result["overlap_candidates"] = fairing.overlap_candidates(target)
            elif op == "material":
                result = materials.assign(
                    [obj(n) for n in c["objects"]],
                    c["name"],
                    c["color"],
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
                    if c.get("viewport", False):
                        obj(name).hide_set(not c["value"])
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
                item = {"object": result.name}
                if op == "remesh":
                    item["report"] = json.loads(result["mw_remesh"])["report"]
                if op == "remesh_pattern":
                    item["transfer"] = json.loads(result["mw_transfer_report"])
                result = item
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
    except Exception as exc:
        if isinstance(exc, assembly.Rejected):
            audit["rejection"] = exc.report
        audit["status"] = "failed"
        audit["failed_operation"] = current_operation
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
