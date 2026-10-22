"""Closed Z-ordered superellipse stock, with explicit section dimensions."""

import json

import numpy as np

from . import enclosure, geometry, mechanical


@mechanical._atomic
def create(name, sections, exponent=4, segments=128, origin=(0, 0, 0)):
    """Rows are [z, center_x, center_y, half_x, half_y]; no input mesh edits.

    Convex corresponding rings interpolate linearly between ordered stations.
    Caps are planar. This is solid stock, not a hollow shell or general loft.
    """
    rows = np.asarray(sections, dtype=float)
    if (rows.ndim != 2 or rows.shape[1] != 5 or not 2 <= len(rows) <= 512
            or not np.isfinite(rows).all() or np.any(np.diff(rows[:, 0]) <= 0)
            or np.any(rows[:, 3:] <= 0)):
        raise ValueError("Ordered finite sections and positive half extents required")
    if (type(segments) is not int or not 16 <= segments <= 1024 or segments % 4
            or not isinstance(exponent, (int, float)) or isinstance(exponent, bool)
            or not np.isfinite(exponent) or not 2 <= exponent <= 8):
        raise ValueError("Exponent 2..8 and quadrant-aligned sampling required")
    offset = np.array(geometry.vector(origin))
    theta = np.arange(segments) * (2*np.pi/segments)
    cosine, sine = np.cos(theta), np.sin(theta)
    # Exact cardinal axes prevent tiny floating-point signed-power offsets.
    cosine[np.abs(cosine) < 1e-12] = 0
    sine[np.abs(sine) < 1e-12] = 0
    x = np.sign(cosine)*np.abs(cosine)**(2/exponent)
    y = np.sign(sine)*np.abs(sine)**(2/exponent)
    vertices = np.concatenate([
        np.column_stack((cx+hx*x, cy+hy*y, np.full(segments, z)))+offset
        for z,cx,cy,hx,hy in rows])
    faces = [list(reversed(range(segments)))]
    for row in range(len(rows)-1):
        for i in range(segments):
            a, b = row*segments+i, row*segments+(i+1)%segments
            faces.append([a, b, b+segments, a+segments])
    faces.append(list(range((len(rows)-1)*segments, len(vertices))))
    result = enclosure._mesh(name, vertices.tolist(), faces)
    enclosure._valid(result)
    result.data.polygons[0].use_smooth = False
    result.data.polygons[-1].use_smooth = False
    result["mw_section_stock"] = json.dumps({
        "sections": rows.tolist(), "exponent": exponent,
        "segments": segments, "origin": offset.tolist()})
    return result
