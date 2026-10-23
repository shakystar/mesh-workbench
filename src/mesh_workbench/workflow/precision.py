"""Independent outline/edge radii and explicitly controlled cubic sweep paths."""

import math
import json
import bpy
import bmesh
import numpy as np
from . import geometry, sculpt, sweep, attachments, patterns


def rounded_panel(
    name,
    dimensions,
    corner_radius,
    edge_radius,
    location=(0, 0, 0),
    segments=16,
    edge_segments=5,
):
    """Closed XZ rounded panel extruded along Y; outline radius independent of thickness."""
    w, d, h = geometry.vector(dimensions)
    pos = geometry.vector(location)
    r = sculpt.number(corner_radius, 1e-6, min(w, h) / 2 - 1e-6, "corner radius")
    e = sculpt.number(edge_radius, 1e-6, min(d / 2, r) - 1e-6, "edge radius")
    if (
        type(segments) is not int
        or not 2 <= segments <= 128
        or type(edge_segments) is not int
        or not 1 <= edge_segments <= 32
    ):
        raise ValueError("Invalid sampling")
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    front = [
        (-d / 2 + e - e * math.cos(t), e - e * math.sin(t))
        for t in np.linspace(0, math.pi / 2, edge_segments + 1)
    ]
    sections = front + [(-y, inset) for y, inset in reversed(front)]
    vertices = []
    for y, inset in sections:
        for cx, cz, start in [
            (w / 2 - r, h / 2 - r, 0),
            (-w / 2 + r, h / 2 - r, 90),
            (-w / 2 + r, -h / 2 + r, 180),
            (w / 2 - r, -h / 2 + r, 270),
        ]:
            for angle in np.linspace(start, start + 90, segments + 1):
                t = math.radians(angle)
                vertices.append(
                    (cx + (r - inset) * math.cos(t), y, cz + (r - inset) * math.sin(t))
                )
    n = 4 * (segments + 1)
    faces = []
    for j in range(len(sections) - 1):
        for i in range(n):
            k = (i + 1) % n
            faces.append((j * n + i, j * n + k, (j + 1) * n + k, (j + 1) * n + i))
    faces += [
        tuple(reversed(range(n))),
        tuple((len(sections) - 1) * n + i for i in range(n)),
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
    for f in mesh.polygons:
        f.use_smooth = len(f.vertices) == 4
    obj["mw_precision_panel"] = json.dumps(
        {"dimensions": list(dimensions), "corner_radius": r, "edge_radius": e}
    )
    bpy.context.view_layer.update()
    return obj


def bezier_path(segments, samples=16):
    """Piecewise cubic Bezier controls with matching endpoints and G1 joins."""
    a = np.asarray(segments, dtype=float)
    if (
        a.ndim != 3
        or a.shape[1:] != (4, 3)
        or not len(a)
        or not np.isfinite(a).all()
        or type(samples) is not int
        or not 3 <= samples <= 256
    ):
        raise ValueError("Expected cubic control segments and samples 3..256")
    for c in a:
        if np.linalg.norm(c[1] - c[0]) < 1e-8 or np.linalg.norm(c[3] - c[2]) < 1e-8:
            raise ValueError("Zero endpoint tangent")
    for left, right in zip(a, a[1:]):
        u, v = left[3] - left[2], right[1] - right[0]
        if (
            np.linalg.norm(left[3] - right[0]) > 1e-7
            or np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)) < 0.99999
        ):
            raise ValueError("Disconnected or non-tangent cubic join")
    points = []
    for i, c in enumerate(a):
        t = np.linspace(0, 1, samples + 1)[int(i > 0) :, None]
        points.extend(
            (
                (1 - t) ** 3 * c[0]
                + 3 * (1 - t) ** 2 * t * c[1]
                + 3 * (1 - t) * t * t * c[2]
                + t**3 * c[3]
            ).tolist()
        )
    return points


def bezier_tube(
    name, controls, radius=0.05, samples=16, segments=32, reference=(0, 1, 0)
):
    radius = sculpt.number(radius, 1e-6, 1e3, "tube radius")
    points = bezier_path(controls, samples)
    obj = sweep.sweep(
        name,
        points,
        [[radius, radius]] * len(points),
        segments=segments,
        reference=reference,
    )
    obj["mw_bezier_controls"] = json.dumps(controls)
    return obj


def bound_seam(
    target, points, name, radius=0.008, offset=0.005, max_distance=0.1, spacing=0.04
):
    """Capped mesh seam with persistent surface anchors; no global clearance guarantee."""
    radius = sculpt.number(radius, 1e-6, 100, "seam radius")
    offset = sculpt.number(offset, 0, 100, "seam offset")
    spacing = sculpt.number(spacing, 1e-5, 100, "sample spacing")
    values = [geometry.vector(p) for p in points]
    if len(values) < 2:
        raise ValueError("At least two seam points required")
    samples = [values[0]]
    for a, b in zip(values, values[1:]):
        if (b - a).length < 1e-8:
            raise ValueError("Coincident seam points")
        count = max(1, math.ceil((b - a).length / spacing))
        if len(samples) + count > 10000:
            raise ValueError("Too many seam samples")
        samples.extend(a.lerp(b, i / count) for i in range(1, count + 1))
    hits = patterns.project(target, samples, max_distance)
    binding = attachments.bind(target, [h["position"] for h in hits], max_distance)
    return _seam(target, binding, name, radius, offset)


def _seam(target, binding, name, radius, offset):
    hits = attachments.resolve(target, binding)
    centers = [
        (geometry.vector(h["position"]) + geometry.vector(h["normal"]) * offset)
        for h in hits
    ]
    obj = sweep.sweep(
        name,
        centers,
        [[radius, radius]] * len(centers),
        segments=12,
        reference=hits[0]["normal"],
    )
    obj["mw_surface_binding"] = json.dumps(binding)
    obj["mw_attachment_revision"] = attachments.revision(target)
    obj["mw_seam_settings"] = json.dumps({"radius": radius, "offset": offset})
    return obj


def refresh_seam(target, seam, name):
    if "mw_seam_settings" not in seam or "mw_surface_binding" not in seam:
        raise ValueError("Bound mesh seam required")
    obj = _seam(
        target,
        json.loads(seam["mw_surface_binding"]),
        name,
        **json.loads(seam["mw_seam_settings"]),
    )
    for material in seam.data.materials:
        obj.data.materials.append(material)
    return obj
