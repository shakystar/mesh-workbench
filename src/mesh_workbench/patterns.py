"""Surface projection, repeated mesh motifs, seam curves and cylindrical weave."""

import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import geometry, sculpt


def tree(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    result = BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in m.vertices],
        [tuple(p.vertices) for p in m.polygons],
    )
    ev.to_mesh_clear()
    return result


def project(target, points, max_distance=1, offset=0, direction=None):
    max_distance = sculpt.number(max_distance, 0.00001, 1e6, "projection distance")
    offset = sculpt.number(offset, -1e6, 1e6, "offset")
    bvh = tree(target)
    points = [geometry.vector(p) for p in points]
    ray = None if direction is None else geometry.vector(direction)
    if ray is not None:
        if ray.length < 1e-10:
            raise ValueError("Nonzero projection direction required")
        ray.normalize()
    result = []
    for point in points:
        hit, normal, face, distance = (
            bvh.find_nearest(point, max_distance)
            if ray is None
            else bvh.ray_cast(point, ray, max_distance)
        )
        if hit is None:
            raise ValueError("Projection missed target within distance")
        result.append(
            {
                "position": list(hit + normal * offset),
                "normal": list(normal),
                "face": face,
                "distance": distance,
            }
        )
    return result


def seam(target, points, name, radius=0.01, spacing=0.05, offset=0.005, max_distance=1):
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    radius = sculpt.number(radius, 0.00001, 100, "seam radius")
    spacing = sculpt.number(spacing, 0.00001, 100, "spacing")
    points = [geometry.vector(p) for p in points]
    if len(points) < 2:
        raise ValueError("Seam needs at least two points")
    samples = [points[0]]
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil((b - a).length / spacing))
        if len(samples) + count > 10000:
            raise ValueError("Seam exceeds 10000 samples")
        samples.extend(a.lerp(b, i / count) for i in range(1, count + 1))
    hits = project(target, samples, max_distance, offset)
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(hits) - 1)
    for p, hit in zip(spline.points, hits):
        p.co = (*hit["position"], 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    return obj


def scatter(
    target, motif, points, name, scale=1, offset=0.01, max_distance=1, minimum_spacing=0
):
    """Place evaluated motif mesh with local +Z aligned to surface normal.

    Minimum spacing rejects nearby anchors; it is not full mesh collision detection.
    """
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    scale = sculpt.number(scale, 0.00001, 1000, "scale")
    minimum_spacing = sculpt.number(minimum_spacing, 0, 1e6, "minimum spacing")
    if not points or len(points) > 10000:
        raise ValueError("Expected 1..10000 anchors")
    hits = project(target, points, max_distance, offset)
    anchors = []
    for hit in hits:
        p = Vector(hit["position"])
        if any((p - q).length < minimum_spacing for q in anchors):
            raise ValueError("Pattern anchors violate minimum spacing")
        anchors.append(p)
    ev = motif.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    base = [v.co.copy() * scale for v in m.vertices]
    polys = [tuple(p.vertices) for p in m.polygons]
    materials = list(m.materials)
    ev.to_mesh_clear()
    vertices = []
    faces = []
    for anchor, hit in zip(anchors, hits):
        rotation = Vector((0, 0, 1)).rotation_difference(Vector(hit["normal"]))
        start = len(vertices)
        vertices.extend(anchor + rotation @ v for v in base)
        faces.extend(tuple(start + i for i in face) for face in polys)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj["mw_pattern_count"] = len(anchors)
    return obj


def conform(obj, sel, target, name, max_distance=1, offset=0, direction=None):
    geometry.validate_selection(obj, sel)
    if sel["domain"] != "VERT":
        raise ValueError("Conform requires vertices")
    coords = sculpt.coordinates(obj)
    indices = sel["indices"]
    hits = project(
        target, [coords[i] for i in indices], max_distance, offset, direction
    )
    result = geometry.fork(obj, name)
    inverse = result.matrix_world.inverted()
    for index, hit in zip(indices, hits):
        result.data.vertices[index].co = inverse @ Vector(hit["position"])
    return result


def cylindrical_uv(obj, name="MW cylindrical UV"):
    """World-Z cylindrical unwrap, rear seam; not an arbitrary-surface unwrap."""
    sculpt.editable(obj)
    if obj.data.uv_layers.get(name):
        raise ValueError("UV map already exists")
    coords = sculpt.coordinates(obj)
    if len(coords) == 0:
        raise ValueError("Empty mesh")
    center = (coords.min(axis=0) + coords.max(axis=0)) / 2
    zmin = coords[:, 2].min()
    uv = obj.data.uv_layers.new(name=name)
    for face in obj.data.polygons:
        values = []
        for i in face.vertices:
            x, y, z = coords[i]
            values.append(
                [
                    (math.atan2(x - center[0], -(y - center[1])) / (2 * math.pi) + 0.5)
                    % 1,
                    float(z - zmin),
                ]
            )
        if max(p[0] for p in values) - min(p[0] for p in values) > 0.5:
            for p in values:
                if p[0] < 0.5:
                    p[0] += 1
        for index, value in zip(face.loop_indices, values):
            uv.data[index].uv = value
    obj.data.uv_layers.active = uv
    return uv.name


def weave(obj, uv_name, frequency=60, depth=0.002, color=(0.2, 0.06, 0.35, 1)):
    if obj.data.uv_layers.get(uv_name) is None:
        raise ValueError("Missing UV map")
    frequency = sculpt.number(frequency, 0.1, 1000, "frequency")
    depth = sculpt.number(depth, 0, 1, "depth")
    if len(color) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in color):
        raise ValueError("Invalid RGBA")
    mat = bpy.data.materials.new("MW woven surface")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.72
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    tex = nodes.new("ShaderNodeUVMap")
    tex.uv_map = uv_name
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["UV"], split.inputs[0])

    def calc(op, a, b=None):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    chevron = calc("PINGPONG", calc("MULTIPLY", split.outputs["X"], 90), 1)
    wave = calc(
        "SINE",
        calc(
            "MULTIPLY",
            calc(
                "ADD",
                calc("MULTIPLY", split.outputs["Y"], frequency),
                calc("MULTIPLY", chevron, 1.5),
            ),
            2 * math.pi,
        ),
    )
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = depth
    links.new(wave, bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat.name
