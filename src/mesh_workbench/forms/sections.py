"""Evaluated triangle/plane sections and bounded contour distances."""

import bpy
import numpy as np


def cut(obj, axis, value):
    if (
        type(axis) is not int
        or axis not in range(3)
        or not np.isfinite(value)
        or obj.type != "MESH"
    ):
        raise ValueError("Mesh, axis and finite section value required")
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    segments = []
    try:
        mesh.calc_loop_triangles()
        coords = np.array([obj.matrix_world @ v.co for v in mesh.vertices])
        for tri in mesh.loop_triangles:
            points = coords[list(tri.vertices)]
            distances = points[:, axis] - value
            if min(distances) > 1e-7 or max(distances) < -1e-7:
                continue
            hits = []
            for i, j in [(0, 1), (1, 2), (2, 0)]:
                a, b = points[i], points[j]
                da, db = distances[i], distances[j]
                if abs(da) < 1e-7:
                    hits.append(a)
                if da * db < 0:
                    hits.append(a + (b - a) * da / (da - db))
            unique = []
            for hit in hits:
                if not any(np.linalg.norm(hit - p) < 1e-7 for p in unique):
                    unique.append(hit)
            if len(unique) == 2:
                segments.append([unique[0].tolist(), unique[1].tolist()])
    finally:
        ev.to_mesh_clear()
    if not segments:
        raise ValueError("Section misses mesh or is coplanar")
    values = np.asarray(segments)
    return {
        "object": obj.name,
        "axis": axis,
        "value": float(value),
        "segments": segments,
        "bounds": [
            values.reshape(-1, 3).min(0).tolist(),
            values.reshape(-1, 3).max(0).tolist(),
        ],
    }


def compare(section, expected_bounds):
    actual = np.asarray(section["bounds"], float)
    expected = np.asarray(expected_bounds, float)
    if (
        expected.shape != (2, 3)
        or not np.isfinite(expected).all()
        or (expected[0] > expected[1]).any()
    ):
        raise ValueError("Expected ordered finite XYZ bounds")
    return {
        "object": section["object"],
        "value": section["value"],
        "bound_error_max": float(np.max(np.abs(actual - expected))),
        "actual_bounds": actual.tolist(),
        "expected_bounds": expected.tolist(),
    }
