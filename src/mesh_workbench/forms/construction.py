"""Dimensioned construction helpers; fresh objects, world-unit dimensions."""

import math

import bmesh
import bpy
from mathutils import Vector

from . import geometry, models


def rounded_box(name, dimensions, location=(0, 0, 0), radius=0.05, segments=8):
    dims = geometry.vector(dimensions)
    pos = geometry.vector(location)
    if min(dims) <= 0 or not math.isfinite(radius) or not 0 < radius < min(dims) / 2:
        raise ValueError(
            "Radius must be positive and below half the smallest dimension"
        )
    if type(segments) is not int or not 1 <= segments <= 32:
        raise ValueError("Segments must be 1..32")
    obj = models.primitive("cube", name, location=pos)
    for v in obj.data.vertices:
        v.co = Vector([v.co[i] * dims[i] / 2 for i in range(3)])
    mod = obj.modifiers.new("Dimensioned edge radius", "BEVEL")
    mod.width = radius
    mod.segments = segments
    mod.limit_method = "ANGLE"
    for face in obj.data.polygons:
        face.use_smooth = True
    normals = obj.modifiers.new("Face weighted normals", "WEIGHTED_NORMAL")
    normals.keep_sharp = True
    return obj


def revolve(name, profile, segments=64, closed=False, location=(0, 0, 0)):
    """Revolve positive-radius (radius,z) polyline about Z. Caps on open profiles.

    Closed profiles produce hollow rings. Profile must be simple; arbitrary
    self-intersection detection is not implemented. Flat caps remain flat shaded.
    """
    pos = geometry.vector(location)
    try:
        points = [(float(r), float(z)) for r, z in profile]
    except (TypeError, ValueError) as exc:
        raise ValueError("Expected radius,z pairs") from exc
    if len(points) < (3 if closed else 2) or any(
        r <= 0 or not math.isfinite(r + z) for r, z in points
    ):
        raise ValueError("Finite positive radii and sufficient profile points required")
    pairs = list(zip(points, points[1:] + ([points[0]] if closed else [])))
    if any(a == b for a, b in pairs):
        raise ValueError("Repeated adjacent profile point")
    if type(segments) is not int or not 3 <= segments <= 512:
        raise ValueError("Segments must be 3..512")
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    vertices = [
        (
            r * math.cos(2 * math.pi * j / segments),
            r * math.sin(2 * math.pi * j / segments),
            z,
        )
        for r, z in points
        for j in range(segments)
    ]
    faces = []
    for i in range(len(points) if closed else len(points) - 1):
        k = (i + 1) % len(points)
        for j in range(segments):
            n = (j + 1) % segments
            faces.append(
                (i * segments + j, i * segments + n, k * segments + n, k * segments + j)
            )
    if not closed:
        faces += [
            tuple(reversed(range(segments))),
            tuple((len(points) - 1) * segments + j for j in range(segments)),
        ]
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
    obj.location = pos
    for p in mesh.polygons:
        p.use_smooth = len(p.vertices) == 4
    bpy.context.view_layer.update()
    return obj


def strut(name, start, end, radius=0.05, segments=32):
    """Cylinder whose end faces coincide with two world-space anchors."""
    a, b = geometry.vector(start), geometry.vector(end)
    d = b - a
    if d.length < 1e-8 or not math.isfinite(radius) or radius <= 0:
        raise ValueError("Distinct anchors and positive finite radius required")
    obj = revolve(
        name,
        [(radius, -d.length / 2), (radius, d.length / 2)],
        segments,
        location=(a + b) / 2,
    )
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return obj
