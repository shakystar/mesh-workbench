"""Measured section sweeps and Hermite ring bridges."""

import json
import math
import bpy
import bmesh
import numpy as np
from . import geometry, sculpt, sweep


def _mesh(name, vertices, faces, smooth=True):
    if name in bpy.data.objects:
        raise ValueError("Output exists")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = smooth
    return obj


def create(name, centers, radii, segments=32, reference=(0, 1, 0), closed=False):
    if not closed:
        obj = sweep.sweep(name, centers, radii, segments, reference)
    else:
        points = [geometry.vector(p) for p in centers]
        normal = geometry.vector(reference).normalized()
        if (
            len(points) < 4
            or len(points) != len(radii)
            or type(segments) is not int
            or not 4 <= segments <= 256
        ):
            raise ValueError("Invalid closed path sampling")
        if (
            any(abs((p - points[0]).dot(normal)) > 1e-5 for p in points)
            or normal.length < 0.9
        ):
            raise ValueError("Closed paths require a planar loop and its normal")
        vertices = []
        faces = []
        for i, (p, r) in enumerate(zip(points, radii)):
            if len(r) != 2 or any(not math.isfinite(v) or v <= 0 for v in r):
                raise ValueError("Invalid radii")
            if (points[(i + 1) % len(points)] - p).length < 1e-7:
                raise ValueError("Repeated path point")
            tangent = points[(i + 1) % len(points)] - points[i - 1]
            if tangent.length < 1e-7:
                raise ValueError("Reversing closed path")
            second = tangent.normalized().cross(normal).normalized()
            vertices.extend(
                p
                + normal * r[0] * math.cos(j * math.tau / segments)
                + second * r[1] * math.sin(j * math.tau / segments)
                for j in range(segments)
            )
            for j in range(segments):
                faces.append(
                    (
                        i * segments + j,
                        i * segments + (j + 1) % segments,
                        ((i + 1) % len(points)) * segments + (j + 1) % segments,
                        ((i + 1) % len(points)) * segments + j,
                    )
                )
        obj = _mesh(name, vertices, faces)
    obj["mw_path"] = json.dumps(
        {
            "version": 1,
            "centers": centers,
            "radii": radii,
            "segments": segments,
            "reference": reference,
            "closed": closed,
            "topology": geometry.signature(obj),
        }
    )
    return obj


def reshape(source, centers, name):
    state = json.loads(source.get("mw_path", "{}"))
    if (
        state.get("version") != 1
        or state["topology"] != geometry.signature(source)
        or len(centers) != len(state["centers"])
    ):
        raise ValueError("Compatible path mesh and center count required")
    obj = create(
        name,
        centers,
        state["radii"],
        state["segments"],
        state["reference"],
        state["closed"],
    )
    for material in source.data.materials:
        obj.data.materials.append(material)
    return obj


def sections(obj):
    state = json.loads(obj["mw_path"])
    if geometry.signature(obj) != state["topology"]:
        raise ValueError("Stale path topology")
    coords = sculpt.coordinates(obj)
    n = state["segments"]
    errors = []
    center_errors = []
    for i, (center, radii) in enumerate(zip(state["centers"], state["radii"])):
        ring = coords[i * n : (i + 1) * n]
        mean = ring.mean(axis=0)
        measured = np.sqrt(
            np.maximum(0, np.linalg.eigvalsh((ring - mean).T @ (ring - mean) / n) * 2)
        )[-2:]
        errors.append(float(np.max(np.abs(measured - np.sort(radii)))))
        center_errors.append(float(np.linalg.norm(mean - center)))
    return {
        "rings": len(errors),
        "radius_error_max": max(errors),
        "center_error_max": max(center_errors),
    }


def bridge(name, start, end, start_tangent, end_tangent, rows=16, caps=True):
    a = np.asarray(start, dtype=float)
    b = np.asarray(end, dtype=float)
    u = np.asarray(start_tangent, dtype=float)
    v = np.asarray(end_tangent, dtype=float)
    if (
        a.ndim != 2
        or a.shape[1] != 3
        or len(a) < 4
        or b.shape != a.shape
        or u.shape != a.shape
        or v.shape != a.shape
        or not np.isfinite([a, b, u, v]).all()
    ):
        raise ValueError("Matching finite rings and per-vertex tangents required")
    if type(rows) is not int or not 2 <= rows <= 256:
        raise ValueError("Invalid bridge rows")
    if (
        np.min(np.linalg.norm(u, axis=1)) < 1e-8
        or np.min(np.linalg.norm(v, axis=1)) < 1e-8
    ):
        raise ValueError("Nonzero bridge tangents required")
    vertices = []
    n = len(a)
    for t in np.linspace(0, 1, rows + 1):
        ring = (
            (2 * t**3 - 3 * t * t + 1) * a
            + (t**3 - 2 * t * t + t) * u
            + (-2 * t**3 + 3 * t * t) * b
            + (t**3 - t * t) * v
        )
        vertices.extend(ring.tolist())
    faces = [
        (i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j)
        for i in range(rows)
        for j in range(n)
    ]
    if caps:
        faces.extend([tuple(reversed(range(n))), tuple(rows * n + j for j in range(n))])
    obj = _mesh(name, vertices, faces)
    obj["mw_bridge"] = json.dumps(
        {
            "rows": rows,
            "segments": n,
            "start": a.tolist(),
            "end": b.tolist(),
            "start_tangent": u.tolist(),
            "end_tangent": v.tolist(),
        }
    )
    return obj


def bridge_report(obj):
    state = json.loads(obj["mw_bridge"])
    n = state["segments"]
    rows = state["rows"]
    xyz = sculpt.coordinates(obj)
    start = np.asarray(state["start"])
    end = np.asarray(state["end"])
    angles = []
    for d, t in [
        (xyz[n : 2 * n] - xyz[:n], np.asarray(state["start_tangent"])),
        (
            xyz[rows * n : (rows + 1) * n] - xyz[(rows - 1) * n : rows * n],
            np.asarray(state["end_tangent"]),
        ),
    ]:
        dot = np.sum(d * t, axis=1) / (
            np.linalg.norm(d, axis=1) * np.linalg.norm(t, axis=1)
        )
        angles.extend(np.degrees(np.arccos(np.clip(dot, -1, 1))).tolist())
    return {
        "endpoint_position_error": float(
            max(
                np.max(np.abs(xyz[:n] - start)),
                np.max(np.abs(xyz[rows * n : (rows + 1) * n] - end)),
            )
        ),
        "sampled_endpoint_tangent_angle_degrees": max(angles),
        "analytic_endpoint_derivatives": "specified Hermite tangents",
    }
