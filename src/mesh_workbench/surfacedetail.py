"""Projected solid ribbons and subtractive grooves with explicit correspondence.

Paths are sampled in a chosen coordinate plane and projected onto one connected
facing chart. Holes, chart discontinuities and unsupported turns are rejected.
"""

import json
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import attachments, enclosure, mechanical, sculpt, semantic


@mechanical._atomic
def paths(
    source,
    name,
    query,
    paths,
    projection_axis=1,
    side=-1,
    width=0.8,
    height=0.4,
    embed=0.1,
    spacing=0.8,
    cross_samples=6,
    mode="raised",
    max_distance=100,
):
    if (
        projection_axis not in (0, 1, 2)
        or side not in (-1, 1)
        or mode not in ("raised", "groove")
    ):
        raise ValueError("Invalid projection or path mode")
    if type(cross_samples) != int or not 2 <= cross_samples <= 24 or not paths:
        raise ValueError("Nonempty sampled paths required")
    width = sculpt.number(width, 0.01, 100, "path width")
    height = sculpt.number(height, 0.001, 100, "path height")
    embed = sculpt.number(embed, 0.001, 100, "path embed")
    spacing = sculpt.number(spacing, 0.01, 100, "path spacing")
    max_distance = sculpt.number(max_distance, 0.001, 1e6, "projection distance")
    selected = set(semantic.resolve(source, query)["indices"])
    coords = sculpt.coordinates(source)
    source.data.calc_loop_triangles()
    tris = [t for t in source.data.loop_triangles if t.polygon_index in selected]
    if len({source.data.polygons[i].material_index for i in selected}) != 1:
        raise ValueError("Path region crosses material boundary")
    for uv in source.data.uv_layers:
        known = {}
        for t in tris:
            for v, l in zip(t.vertices, t.loops):
                value = np.array(uv.data[l].uv)
                if v in known and np.linalg.norm(known[v] - value) > 1e-6:
                    raise ValueError("Path region crosses UV seam")
                known[v] = value
    tree = BVHTree.FromPolygons(
        coords.tolist(), [tuple(t.vertices) for t in tris], all_triangles=True
    )
    plane = [i for i in range(3) if i != projection_axis]
    direction = Vector((0, 0, 0))
    direction[projection_axis] = -side
    seeds = []
    tops = []
    faces = []
    for path in paths:
        if set(path) - {"points", "closed", "width", "height"}:
            raise ValueError("Unknown path field")
        knots = np.array(path["points"], dtype=float)
        closed = path.get("closed", False)
        if (
            knots.ndim != 2
            or knots.shape[1] != 3
            or len(knots) < (3 if closed else 2)
            or not np.isfinite(knots).all()
        ):
            raise ValueError("Finite path points required")
        w = sculpt.number(path.get("width", width), 0.01, 100, "path width")
        h = sculpt.number(path.get("height", height), 0.001, 100, "path height")
        samples = []
        for i in range(len(knots) if closed else len(knots) - 1):
            a = knots[i]
            b = knots[(i + 1) % len(knots)]
            length = np.linalg.norm((b - a)[plane])
            if length < 1e-6:
                raise ValueError("Repeated projected path point")
            count = max(1, math.ceil(length / spacing))
            samples.extend(
                a + (b - a) * t for t in np.linspace(0, 1, count, endpoint=False)
            )
        if not closed:
            samples.append(knots[-1])
        samples = np.array(samples)
        offset = len(seeds)
        cols = cross_samples + 1
        if (len(seeds) + len(samples) * cols) > 10000:
            raise ValueError("Too many path samples")
        for i, p in enumerate(samples):
            tangent = (
                samples[(i + 1) % len(samples)] - samples[(i - 1) % len(samples)]
                if closed or 0 < i < len(samples) - 1
                else samples[1] - samples[0]
                if i == 0
                else samples[-1] - samples[-2]
            )
            t = tangent[plane]
            norm = np.linalg.norm(t)
            if norm < 1e-6:
                raise ValueError("Ambiguous path turn")
            lateral = np.array([-t[1], t[0]]) / norm
            for u in np.linspace(-1, 1, cols):
                seed = p.copy()
                seed[plane] += lateral * u * w / 2
                seeds.append(seed)
                tops.append(h * math.sqrt(max(0, 1 - u * u)))
        for i in range(len(samples) if closed else len(samples) - 1):
            a = offset + i * cols
            b = offset + ((i + 1) % len(samples)) * cols
            for j in range(cols - 1):
                faces.append([a + j, a + j + 1, b + j + 1, b + j])
    hits = []
    normals = []
    for seed in seeds:
        ray = Vector(seed)
        ray[projection_axis] = side * max_distance
        p, n, index, d = tree.ray_cast(ray, direction, max_distance * 2)
        if p is None or n[projection_axis] * side < 0.5:
            raise ValueError("Path projection missed or changed side")
        hits.append(list(p))
        normals.append(np.array(n))
    binding = attachments.bind(source, hits, max_distance=0.01)
    points = np.array(hits)
    normal = np.array(normals)
    count = len(points)
    top = points + normal * np.array(tops)[:, None]
    bottom = points - normal * embed
    # For grooves, height is exterior cutter clearance and embed is cut depth.
    xyz = np.concatenate((top, bottom))
    all_faces = faces + [[v + count for v in reversed(f)] for f in faces]
    edges = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
    for directed in edges.values():
        if len(directed) == 1:
            a, b = directed[0]
            all_faces.append([b, a, a + count, b + count])
        elif len(directed) != 2:
            raise ValueError("Nonmanifold ribbon grid")
    obj = enclosure._mesh(
        name if mode == "raised" else name + " cutter", xyz, all_faces
    )
    enclosure._valid(obj)
    source.data.calc_loop_triangles()
    lookup = {tuple(sorted(t.vertices)): t for t in source.data.loop_triangles}
    for group in source.vertex_groups:
        target = obj.vertex_groups.new(name=group.name)
        weights = np.array(
            [
                next((g.weight for g in v.groups if g.group == group.index), 0)
                for v in source.data.vertices
            ]
        )
        for i, a in enumerate(binding["anchors"]):
            w = float(weights[list(a["vertices"])] @ a["weights"])
            if w:
                target.add([i, i + count], w, "REPLACE")
    for uv in source.data.uv_layers:
        sampled = []
        for a in binding["anchors"]:
            t = lookup[tuple(sorted(a["vertices"]))]
            values = {v: np.array(uv.data[l].uv) for v, l in zip(t.vertices, t.loops)}
            sampled.append(
                sum(values[v] * w for v, w in zip(a["vertices"], a["weights"]))
            )
        target = obj.data.uv_layers.new(name=uv.name)
        for loop in obj.data.loops:
            target.data[loop.index].uv = sampled[loop.vertex_index % count]
    masks = json.loads(source.get("mw_masks", "{}"))
    for mask in masks.values():
        if (
            mask["topology"] != sculpt.topology(source)
            or source.vertex_groups.get(mask["group"]) is None
        ):
            raise ValueError("Stale path source mask")
        mask["topology"] = sculpt.topology(obj)
    if masks:
        obj["mw_masks"] = json.dumps(masks)
    record = {
        "source": source.name,
        "source_revision": attachments.revision(source),
        "binding": binding,
        "mode": mode,
        "paths": paths,
        "width": width,
        "height": height,
        "embed": embed,
    }
    if mode == "groove":
        if len(source.data.materials) > 2:
            obj.data.materials.append(source.data.materials[2])
        cutter = obj
        obj = enclosure.boolean(source, cutter, "DIFFERENCE", name)
        mechanical.remove(cutter)
    obj["mw_surface_paths"] = json.dumps(record)
    return obj
