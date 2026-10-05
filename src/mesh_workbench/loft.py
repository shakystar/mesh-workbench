"""Closed asymmetric guide lofts with shape-preserving longitudinal interpolation."""

import json
import math
import numpy as np
import bpy
import bmesh
from . import sculpt


def interpolate(x, y, samples):
    """Monotone piecewise cubic Hermite interpolation; no extrapolation."""
    x, y, q = np.asarray(x, float), np.asarray(y, float), np.asarray(samples, float)
    if (
        x.ndim != 1
        or y.shape != x.shape
        or len(x) < 3
        or not np.isfinite(np.concatenate((x, y, q.ravel()))).all()
        or not (np.diff(x) > 0).all()
        or q.min() < x[0]
        or q.max() > x[-1]
    ):
        raise ValueError("Finite ordered guides and in-range samples required")
    h = np.diff(x)
    d = np.diff(y) / h
    slopes = np.zeros(len(x))
    for i in range(1, len(x) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            slopes[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    for end, a, b, ha, hb in [
        (0, d[0], d[1], h[0], h[1]),
        (-1, d[-1], d[-2], h[-1], h[-2]),
    ]:
        m = ((2 * ha + hb) * a - ha * b) / (ha + hb)
        if m * a <= 0:
            m = 0
        elif a * b < 0 and abs(m) > 3 * abs(a):
            m = 3 * a
        slopes[end] = m
    idx = np.clip(np.searchsorted(x, q, side="right") - 1, 0, len(x) - 2)
    t = (q - x[idx]) / h[idx]
    return (
        (2 * t**3 - 3 * t**2 + 1) * y[idx]
        + (t**3 - 2 * t**2 + t) * h[idx] * slopes[idx]
        + (-2 * t**3 + 3 * t**2) * y[idx + 1]
        + (t**3 - t**2) * h[idx] * slopes[idx + 1]
    )


def section_values(sections, seam_height, ys):
    x = np.array([s["y"] for s in sections], float)
    columns = np.array(
        [
            [s["left"], s["right"], s["top"] - seam_height, seam_height - s["bottom"]]
            for s in sections
        ],
        float,
    )
    if (
        len(sections) < 3
        or not np.isfinite(columns).all()
        or (columns < 0).any()
        or np.any(columns[[0, -1]] != 0)
        or (columns[1:-1] <= 0).any()
    ):
        raise ValueError(
            "Positive interior sections and zero-radius end poles required"
        )
    # Interpolate squared radii for rounded, rather than conical, end poles.
    return np.column_stack(
        [np.sqrt(np.maximum(0, interpolate(x, c * c, ys))) for c in columns.T]
    )


def cross_section(y, values, seam_height, tilt, angles):
    left, right, upper, lower = values
    angles = np.asarray(angles, float)
    c, s = np.cos(angles), np.sin(angles)
    crown = (
        0 if abs(tilt) < 1e-10 else (-1 + math.sqrt(1 + 8 * tilt * tilt)) / (4 * tilt)
    )
    normalization = math.sqrt(1 - crown * crown) * (1 + tilt * crown)
    x = (left + right) / 2 * c + (right - left) / 2 * c * c
    z = seam_height + np.where(
        s >= 0, upper * s * (1 + tilt * c) / normalization, lower * s
    )
    return np.column_stack((x, np.full_like(x, y), z))


def create(
    name, sections, seam_height=11, tilt=0, rows=128, segments=128, end_refinement=0.5
):
    seam_height = sculpt.number(seam_height, -1e5, 1e5, "seam height")
    tilt = sculpt.number(tilt, -0.4, 0.4, "tilt")
    end_refinement = sculpt.number(end_refinement, 0, 1, "end refinement")
    if (
        type(rows) is not int
        or not 16 <= rows <= 512
        or type(segments) is not int
        or not 16 <= segments <= 256
        or segments % 4
    ):
        raise ValueError(
            "Rows 16..512 and angular segments 16..256 divisible by four required"
        )
    if name in bpy.data.objects:
        raise ValueError("Output exists")
    ys = sorted(
        set(
            (
                sections[0]["y"]
                + (sections[-1]["y"] - sections[0]["y"])
                * (
                    (1 - end_refinement) * np.linspace(0, 1, rows + 1)
                    + end_refinement
                    * (1 - np.cos(np.linspace(0, math.pi, rows + 1)))
                    / 2
                )
            ).tolist()
            + [float(s["y"]) for s in sections]
        )
    )
    tolerance = (sections[-1]["y"] - sections[0]["y"]) * 1e-10
    ys = sorted(
        set(
            next((float(s["y"]) for s in sections if abs(y - s["y"]) < tolerance), y)
            for y in ys
        )
    )
    values = section_values(sections, seam_height, ys)
    vertices = [[0, ys[0], seam_height]]
    angles = np.arange(segments) * math.tau / segments
    for y, v in zip(ys[1:-1], values[1:-1]):
        vertices.extend(cross_section(y, v, seam_height, tilt, angles).tolist())
    last = len(vertices)
    vertices.append([0, ys[-1], seam_height])
    faces = []
    params = []
    for j in range(segments):
        k = (j + 1) % segments
        faces.append((0, 1 + k, 1 + j))
        params.append([(ys[0] + ys[1]) / 2, (j + 0.5) * math.tau / segments])
    for i in range(len(ys) - 3):
        for j in range(segments):
            k = (j + 1) % segments
            a = 1 + i * segments
            b = a + segments
            faces.append((a + j, a + k, b + k, b + j))
            params.append(
                [(ys[i + 1] + ys[i + 2]) / 2, (j + 0.5) * math.tau / segments]
            )
    a = last - segments
    for j in range(segments):
        k = (j + 1) % segments
        faces.append((a + j, a + k, last))
        params.append([(ys[-2] + ys[-1]) / 2, (j + 0.5) * math.tau / segments])
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
    for face in mesh.polygons:
        face.use_smooth = True
    obj["mw_loft_face_params"] = json.dumps(params)
    obj["mw_loft_settings"] = json.dumps(
        {
            "sections": sections,
            "seam_height": seam_height,
            "tilt": tilt,
            "rows": rows,
            "segments": segments,
            "end_refinement": end_refinement,
        }
    )
    bpy.context.view_layer.update()
    return obj
