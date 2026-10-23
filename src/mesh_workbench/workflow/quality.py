"""Discrete curvature, diagnostic reflection bands and pinned patch fairing.

Cotan stiffness / lumped barycentric mass convention: |Delta x| / 2.
Reference: https://libigl.github.io/tutorial/#curvature-directions
"""

import bpy
import numpy as np
from mathutils import Vector
from . import geometry, sculpt, layers, fairing


def curvature(obj, indices=None, attribute=None):
    sculpt.editable(obj)
    xyz = sculpt.coordinates(obj)
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated = ev.to_mesh()
    try:
        evaluated.calc_loop_triangles()
        triangles = [tuple(t.vertices) for t in evaluated.loop_triangles]
    finally:
        ev.to_mesh_clear()
    area = np.zeros(len(xyz))
    lap = np.zeros_like(xyz)
    normals = np.zeros_like(xyz)
    edges = {}
    for ids in triangles:
        a, b, c = xyz[list(ids)]
        cross = np.cross(b - a, c - a)
        twice = np.linalg.norm(cross)
        if twice < 1e-12:
            raise ValueError("Degenerate curvature triangle")
        for i in ids:
            area[i] += twice / 6
            normals[i] += cross
        for i, j, k in [
            (ids[0], ids[1], ids[2]),
            (ids[1], ids[2], ids[0]),
            (ids[2], ids[0], ids[1]),
        ]:
            cot = np.dot(xyz[i] - xyz[k], xyz[j] - xyz[k]) / twice
            d = cot * 0.5 * (xyz[j] - xyz[i])
            lap[i] += d
            lap[j] -= d
            edge = tuple(sorted((i, j)))
            edges[edge] = edges.get(edge, 0) + 1
    if (area <= 0).any():
        raise ValueError("Isolated curvature vertex")
    mean = np.linalg.norm(lap / area[:, None], axis=1) * 0.5
    boundary = {i for e, count in edges.items() if count != 2 for i in e}
    selected = (
        set(range(len(xyz)))
        if indices is None
        else set(geometry.selection(obj, "VERT", indices)["indices"])
    )
    selected -= boundary
    if not selected:
        raise ValueError("No interior curvature samples")
    ids = sorted(selected)
    gradients = [
        abs(mean[a] - mean[b]) / max(np.linalg.norm(xyz[a] - xyz[b]), 1e-12)
        for a, b in edges
        if a in selected and b in selected
    ]
    if attribute:
        attr = obj.data.attributes.get(attribute) or obj.data.attributes.new(
            attribute, "FLOAT", "POINT"
        )
        if attr.domain != "POINT" or attr.data_type != "FLOAT":
            raise ValueError("Incompatible curvature attribute")
        attr.data.foreach_set("value", mean.astype(np.float32))
    return {
        "method": "cotangent mean-curvature magnitude with barycentric mass",
        "samples": len(ids),
        "boundary_excluded": len(boundary),
        "mean": float(mean[ids].mean()),
        "p95": float(np.percentile(mean[ids], 95)),
        "max": float(mean[ids].max()),
        "roughness_rms": float(np.sqrt(np.mean(np.square(gradients))))
        if gradients
        else 0,
        "values": mean.tolist(),
    }


def fair_patch(
    obj,
    selection,
    iterations=24,
    strength=0.45,
    reverse=-0.47,
    max_shift=3,
    method="laplacian",
    fit_radius=6,
):
    sel = geometry.validate_selection(obj, selection)
    if sel["domain"] != "VERT" or not sel["indices"] or obj.data.users != 1:
        raise ValueError("Nonempty single-user vertex patch required")
    if type(iterations) is not int or not 1 <= iterations <= 100:
        raise ValueError("Invalid fairing iterations")
    strength = sculpt.number(strength, 0.001, 0.8, "strength")
    reverse = sculpt.number(reverse, -0.8, 0, "reverse")
    max_shift = sculpt.number(max_shift, 1e-6, 1e4, "maximum shift")
    if fairing.overlap_candidates(obj):
        raise ValueError("Input has overlaps")
    before = sculpt.coordinates(obj)
    coords = before.copy()
    neighbors = [set() for _ in coords]
    edges = {tuple(sorted(e.vertices)): 0 for e in obj.data.edges}
    for face in obj.data.polygons:
        ids = list(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
            neighbors[a].add(b)
            neighbors[b].add(a)
    chosen = set(sel["indices"])
    pinned = {
        i for i, n in enumerate(neighbors) if i not in chosen or not n.issubset(chosen)
    }
    pinned.update(i for e, count in edges.items() if count != 2 for i in e)
    active = sorted(chosen - pinned)
    if not active:
        raise ValueError("No unpinned patch interior")
    initial = curvature(obj, active)
    if method == "quadratic":
        from mathutils.kdtree import KDTree

        fit_radius = sculpt.number(fit_radius, 1e-5, 1e4, "fit radius")
        tree = KDTree(len(before))
        for i, p in enumerate(before):
            tree.insert(Vector(p), i)
        tree.balance()
        normal_matrix = obj.matrix_world.inverted().transposed().to_3x3()
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated = ev.to_mesh()
        try:
            normals = np.asarray(
                [(normal_matrix @ v.normal).normalized() for v in evaluated.vertices]
            )
        finally:
            ev.to_mesh_clear()
        supports = {
            i: [
                j
                for _, j, _ in tree.find_range(Vector(before[i]), fit_radius)
                if normals[i].dot(normals[j]) > 0.4 and j != i
            ]
            for i in active
        }
        if any(len(ids) < 8 for ids in supports.values()):
            raise ValueError("Insufficient quadratic patch support")
        for _ in range(iterations):
            updated = coords.copy()
            for i in active:
                local = coords[supports[i]] - coords[i]
                _, basis = np.linalg.eigh(local.T @ local)
                normal = basis[:, 0]
                uv = local @ basis[:, 1:]
                u, v = uv.T
                z = local @ normal
                design = np.column_stack((np.ones(len(u)), u, v, u * u, u * v, v * v))
                weights = np.exp(
                    -np.sum(local * local, axis=1) / (fit_radius * 0.7) ** 2
                )
                coefficients, _, rank, _ = np.linalg.lstsq(
                    design * weights[:, None], z * weights, rcond=1e-10
                )
                if rank < 6:
                    raise ValueError("Rank-deficient quadratic support")
                updated[i] += strength * coefficients[0] * normal
            coords = updated
    elif method == "laplacian":
        for _ in range(iterations):
            for step in (strength, reverse):
                d = np.zeros_like(coords)
                for i in active:
                    d[i] = coords[sorted(neighbors[i])].mean(axis=0) - coords[i]
                coords += step * d
    else:
        raise ValueError("Unknown patch fairing method")
    shift = float(np.linalg.norm(coords - before, axis=1).max())
    if not np.isfinite(coords).all() or shift > max_shift:
        raise ValueError("Patch displacement limit exceeded")
    had_keys = obj.data.shape_keys is not None
    key = layers.begin(obj)
    layer = None
    try:
        inv = obj.matrix_world.inverted()
        for i in active:
            key.data[i].co = inv @ Vector(coords[i])
        layer = layers.finish(obj)
        if fairing.overlap_candidates(obj):
            raise ValueError("Patch overlaps; restored")
        after = curvature(obj, active)
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, cancel=True)
        elif layer is not None:
            obj.shape_key_remove(layer)
        if not had_keys and obj.data.shape_keys:
            obj.shape_key_clear()
        raise
    layer.name = "MW pinned patch"
    return {
        "method": method,
        "layer": layer.name,
        "active": len(active),
        "pinned": len(pinned),
        "pinned_error": float(
            np.max(
                np.abs(sculpt.coordinates(obj)[sorted(pinned)] - before[sorted(pinned)])
            )
        )
        if pinned
        else 0,
        "max_shift": shift,
        "before": {k: v for k, v in initial.items() if k != "values"},
        "after": {k: v for k, v in after.items() if k != "values"},
    }


def reflection_bands(obj, name="MW reflection bands", frequency=18):
    frequency = sculpt.number(frequency, 1, 200, "band frequency")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    geo = nodes.new("ShaderNodeNewGeometry")
    reflect = nodes.new("ShaderNodeVectorMath")
    reflect.operation = "REFLECT"
    links.new(geo.outputs["Incoming"], reflect.inputs[0])
    links.new(geo.outputs["Normal"], reflect.inputs[1])
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = (0.2, 0.6, 1)
    links.new(reflect.outputs["Vector"], dot.inputs[0])
    mult = nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = frequency
    links.new(dot.outputs["Value"], mult.inputs[0])
    sine = nodes.new("ShaderNodeMath")
    sine.operation = "SINE"
    links.new(mult.outputs[0], sine.inputs[0])
    step = nodes.new("ShaderNodeMath")
    step.operation = "GREATER_THAN"
    links.new(sine.outputs[0], step.inputs[0])
    mix = nodes.new("ShaderNodeMixRGB")
    mix.inputs[1].default_value = (0.005, 0.015, 0.03, 1)
    mix.inputs[2].default_value = (0.8, 0.9, 1, 1)
    links.new(step.outputs[0], mix.inputs[0])
    emit = nodes.new("ShaderNodeEmission")
    links.new(mix.outputs[0], emit.inputs["Color"])
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs[0], out.inputs["Surface"])
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return material


def curvature_material(obj, attribute="MW mean curvature", maximum=0.1):
    maximum = sculpt.number(maximum, 1e-8, 1e6, "curvature scale")
    curvature(obj, attribute=attribute)
    material = bpy.data.materials.new("MW curvature map")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_name = attribute
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "DIVIDE"
    scale.inputs[1].default_value = maximum
    links.new(attr.outputs["Fac"], scale.inputs[0])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.01, 0.04, 0.5, 1)
    ramp.color_ramp.elements[1].color = (0.8, 0.01, 0.005, 1)
    ramp.color_ramp.elements.new(0.5).color = (0.01, 0.8, 0.4, 1)
    links.new(scale.outputs[0], ramp.inputs[0])
    emit = nodes.new("ShaderNodeEmission")
    links.new(ramp.outputs[0], emit.inputs["Color"])
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs[0], out.inputs["Surface"])
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return material
