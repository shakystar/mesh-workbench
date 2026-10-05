"""Persistent barycentric surface anchors for topology-preserving shape edits."""

import hashlib
import json

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import geometry, sculpt


def revision(target):
    sculpt.editable(target)
    return hashlib.sha256(
        (geometry.signature(target)).encode() + sculpt.coordinates(target).tobytes()
    ).hexdigest()


def bind(target, points, max_distance=0.01):
    sculpt.editable(target)
    max_distance = sculpt.number(max_distance, 1e-7, 1e6, "binding distance")
    if not 1 <= len(points) <= 10000:
        raise ValueError("Expected 1..10000 anchors")
    coords = sculpt.coordinates(target)
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite target coordinates")
    ev = target.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    finally:
        ev.to_mesh_clear()
    if not triangles:
        raise ValueError("Cannot bind an empty surface")
    tree = BVHTree.FromPolygons(coords.tolist(), triangles, all_triangles=True)
    anchors = []
    for value in points:
        point = geometry.vector(value)
        hit, normal, index, distance = tree.find_nearest(point, max_distance)
        if hit is None:
            raise ValueError("Anchor outside binding distance")
        ids = triangles[index]
        a, b, c = [Vector(coords[i]) for i in ids]
        u, v, w = b - a, c - a, hit - a
        aa, ab, bb = u.dot(u), u.dot(v), v.dot(v)
        den = aa * bb - ab * ab
        if abs(den) < 1e-20:
            raise ValueError("Degenerate binding triangle")
        wb = (bb * w.dot(u) - ab * w.dot(v)) / den
        wc = (aa * w.dot(v) - ab * w.dot(u)) / den
        weights = [1 - wb - wc, wb, wc]
        if min(weights) < -1e-5 or max(weights) > 1 + 1e-5:
            raise ValueError("Unstable binding weights")
        anchors.append({"vertices": ids, "weights": weights})
    return {
        "version": 1,
        "target": target.name,
        "topology": geometry.signature(target),
        "anchors": anchors,
    }


def resolve(target, binding):
    sculpt.editable(target)
    if (
        binding.get("version") != 1
        or binding.get("target") != target.name
        or binding.get("topology") != geometry.signature(target)
    ):
        raise ValueError("Foreign or stale topology binding; rebind required")
    coords = sculpt.coordinates(target)
    result = []
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite target coordinates")
    for anchor in binding["anchors"]:
        ids = anchor["vertices"]
        weights = anchor["weights"]
        if len(ids) != 3 or any(
            type(i) is not int or not 0 <= i < len(coords) for i in ids
        ):
            raise ValueError("Invalid binding indices")
        if (
            len(weights) != 3
            or not np.isfinite(weights).all()
            or min(weights) < -1e-5
            or abs(sum(weights) - 1) > 1e-5
        ):
            raise ValueError("Invalid binding weights")
        a, b, c = [Vector(coords[i]) for i in ids]
        normal = (b - a).cross(c - a)
        if normal.length < 1e-12:
            raise ValueError("Binding triangle collapsed")
        p = a * weights[0] + b * weights[1] + c * weights[2]
        result.append({"position": list(p), "normal": list(normal.normalized())})
    return result


def bind_relief(target, pattern, max_distance=0.01):
    if "mw_relief_settings" not in pattern or "mw_relief_anchors" not in pattern:
        raise ValueError(
            "Relief generation settings missing; regenerate with current tool"
        )
    anchors = np.array(pattern["mw_relief_anchors"]).reshape(-1, 3).tolist()
    binding = bind(target, anchors, max_distance)
    pattern["mw_surface_binding"] = json.dumps(binding)
    pattern["mw_attachment_revision"] = revision(target)
    return {
        "object": pattern.name,
        "target": target.name,
        "anchors": len(anchors),
        "status": "current",
    }


def status(target, pattern):
    if "mw_surface_binding" not in pattern:
        raise ValueError("Pattern is not bound")
    binding = json.loads(pattern["mw_surface_binding"])
    try:
        resolve(target, binding)
    except ValueError as exc:
        return {"status": "incompatible", "reason": str(exc)}
    return {
        "status": "current"
        if pattern.get("mw_attachment_revision") == revision(target)
        else "needs_refresh",
        "anchors": len(binding["anchors"]),
    }


def refresh_relief(target, pattern, name, max_distance=0.05):
    from . import patterns, relief

    if "mw_surface_binding" not in pattern:
        raise ValueError("Pattern is not bound")
    binding = json.loads(pattern["mw_surface_binding"])
    hits = resolve(target, binding)
    projected = patterns.project(target, [h["position"] for h in hits], max_distance)
    if any(
        Vector(a["normal"]).dot(Vector(b["normal"])) < 0.5
        for a, b in zip(hits, projected)
    ):
        raise ValueError("Attachment projection changed surface side")
    settings = json.loads(pattern["mw_relief_settings"])
    result = relief.dots(
        target,
        [h["position"] for h in hits],
        name,
        max_distance=max_distance,
        **settings,
    )
    for material in pattern.data.materials:
        result.data.materials.append(material)
    result["mw_surface_binding"] = json.dumps(binding)
    result["mw_attachment_revision"] = revision(target)
    return result
