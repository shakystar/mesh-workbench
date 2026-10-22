"""Bounded cubic lattice offsets committed as independent deformation layers."""

import json

import numpy as np

from . import geometry, layers, sculpt


def _array(value, shape, label):
    result = np.asarray(value, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError("Invalid " + label)
    return result


def _basis(t):
    return np.column_stack(
        ((1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3)
    )


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * t * (10 + t * (-15 + 6 * t))


def _field(points, origin, axes, bounds, controls, feather, pins):
    local = (points - origin) @ axes.T
    t = (local - bounds[0]) / (bounds[1] - bounds[0])
    active = ((t >= 0) & (t <= 1)).all(axis=1)
    tc = np.clip(t, 0, 1)
    b = [_basis(tc[:, i]) for i in range(3)]
    offsets = np.einsum("ni,nj,nk,ijkd->nd", *b, controls, optimize=True)
    # Boundary taper applies to both the evaluated field and Jacobian probes.
    weight = np.prod(_smooth(np.minimum(tc, 1 - tc) / feather), axis=1) * active
    for pin in pins:
        distance = np.linalg.norm(points - pin[0], axis=1)
        weight *= _smooth((distance - pin[1]) / (pin[2] - pin[1]))
    return points + (offsets @ axes) * weight[:, None]


def cage(
    obj,
    selection,
    bounds,
    controls,
    origin=(0, 0, 0),
    axes=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    pins=None,
    weights=None,
    feather=0.15,
    max_displacement=20,
    label="Form cage",
):
    """Apply local-axis offsets (4x4x4x3) with zero displacement at cage bounds.

    A regular lattice plus every selected vertex samples the weighted Jacobian.
    Per-vertex weights are checked additionally for face inversions; they do not
    constitute a continuous deformation field or a self-intersection proof.
    """
    selection = geometry.validate_selection(obj, selection)
    ids = np.array(selection["indices"], dtype=int)
    if selection["domain"] != "VERT" or not len(ids):
        raise ValueError("Nonempty vertex selection required")
    if obj.data.users != 1 or obj.modifiers or obj.constraints:
        raise ValueError("Single-user unmodified unconstrained mesh required")
    matrix = np.array(obj.matrix_world)
    if (
        not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-7)
        or np.linalg.det(matrix[:3, :3]) < 0
    ):
        raise ValueError("Only rigid object transforms supported")
    origin = _array(origin, (3,), "cage origin")
    axes = _array(axes, (3, 3), "cage axes")
    bounds = _array(bounds, (2, 3), "cage bounds")
    controls = _array(controls, (4, 4, 4, 3), "cubic control offsets")
    if (
        not np.allclose(axes @ axes.T, np.eye(3), atol=1e-7)
        or np.linalg.det(axes) < 0
        or np.any(bounds[1] - bounds[0] < 1e-5)
    ):
        raise ValueError("Right-handed orthonormal cage and positive extents required")
    feather = sculpt.number(feather, 0.01, 0.5, "boundary feather")
    limit = sculpt.number(max_displacement, 1e-6, 1000, "maximum displacement")
    if np.linalg.norm(controls, axis=3).max() > limit:
        raise ValueError("Control offset exceeds displacement limit")
    if not isinstance(label, str) or not 1 <= len(label) <= 48:
        raise ValueError("Invalid layer label")
    pin_data = []
    for pin in pins or []:
        center = _array(pin["center"], (3,), "pin center")
        fixed = sculpt.number(pin["fixed_radius"], 0, 1e5, "pin fixed radius")
        release = sculpt.number(pin["release_radius"], 0, 1e5, "pin release radius")
        if release <= fixed:
            raise ValueError("Pin release radius must exceed fixed radius")
        pin_data.append((center, fixed, release))
    weight = (
        np.ones(len(ids))
        if weights is None
        else _array(weights, (len(ids),), "region weights")
    )
    if np.any(weight < 0) or np.any(weight > 1):
        raise ValueError("Region weights must be in [0,1]")
    before = sculpt.coordinates(obj)

    def field(points):
        return _field(points, origin, axes, bounds, controls, feather, pin_data)

    # Include the taper transition explicitly instead of only coarse cell centers.
    ts = np.unique(
        np.r_[np.linspace(0, 1, 9), feather / 2, feather, 1 - feather, 1 - feather / 2]
    )
    grid = np.array(np.meshgrid(ts, ts, ts, indexing="ij")).reshape(3, -1).T
    probe = origin + (bounds[0] + grid * (bounds[1] - bounds[0])) @ axes
    probe = np.vstack((probe, before[ids]))
    epsilon = float(min(bounds[1] - bounds[0]) * 1e-5)
    derivative = []
    for direction in np.eye(3):
        derivative.append(
            (field(probe + epsilon * direction) - field(probe - epsilon * direction))
            / (2 * epsilon)
        )
    jacobian = np.stack(derivative, axis=2)
    determinants = np.linalg.det(jacobian)
    if not np.isfinite(determinants).all() or determinants.min() <= 0.05:
        raise ValueError("Cage produces sampled foldover or near-collapse")
    after = before.copy()
    after[ids] += (field(before[ids]) - before[ids]) * weight[:, None]
    delta = after - before
    movement = np.linalg.norm(delta, axis=1)
    if movement.max() < 1e-8:
        raise ValueError("Cage produced no change")
    if movement.max() > limit + 1e-8:
        raise ValueError("Result exceeds displacement limit")
    chosen = set(ids)
    for edge in obj.data.edges:
        a, b = edge.vertices
        if (a in chosen) != (b in chosen) and max(movement[a], movement[b]) > 1e-8:
            raise ValueError("Selected region boundary must have zero displacement")
    obj.data.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in obj.data.loop_triangles], dtype=int)
    if len(triangles):
        old, new = before[triangles], after[triangles]
        old_norm = np.cross(old[:, 1] - old[:, 0], old[:, 2] - old[:, 0])
        new_norm = np.cross(new[:, 1] - new[:, 0], new[:, 2] - new[:, 0])
        dots = np.einsum("ij,ij->i", old_norm, new_norm)
        if np.any(dots <= 0):
            raise ValueError("Cage produces degenerate or inverted sampled faces")
    # Validate and calculate everything before changing Blender state.
    had_keys = obj.data.shape_keys is not None
    old_history = obj.get("mw_layers")
    history = json.loads(old_history or "[]")
    settings = {
        "bounds": bounds.tolist(),
        "controls": controls.tolist(),
        "origin": origin.tolist(),
        "axes": axes.tolist(),
        "pins": [
            {"center": p[0].tolist(), "fixed_radius": p[1], "release_radius": p[2]}
            for p in pin_data
        ],
        "feather": feather,
        "max_displacement": limit,
        "weights": weight.tolist(),
    }
    key = None
    result = None
    try:
        key = layers.begin(obj)
        local_delta = delta @ matrix[:3, :3]
        for i in ids:
            key.data[int(i)].co += geometry.vector(local_delta[i])
        result = layers.finish(obj)
        result.name = "MW " + label
        history.append(
            {
                "name": result.name,
                "topology": sculpt.topology(obj),
                "operation": "form_cage",
                "settings": settings,
                "indices": ids.tolist(),
            }
        )
        obj["mw_layers"] = json.dumps(history, allow_nan=False)
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, True)
        elif result is not None:
            obj.shape_key_remove(result)
        if old_history is None:
            if "mw_layers" in obj:
                del obj["mw_layers"]
        else:
            obj["mw_layers"] = old_history
        if (
            not had_keys
            and obj.data.shape_keys
            and len(obj.data.shape_keys.key_blocks) == 1
        ):
            obj.shape_key_clear()
        raise
    return {
        "layer": result.name,
        "vertices": int((movement > 1e-8).sum()),
        "maximum_displacement": float(movement.max()),
        "minimum_sampled_jacobian": float(determinants.min()),
        "jacobian_samples": len(probe),
        "pins": len(pin_data),
        "topology": geometry.signature(obj),
    }
