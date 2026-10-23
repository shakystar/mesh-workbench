"""Source-preserving surface partitions, closed offset shells and sampled gauges."""

import json
import heapq
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import geometry, sculpt


def extract(source, selection, name, thickness=1.6, trim=0.35):
    selection = geometry.validate_selection(source, selection)
    if selection["domain"] != "FACE" or not selection["indices"]:
        raise ValueError("Nonempty face selection required")
    thickness = sculpt.number(thickness, 1e-5, 1e5, "thickness")
    trim = sculpt.number(trim, 0, 1e4, "trim")
    if name in bpy.data.objects:
        raise ValueError("Output exists")
    coords = sculpt.coordinates(source)
    normal_matrix = source.matrix_world.inverted().transposed().to_3x3()
    ev = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        normals = [(normal_matrix @ v.normal).normalized() for v in mesh.vertices]
        source_faces = [tuple(p.vertices) for p in mesh.polygons]
        mesh.calc_loop_triangles()
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    finally:
        ev.to_mesh_clear()
    faces = [source_faces[i] for i in selection["indices"]]
    used = sorted({v for f in faces for v in f})
    edge_faces = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            edge_faces.setdefault(tuple(sorted((a, b))), []).append((a, b))
    if any(len(v) > 2 for v in edge_faces.values()):
        raise ValueError("Nonmanifold selected patch")
    edges = [v[0] for v in edge_faces.values() if len(v) == 1]
    degree = {}
    for a, b in edges:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    if not edges or any(v != 2 for v in degree.values()):
        raise ValueError("Patch boundaries must form disjoint loops")
    outer = {i: Vector(coords[i]) for i in used}
    if trim:
        tree = BVHTree.FromPolygons(coords.tolist(), triangles, all_triangles=True)
        base_normals = [v.copy() for v in normals]
        directions = {i: Vector((0, 0, 0)) for i in degree}
        for a, b in edges:
            tangent = (Vector(coords[b]) - Vector(coords[a])).normalized()
            for i in [a, b]:
                directions[i] += normals[i].cross(tangent)
        for i, direction in directions.items():
            if direction.length < 1e-8:
                raise ValueError("Ambiguous boundary trim direction")
            direction.normalize()
        # Carry boundary motion into a geodesic collar so fine cells cannot
        # invert merely because their width is smaller than the requested trim.
        adjacency = {i: [] for i in used}
        for a, b in edge_faces:
            length = float(np.linalg.norm(coords[a] - coords[b]))
            adjacency[a].append((b, length))
            adjacency[b].append((a, length))
        distance = {i: 0.0 for i in degree}
        seed = {i: i for i in degree}
        queue = [(0.0, i) for i in degree]
        heapq.heapify(queue)
        support = trim * 4
        while queue:
            d, i = heapq.heappop(queue)
            if d != distance[i]:
                continue
            for j, length in adjacency[i]:
                new = d + length
                if new < support and new < distance.get(j, float("inf")):
                    distance[j] = new
                    seed[j] = seed[i]
                    heapq.heappush(queue, (new, j))
        for i, d in distance.items():
            amount = trim * (1 - d / support) ** 2
            guess = outer[i] + directions[seed[i]] * amount
            hit, n, index, _ = tree.find_nearest(guess, trim * 2 + 1e-5)
            if hit is None or n.dot(base_normals[i]) < 0.25:
                raise ValueError("Trim projection missed or changed side")
            outer[i] = hit
            ids = triangles[index]
            a, b, c = [Vector(coords[j]) for j in ids]
            u, v, w = b - a, c - a, hit - a
            aa, ab, bb = u.dot(u), u.dot(v), v.dot(v)
            denominator = aa * bb - ab * ab
            if abs(denominator) < 1e-16:
                raise ValueError("Degenerate projection triangle")
            wb = (bb * w.dot(u) - ab * w.dot(v)) / denominator
            wc = (aa * w.dot(v) - ab * w.dot(u)) / denominator
            normals[i] = (
                base_normals[ids[0]] * (1 - wb - wc)
                + base_normals[ids[1]] * wb
                + base_normals[ids[2]] * wc
            ).normalized()
    for a, b in edge_faces:
        if (outer[b] - outer[a]).dot(Vector(coords[b]) - Vector(coords[a])) <= 0:
            raise ValueError("Trim reversed a mesh edge; reduce trim")
    # Reject reversed or collapsed outer cells before allocating an output object.
    for face in faces:
        for j in range(1, len(face) - 1):
            ids = [face[0], face[j], face[j + 1]]
            a, b, c = [outer[i] for i in ids]
            n = (b - a).cross(c - a)
            expected = sum((normals[i] for i in ids), Vector((0, 0, 0)))
            if n.length < 1e-10 or n.dot(expected) <= 0:
                raise ValueError(
                    "Trim folded a surface cell; use wider guides or smaller trim"
                )
    mapping = {old: i for i, old in enumerate(used)}
    n = len(used)
    vertices = [outer[i] for i in used] + [
        outer[i] - normals[i] * thickness for i in used
    ]
    outer_faces = [tuple(mapping[i] for i in f) for f in faces]
    inner_faces = [tuple(n + mapping[i] for i in reversed(f)) for f in faces]
    all_faces = (
        outer_faces
        + inner_faces
        + [(mapping[a], mapping[a] + n, mapping[b] + n, mapping[b]) for a, b in edges]
    )
    result = bpy.data.meshes.new(name)
    result.from_pydata(vertices, [], all_faces)
    bm = bmesh.new()
    bm.from_mesh(result)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(result)
    bm.free()
    result.update()
    obj = bpy.data.objects.new(name, result)
    bpy.context.collection.objects.link(obj)
    for f in result.polygons:
        f.use_smooth = f.index < len(outer_faces) * 2
    obj["mw_shell"] = json.dumps(
        {
            "source": source.name,
            "source_topology": geometry.signature(source),
            "topology": geometry.signature(obj),
            "outer_faces": outer_faces,
            "inner_faces": inner_faces,
            "boundary_edges": [list(e) for e in edges],
            "source_to_outer": mapping,
            "nominal_thickness": thickness,
            "trim": trim,
        }
    )
    bpy.context.view_layer.update()
    from . import fairing

    if fairing.overlap_candidates(obj):
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        raise ValueError(
            "Offset shell introduced nonadjacent overlaps; output discarded"
        )
    return obj


def _state(obj):
    if "mw_shell" not in obj:
        raise ValueError("Measured shell metadata required")
    sculpt.editable(obj)
    state = json.loads(obj["mw_shell"])
    if state["topology"] != geometry.signature(obj):
        raise ValueError("Shell topology changed; gauge metadata stale")
    return state, sculpt.coordinates(obj)


def thickness(obj, minimum=1.35, maximum=1.9, method="nearest"):
    """Sample opposite-skin distance; nearest is conservative vs normal-ray length.

    Normal rays can leave a finite panel through its rim. They remain available
    as a separate diagnostic, and every miss is reported as a failed sample.
    """
    if method not in ("nearest", "normal"):
        raise ValueError("Thickness method must be nearest or normal")
    minimum = sculpt.number(minimum, 1e-6, 1e6, "minimum thickness")
    maximum = sculpt.number(maximum, minimum, 1e6, "maximum thickness")
    state, coords = _state(obj)
    inner = BVHTree.FromPolygons(coords.tolist(), state["inner_faces"])
    values = []
    violations = []
    missing = 0
    for index, face in enumerate(state["outer_faces"]):
        # Triangulate convex quads/fans for independent centroid probes.
        for j in range(1, len(face) - 1):
            a, b, c = [Vector(coords[i]) for i in [face[0], face[j], face[j + 1]]]
            normal = (b - a).cross(c - a)
            point = (a + b + c) / 3
            if normal.length < 1e-10:
                violations.append(
                    {
                        "face": index,
                        "position": list(point),
                        "reason": "degenerate outer triangle",
                    }
                )
                missing += 1
                continue
            normal.normalize()
            if method == "normal":
                hit, _, _, distance = inner.ray_cast(point, -normal, maximum * 10)
            else:
                hit, _, _, distance = inner.find_nearest(point, maximum * 10)
            if hit is None:
                missing += 1
                violations.append(
                    {
                        "face": index,
                        "position": list(point),
                        "reason": "inner surface query missed",
                    }
                )
            else:
                values.append(distance)
                if not minimum <= distance <= maximum:
                    violations.append(
                        {
                            "face": index,
                            "position": list(point),
                            "value": distance,
                            "reason": "thickness outside range",
                        }
                    )
    return {
        "object": obj.name,
        "method": method,
        "samples": len(values) + missing,
        "missing": missing,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": sum(values) / len(values) if values else None,
        "passed": not violations,
        "violations": violations,
    }


def gap(left, right, minimum=0.45, maximum=1.05):
    minimum = sculpt.number(minimum, 0, 1e6, "minimum gap")
    maximum = sculpt.number(maximum, minimum, 1e6, "maximum gap")
    a, ca = _state(left)
    b, cb = _state(right)
    if a["source"] != b["source"] or a["source_topology"] != b["source_topology"]:
        raise ValueError("Panels must share the same indexed master")
    ea = {tuple(sorted(e)) for e in a["boundary_edges"]}
    eb = {tuple(sorted(e)) for e in b["boundary_edges"]}
    shared = sorted(ea & eb)
    if not shared:
        raise ValueError("No shared trim boundary")
    values = []
    violations = []
    for edge in shared:
        pa = [Vector(ca[a["source_to_outer"][str(i)]]) for i in edge]
        pb = [Vector(cb[b["source_to_outer"][str(i)]]) for i in edge]
        for p, q in [(pa, pb), (pb, pa)]:
            line = q[1] - q[0]
            if line.length_squared < 1e-12:
                raise ValueError("Collapsed gap edge")
            for t in [0, 0.5, 1]:
                point = p[0].lerp(p[1], t)
                hit = q[0] + line * max(
                    0, min(1, (point - q[0]).dot(line) / line.length_squared)
                )
                distance = (point - hit).length
                values.append(distance)
                if not minimum <= distance <= maximum:
                    violations.append(
                        {
                            "source_edge": list(edge),
                            "position": list((point + hit) / 2),
                            "value": distance,
                            "reason": "gap outside range",
                        }
                    )
    return {
        "objects": [left.name, right.name],
        "edges": len(shared),
        "samples": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "passed": not violations,
        "violations": violations,
    }


def markers(name, report, radius=0.5, limit=100):
    if name in bpy.data.objects or type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("New marker name and limit 1..1000 required")
    radius = sculpt.number(radius, 1e-6, 1000, "marker radius")
    points = report["violations"]
    if not points:
        raise ValueError("No violations to mark")
    stride = max(1, math.ceil(len(points) / limit))
    vertices = []
    faces = []
    for hit in points[::stride]:
        center = Vector(hit["position"])
        offset = len(vertices)
        vertices.extend(
            center + Vector(p) * radius
            for p in [
                (1, 0, 0),
                (-1, 0, 0),
                (0, 1, 0),
                (0, -1, 0),
                (0, 0, 1),
                (0, 0, -1),
            ]
        )
        faces.extend(
            tuple(offset + i for i in f)
            for f in [
                (0, 2, 4),
                (2, 1, 4),
                (1, 3, 4),
                (3, 0, 4),
                (2, 0, 5),
                (1, 2, 5),
                (3, 1, 5),
                (0, 3, 5),
            ]
        )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def intersections(left, right):
    """Cross-object triangle intersection candidates, excluding no contacts.

    Does not detect full containment without surface crossings.
    """

    def tree(obj):
        if obj.type != "MESH":
            raise ValueError("Mesh required")
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ev.to_mesh()
        try:
            mesh.calc_loop_triangles()
            coords = [obj.matrix_world @ v.co for v in mesh.vertices]
            triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
            if not triangles:
                raise ValueError("Empty mesh")
            return BVHTree.FromPolygons(coords, triangles, all_triangles=True)
        finally:
            ev.to_mesh_clear()

    bpy.context.view_layer.update()
    pairs = tree(left).overlap(tree(right))
    return {"objects": [left.name, right.name], "triangle_pair_count": len(pairs)}
