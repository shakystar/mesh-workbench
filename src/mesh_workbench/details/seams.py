"""Bounded seam lips and projected blind seats on explicit surface charts."""

import json

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import (
    actuators,
    assembly,
    attachments,
    construction,
    enclosure,
    geometry,
    mechanical,
    pathmodel,
    sculpt,
    semantic,
    shells,
)


def _chart(source, query):
    selected = semantic.resolve(source, query)
    polygons = [source.data.polygons[i] for i in selected["indices"]]
    if len({p.material_index for p in polygons}) != 1:
        raise ValueError("Single material chart required")
    for uv in source.data.uv_layers:
        known = {}
        for polygon in polygons:
            for loop in polygon.loop_indices:
                vertex = source.data.loops[loop].vertex_index
                value = np.array(uv.data[loop].uv)
                if vertex in known and np.linalg.norm(value - known[vertex]) > 1e-6:
                    raise ValueError("Seam chart crosses UV boundary")
                known[vertex] = value
    source.data.calc_loop_triangles()
    ids = set(selected["indices"])
    triangles = [
        list(t.vertices) for t in source.data.loop_triangles if t.polygon_index in ids
    ]
    return BVHTree.FromPolygons(
        sculpt.coordinates(source).tolist(), triangles, all_triangles=True
    )


def _probes(obj):
    vertices = sculpt.coordinates(obj)
    return np.vstack(
        (
            vertices,
            [
                (vertices[e.vertices[0]] + vertices[e.vertices[1]]) / 2
                for e in obj.data.edges
            ],
            [vertices[list(f.vertices)].mean(axis=0) for f in obj.data.polygons],
        )
    )


@mechanical._atomic
def seam_lip(
    source,
    opposing,
    name,
    points,
    normal,
    query,
    overlap=2.4,
    thickness=0.8,
    clearance=0.2,
    attachment_distance=0.8,
    closed=True,
):
    """Rounded internal rib along an explicit planar seam; outputs a new solid.

    The path must lie close to the selected source chart. Opposing-shell distance,
    containment and surface-crossing checks include vertices, edges and faces.
    This is an authored support rib, not automatic arbitrary seam extraction.
    """
    if source == opposing:
        raise ValueError("Distinct mating shells required")
    overlap = sculpt.number(overlap, 0.1, 20, "lip overlap")
    thickness = sculpt.number(thickness, 0.1, 5, "lip thickness")
    clearance = sculpt.number(clearance, 0.01, 5, "opposing clearance")
    attachment_distance = sculpt.number(
        attachment_distance, 0.01, 2, "attachment distance"
    )
    path = np.asarray(points, dtype=float)
    axis = np.asarray(normal, dtype=float)
    if (
        path.ndim != 2
        or path.shape[1] != 3
        or len(path) < (4 if closed else 2)
        or len(path) > 2048
        or not np.isfinite(path).all()
        or axis.shape != (3,)
        or not np.isfinite(axis).all()
        or abs(np.linalg.norm(axis) - 1) > 1e-7
    ):
        raise ValueError("Finite sampled path and unit normal required")
    if type(closed) is not bool or np.max(np.abs((path - path[0]) @ axis)) > 1e-5:
        raise ValueError("Planar seam required")
    chart = _chart(source, query)
    distances = [chart.find_nearest(Vector(p))[3] for p in path]
    if any(d is None or d > attachment_distance for d in distances):
        raise ValueError("Seam path is not attached to declared chart")
    rib = pathmodel.create(
        name,
        path.tolist(),
        [[overlap / 2, thickness / 2]] * len(path),
        segments=12,
        reference=axis.tolist(),
        closed=closed,
    )
    enclosure._valid(rib)
    # Normal projection is not clearance at a concave rim. Use geometric
    # distances plus overlap and containment checks, including both surfaces.
    opposing_check = actuators.pair(rib, opposing, minimum=clearance)
    if not opposing_check["passed"] or opposing_check["minimum_distance"] < clearance - 1e-6:
        raise ValueError("Lip violates opposing clearance")
    # A support rib must actually connect to its owning shell, not float nearby.
    contacts = shells.intersections(rib, source)["triangle_pair_count"]
    if not contacts:
        raise ValueError("Lip has no source attachment intersection")
    rib["mw_seam_lip"] = json.dumps(
        {
            "source": source.name,
            "opposing": opposing.name,
            "source_revision": attachments.revision(source),
            "path": path.tolist(),
            "normal": axis.tolist(),
            "overlap": overlap,
            "thickness": thickness,
            "clearance": clearance,
            "minimum_sampled_clearance": opposing_check["minimum_distance"],
            "samples": opposing_check["probes"],
            "opposing_clearance": opposing_check,
            "source_contact_candidates": contacts,
        }
    )
    return rib


@mechanical._atomic
def recess_seat(
    source,
    name,
    point,
    outward,
    query,
    radius,
    depth,
    max_distance=5,
    wall_min=1.6,
    wall_max=2.6,
):
    """Project a circular blind seat, cut a new shell, and enforce wall gauges."""
    point = geometry.vector(point)
    axis = geometry.vector(outward)
    if abs(axis.length - 1) > 1e-7:
        raise ValueError("Unit seat direction required")
    radius = sculpt.number(radius, 0.1, 30, "seat radius")
    depth = sculpt.number(depth, 0.01, 5, "seat depth")
    max_distance = sculpt.number(max_distance, 0.01, 100, "seat projection distance")
    wall_min = sculpt.number(wall_min, 0.01, 100, "minimum wall")
    wall_max = sculpt.number(wall_max, wall_min, 100, "maximum wall")
    if "mw_skin_roles" not in source:
        raise ValueError("Explicit shell wall roles required for blind seat")
    tree = _chart(source, query)
    hit, normal, _, _ = tree.ray_cast(
        point + axis * max_distance, -axis, max_distance * 2
    )
    if hit is None or normal.dot(axis) < 0.95:
        raise ValueError("Missing or oblique seat projection")
    # All ring points must hit the same chart near the seat plane.
    tangent = axis.orthogonal().normalized()
    other = axis.cross(tangent)
    for theta in np.linspace(0, np.pi * 2, 64, endpoint=False):
        probe = hit + (tangent * np.cos(theta) + other * np.sin(theta)) * radius
        h, n, _, _ = tree.ray_cast(probe + axis * max_distance, -axis, max_distance * 2)
        if h is None or n.dot(axis) < 0.95 or abs((h - hit).dot(axis)) > depth / 4:
            raise ValueError("Seat crosses chart boundary or excessive curvature")
    cutter = construction.strut(
        name + " cutter",
        hit - axis * depth,
        hit + axis * 0.1,
        radius=radius,
        segments=64,
    )
    roles = json.loads(source["mw_skin_roles"])
    cutter.data.materials.append(source.data.materials[roles["cut"]])
    try:
        result = enclosure.boolean(source, cutter, "DIFFERENCE", name)
    finally:
        mechanical.remove(cutter)
    report = enclosure.gauge(result, minimum=wall_min, maximum=wall_max)
    if not report["passed"]:
        raise ValueError("Recess violates shell wall bounds")
    # Boolean-created floor has the cut role; the outer-skin gauge alone misses it.
    roles = json.loads(result["mw_skin_roles"])
    result.data.calc_loop_triangles()
    inner_faces = [
        list(t.vertices)
        for t in result.data.loop_triangles
        if result.data.polygons[t.polygon_index].material_index == roles["inner"]
    ]
    inner = BVHTree.FromPolygons(
        sculpt.coordinates(result).tolist(), inner_faces, all_triangles=True
    )
    all_faces = assembly._tree(result)
    floor_thickness = []
    for radial in (0, 0.5, 0.95):
        for theta in np.linspace(0, np.pi * 2, 16, endpoint=False):
            point = (
                hit
                + (tangent * np.cos(theta) + other * np.sin(theta)) * radius * radial
            )
            floor, n, _, _ = all_faces.ray_cast(point + axis, -axis, depth + 2)
            if (
                floor is None
                or n.dot(axis) < 0.95
                or abs((hit - floor).dot(axis) - depth) > 1e-4
            ):
                raise ValueError("Seat floor missing or depth incorrect")
            opposite, inner_normal, _, distance = inner.find_nearest(floor)
            if (
                opposite is None
                or inner_normal.dot(axis) > -0.5
                or not wall_min - 1e-5 <= distance <= wall_max + 1e-5
            ):
                raise ValueError("Recess floor violates wall bounds")
            floor_thickness.append(distance)
    result["mw_recess_seat"] = json.dumps(
        {
            "source": source.name,
            "point": list(hit),
            "outward": list(axis),
            "radius": radius,
            "depth": depth,
            "wall": report,
            "floor_samples": len(floor_thickness),
            "floor_minimum": min(floor_thickness),
        }
    )
    return result
