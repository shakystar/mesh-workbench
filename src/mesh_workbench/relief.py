"""Closed relief dots that conform each vertex to an evaluated target surface."""

import json
import math

import bmesh
import bpy
from mathutils import Vector

from . import patterns, sculpt


def dots(
    target,
    points,
    name,
    radii=0.04,
    height=0.004,
    embed=0.002,
    segments=24,
    rings=3,
    max_distance=1,
    direction=None,
    gap=0.005,
    clearance=0.0005,
):
    """Build separate capped reliefs in one new mesh, without changing the target.

    Offsets follow each hit normal. Bottom surfaces intentionally enter the target.
    Conservative bounding spheres reject overlapping motifs; arbitrary target
    collision, sharp creases and adjacent-face self-folds are not solved.
    """
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    if not 1 <= len(points) <= 1000:
        raise ValueError("Expected 1..1000 points")
    rs = [radii] * len(points) if isinstance(radii, (int, float)) else list(radii)
    if len(rs) != len(points):
        raise ValueError("One radius per anchor required")
    rs = [sculpt.number(r, 1e-5, 100, "radius") for r in rs]
    height = sculpt.number(height, 0, 100, "height")
    embed = sculpt.number(embed, 1e-6, 100, "embed")
    gap = sculpt.number(gap, 0, 100, "gap")
    clearance = sculpt.number(clearance, 1e-6, 100, "clearance")
    minimum_clearance = float("inf")
    if type(segments) is not int or not 8 <= segments <= 128:
        raise ValueError("Segments must be 8..128")
    if type(rings) is not int or not 1 <= rings <= 12:
        raise ValueError("Rings must be 1..12")
    hits = patterns.project(target, points, max_distance, 0, direction)
    tree = patterns.tree(target)
    vertices = []
    faces = []
    bounds = []
    anchors = []
    for hit, radius in zip(hits, rs):
        anchor = Vector(hit["position"])
        normal = Vector(hit["normal"])
        rot = Vector((0, 0, 1)).rotation_difference(normal)
        samples = [(0, 0, 0)]
        samples.extend(
            (
                radius * k / rings * math.cos(j * math.tau / segments),
                radius * k / rings * math.sin(j * math.tau / segments),
                k / rings,
            )
            for k in range(1, rings + 1)
            for j in range(segments)
        )
        top = []
        bottom = []
        reach = radius * 2 + 0.01
        for x, y, t in samples:
            origin = anchor + rot @ Vector((x, y, 0)) + normal * reach
            pos, n, face, distance = tree.ray_cast(origin, -normal, reach * 2)
            if pos is None or n.dot(normal) < 0.5:
                raise ValueError("Relief footprint missed or crossed a steep surface")
            top.append(pos + n * (height * (1 - t * t) ** 2 + clearance))
            bottom.append(pos - n * embed)
        bound = max((p - anchor).length for p in top + bottom)
        if any((anchor - a).length < bound + b + gap for a, b in bounds):
            raise ValueError("Relief bounding spheres violate gap")
        bounds.append((anchor, bound))
        anchors.append(list(anchor))
        offset = len(vertices)
        count = len(top)
        vertices.extend(top + bottom)
        local = []
        for j in range(segments):
            local.append((0, 1 + j, 1 + (j + 1) % segments))
        for k in range(rings - 1):
            a = 1 + k * segments
            b = a + segments
            for j in range(segments):
                q = (j + 1) % segments
                local.append((a + j, b + j, b + q, a + q))
        edges = {tuple(sorted((a, b))) for f in local for a, b in zip(f, f[1:] + f[:1])}
        probes = top + [(top[a] + top[b]) / 2 for a, b in edges]
        probes.extend(sum((top[i] for i in f), Vector()) / len(f) for f in local)
        for probe in probes:
            hit_point, hit_normal, _, _ = tree.find_nearest(probe)
            signed = (probe - hit_point).dot(hit_normal)
            minimum_clearance = min(minimum_clearance, signed)
            if signed < -1e-7:
                raise ValueError(
                    "Relief top intersects target at a sampled point; increase clearance or resolution"
                )
        faces.extend(tuple(offset + i for i in f) for f in local)
        faces.extend(tuple(offset + count + i for i in reversed(f)) for f in local)
        outer = 1 + (rings - 1) * segments
        for j in range(segments):
            q = (j + 1) % segments
            faces.append(
                (
                    offset + outer + j,
                    offset + outer + q,
                    offset + count + outer + q,
                    offset + count + outer + j,
                )
            )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = True
    obj["mw_relief_settings"] = json.dumps(
        {
            "radii": rs,
            "height": height,
            "embed": embed,
            "segments": segments,
            "rings": rings,
            "gap": gap,
            "clearance": clearance,
        }
    )
    obj["mw_relief_count"] = len(points)
    obj["mw_relief_anchors"] = [v for a in anchors for v in a]
    obj["mw_relief_gap"] = gap
    obj["mw_relief_sampled_clearance"] = minimum_clearance
    bpy.context.view_layer.update()
    return obj
