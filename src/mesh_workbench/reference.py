"""Fixed orthographic component masks against authored analytic drawings.

Independent of lighting/materials and scene occlusion. Pixel-center sampling;
boundary distances are raster estimates, not continuous surface certificates.
"""

import hashlib
import json
import numpy as np


def fingerprint(spec):
    return hashlib.sha256(
        json.dumps(spec, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def grid(view):
    size = view["size"]
    if len(size) != 2 or any(type(v) is not int or not 16 <= v <= 1024 for v in size):
        raise ValueError("Reference size must be 16..1024")
    w, h = size
    bounds = np.asarray(view["bounds"], dtype=float)
    if bounds.shape != (4,) or not np.isfinite(bounds).all():
        raise ValueError("Invalid bounds")
    x0, x1, y0, y1 = bounds
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Empty bounds")
    axes = np.asarray(
        [view[k] for k in ("horizontal", "vertical", "direction")], dtype=float
    )
    if (
        axes.shape != (3, 3)
        or not np.isfinite(axes).all()
        or not np.allclose(axes @ axes.T, np.eye(3), atol=1e-7)
    ):
        raise ValueError("Orthonormal reference axes required")
    depth = np.asarray(view["depth"], dtype=float)
    if depth.shape != (2,) or not np.isfinite(depth).all() or depth[1] <= depth[0]:
        raise ValueError("Invalid depth interval")
    x, y = np.meshgrid(
        x0 + (np.arange(w) + 0.5) * (x1 - x0) / w,
        y1 - (np.arange(h) + 0.5) * (y1 - y0) / h,
    )
    return x, y, axes, depth


def target_mask(view, shapes):
    x, y, _, _ = grid(view)
    result = np.zeros(x.shape, dtype=bool)
    if not shapes:
        raise ValueError("Empty target")
    for s in shapes:
        center = np.asarray(s["center"], dtype=float)
        radius = float(s["radius"])
        if (
            center.shape != (2,)
            or not np.isfinite(center).all()
            or not np.isfinite(radius)
            or radius <= 0
        ):
            raise ValueError("Invalid target shape")
        dx, dy = np.abs(x - center[0]), np.abs(y - center[1])
        if s["kind"] == "circle":
            inside = dx * dx + dy * dy <= radius * radius
        elif s["kind"] == "rounded_rect":
            size = np.asarray(s["size"], dtype=float)
            if (
                size.shape != (2,)
                or not np.isfinite(size).all()
                or min(size) <= 0
                or radius > min(size) / 2
            ):
                raise ValueError("Invalid rounded rectangle")
            qx, qy = dx - size[0] / 2 + radius, dy - size[1] / 2 + radius
            distance = (
                np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
                + np.minimum(np.maximum(qx, qy), 0)
                - radius
            )
            inside = distance <= 0
        else:
            raise ValueError("Unknown target shape")
        result = result & ~inside if s.get("subtract", False) else result | inside
    if not result.any():
        raise ValueError("Target has no sampled coverage")
    return result


def mesh_mask(obj, view):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    x, y, axes, depth = grid(view)
    if obj.type != "MESH":
        raise ValueError("Mesh required")
    if any(
        m.show_render != m.show_viewport
        or (m.type == "SUBSURF" and m.levels != m.render_levels)
        for m in obj.modifiers
    ):
        raise ValueError("Reference requires matching render/viewport modifiers")
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        if not triangles:
            raise ValueError("Empty evaluated mesh")
        tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    finally:
        ev.to_mesh_clear()
    origins = x[..., None] * axes[0] + y[..., None] * axes[1] + depth[0] * axes[2]
    direction = Vector(axes[2])
    return np.array(
        [
            tree.ray_cast(Vector(p), direction, float(depth[1] - depth[0]))[0]
            is not None
            for p in origins.reshape(-1, 3)
        ],
        dtype=bool,
    ).reshape(x.shape)


def _boundary(mask, view):
    padded = np.pad(mask, 1)
    interior = (
        mask
        & padded[:-2, 1:-1]
        & padded[2:, 1:-1]
        & padded[1:-1, :-2]
        & padded[1:-1, 2:]
    )
    x, y, _, _ = grid(view)
    edge = mask & ~interior
    return np.column_stack((x[edge], y[edge]))


def compare(actual, expected, view):
    grid(view)
    actual, expected = np.asarray(actual), np.asarray(expected)
    if (
        actual.dtype != bool
        or expected.dtype != bool
        or actual.shape != tuple(reversed(view["size"]))
        or expected.shape != actual.shape
    ):
        raise ValueError("Boolean masks matching view required")
    if not actual.any() or not expected.any():
        raise ValueError("Cannot score empty coverage")
    # Reject truncated masks: high IoU on a cropped fragment is misleading.
    if any(
        m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()
        for m in (actual, expected)
    ):
        raise ValueError("Reference framing clips silhouette")
    a, b = _boundary(actual, view), _boundary(expected, view)
    if max(len(a), len(b)) > 20000:
        raise ValueError("Boundary exceeds comparison budget; use a smaller view")

    def nearest(p, q):
        return np.concatenate(
            [
                np.sqrt(((chunk[:, None, :] - q[None, :, :]) ** 2).sum(2).min(1))
                for chunk in np.array_split(p, max(1, (len(p) + 127) // 128))
            ]
        )

    distances = np.concatenate((nearest(a, b), nearest(b, a)))
    return {
        "iou": float((actual & expected).sum() / (actual | expected).sum()),
        "different_pixels": int((actual ^ expected).sum()),
        "boundary_mean": float(distances.mean()),
        "boundary_p95": float(np.percentile(distances, 95)),
        "boundary_max": float(distances.max()),
        "sample_count": int(len(distances)),
    }


def evaluate(obj, spec, component, supersample=1):
    if spec.get("version") != 1:
        raise ValueError("Unsupported target version")
    c = spec["components"][component]
    if type(supersample) is not int or not 1 <= supersample <= 4:
        raise ValueError("Supersample must be 1..4")
    view = dict(spec["views"][c["view"]])
    view["size"] = [n * supersample for n in view["size"]]
    expected, actual = target_mask(view, c["shapes"]), mesh_mask(obj, view)
    report = compare(actual, expected, view)
    report.update(
        object=obj.name,
        component=component,
        target_sha256=fingerprint(spec),
        sampling_size=view["size"],
    )
    return report, actual, expected


def save_overlay(path, actual, expected):
    """Save a diagnostic PNG: agreement gray, excess orange, missing blue."""
    import bpy

    if actual.shape != expected.shape:
        raise ValueError("Mismatched masks")
    h, w = actual.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = [0.035, 0.045, 0.065]
    rgba[actual & expected, :3] = [0.42, 0.5, 0.55]
    rgba[actual & ~expected, :3] = [1, 0.25, 0.05]
    rgba[expected & ~actual, :3] = [0.05, 0.5, 1]
    image = bpy.data.images.new("Reference diagnostic", width=w, height=h, alpha=True)
    try:
        image.pixels.foreach_set(rgba[::-1].ravel())
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
    finally:
        bpy.data.images.remove(image)
