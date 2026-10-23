"""Render-linked surface data and camera-space mesh brushes inside Blender.

No viewport or simulated mouse input. Pixel origin is top left, centers at +0.5.
Opaque, static orthographic mesh studies only; evaluated face IDs are diagnostic.
"""

import hashlib
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SURFACE_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}


def render_surfaces():
    """Resolve collection render visibility and the active view-layer exclusions."""
    objects = {}

    def visit(layer):
        if layer.exclude or layer.collection.hide_render:
            return
        for obj in layer.collection.objects:
            if obj.type in SURFACE_TYPES and not obj.hide_render:
                objects[obj.name] = obj
        for child in layer.children:
            visit(child)

    visit(bpy.context.view_layer.layer_collection)
    return [objects[name] for name in sorted(objects)]


def revision():
    bpy.context.view_layer.update()
    h = hashlib.sha256()
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in render_surfaces():
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", coords)
        h.update(obj.name.encode())
        h.update(coords.tobytes())
        h.update(np.asarray(obj.matrix_world, dtype=np.float64).tobytes())
        h.update(str([tuple(p.vertices) for p in mesh.polygons]).encode())
        evaluated.to_mesh_clear()
    scene = bpy.context.scene
    h.update(str(camera_info(scene)).encode())
    return h.hexdigest()


def camera_info(scene):
    cam = scene.camera
    if cam.data.type != "ORTHO" or scene.render.resolution_percentage != 100:
        raise ValueError("Requires orthographic camera and 100 percent resolution")
    if (
        cam.parent
        or any(abs(v - 1) > 1e-7 for v in cam.scale)
        or scene.render.use_border
    ):
        raise ValueError("Requires unparented unit-scale camera and uncropped render")
    return {
        "matrix_world": [list(row) for row in cam.matrix_world],
        "location": list(cam.location),
        "scale": list(cam.scale),
        "rotation_mode": cam.rotation_mode,
        "rotation_euler": list(cam.rotation_euler),
        "rotation_quaternion": list(cam.rotation_quaternion),
        "rotation_axis_angle": list(cam.rotation_axis_angle),
        "frame": [list(p) for p in cam.data.view_frame(scene=scene)],
        "size": [scene.render.resolution_x, scene.render.resolution_y],
        "ortho_scale": cam.data.ortho_scale,
        "sensor_fit": cam.data.sensor_fit,
        "shift": [cam.data.shift_x, cam.data.shift_y],
        "clip": [cam.data.clip_start, cam.data.clip_end],
        "pixel_aspect": [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
    }


def capture(folder, render=True):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    info = camera_info(scene)
    width, height = info["size"]
    frame = scene.camera.data.view_frame(scene=scene)
    xmin, xmax = min(p.x for p in frame), max(p.x for p in frame)
    ymin, ymax = min(p.y for p in frame), max(p.y for p in frame)
    matrix = scene.camera.matrix_world.copy()
    direction = matrix.to_quaternion() @ Vector((0, 0, -1))
    graph = bpy.context.evaluated_depsgraph_get()
    names = [o.name for o in render_surfaces()]
    ids = {name: i + 1 for i, name in enumerate(names)}
    # Explicit render-visible geometry avoids viewport hide_set/ray_cast ambiguity.
    # Unsupported evaluation differences are rejected instead of producing mismatched maps.
    vertices, triangles, triangle_objects, triangle_faces = [], [], [], []
    # Blender exposes evaluated curve geometry as a same-name mesh instance.
    # It is covered by to_mesh below; collection/particle instances are not.
    if any(
        i.is_instance and (not i.parent or i.parent.name != i.object.name)
        for i in graph.object_instances
    ):
        raise ValueError("Realize instances before capture")
    for name in names:
        obj = scene.objects[name]
        if not obj.visible_get() or any(
            m.show_render != m.show_viewport for m in obj.modifiers
        ):
            raise ValueError("Render/viewport visibility or modifiers differ: " + name)
        if obj.type == "CURVE" and obj.data.render_resolution_u not in (
            0,
            obj.data.resolution_u,
        ):
            raise ValueError("Curve render/viewport resolution differs: " + name)
        if any(
            m.type == "SUBSURF" and m.show_render and m.levels != m.render_levels
            for m in obj.modifiers
        ):
            raise ValueError("Render/viewport subdivision levels differ: " + name)
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in mesh.vertices)
        for tri in mesh.loop_triangles:
            triangles.append(tuple(offset + i for i in tri.vertices))
            triangle_objects.append(ids[name])
            triangle_faces.append(tri.polygon_index)
        evaluated.to_mesh_clear()
    bvh = (
        BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
        if triangles
        else None
    )
    world = np.full((height, width, 3), np.nan, dtype=np.float32)
    normal = world.copy()
    depth = np.full((height, width), np.nan, dtype=np.float32)
    object_id = np.zeros((height, width), dtype=np.int32)
    face_id = np.full((height, width), -1, dtype=np.int32)
    near, far = info["clip"]
    for y in range(height):
        for x in range(width):
            origin = matrix @ Vector(
                (
                    xmin + (x + 0.5) / width * (xmax - xmin),
                    ymax - (y + 0.5) / height * (ymax - ymin),
                    0,
                )
            )
            if bvh is None:
                continue
            point, n, triangle, distance = bvh.ray_cast(
                origin + direction * near, direction, far - near
            )
            if triangle is not None:
                world[y, x], normal[y, x] = point, n
                depth[y, x] = distance + near
                object_id[y, x], face_id[y, x] = (
                    triangle_objects[triangle],
                    triangle_faces[triangle],
                )
    np.savez_compressed(
        folder / "surface.npz",
        world=world,
        normal=normal,
        depth=depth,
        object_id=object_id,
        face_id=face_id,
    )
    info.update(
        revision=revision(),
        objects={str(i): name for name, i in ids.items()},
        convention="top-left pixel centers; world positions/normals; linear camera depth",
        limitation="geometric first hit; transparent shading and antialiased boundary coverage not represented",
    )
    (folder / "surface.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    if render:
        scene.render.filepath = str(folder / "render.png")
        bpy.ops.render.render(write_still=True)
    return info


def read_pixel(folder, pixel):
    folder = Path(folder)
    info = json.loads((folder / "surface.json").read_text(encoding="utf-8"))
    x, y = pixel
    if (
        type(x) != int
        or type(y) != int
        or not (0 <= x < info["size"][0] and 0 <= y < info["size"][1])
    ):
        raise ValueError("Pixel outside data map")
    with np.load(folder / "surface.npz") as data:
        ident = int(data["object_id"][y, x])
        if not ident:
            raise ValueError("Pixel hits background")
        return {
            "pixel": pixel,
            "object": info["objects"][str(ident)],
            "world": data["world"][y, x].tolist(),
            "normal": data["normal"][y, x].tolist(),
            "depth": float(data["depth"][y, x]),
            "revision": info["revision"],
        }
