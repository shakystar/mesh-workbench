"""Coordinate sculpt v2: data inspection, paths, masks, symmetry and edit history.

All geometry operations run in Blender; no viewport/mouse dependency.
"""

import hashlib
import heapq
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import surface as cs
from . import layers as tw


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def topology(obj):
    edges = np.empty(len(obj.data.edges) * 2, dtype=np.int32)
    obj.data.edges.foreach_get("vertices", edges)
    return hashlib.sha256(
        str(len(obj.data.vertices)).encode() + edges.tobytes()
    ).hexdigest()


def coordinates(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = np.array(
        [obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64
    )
    evaluated.to_mesh_clear()
    return result


def bake(obj):
    if obj.animation_data or (
        obj.data.shape_keys and obj.data.shape_keys.animation_data
    ):
        raise ValueError("Use a static study")
    if obj.get("mw_pending"):
        raise ValueError("Finish pending edit first")
    graph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), depsgraph=graph)
    obj.modifiers.clear()
    obj.data = mesh
    for name in ("mw_masks", "mw_layers"):
        if name in obj:
            del obj[name]
    return {
        "object": obj.name,
        "vertices": len(mesh.vertices),
        "topology": topology(obj),
    }


def activate_map(folder):
    info = json.loads((Path(folder) / "surface.json").read_text(encoding="utf-8"))
    restore_camera(info)
    return info


def restore_camera(info):
    scene = bpy.context.scene
    camera = scene.camera
    if camera.parent:
        raise ValueError("Use an unparented data camera")
    camera.location = info["location"]
    camera.scale = info["scale"]
    camera.rotation_mode = info["rotation_mode"]
    camera.rotation_euler = info["rotation_euler"]
    camera.rotation_quaternion = info["rotation_quaternion"]
    camera.rotation_axis_angle = info["rotation_axis_angle"]
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = info["ortho_scale"]
    camera.data.sensor_fit = info["sensor_fit"]
    camera.data.shift_x, camera.data.shift_y = info["shift"]
    camera.data.clip_start, camera.data.clip_end = info["clip"]
    scene.render.resolution_x, scene.render.resolution_y = info["size"]
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = info["pixel_aspect"]
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()


def capture_views(folder, views, render=True):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    original = cs.camera_info(scene)
    results = {}
    try:
        for view in views:
            name = view["name"]
            if (
                not name
                or Path(name).name != name
                or name in results
                or name in (".", "..")
            ):
                raise ValueError("Unique simple view names required")
            camera = scene.camera
            camera.location = view["position"]
            camera.rotation_euler = (
                (Vector(view["target"]) - camera.location)
                .to_track_quat("-Z", "Y")
                .to_euler()
            )
            camera.data.ortho_scale = float(view["scale"])
            scene.render.resolution_x, scene.render.resolution_y = view["size"]
            bpy.context.view_layer.update()
            results[name] = cs.capture(folder / name, render=render)
        dump(folder / "views.json", results)
    finally:
        restore_camera(original)
    return results


class Surface:
    def __init__(self, folder, check=True):
        self.folder = Path(folder)
        self.info = json.loads(
            (self.folder / "surface.json").read_text(encoding="utf-8")
        )
        if check and cs.revision() != self.info["revision"]:
            raise ValueError("Stale surface map or mismatched camera")
        with np.load(self.folder / "surface.npz") as data:
            self.data = {k: data[k].copy() for k in data.files}

    def point(self, pixel, target=None):
        p = np.asarray(pixel, dtype=float)
        if p.shape != (2,) or not np.isfinite(p).all():
            raise ValueError("Expected finite pixel pair")
        x, y = np.floor(p + 0.5).astype(int)
        width, height = self.info["size"]
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError("Pixel outside map")
        ident = int(self.data["object_id"][y, x])
        if ident == 0:
            raise ValueError("Pixel hits background")
        name = self.info["objects"][str(ident)]
        if target is not None and name != target:
            raise ValueError("Occluded or wrong target: " + name)
        return self.data["world"][y, x].astype(float), self.data["normal"][y, x].astype(
            float
        )

    def summary(self, pixels=None):
        result = {
            "revision": self.info["revision"],
            "size": self.info["size"],
            "objects": [],
        }
        for ident, name in self.info["objects"].items():
            y, x = np.where(self.data["object_id"] == int(ident))
            if len(x):
                depths = self.data["depth"][y, x]
                result["objects"].append(
                    {
                        "name": name,
                        "pixels": len(x),
                        "bounds": [
                            int(x.min()),
                            int(y.min()),
                            int(x.max()),
                            int(y.max()),
                        ],
                        "depth_range": [float(depths.min()), float(depths.max())],
                    }
                )
        result["samples"] = []
        for pixel in pixels or []:
            world, normal = self.point(pixel)
            result["samples"].append(
                {"pixel": pixel, "world": world.tolist(), "normal": normal.tolist()}
            )
        return result

    def seed(self, pixel, obj, coords):
        x, y = np.floor(np.asarray(pixel, dtype=float) + 0.5).astype(int)
        face = int(self.data["face_id"][y, x])
        if not 0 <= face < len(obj.data.polygons):
            raise ValueError("Surface topology differs")
        indices = list(obj.data.polygons[face].vertices)
        center = self.data["world"][y, x]
        return min(indices, key=lambda i: float(np.linalg.norm(coords[i] - center)))


def export_mesh(obj, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    world = coordinates(obj)
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    mesh.calc_loop_triangles()
    triangles = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
    edges = np.asarray([e.vertices[:] for e in mesh.edges], dtype=np.int32)
    normals_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    normals = np.array(
        [(normals_matrix @ v.normal).normalized() for v in mesh.vertices]
    )
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    np.savez_compressed(
        folder / "mesh.npz",
        world=world,
        triangles=triangles,
        edges=edges,
        normals=normals,
    )
    report = {
        "object": obj.name,
        "vertices": len(world),
        "triangles": len(triangles),
        "world_bounds": [world.min(axis=0).tolist(), world.max(axis=0).tolist()],
        "topology": topology(obj),
        "layers": layers(obj),
    }
    dump(folder / "mesh.json", report)
    return report


def adjacency(obj, coords):
    neighbors = [[] for _ in coords]
    for edge in obj.data.edges:
        a, b = edge.vertices
        length = float(np.linalg.norm(coords[a] - coords[b]))
        neighbors[a].append((b, length))
        neighbors[b].append((a, length))
    return neighbors


def neighborhood(coords, neighbors, center, radius, metric, seed=None):
    distances = np.linalg.norm(coords - center, axis=1)
    if metric == "geodesic":
        seed = int(np.argmin(distances)) if seed is None else seed
        best = np.full(len(coords), np.inf)
        best[seed] = distances[seed]
        heap = [(float(best[seed]), seed)]
        while heap:
            distance, i = heapq.heappop(heap)
            if distance > best[i] or distance >= radius:
                continue
            for j, length in neighbors[i]:
                candidate = distance + length
                if candidate < radius and candidate < best[j]:
                    best[j] = candidate
                    heapq.heappush(heap, (candidate, j))
        distances = best
    elif metric != "sphere":
        raise ValueError("Unknown neighborhood metric")
    return np.square(np.maximum(0, 1 - np.minimum(distances / radius, 1) ** 2))


def editable(obj):
    if (
        obj.type != "MESH"
        or obj.animation_data
        or any(m.show_viewport or m.show_render for m in obj.modifiers)
    ):
        raise ValueError("Edit a static baked mesh")
    if obj.data.shape_keys and obj.data.shape_keys.animation_data:
        raise ValueError("Animated keys are unsupported")


def number(value, low, high, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError("Invalid " + name)
    return float(value)


def mask(folder, command):
    surface = Surface(folder)
    obj = bpy.data.objects[command["object"]]
    editable(obj)
    name = command["name"]
    if not isinstance(name, str) or not name or len(name) > 48:
        raise ValueError("Mask name must have 1..48 characters")
    radius = number(command["radius"], 0.0001, 10, "radius")
    points = [surface.point(p, obj.name)[0] for p in command["pixels"]]
    if not points:
        raise ValueError("Mask needs pixels")
    coords = coordinates(obj)
    neighbors = adjacency(obj, coords)
    values = np.zeros(len(coords))
    for pixel, point in zip(command["pixels"], points):
        weights = neighborhood(
            coords,
            neighbors,
            point,
            radius,
            command.get("metric", "geodesic"),
            surface.seed(pixel, obj, coords),
        )
        if command.get("hard", True):
            weights = (weights > 0).astype(float)
        values = np.maximum(values, weights)
    if command.get("invert", False):
        values = 1 - values
    group_name = "MW protect " + name
    group = obj.vertex_groups.get(group_name)
    if group:
        obj.vertex_groups.remove(group)
    group = obj.vertex_groups.new(name=group_name)
    for i, value in enumerate(values):
        if value:
            group.add([i], float(value), "REPLACE")
    records = json.loads(obj.get("mw_masks", "{}"))
    records[name] = {"group": group.name, "topology": topology(obj)}
    obj["mw_masks"] = json.dumps(records)
    return {"name": name, "protected_vertices": int(np.count_nonzero(values))}


def protection(obj, name):
    weights = np.zeros(len(obj.data.vertices))
    if name is None:
        return weights
    records = json.loads(obj.get("mw_masks", "{}"))
    if name not in records or records[name]["topology"] != topology(obj):
        raise ValueError("Missing or stale mask")
    group = obj.vertex_groups.get(records[name]["group"])
    if group is None:
        raise ValueError("Missing mask group")
    for vertex in obj.data.vertices:
        for link in vertex.groups:
            if link.group == group.index:
                weights[vertex.index] = link.weight
    return weights


def interpolate(points, pressures, spacing):
    result = [(points[0], pressures[0])]
    for a, b, pa, pb in zip(points, points[1:], pressures, pressures[1:]):
        count = max(1, math.ceil(float(np.linalg.norm(b - a)) / spacing))
        if len(result) + count > 4096:
            raise ValueError("Stroke exceeds 4096 samples")
        result.extend(
            (a + (b - a) * t / count, pa + (pb - pa) * t / count)
            for t in range(1, count + 1)
        )
    return result


def path_stroke(folder, command):
    surface = Surface(folder)
    obj = bpy.data.objects[command["object"]]
    editable(obj)
    mode = command["mode"]
    if mode not in ("grab", "pinch", "smooth", "normal"):
        raise ValueError("Unknown brush")
    label = command.get("label", mode)
    if not isinstance(label, str) or not 1 <= len(label) <= 48:
        raise ValueError("Invalid layer label")
    points = np.asarray(command["points"], dtype=float)
    if (
        points.ndim != 2
        or points.shape[1] != 2
        or not 1 <= len(points) <= 256
        or not np.isfinite(points).all()
    ):
        raise ValueError("Expected 1..256 finite pixel pairs")
    pressures = np.asarray(command.get("pressures", [1] * len(points)), dtype=float)
    if (
        pressures.shape != (len(points),)
        or not np.isfinite(pressures).all()
        or np.any(pressures < 0)
        or np.any(pressures > 1)
    ):
        raise ValueError("Pressure count/range invalid")
    radius = number(command["radius"], 0.0001, 10, "radius")
    strength = number(command.get("strength", 0.3), 0, 1, "strength")
    spacing = number(command.get("spacing", 2), 0.25, 64, "spacing")
    distance = number(command.get("distance", 0.01), -1, 1, "distance")
    metric = command.get("metric", "geodesic")
    if metric not in ("geodesic", "sphere"):
        raise ValueError("Unknown metric")
    symmetry = command.get("symmetry_x", False)
    if type(symmetry) is not bool:
        raise ValueError("symmetry_x must be boolean")
    plane = number(command.get("symmetry_plane", 0), -1000, 1000, "symmetry plane")
    coords = coordinates(obj)
    original = coords.copy()
    neighbors = adjacency(obj, coords)
    protected = protection(obj, command.get("mask"))
    # Validate every sampled hit before opening a transaction. Paths sample the
    # stroke-start surface; overlapping dabs deform the current coordinates.
    samples = interpolate(points, pressures, spacing)
    if mode == "grab":
        center, normal = surface.point(points[0], obj.name)
        frame = np.asarray(surface.info["frame"])
        width, height = surface.info["size"]
        delta = points[-1] - points[0]
        rotation = bpy.context.scene.camera.matrix_world.to_quaternion()
        shift = np.asarray(
            rotation
            @ Vector(
                (
                    delta[0] * np.ptp(frame[:, 0]) / width,
                    -delta[1] * np.ptp(frame[:, 1]) / height,
                    0,
                )
            )
        )
        dabs = [
            (
                center,
                normal,
                float(pressures[-1]),
                shift,
                surface.seed(points[0], obj, coords),
            )
        ]
    else:
        dabs = [
            (
                *surface.point(p, obj.name),
                float(pressure),
                None,
                surface.seed(p, obj, coords),
            )
            for p, pressure in samples
        ]
    surface_bvh = (
        BVHTree.FromPolygons(
            coords.tolist(), [list(p.vertices) for p in obj.data.polygons]
        )
        if symmetry
        else None
    )
    for center, normal, pressure, shift, seed in dabs:
        centers = [(center, normal, shift, seed)]
        if symmetry:
            mirrored = center.copy()
            mirrored[0] = 2 * plane - center[0]
            mirrored_normal = normal.copy()
            mirrored_normal[0] *= -1
            mirrored_shift = None if shift is None else shift.copy()
            if mirrored_shift is not None:
                mirrored_shift[0] *= -1
            _, _, face, _ = surface_bvh.find_nearest(Vector(mirrored))
            mirror_seed = min(
                obj.data.polygons[face].vertices,
                key=lambda i: float(np.linalg.norm(original[i] - mirrored)),
            )
            centers.append((mirrored, mirrored_normal, mirrored_shift, mirror_seed))
        selected_weight = np.zeros(len(coords))
        selected_delta = np.zeros_like(coords)
        for c, n, s, seed in centers:
            # Frozen topology distances keep surface selection stable within a stroke.
            weights = (
                neighborhood(original, neighbors, c, radius, metric, seed)
                * strength
                * pressure
                * (1 - protected)
            )
            if mode == "grab":
                changes = np.broadcast_to(s, coords.shape)
            elif mode == "normal":
                changes = np.broadcast_to(n * distance, coords.shape)
            elif mode == "pinch":
                toward = c - coords
                changes = toward - np.outer(toward @ n, n)
            else:
                changes = np.zeros_like(coords)
                for i in np.flatnonzero(weights):
                    if neighbors[i]:
                        changes[i] = (
                            coords[[j for j, _ in neighbors[i]]].mean(axis=0)
                            - coords[i]
                        )
            # Stronger side wins in overlap; symmetry center isn't double sculpted.
            choose = weights > selected_weight
            selected_delta[choose] = changes[choose] * weights[choose, None]
            selected_weight[choose] = weights[choose]
        coords += selected_delta
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite result")
    key = tw.begin(obj)
    try:
        inverse = obj.matrix_world.inverted()
        # Leave untouched local coordinates byte-exact: a world/local roundtrip
        # can otherwise move protected vertices under nonuniform object scale.
        for i in np.flatnonzero(np.any(coords != original, axis=1)):
            key.data[int(i)].co = inverse @ Vector(coords[i])
        layer = tw.finish(obj)
    except Exception:
        if obj.get("mw_pending"):
            tw.finish(obj, cancel=True)
        raise
    layer.name = "MW " + label
    records = json.loads(obj.get("mw_layers", "[]"))
    delta = coords - original
    changed = np.linalg.norm(delta, axis=1) > 1e-7
    report = {
        "layer": layer.name,
        "object": obj.name,
        "command": command,
        "source_revision": surface.info["revision"],
        "samples": len(samples),
        "changed_vertices": int(changed.sum()),
        "max_displacement": float(np.linalg.norm(delta, axis=1).max()),
        "protected_max_displacement": float(
            np.linalg.norm(delta[protected == 1], axis=1).max()
        )
        if np.any(protected == 1)
        else 0,
        "mean_world_delta": delta[changed].mean(axis=0).tolist()
        if changed.any()
        else [0, 0, 0],
    }
    records.append({"name": layer.name, "topology": topology(obj), "report": report})
    obj["mw_layers"] = json.dumps(records)
    return report


def layers(obj):
    return [
        {
            "name": r["name"],
            "value": float(obj.data.shape_keys.key_blocks[r["name"]].value),
            "topology": r["topology"],
        }
        for r in json.loads(obj.get("mw_layers", "[]"))
        if obj.data.shape_keys and r["name"] in obj.data.shape_keys.key_blocks
    ]


def set_layer(obj, name, value):
    value = number(value, 0, 1, "layer value")
    records = {r["name"]: r for r in json.loads(obj.get("mw_layers", "[]"))}
    if name not in records or records[name]["topology"] != topology(obj):
        raise ValueError("Missing or stale coordinate layer")
    obj.data.shape_keys.key_blocks[name].value = value
    bpy.context.view_layer.update()
    return layers(obj)
