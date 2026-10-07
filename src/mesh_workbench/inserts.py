"""Topology-independent projected inserts with explicit surface correspondence."""

import json
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import attachments, enclosure, geometry, sculpt, semantic, mechanical


def create(
    source,
    query,
    name,
    center,
    radii,
    side=-1,
    shear=0,
    offset=0.6,
    thickness=0.8,
    rings=10,
    segments=64,
    max_distance=100,
):
    """Project an elliptical XZ patch onto one semantic side, then make a solid.

    Patch samples are regenerated from geometric guides after parent topology
    changes. All hits must belong to the declared connected region and face the
    requested side; holes and missing support reject the operation.
    """
    region = semantic.resolve(source, query)
    if (
        side not in (-1, 1)
        or type(rings) != int
        or not 2 <= rings <= 64
        or type(segments) != int
        or not 12 <= segments <= 256
    ):
        raise ValueError("Invalid insert sampling")
    if len(radii) != 2 or min(radii) <= 0 or thickness <= 0:
        raise ValueError("Positive insert dimensions required")
    center = np.asarray(geometry.vector(center))
    coords = sculpt.coordinates(source)
    selected = set(region["indices"])
    source.data.calc_loop_triangles()
    triangles = [t for t in source.data.loop_triangles if t.polygon_index in selected]
    # An independently tessellated insert cannot straddle source chart/material
    # discontinuities without an explicit split. Reject instead of blending them.
    if len({source.data.polygons[i].material_index for i in selected}) != 1:
        raise ValueError("Insert region crosses material boundary")
    for uv in source.data.uv_layers:
        values = {}
        for triangle in triangles:
            for vertex, loop in zip(triangle.vertices, triangle.loops):
                value = np.asarray(uv.data[loop].uv)
                if vertex in values and np.linalg.norm(value - values[vertex]) > 1e-6:
                    raise ValueError("Insert region crosses UV chart seam")
                values[vertex] = value
    tree = BVHTree.FromPolygons(
        coords.tolist(), [tuple(t.vertices) for t in triangles], all_triangles=True
    )
    seeds = [(0, 0)]
    for i in range(1, rings + 1):
        for j in range(segments):
            angle = math.tau * j / segments
            z = radii[1] * i / rings * math.sin(angle)
            seeds.append((radii[0] * i / rings * math.cos(angle) + shear * z, z))
    points = []
    for dx, dz in seeds:
        ray = Vector(
            [center[0] + dx, center[1] + side * max_distance / 2, center[2] + dz]
        )
        direction = Vector((0, -side, 0))
        p, n, index, d = tree.ray_cast(ray, direction, max_distance)
        if p is None or n.y * side < 0.5:
            raise ValueError("Insert projection missed or changed surface side")
        points.append(list(p))
    binding = attachments.bind(source, points, max_distance=0.01)
    hits = attachments.resolve(source, binding)
    xyz = []
    for distance in (offset, offset - thickness):
        xyz.extend(
            [list(Vector(h["position"]) + Vector(h["normal"]) * distance) for h in hits]
        )
    count = len(hits)
    outer = []
    for j in range(segments):
        outer.append([0, 1 + j, 1 + (j + 1) % segments])
    for i in range(rings - 1):
        a = 1 + i * segments
        b = a + segments
        for j in range(segments):
            outer.append([a + j, b + j, b + (j + 1) % segments, a + (j + 1) % segments])
    faces = outer + [[v + count for v in reversed(f)] for f in outer]
    start = 1 + (rings - 1) * segments
    faces.extend(
        [
            [
                start + j,
                start + (j + 1) % segments,
                start + (j + 1) % segments + count,
                start + j + count,
            ]
            for j in range(segments)
        ]
    )
    obj = enclosure._mesh(name, xyz, faces)
    try:
        enclosure._valid(obj)
        for group in source.vertex_groups:
            target = obj.vertex_groups.new(name=group.name)
            weights = np.zeros(len(coords))
            for v in source.data.vertices:
                for entry in v.groups:
                    if entry.group == group.index:
                        weights[v.index] = entry.weight
            for i, a in enumerate(binding["anchors"]):
                w = float(weights[list(a["vertices"])] @ a["weights"])
                if w:
                    target.add([i, i + count], w, "REPLACE")
        # Corner data comes from each actual bound triangle, preserving chart
        # provenance instead of averaging UVs at a seam vertex.
        source.data.calc_loop_triangles()
        lookup = {tuple(sorted(t.vertices)): t for t in source.data.loop_triangles}
        for uv in source.data.uv_layers:
            sampled = []
            for a in binding["anchors"]:
                triangle = lookup[tuple(sorted(a["vertices"]))]
                values = {
                    v: np.asarray(uv.data[l].uv)
                    for v, l in zip(triangle.vertices, triangle.loops)
                }
                sampled.append(
                    sum(values[v] * w for v, w in zip(a["vertices"], a["weights"]))
                )
            target = obj.data.uv_layers.new(name=uv.name)
            for loop in obj.data.loops:
                target.data[loop.index].uv = sampled[loop.vertex_index % count]
        masks = json.loads(source.get("mw_masks", "{}"))
        for m in masks.values():
            if (
                m["topology"] != sculpt.topology(source)
                or source.vertex_groups.get(m["group"]) is None
            ):
                raise ValueError("Stale insert source mask")
            m["topology"] = sculpt.topology(obj)
        if masks:
            obj["mw_masks"] = json.dumps(masks)
        for material in source.data.materials:
            obj.data.materials.append(material)
        obj["mw_insert"] = json.dumps(
            {
                "version": 2,
                "source": source.name,
                "query": query,
                "guide": {
                    "center": center.tolist(),
                    "radii": radii,
                    "shear": shear,
                    "side": side,
                },
                "offset": offset,
                "thickness": thickness,
                "source_binding": binding,
                "source_revision": attachments.revision(source),
                "topology": geometry.signature(obj),
            }
        )
        return obj
    except Exception:
        mechanical.remove(obj)
        raise
