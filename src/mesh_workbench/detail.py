"""Profiled mechanical surfaces and source-preserving edge finishing."""

import json
import math
import bpy
import numpy as np
from mathutils import Vector
from . import enclosure, mechanical, sculpt, geometry, models


@mechanical._atomic
def profiled_ring(
    name,
    start,
    profile,
    flutes=0,
    depth=0,
    segments=192,
    axis=(1, 0, 0),
    ticks=0,
    tick_depth=0,
    tick_range=None,
):
    """Closed annular solid from [axial,outer,inner,flute_amplitude] rows.

    Flutes remove radius only; fixed inner profiles preserve mechanism space.
    Profile dimensions and depth are geometry, not a bump-map approximation.
    """
    rows = np.asarray(profile, dtype=float)
    if (
        rows.ndim != 2
        or rows.shape[1] != 4
        or len(rows) < 2
        or not np.isfinite(rows).all()
    ):
        raise ValueError("Finite axial/outer/inner/flute profile required")
    if (
        np.any(np.diff(rows[:, 0]) <= 0)
        or np.any(rows[:, 2] <= 0)
        or np.any(rows[:, 3] < 0)
        or np.any(rows[:, 3] > 1)
    ):
        raise ValueError("Ordered axial rows and positive radii required")
    if (
        type(flutes) != int
        or not 0 <= flutes <= 96
        or type(segments) != int
        or not 16 <= segments <= 1536
    ):
        raise ValueError("Invalid radial sampling")
    depth = sculpt.number(depth, 0, 100, "flute depth")
    if flutes and (segments % flutes or segments < flutes * 8):
        raise ValueError(
            "At least eight samples per flute and exact divisibility required"
        )
    if np.any(rows[:, 1] - depth * rows[:, 3] <= rows[:, 2]):
        raise ValueError("Flute breaks annular wall")
    if type(ticks) != int or not 0 <= ticks <= 96:
        raise ValueError("Invalid index tick count")
    tick_depth = sculpt.number(tick_depth, 0, 10, "index tick depth")
    if ticks:
        if (
            segments % ticks
            or segments < ticks * 8
            or tick_range is None
            or len(tick_range) != 2
            or not np.isfinite(tick_range).all()
            or not rows[0, 0] <= tick_range[0] < tick_range[1] <= rows[-1, 0]
        ):
            raise ValueError("Index ticks require sampled axial span")
        if np.any(rows[:, 1] - depth * rows[:, 3] - tick_depth <= rows[:, 2]):
            raise ValueError("Index tick breaks annular wall")
    direction = geometry.vector(axis)
    if direction.length < 1e-8:
        raise ValueError("Nonzero ring axis required")
    rotation = Vector((1, 0, 0)).rotation_difference(direction.normalized())
    origin = geometry.vector(start)
    path = [(x, outer, amp, False) for x, outer, inner, amp in rows] + [
        (x, inner, 0, True) for x, outer, inner, amp in reversed(rows)
    ]
    vertices = []
    for x, r, amp, inside in path:
        for j in range(segments):
            theta = math.tau * j / segments
            radius = (
                r - depth * amp * ((1 - math.cos(flutes * theta)) / 2) ** 2
                if flutes
                else r
            )
            if ticks and not inside and tick_range[0] < x < tick_range[1]:
                axial = math.sin(
                    math.pi * (x - tick_range[0]) / (tick_range[1] - tick_range[0])
                )
                pulse = max(0, (math.cos(ticks * theta) - 0.85) / 0.15)
                radius -= tick_depth * axial * pulse
            vertices.append(
                origin
                + rotation
                @ Vector((x, radius * math.cos(theta), radius * math.sin(theta)))
            )
    faces = []
    for i in range(len(path)):
        k = (i + 1) % len(path)
        for j in range(segments):
            faces.append(
                [
                    i * segments + j,
                    i * segments + (j + 1) % segments,
                    k * segments + (j + 1) % segments,
                    k * segments + j,
                ]
            )
    obj = enclosure._mesh(name, vertices, faces)
    uv = obj.data.uv_layers.new(name="AxialSurface")
    length = rows[-1, 0] - rows[0, 0]
    for f in obj.data.polygons:
        stations = {v // segments for v in f.vertices}
        cap = stations in ({len(rows) - 1, len(rows)}, {0, len(path) - 1})
        f.use_smooth = not cap
        angular = [v % segments for v in f.vertices]
        wrap = max(angular) - min(angular) > segments // 2
        for li in f.loop_indices:
            v = obj.data.loops[li].vertex_index
            j = v % segments
            uv.data[li].uv = (
                1 if wrap and j == 0 else j / segments,
                (path[v // segments][0] - rows[0, 0]) / length,
            )
    obj["mw_profiled_ring"] = json.dumps(
        {
            "profile": profile,
            "flutes": flutes,
            "depth": depth,
            "segments": segments,
            "axis": list(axis),
            "ticks": ticks,
            "tick_depth": tick_depth,
            "tick_range": tick_range,
        }
    )
    enclosure._valid(obj)
    return obj


@mechanical._atomic
def variable_bevel(source, selection, name, widths, segments=4):
    """Per-edge bevel offsets, preserving the input and native UV/deform layers.

    Static unscaled meshes only. Bindings and prior topology selections require
    explicit rebuilding; this operation does not infer attachment migration.
    """
    sculpt.editable(source)
    sel = geometry.validate_selection(source, selection)
    if (
        sel["domain"] != "EDGE"
        or not sel["indices"]
        or len(widths) != len(sel["indices"])
    ):
        raise ValueError("One width per selected edge required")
    if source.data.shape_keys or not np.allclose(
        source.matrix_world.to_scale(), [1, 1, 1], atol=1e-7
    ):
        raise ValueError("Static unit-scale mesh required")
    if name in bpy.data.objects or type(segments) != int or not 1 <= segments <= 16:
        raise ValueError("Invalid bevel output or segments")
    if any(k in source for k in ["mw_surface_binding", "mw_nested_assembly"]):
        raise ValueError("Rebuild bound descendants explicitly before beveling")
    for mask in json.loads(source.get("mw_masks", "{}")).values():
        if (
            mask["topology"] != sculpt.topology(source)
            or source.vertex_groups.get(mask["group"]) is None
        ):
            raise ValueError("Stale bevel source mask")
    widths = [sculpt.number(w, 1e-5, 10000, "edge bevel width") for w in widths]
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    attr = obj.data.attributes.get("bevel_weight_edge") or obj.data.attributes.new(
        "bevel_weight_edge", "FLOAT", "EDGE"
    )
    maximum = max(widths)
    for v in attr.data:
        v.value = 0
    for i, w in zip(sel["indices"], widths):
        attr.data[i].value = w / maximum
    models.activate(obj)
    mod = obj.modifiers.new("Variable edge offsets", "BEVEL")
    mod.limit_method = "WEIGHT"
    mod.width = maximum
    mod.segments = segments
    mod.use_clamp_overlap = False
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for key in [
        "mw_layers",
        "mw_pending",
        "mw_remesh",
        "mw_refinement",
        "mw_regions",
        "mw_attachment_revision",
        "mw_enclosure",
        "mw_section_shape",
    ]:
        if key in obj:
            del obj[key]
    masks = json.loads(obj.get("mw_masks", "{}"))
    for mask in masks.values():
        mask["topology"] = sculpt.topology(obj)
    if masks:
        obj["mw_masks"] = json.dumps(masks)
    # Preserve global affine coordinate fields exactly when the source proves
    # that representation. General charts retain Blender corner interpolation.
    source_xyz = sculpt.coordinates(source)
    result_xyz = sculpt.coordinates(obj)
    source_basis = np.column_stack((source_xyz, np.ones(len(source_xyz))))
    result_basis = np.column_stack((result_xyz, np.ones(len(result_xyz))))
    affine_fields = []
    native_fields = []
    for layer in source.data.uv_layers:
        ids = [loop.vertex_index for loop in source.data.loops]
        basis = source_basis[ids]
        values = np.array([v.uv[:] for v in layer.data])
        coefficients, _, rank, _ = np.linalg.lstsq(basis, values, rcond=None)
        if rank == 4 and np.max(np.abs(basis @ coefficients - values)) <= 1e-6:
            mapped = result_basis @ coefficients
            target_layer = obj.data.uv_layers[layer.name]
            for loop in obj.data.loops:
                target_layer.data[loop.index].uv = mapped[loop.vertex_index]
            affine_fields.append("UV:" + layer.name)
        else:
            native_fields.append("UV:" + layer.name)
    for group in source.vertex_groups:
        values = np.array(
            [
                next((g.weight for g in v.groups if g.group == group.index), 0)
                for v in source.data.vertices
            ]
        )
        coefficients, _, rank, _ = np.linalg.lstsq(source_basis, values, rcond=None)
        if rank == 4 and np.max(np.abs(source_basis @ coefficients - values)) <= 1e-6:
            target_group = obj.vertex_groups[group.name]
            for i, w in enumerate(np.clip(result_basis @ coefficients, 0, 1)):
                target_group.add([i], float(w), "REPLACE")
            affine_fields.append("GROUP:" + group.name)
        else:
            native_fields.append("GROUP:" + group.name)
    enclosure._valid(obj)
    if len(obj.data.vertices) <= len(source.data.vertices):
        raise ValueError("Bevel produced no geometric change")
    obj["mw_variable_bevel"] = json.dumps(
        {
            "source": source.name,
            "edges": sel["indices"],
            "widths": widths,
            "segments": segments,
            "attribute_transfer": "exact proven affine fields; native corner/deform interpolation otherwise; fresh selection required",
            "affine_fields": affine_fields,
            "native_fields": native_fields,
        }
    )
    return obj


@mechanical._atomic
def edge_box(name, dimensions, center, upper=0.6, lower=0.2, vertical=0.4, segments=4):
    """Box with separately specified top, bottom and vertical edge offsets."""
    dims = geometry.vector(dimensions)
    origin = geometry.vector(center)
    if min(dims) <= 0 or max(upper, lower, vertical) >= min(dims) / 2:
        raise ValueError("Box bevel offsets must fit the smallest dimension")
    stock = models.primitive("cube", name + " stock")
    try:
        for v in stock.data.vertices:
            v.co = origin + Vector([v.co[i] * dims[i] / 2 for i in range(3)])
        stock.data.update()
        xyz = sculpt.coordinates(stock)
        ids = []
        widths = []
        for edge in stock.data.edges:
            a, b = xyz[list(edge.vertices)]
            ids.append(edge.index)
            widths.append(
                vertical
                if abs(a[2] - b[2]) > 1e-6
                else upper
                if (a[2] + b[2]) / 2 > origin.z
                else lower
            )
        result = variable_bevel(
            stock, geometry.selection(stock, "EDGE", ids), name, widths, segments
        )
        for f in result.data.polygons:
            f.use_smooth = True
        models.activate(result)
        mod = result.modifiers.new("Finished face normals", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        result["mw_edge_box"] = json.dumps(
            {
                "dimensions": list(dimensions),
                "center": list(center),
                "upper": upper,
                "lower": lower,
                "vertical": vertical,
            }
        )
        return result
    finally:
        mechanical.remove(stock)
