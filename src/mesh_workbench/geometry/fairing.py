"""Local two-pass mesh fairing with reversible deformation layers."""

import json

import bpy
import numpy as np
from mathutils import Vector

from . import geometry, layers, sculpt


def region(
    obj,
    center,
    radius,
    iterations=8,
    positive=0.5,
    negative=-0.53,
    label="Local fairing",
):
    """Weighted Laplacian positive/negative passes; reduces shrink, not volume preserving.

    Freeze weights on input geometry, pin mesh boundaries and vertices
    outside the world-space sphere. Connectivity never changes.
    """
    sculpt.editable(obj)
    center = np.array(geometry.vector(center))
    radius = sculpt.number(radius, 1e-6, 1e6, "radius")
    positive = sculpt.number(positive, 0.001, 0.8, "positive step")
    negative = sculpt.number(negative, -0.8, -0.001, "negative step")
    if type(iterations) is not int or not 1 <= iterations <= 50:
        raise ValueError("Iterations must be 1..50")
    if not isinstance(label, str) or not 1 <= len(label) <= 48:
        raise ValueError("Invalid layer label")
    original = sculpt.coordinates(obj)
    coords = original.copy()
    distance = np.linalg.norm(coords - center, axis=1) / radius
    t = np.clip(1 - distance, 0, 1)
    weights = t * t * (3 - 2 * t)
    neighbors = sculpt.adjacency(obj, coords)
    edge_faces = {tuple(sorted(e.vertices)): 0 for e in obj.data.edges}
    for face in obj.data.polygons:
        verts = list(face.vertices)
        for a, b in zip(verts, verts[1:] + verts[:1]):
            edge_faces[tuple(sorted((a, b)))] += 1
    for (a, b), count in edge_faces.items():
        if count != 2:
            weights[[a, b]] = 0
    active = np.flatnonzero(weights > 0)
    if not len(active):
        raise ValueError("Region contains no movable interior vertices")
    for _ in range(iterations):
        for step in [positive, negative]:
            displacement = np.zeros_like(coords)
            for i in active:
                if neighbors[i]:
                    displacement[i] = (
                        coords[[j for j, _ in neighbors[i]]].mean(axis=0) - coords[i]
                    )
            coords += step * weights[:, None] * displacement
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite result")
    changed = np.flatnonzero(np.linalg.norm(coords - original, axis=1) > 1e-12)
    if not len(changed):
        raise ValueError("Fairing produced no change")
    initial_overlaps = overlap_candidates(obj)
    if initial_overlaps:
        raise ValueError(
            "Fairing requires an input without nonadjacent overlap candidates"
        )
    had_keys = obj.data.shape_keys is not None
    key = layers.begin(obj)
    try:
        inverse = obj.matrix_world.inverted()
        for i in changed:
            key.data[int(i)].co = inverse @ Vector(coords[i])
        layer = layers.finish(obj)
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, cancel=True)
        raise
    final_overlaps = overlap_candidates(obj)
    if final_overlaps > initial_overlaps:
        obj.shape_key_remove(layer)
        if not had_keys:
            obj.shape_key_clear()
        bpy.context.view_layer.update()
        raise ValueError(
            "Fairing introduced nonadjacent triangle overlaps; rolled back"
        )
    layer.name = "MW " + label
    report = {
        "layer": layer.name,
        "changed_vertices": len(changed),
        "max_displacement": float(np.linalg.norm(coords - original, axis=1).max()),
        "iterations": iterations,
        "radius": radius,
        "center": center.tolist(),
        "overlaps_before": initial_overlaps,
        "overlaps_after": final_overlaps,
        "pinned_vertices": int((weights == 0).sum()),
    }
    history = json.loads(obj.get("mw_layers", "[]"))
    history.append(
        {"name": layer.name, "topology": sculpt.topology(obj), "report": report}
    )
    obj["mw_layers"] = json.dumps(history)
    return report


def components(obj):
    """Count connected vertex components on the evaluated mesh."""
    graph = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(graph)
    mesh = ev.to_mesh()
    try:
        adjacency = [[] for _ in mesh.vertices]
        for e in mesh.edges:
            a, b = e.vertices
            adjacency[a].append(b)
            adjacency[b].append(a)
        remaining = set(range(len(adjacency)))
        sizes = []
        while remaining:
            stack = [remaining.pop()]
            count = 0
            while stack:
                v = stack.pop()
                count += 1
                for n in adjacency[v]:
                    if n in remaining:
                        remaining.remove(n)
                        stack.append(n)
            sizes.append(count)
        return sorted(sizes, reverse=True)
    finally:
        ev.to_mesh_clear()


def overlap_candidates(obj):
    """Nonadjacent triangle BVH overlaps; diagnostic, not a full solid validator."""
    from mathutils.bvhtree import BVHTree

    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
        if not triangles:
            return 0
        tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
        return sum(
            a < b and not set(triangles[a]).intersection(triangles[b])
            for a, b in tree.overlap(tree)
        )
    finally:
        ev.to_mesh_clear()
