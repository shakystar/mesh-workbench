"""Guide-built continuous enclosures and semantic shell partitions.

All dimensions are world units. Geometry is created in new, static mesh objects.
"""

import json
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree
from . import geometry, sculpt, models, fairing


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def outline(profile, trim=6, spacing=2.5, length_delta=0):
    p = np.asarray(profile, dtype=float).copy()
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError("Finite XZ polygon required")
    p[:, 1] -= length_delta * smooth((140 - p[:, 1]) / 40)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, np.roll(p, -1, axis=0)))
    if area < 0:
        p = p[::-1]
    corners = []
    for i, q in enumerate(p):
        a = p[(i - 1) % len(p)] - q
        b = p[(i + 1) % len(p)] - q
        distance = min(trim, np.linalg.norm(a) * 0.45, np.linalg.norm(b) * 0.45)
        corners.append(
            (
                q + a / np.linalg.norm(a) * distance,
                q,
                q + b / np.linalg.norm(b) * distance,
            )
        )
    result = []
    for i, (a, b, c) in enumerate(corners):
        count = max(
            12,
            int(math.ceil((np.linalg.norm(b - a) + np.linalg.norm(c - b)) / spacing)),
        )
        for t in np.linspace(0, 1, count, endpoint=False):
            result.append((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c)
        end = corners[(i + 1) % len(corners)][0]
        for t in np.linspace(
            0,
            1,
            max(1, int(math.ceil(np.linalg.norm(end - c) / spacing))),
            endpoint=False,
        ):
            result.append(c * (1 - t) + end * t)
    return np.array(result)


def _inside(p, polygon):
    x, z = p
    inside = False
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        if (a[1] > z) != (b[1] > z) and x < (b[0] - a[0]) * (z - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            inside = not inside
    return inside


def _distance(p, polygon):
    a = polygon
    b = np.roll(polygon, -1, axis=0)
    d = b - a
    t = np.clip(((p - a) * d).sum(axis=1) / (d * d).sum(axis=1), 0, 1)
    return float(np.linalg.norm(p - (a + d * t[:, None]), axis=1).min())


def _mesh(name, xyz, faces):
    if name in bpy.data.objects:
        raise ValueError("Output exists")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(xyz).tolist(), [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for f in mesh.polygons:
        f.use_smooth = True
    return obj


def create(
    name,
    profile_xz,
    corner_trim=6,
    rim_radius=5,
    rim_steps=20,
    edge_spacing=2.5,
    cap_spacing=3,
    head_half_width=26,
    grip_half_width=14,
    transition_z=(100, 140),
    grip_width=0,
    grip_length=0,
):
    for key, value in [
        ("corner trim", corner_trim),
        ("rim radius", rim_radius),
        ("edge spacing", edge_spacing),
        ("cap spacing", cap_spacing),
        ("head width", head_half_width),
        ("grip width", grip_half_width),
    ]:
        sculpt.number(value, 0.01, 10000, key)
    if (
        len(transition_z) != 2
        or not np.isfinite(transition_z).all()
        or transition_z[0] >= transition_z[1]
    ):
        raise ValueError("Ordered finite transition heights required")
    if (
        type(rim_steps) != int
        or not 3 <= rim_steps <= 64
        or not 0 < rim_radius < grip_half_width
    ):
        raise ValueError("Invalid enclosure rim")
    curve = outline(profile_xz, corner_trim, edge_spacing, grip_length)
    incoming = curve - np.roll(curve, 1, axis=0)
    outgoing = np.roll(curve, -1, axis=0) - curve
    li = np.linalg.norm(incoming, axis=1)
    lo = np.linalg.norm(outgoing, axis=1)
    tangent = (
        incoming / li[:, None] * lo[:, None] + outgoing / lo[:, None] * li[:, None]
    )
    inward = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    inward /= np.linalg.norm(inward, axis=1)[:, None]
    cross = incoming[:, 0] * outgoing[:, 1] - incoming[:, 1] * outgoing[:, 0]
    curvature_radius = (
        li
        * lo
        * np.linalg.norm(incoming + outgoing, axis=1)
        / np.maximum(2 * np.abs(cross), 1e-12)
    )
    # Convex profile corners cannot accept a rim wider than their curvature.
    cap = np.where(
        cross > 0, np.minimum(rim_radius, 0.75 * curvature_radius), rim_radius
    )
    arc = np.r_[0, np.cumsum(lo[:-1])]
    length = lo.sum()
    distance = np.abs(arc[:, None] - arc[None, :])
    distance = np.minimum(distance, length - distance)
    radii = np.min(cap[None, :] + 0.12 * distance, axis=1)
    for _ in range(6):
        radii = np.minimum(
            radii, (np.roll(radii, 1) + 2 * radii + np.roll(radii, -1)) / 4
        )
    if radii.min() <= rim_radius * 0.42:
        raise ValueError("Profile too sharp for the requested enclosure rim")

    def width(z):
        t = smooth((z - transition_z[0]) / (transition_z[1] - transition_z[0]))
        return (grip_half_width + grip_width / 2) * (1 - t) + head_half_width * t

    # Ordered closed cross section, with shared boundary rings at the two caps.
    rings = []
    for theta in np.linspace(math.pi / 2, 0, rim_steps + 1):
        rings.append(
            (rim_radius * (1 - math.cos(theta)), -1, rim_radius * (1 - math.sin(theta)))
        )
    for fraction in np.linspace(-1, 1, 9)[1:-1]:
        rings.append((0, fraction, rim_radius))
    for theta in np.linspace(0, math.pi / 2, rim_steps + 1):
        rings.append(
            (rim_radius * (1 - math.cos(theta)), 1, rim_radius * (1 - math.sin(theta)))
        )
    xyz = []
    faces = []
    n = len(curve)
    for inset, sign, reduce in rings:
        ring = curve + inward * (radii * inset / rim_radius)[:, None]
        xyz.extend(
            [
                [p[0], sign * (width(p[1]) - reduce * r / rim_radius), p[1]]
                for p, r in zip(ring, radii)
            ]
        )
    for j in range(len(rings) - 1):
        for i in range(n):
            faces.append(
                [
                    j * n + i,
                    j * n + (i + 1) % n,
                    (j + 1) * n + (i + 1) % n,
                    (j + 1) * n + i,
                ]
            )
    inner = curve + inward * radii[:, None]
    samples = list(inner)
    for z in np.arange(
        inner[:, 1].min() + cap_spacing / 2, inner[:, 1].max(), cap_spacing
    ):
        for x in np.arange(
            inner[:, 0].min() + cap_spacing / 2, inner[:, 0].max(), cap_spacing
        ):
            p = np.array([x, z])
            if _inside(p, inner) and _distance(p, inner) > cap_spacing * 0.35:
                samples.append(p)
    coords, _, triangles, orig, _, _ = delaunay_2d_cdt(
        [Vector(p) for p in samples], [], [list(range(n))], 1, 1e-6, True
    )
    for side, base in [(-1, 0), (1, (len(rings) - 1) * n)]:
        mapping = []
        for p, ids in zip(coords, orig):
            border = [i for i in ids if i < n]
            if len(border) > 1:
                raise ValueError("Ambiguous enclosure cap boundary")
            if border:
                mapping.append(base + border[0])
            else:
                mapping.append(len(xyz))
                xyz.append([p.x, side * width(p.y), p.y])
        faces.extend([[mapping[i] for i in f] for f in triangles])
    obj = _mesh(name, xyz, faces)
    obj["mw_enclosure"] = json.dumps(
        {
            "version": 1,
            "profile_xz": profile_xz,
            "grip_width": grip_width,
            "grip_length": grip_length,
            "ring_size": n,
            "ring_count": len(rings),
            "cap_spacing": cap_spacing,
            "rim_radius_min": float(radii.min()),
            "rim_radius_max": float(radii.max()),
        }
    )
    try:
        _valid(obj)
        analytic_attributes(obj)
        return obj
    except Exception:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
        raise


def analytic_attributes(obj):
    """Independent known XZ field and grip weight, useful for transfer fixtures."""
    x = sculpt.coordinates(obj)
    uv = obj.data.uv_layers.new(name="DesignXZ")
    for loop in obj.data.loops:
        p = x[loop.vertex_index]
        uv.data[loop.index].uv = (p[0] / 120, p[2] / 200)
    group = obj.vertex_groups.new(name="Grip weight")
    for i, p in enumerate(x):
        w = float(1 - smooth((p[2] - 100) / 40))
        if w:
            group.add([i], w, "REPLACE")
    obj["mw_masks"] = json.dumps(
        {"grip": {"group": group.name, "topology": sculpt.topology(obj)}}
    )


def hollow(source, name, thickness=2):
    """Closed outer/inner skins with material roles 0=outer,1=inner."""
    if name in bpy.data.objects:
        raise ValueError("Output exists")
    sculpt.editable(source)
    thickness = sculpt.number(thickness, 0.01, 100, "wall thickness")
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_render = False
    try:
        # Stable material roles survive boolean cuts and support independent gauges.
        obj.data.materials.clear()
        for label in ("MW outer role", "MW inner role", "MW cut role"):
            obj.data.materials.append(
                bpy.data.materials.get(label) or bpy.data.materials.new(label)
            )
        for f in obj.data.polygons:
            f.material_index = 0
        models.activate(obj)
        mod = obj.modifiers.new("Closed offset skin", "SOLIDIFY")
        mod.thickness = thickness
        mod.offset = -1
        mod.use_even_offset = True
        mod.material_offset = 1
        mod.material_offset_rim = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj["mw_masks"] = json.dumps(
            {"grip": {"group": "Grip weight", "topology": sculpt.topology(obj)}}
        )
        obj["mw_skin_roles"] = json.dumps(
            {"outer": 0, "inner": 1, "cut": 2, "nominal": thickness}
        )
        _valid(obj)
        return obj
    except Exception:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
        raise


def partition(source, name, side, offset=0, gap=0.8):
    if side not in ("left", "right"):
        raise ValueError("Expected left or right")
    xyz = sculpt.coordinates(source)
    low = xyz.min(axis=0) - 10
    high = xyz.max(axis=0) + 10
    if side == "left":
        high[1] = offset - gap / 2
    else:
        low[1] = offset + gap / 2
    center = (low + high) / 2
    scale = (high - low) / 2
    cutter = models.primitive("cube", name + " clip", location=center, scale=scale)
    try:
        cutter.data.materials.append(source.data.materials[2])
        result = boolean(source, cutter, "INTERSECT", name)
        if not result.data.polygons:
            raise ValueError("Empty shell partition")
        result["mw_skin_roles"] = source["mw_skin_roles"]
        result["mw_partition"] = json.dumps(
            {
                "side": side,
                "plane": float(high[1] if side == "left" else low[1]),
                "gap": gap,
            }
        )
        masks = json.loads(source.get("mw_masks", "{}"))
        for m in masks.values():
            m["topology"] = sculpt.topology(result)
        result["mw_masks"] = json.dumps(masks)
        return result
    finally:
        mesh = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        if not mesh.users:
            bpy.data.meshes.remove(mesh)


def gauge(obj, minimum=1.6, maximum=2.6):
    """All outer triangle vertices, edge midpoints and centroids to opposite skin.

    Every missing/ambiguous sample is counted as failure. No rim exclusions.
    """
    roles = json.loads(obj["mw_skin_roles"])
    x = sculpt.coordinates(obj)
    obj.data.calc_loop_triangles()
    inner = []
    outer = []
    for t in obj.data.loop_triangles:
        role = obj.data.polygons[t.polygon_index].material_index
        if role == roles["inner"]:
            inner.append(tuple(t.vertices))
        elif role == roles["outer"]:
            outer.append(tuple(t.vertices))
    if not inner or not outer:
        raise ValueError("Missing inner or outer skin role")
    tree = BVHTree.FromPolygons(x.tolist(), inner, all_triangles=True)
    failures = []
    values = []
    samples = 0
    for i, f in enumerate(outer):
        points = x[list(f)]
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        length = np.linalg.norm(normal)
        if length < 1e-10:
            failures.append({"face": i, "reason": "degenerate outer triangle"})
            continue
        normal /= length
        # Midpoints/centroids include cells adjacent to openings; vertices included.
        for point in (
            list(points)
            + [(points[j] + points[(j + 1) % 3]) / 2 for j in range(3)]
            + [points.mean(axis=0)]
        ):
            samples += 1
            hit, n, index, d = tree.find_nearest(Vector(point), maximum * 4)
            if hit is None:
                failures.append(
                    {
                        "face": i,
                        "reason": "opposite skin missed",
                        "point": point.tolist(),
                    }
                )
                continue
            a, b, c = x[list(inner[index])]
            target_normal = np.cross(b - a, c - a)
            target_normal /= np.linalg.norm(target_normal)
            if np.dot(normal, target_normal) > -0.5:
                failures.append(
                    {
                        "face": i,
                        "reason": "opposite skin ambiguous",
                        "point": point.tolist(),
                    }
                )
                continue
            values.append(float(d))
            if d < minimum - 1e-5 or d > maximum + 1e-5:
                failures.append(
                    {
                        "face": i,
                        "reason": "wall range",
                        "value": float(d),
                        "point": point.tolist(),
                    }
                )
    return {
        "passed": not failures,
        "samples": samples,
        "missing_or_invalid": samples - len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "violations": failures,
        "method": "all outer triangle vertices, midpoints, centroids to opposite material-role skin; normal gate",
    }


def boolean(source, cutter, operation, name):
    """Source-preserving Boolean retaining named deform and corner data layers.

    Blender interpolates UV/deform layers at intersections. New cut faces use the
    cutter's explicitly assigned material/UV data; their provenance is generation,
    not a false source-face binding. Native results are audited before returning.
    """
    if (
        operation not in ("DIFFERENCE", "INTERSECT", "UNION")
        or name in bpy.data.objects
    ):
        raise ValueError("Invalid CSG operation or existing output")
    sculpt.editable(source)
    sculpt.editable(cutter)
    ev = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(
        ev, depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    obj = source.copy()
    obj.data = mesh
    obj.name = name
    obj.modifiers.clear()
    bpy.context.collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_render = False
    try:
        models.activate(obj)
        mod = obj.modifiers.new("Layer-preserving CSG", "BOOLEAN")
        mod.operation = operation
        mod.solver = "EXACT"
        mod.object = cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
        # Explicit tessellation preserves Boolean edge subdivisions that the
        # display tessellator may skip at collinear n-gon corners. BMesh carries
        # per-corner UVs, deform weights and material roles through this step.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(
            bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY"
        )
        # Exact CSG can leave zero-area slivers at tangent intersections.
        # Dissolve only numerical degeneracy; do not smooth or relax the skin.
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=list(bm.edges))
        bmesh.ops.triangulate(
            bm,
            faces=[f for f in bm.faces if len(f.verts) > 3],
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        if not obj.data.polygons:
            raise ValueError("CSG produced empty geometry")
        _valid(obj)
        names = [g.name for g in source.vertex_groups]
        if [g.name for g in obj.vertex_groups] != names:
            raise ValueError("CSG lost named deform groups")
        for uv in source.data.uv_layers:
            layer = obj.data.uv_layers.get(uv.name)
            if layer is None or any(not np.isfinite(v.uv).all() for v in layer.data):
                raise ValueError("CSG lost or invalidated UV layer")
        masks = json.loads(source.get("mw_masks", "{}"))
        for record in masks.values():
            if (
                record["topology"] != sculpt.topology(source)
                or source.vertex_groups.get(record["group"]) is None
            ):
                raise ValueError("Stale or missing input mask")
            record["topology"] = sculpt.topology(obj)
        if masks:
            obj["mw_masks"] = json.dumps(masks)
        # Old indexed state never survives as an apparently valid attachment.
        for field in (
            "mw_layers",
            "mw_pending",
            "mw_remesh",
            "mw_refinement",
            "mw_shell",
            "mw_regions",
            "mw_surface_binding",
            "mw_attachment_revision",
        ):
            if field in obj:
                del obj[field]
        obj["mw_csg_transfer"] = json.dumps(
            {
                "version": 1,
                "source": source.name,
                "cutter": cutter.name,
                "operation": operation,
                "groups": names,
                "uv_layers": [u.name for u in obj.data.uv_layers],
                "topology": geometry.signature(obj),
                "method": "native Boolean deform/corner interpolation; cut faces generated from cutter",
            }
        )
        return obj
    except Exception:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
        raise


def _valid(obj):
    info = geometry.inspect(obj)
    overlaps = fairing.overlap_candidates(obj)
    if not info["finite"] or info["nonmanifold_edges"] or overlaps:
        raise ValueError(
            "Invalid geometry "
            + obj.name
            + ": nonmanifold="
            + str(info["nonmanifold_edges"])
            + ", overlap candidates="
            + str(overlaps)
        )
