"""Named topology-bound vertex regions and reversible profile displacements."""

import json
import numpy as np
import bpy
from mathutils import Vector
from . import geometry, layers, sculpt, fairing


def define(obj, name, selection):
    selection = geometry.validate_selection(obj, selection)
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 48
        or selection["domain"] != "VERT"
        or not selection["indices"]
    ):
        raise ValueError("Named nonempty vertex region required")
    registry = json.loads(obj.get("mw_regions", "{}"))
    if name in registry:
        raise ValueError("Region exists")
    registry[name] = {
        "topology": geometry.signature(obj),
        "indices": selection["indices"],
    }
    obj["mw_regions"] = json.dumps(registry)
    return resolve(obj, name)


def resolve(obj, name):
    sculpt.editable(obj)
    registry = json.loads(obj.get("mw_regions", "{}"))
    if name not in registry:
        raise ValueError("Unknown region")
    entry = registry[name]
    if entry["topology"] != geometry.signature(obj):
        raise ValueError("Region topology changed; explicit reselection required")
    return geometry.selection(obj, "VERT", entry["indices"])


def profile(
    obj,
    name,
    axis,
    displacement_axis,
    knots,
    label="Profile edit",
    max_displacement=0.25,
):
    """World-axis smoothstep profile. Same displacement through paired thickness.

    Zero outside knot range; endpoints must be zero to avoid a jump. Only named
    vertices change. Reject detected nonadjacent overlaps and roll back.
    """
    selected = resolve(obj, name)
    if obj.data.users != 1:
        raise ValueError("Make a single-user mesh before profile editing")
    if (
        type(axis) is not int
        or type(displacement_axis) is not int
        or axis not in range(3)
        or displacement_axis not in range(3)
        or axis == displacement_axis
    ):
        raise ValueError("Distinct coordinate axes required")
    k = np.asarray(knots, dtype=float)
    limit = sculpt.number(max_displacement, 1e-8, 1e3, "displacement limit")
    if (
        k.ndim != 2
        or k.shape[1] != 2
        or len(k) < 3
        or not np.isfinite(k).all()
        or not (np.diff(k[:, 0]) > 0).all()
        or k[0, 1] != 0
        or k[-1, 1] != 0
        or np.abs(k[:, 1]).max() > limit
    ):
        raise ValueError(
            "Ordered finite knots, zero endpoints and bounded offsets required"
        )
    if not isinstance(label, str) or not 1 <= len(label) <= 48:
        raise ValueError("Invalid label")
    if fairing.overlap_candidates(obj):
        raise ValueError("Input has overlap candidates")
    original = sculpt.coordinates(obj)
    ids = np.asarray(selected["indices"], dtype=int)
    values = original[ids, axis]
    offsets = np.zeros(len(ids))
    for (a, u), (b, v) in zip(k, k[1:]):
        active = (values >= a) & (values <= b)
        t = (values[active] - a) / (b - a)
        offsets[active] = u + (v - u) * t * t * (3 - 2 * t)
    if not np.any(np.abs(offsets) > 1e-10):
        raise ValueError("Profile produced no change")
    had_keys = obj.data.shape_keys is not None
    key = layers.begin(obj)
    try:
        inverse = obj.matrix_world.inverted().to_3x3()
        for i, delta in zip(ids, offsets):
            move = Vector((0, 0, 0))
            move[displacement_axis] = float(delta)
            key.data[int(i)].co += inverse @ move
        layer = layers.finish(obj)
        if fairing.overlap_candidates(obj):
            obj.shape_key_remove(layer)
            if not had_keys:
                obj.shape_key_clear()
            bpy.context.view_layer.update()
            raise ValueError("Profile introduced overlaps; rolled back")
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, True)
        raise
    layer.name = "MW " + label
    report = {
        "region": name,
        "layer": layer.name,
        "changed_vertices": int((np.abs(offsets) > 1e-10).sum()),
        "max_displacement": float(np.abs(offsets).max()),
    }
    history = json.loads(obj.get("mw_layers", "[]"))
    history.append(
        {"name": layer.name, "topology": sculpt.topology(obj), "report": report}
    )
    obj["mw_layers"] = json.dumps(history)
    return report


def radial_move(obj, name, center, radius, delta, label="Local displacement"):
    """Frozen smooth radial weights within a named region; additive undo layer."""
    selected = resolve(obj, name)
    if obj.data.users != 1:
        raise ValueError("Make a single-user mesh before radial editing")
    center = np.array(geometry.vector(center))
    delta = geometry.vector(delta)
    radius = sculpt.number(radius, 1e-6, 1e6, "radius")
    if not isinstance(label, str) or not 1 <= len(label) <= 48 or delta.length < 1e-10:
        raise ValueError("Label and nonzero displacement required")
    if fairing.overlap_candidates(obj):
        raise ValueError("Input has overlap candidates")
    original = sculpt.coordinates(obj)
    ids = np.asarray(selected["indices"], int)
    t = np.clip(1 - np.linalg.norm(original[ids] - center, axis=1) / radius, 0, 1)
    weights = t * t * (3 - 2 * t)
    if not np.any(weights > 0):
        raise ValueError("No vertices in influence")
    had_keys = obj.data.shape_keys is not None
    key = layers.begin(obj)
    try:
        local = obj.matrix_world.inverted().to_3x3() @ delta
        for i, w in zip(ids, weights):
            key.data[int(i)].co += local * float(w)
        layer = layers.finish(obj)
        if fairing.overlap_candidates(obj):
            obj.shape_key_remove(layer)
            if not had_keys:
                obj.shape_key_clear()
            bpy.context.view_layer.update()
            raise ValueError("Radial edit introduced overlaps; rolled back")
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, True)
        raise
    layer.name = "MW " + label
    report = {
        "layer": layer.name,
        "region": name,
        "changed_vertices": int((weights > 0).sum()),
        "max_displacement": float(weights.max() * delta.length),
    }
    history = json.loads(obj.get("mw_layers", "[]"))
    history.append(
        {"name": layer.name, "topology": sculpt.topology(obj), "report": report}
    )
    obj["mw_layers"] = json.dumps(history)
    return report
