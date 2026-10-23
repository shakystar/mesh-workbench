"""Dimensioned mechanical primitives with explicit axes and clearance geometry."""

import math
from functools import wraps
import bpy
import numpy as np
from mathutils import Vector
from . import construction, enclosure, geometry, sculpt


def _atomic(builder):
    @wraps(builder)
    def run(*args, **kwargs):
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        selected = {o: o.select_get() for o in objects}
        active = bpy.context.view_layer.objects.active
        try:
            return builder(*args, **kwargs)
        except Exception:
            for obj in list(bpy.data.objects):
                if obj not in objects:
                    remove(obj)
            for mesh in list(bpy.data.meshes):
                if mesh not in meshes and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            for obj, value in selected.items():
                obj.select_set(value)
            bpy.context.view_layer.objects.active = active
            raise

    return run


@_atomic
def box(name, dimensions, center, radius=0.4):
    obj = construction.rounded_box(name, dimensions, center, radius, segments=4)
    sculpt.bake(obj)
    enclosure._valid(obj)
    return obj


@_atomic
def annulus(
    name, outer_radius, inner_radius, start, length, axis=(1, 0, 0), segments=64
):
    if not 0 < inner_radius < outer_radius or length <= 0:
        raise ValueError("Positive annular wall and length required")
    profile = [
        (inner_radius, 0),
        (outer_radius, 0),
        (outer_radius, length),
        (inner_radius, length),
    ]
    obj = construction.revolve(name, profile, segments=segments, closed=True)
    direction = geometry.vector(axis)
    if direction.length < 1e-8:
        raise ValueError("Nonzero mechanical axis required")
    rotation = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    origin = geometry.vector(start)
    for v in obj.data.vertices:
        v.co = origin + rotation @ v.co
    obj.data.update()
    for f in obj.data.polygons:
        f.use_smooth = abs(f.normal.dot(direction.normalized())) < 0.5
    enclosure._valid(obj)
    return obj


@_atomic
def prism(name, section_yz, origin, length):
    section = np.asarray(section_yz, dtype=float)
    if (
        section.ndim != 2
        or section.shape[1] != 2
        or len(section) < 3
        or not np.isfinite(section).all()
        or length <= 0
    ):
        raise ValueError("Finite section and positive extrusion length required")
    origin = np.asarray(geometry.vector(origin))
    n = len(section)
    xyz = [origin + np.array([x, y, z]) for x in (0, length) for y, z in section]
    faces = [list(reversed(range(n))), list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, (i + 1) % n + n, i + n] for i in range(n)]
    obj = enclosure._mesh(name, xyz, faces)
    for f in obj.data.polygons:
        f.use_smooth = False
    enclosure._valid(obj)
    return obj


@_atomic
def jaw(
    name,
    origin,
    length,
    rear_width,
    tip_width,
    rear_depth,
    tip_depth,
    diameter=2,
    angle=0,
):
    diameter = sculpt.number(diameter, 2, 10, "bit diameter")
    theta = math.radians(angle)
    # Rotation around the common chuck axis; face normal points radially inward.
    xyz = []
    base = np.asarray(geometry.vector(origin))
    for x, width, depth in (
        (0, rear_width, rear_depth),
        (length, tip_width, tip_depth),
    ):
        for r, t in (
            (diameter / 2, -width / 2),
            (diameter / 2 + depth, -width / 2),
            (diameter / 2 + depth, width / 2),
            (diameter / 2, width / 2),
        ):
            xyz.append(
                base
                + [
                    x,
                    r * math.cos(theta) - t * math.sin(theta),
                    r * math.sin(theta) + t * math.cos(theta),
                ]
            )
    obj = enclosure._mesh(
        name,
        xyz,
        [
            [3, 2, 1, 0],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ],
    )
    for f in obj.data.polygons:
        f.use_smooth = False
    enclosure._valid(obj)
    obj["mw_radial_jaw"] = str(float(angle))
    return obj


@_atomic
def cut_box(source, name, dimensions, center, radius=0.4):
    cutter = box(name + " cutter", dimensions, center, radius)
    if len(source.data.materials) > 2:
        cutter.data.materials.append(source.data.materials[2])
    try:
        return enclosure.boolean(source, cutter, "DIFFERENCE", name)
    finally:
        remove(cutter)


def remove(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if not mesh.users:
        bpy.data.meshes.remove(mesh)


@_atomic
def radial_cage(
    name, outer_radius, inner_radius, start, length, slot_width, slot_radius
):
    part = annulus(name + " stock", outer_radius, inner_radius, start, length)
    try:
        for i in range(3):
            theta = math.tau * i / 3
            cutter = box(
                name + " slot",
                [length + 2, slot_radius, slot_width],
                [0, 0, 0],
                radius=0.15,
            )
            for v in cutter.data.vertices:
                x, y, z = v.co
                y += slot_radius / 2
                v.co = Vector(start) + Vector(
                    (
                        x + length / 2,
                        y * math.cos(theta) - z * math.sin(theta),
                        y * math.sin(theta) + z * math.cos(theta),
                    )
                )
            result = enclosure.boolean(
                part,
                cutter,
                "DIFFERENCE",
                name if i == 2 else name + " stage " + str(i),
            )
            remove(cutter)
            remove(part)
            part = result
        return part
    except Exception:
        if part.name in bpy.data.objects:
            remove(part)
        raise
