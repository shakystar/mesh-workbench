"""Bounded section-width fields for guide-built XZ enclosures.

Pure coordinate operation: caller owns source-preserving mesh construction.
Rows specify height, rear correction, front correction and side crown in mm.
"""

import numpy as np


def quintic(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def validate(controls):
    if not isinstance(controls, dict) or set(controls) - {
        "rows",
        "pins",
        "maximum_displacement",
    }:
        raise ValueError("Unknown section control fields")
    rows = np.asarray(controls.get("rows"), dtype=float)
    if (
        rows.ndim != 2
        or rows.shape[1] != 4
        or len(rows) < 2
        or not np.isfinite(rows).all()
    ):
        raise ValueError("Finite ordered section rows [z,rear,front,crown] required")
    if np.any(np.diff(rows[:, 0]) <= 0):
        raise ValueError("Section heights must increase")
    pins = np.asarray(controls.get("pins", []), dtype=float)
    if pins.size == 0:
        pins = np.empty((0, 4))
    if pins.ndim != 2 or pins.shape[1] != 4 or not np.isfinite(pins).all():
        raise ValueError("Finite pin rows [x,z,fixed,release] required")
    if np.any(pins[:, 2] < 0) or np.any(pins[:, 3] <= pins[:, 2]):
        raise ValueError("Pin release must exceed fixed radius")
    limit = float(controls.get("maximum_displacement", 6))
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError("Positive finite displacement limit required")
    return rows, pins, limit


def apply(points, outline, base_widths, controls):
    rows, pins, limit = validate(controls)
    xyz = np.asarray(points, dtype=float)
    boundary = np.asarray(outline, dtype=float)
    widths = np.asarray(base_widths, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("Finite XYZ coordinates required")
    if boundary.ndim != 2 or boundary.shape[1] != 2 or not np.isfinite(boundary).all():
        raise ValueError("Finite XZ outline required")
    if (
        widths.shape != (len(xyz),)
        or not np.isfinite(widths).all()
        or (widths <= 0).any()
    ):
        raise ValueError("Positive width for every vertex required")
    z = xyz[:, 2]
    ids = np.clip(np.searchsorted(rows[:, 0], z, side="right") - 1, 0, len(rows) - 2)
    t = quintic((z - rows[ids, 0]) / (rows[ids + 1, 0] - rows[ids, 0]))
    params = rows[ids, 1:] * (1 - t[:, None]) + rows[ids + 1, 1:] * t[:, None]
    # Intersect the independently supplied outline at each unique height.
    low = np.empty(len(xyz))
    high = np.empty(len(xyz))
    a = boundary
    b = np.roll(boundary, -1, axis=0)
    for height in np.unique(z):
        indices = np.flatnonzero(z == height)
        cross = ((a[:, 1] <= height) & (b[:, 1] >= height)) | (
            (b[:, 1] <= height) & (a[:, 1] >= height)
        )
        nonhorizontal = cross & (np.abs(b[:, 1] - a[:, 1]) > 1e-10)
        aa = a[nonhorizontal]
        bb = b[nonhorizontal]
        xs = aa[:, 0] + (height - aa[:, 1]) / (bb[:, 1] - aa[:, 1]) * (
            bb[:, 0] - aa[:, 0]
        )
        if len(xs) < 2:
            # At an exact extremum, the section can degenerate to one point.
            xs = a[np.abs(a[:, 1] - height) < 1e-6, 0]
        if len(xs) == 0:
            raise ValueError("Vertex outside section outline")
        low[indices] = xs.min()
        high[indices] = xs.max()
    span = high - low
    u = np.clip((xyz[:, 0] - low) / np.maximum(span, 1e-9), 0, 1)
    side = params[:, 0] * (1 - u) + params[:, 1] * u + params[:, 2] * 4 * u * (1 - u)
    release = np.ones(len(xyz))
    for px, pz, fixed, full in pins:
        distance = np.hypot(xyz[:, 0] - px, z - pz)
        release *= quintic((distance - fixed) / (full - fixed))
    ratio = xyz[:, 1] / widths
    delta = side * ratio * np.abs(ratio) * release
    if np.max(np.abs(delta), initial=0) > limit + 1e-9:
        raise ValueError("Section displacement exceeds frozen limit")
    # Strictly increasing Y mapping prevents local width reversal.
    derivative = 1 + 2 * side * np.abs(ratio) * release / widths
    if np.min(derivative, initial=1) <= 0.1:
        raise ValueError("Section field folds or collapses the width")
    result = xyz.copy()
    result[:, 1] += delta
    fixed_ids = release == 0
    report = {
        "vertices": len(xyz),
        "changed": int(np.count_nonzero(np.abs(delta) > 1e-8)),
        "maximum_displacement": float(np.max(np.abs(delta), initial=0)),
        "minimum_width_derivative": float(np.min(derivative, initial=1)),
        "fixed_vertices": int(fixed_ids.sum()),
        "fixed_error": float(np.max(np.abs(delta[fixed_ids]), initial=0)),
    }
    return result, report
