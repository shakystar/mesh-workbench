"""Explicit camera registration from known 3D/2D correspondences.

Photo annotations alone do not supply 3D truth. Coordinates and metric scale
must have independent provenance. Distortion is unsupported and must be stated.
"""

import copy
import hashlib
import json

import numpy as np


def _array(value, shape, label):
    a = np.asarray(value, dtype=float)
    if a.shape != shape or not np.isfinite(a).all():
        raise ValueError("Invalid " + label)
    return a


def _normalize(points):
    center = points.mean(axis=0)
    distance = np.linalg.norm(points - center, axis=1).mean()
    if distance < 1e-9:
        raise ValueError("Degenerate calibration points")
    scale = np.sqrt(points.shape[1]) / distance
    matrix = np.eye(points.shape[1] + 1)
    matrix[:-1, :-1] *= scale
    matrix[:-1, -1] = -center * scale
    return (points - center) * scale, matrix


def project(camera, points):
    xyz = np.asarray(points, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("Finite 3D points required")
    p = _array(camera["matrix"], (3, 4), "projection matrix")
    q = np.column_stack((xyz, np.ones(len(xyz)))) @ p.T
    if np.any(q[:, 2] <= 1e-9):
        raise ValueError("Points behind camera or on projection plane")
    return q[:, :2] / q[:, 2, None]


def register(spec):
    """Normalized DLT for perspective; affine fit with metric camera checks.

    At least six fitting points and two held-out points are mandatory. The
    held-out values never enter fitting. A bad residual rejects registration.
    """
    spec = copy.deepcopy(spec)
    kind = spec.get("projection")
    if kind not in ("perspective", "orthographic"):
        raise ValueError("Explicit projection model required")
    if spec.get("distortion") != "none":
        raise ValueError("Only explicitly undistorted references supported")
    if (
        not isinstance(spec.get("coordinate_provenance"), str)
        or not spec["coordinate_provenance"].strip()
    ):
        raise ValueError("Independent 3D coordinate provenance required")
    size = spec.get("size")
    if (
        not isinstance(size, list)
        or len(size) != 2
        or any(type(v) is not int or v < 16 or v > 16384 for v in size)
    ):
        raise ValueError("Invalid image size")
    bbox = _array(spec.get("bbox"), (4,), "object bounding box")
    if not (0 <= bbox[0] < bbox[2] <= size[0] and 0 <= bbox[1] < bbox[3] <= size[1]):
        raise ValueError("Bounding box outside image")
    metric = spec.get("metric", False)
    if type(metric) is not bool:
        raise ValueError("Metric flag must be boolean")
    if metric:
        scale = spec.get("scale_evidence", {})
        length = scale.get("length_mm", 0)
        if (
            not isinstance(length, (int, float))
            or not np.isfinite(length)
            or length <= 0
            or not scale.get("source")
        ):
            raise ValueError("Metric claims require independent scale evidence")
    rows = spec.get("landmarks", [])
    if len(rows) < 8:
        raise ValueError("At least six fit and two held-out landmarks required")
    names = [row.get("id") for row in rows]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(
        names
    ):
        raise ValueError("Unique landmark IDs required")
    if any(type(row.get("holdout")) is not bool for row in rows):
        raise ValueError("Explicit holdout flags required")
    xyz = _array([row["world"] for row in rows], (len(rows), 3), "world landmarks")
    uv = _array([row["pixel"] for row in rows], (len(rows), 2), "image landmarks")
    if np.any(uv < 0) or np.any(uv >= np.asarray(size)):
        raise ValueError("Landmarks outside image")
    fit = np.array([not row["holdout"] for row in rows])
    if fit.sum() < 6 or (~fit).sum() < 2:
        raise ValueError("At least six fit and two held-out landmarks required")
    if np.linalg.matrix_rank(xyz[fit] - xyz[fit].mean(axis=0)) < 3:
        raise ValueError("Noncoplanar fitting landmarks required")
    if np.linalg.matrix_rank(uv[fit] - uv[fit].mean(axis=0)) < 2:
        raise ValueError("Image landmarks must span two dimensions")
    x, tx = _normalize(xyz[fit])
    u, tu = _normalize(uv[fit])
    h = np.column_stack((x, np.ones(len(x))))
    if kind == "perspective":
        a = []
        for point, pixel in zip(h, u):
            a.extend(
                [
                    np.r_[point, np.zeros(4), -pixel[0] * point],
                    np.r_[np.zeros(4), point, -pixel[1] * point],
                ]
            )
        _, singular, vh = np.linalg.svd(a)
        if singular[-2] < singular[0] * 1e-8:
            raise ValueError("Underdetermined perspective calibration")
        p = np.linalg.inv(tu) @ vh[-1].reshape(3, 4) @ tx
        depths = np.column_stack((xyz[fit], np.ones(fit.sum()))) @ p[2]
        if depths.mean() < 0:
            p = -p
        p /= np.linalg.norm(p[2, :3])
        # Recover the intrinsic factors without SciPy (RQ via flipped QR).
        _, r = np.linalg.qr(np.flipud(p[:, :3]).T)
        intrinsic = np.fliplr(np.flipud(r.T))
        signs = np.diag(np.where(np.diag(intrinsic) < 0, -1.0, 1.0))
        intrinsic = intrinsic @ signs
        intrinsic /= intrinsic[2, 2]
        if (
            abs(intrinsic[0, 1]) > 0.01 * intrinsic[0, 0]
            or not 0.98 <= intrinsic[0, 0] / intrinsic[1, 1] <= 1.02
        ):
            raise ValueError("Camera requires unsupported skew or nonsquare pixels")
    else:
        affine = np.linalg.lstsq(h, u, rcond=None)[0].T
        p = np.linalg.inv(tu) @ np.vstack((affine, [0, 0, 0, 1])) @ tx
        axes = p[:2, :3]
        scales = np.linalg.norm(axes, axis=1)
        if (
            min(scales) < 1e-9
            or abs(np.dot(*axes)) > 0.01 * np.prod(scales)
            or not 0.98 <= scales[0] / scales[1] <= 1.02
        ):
            raise ValueError("Affine fit is not a square-pixel orthographic camera")
        intrinsic = None
    camera = {"projection": kind, "matrix": p.tolist(), "size": size, "metric": metric}
    predicted = project(camera, xyz)
    errors = np.linalg.norm(predicted - uv, axis=1)
    diagonal = np.linalg.norm(bbox[2:] - bbox[:2])
    residual = float(np.sqrt(np.mean(errors[~fit] ** 2)) / diagonal)
    if residual > 0.01:
        raise ValueError("Held-out reprojection RMS exceeds 1% of object diagonal")
    digest = hashlib.sha256(
        json.dumps(spec, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    return {
        "schema": 1,
        "reference_sha256": digest,
        "camera": camera,
        "intrinsic": None if intrinsic is None else intrinsic.tolist(),
        "fit_count": int(fit.sum()),
        "holdout_count": int((~fit).sum()),
        "holdout_rms_fraction": residual,
        "fit_rms_pixels": float(np.sqrt(np.mean(errors[fit] ** 2))),
        "landmarks": [
            {
                "id": name,
                "projected": point.tolist(),
                "error_pixels": float(error),
                "holdout": not bool(train),
            }
            for name, point, error, train in zip(names, predicted, errors, fit)
        ],
        "reference": spec,
    }


def compare(registration, world_points):
    """Compare candidate landmarks using an already frozen camera, never refit."""
    reference = registration["reference"]
    digest = hashlib.sha256(
        json.dumps(reference, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    if digest != registration["reference_sha256"]:
        raise ValueError("Reference changed after registration")
    # Recompute only to authenticate the saved camera; candidate points are not used.
    frozen = register(reference)
    if not np.allclose(
        frozen["camera"]["matrix"],
        registration["camera"]["matrix"],
        atol=1e-10,
        rtol=1e-10,
    ):
        raise ValueError("Frozen camera changed")
    ids = [row["id"] for row in reference["landmarks"]]
    if set(world_points) != set(ids):
        raise ValueError("Candidate landmark IDs must match reference")
    predicted = project(registration["camera"], [world_points[k] for k in ids])
    expected = np.array([row["pixel"] for row in reference["landmarks"]])
    error = np.linalg.norm(predicted - expected, axis=1)
    box = np.array(reference["bbox"])
    diagonal = np.linalg.norm(box[2:] - box[:2])
    return {
        "reference_sha256": digest,
        "count": len(ids),
        "rms_fraction": float(np.sqrt(np.mean(error**2)) / diagonal),
        "maximum_pixels": float(error.max()),
        "projected": predicted.tolist(),
        "ids": ids,
    }


def silhouette(objects, camera):
    """Ray-test evaluated meshes with the frozen projection (Blender only)."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    size = camera.get("size")
    if (
        not isinstance(size, list)
        or len(size) != 2
        or any(type(v) is not int or not 16 <= v <= 1024 for v in size)
    ):
        raise ValueError("Silhouette image size must be 16..1024")
    if (
        not objects
        or len(set(objects)) != len(objects)
        or any(o.type != "MESH" for o in objects)
    ):
        raise ValueError("Unique nonempty mesh targets required")
    matrix = _array(camera["matrix"], (3, 4), "projection matrix")
    xyz = []
    triangles = []
    for obj in objects:
        if any(
            m.show_render != m.show_viewport
            or (m.type == "SUBSURF" and m.levels != m.render_levels)
            for m in obj.modifiers
        ):
            raise ValueError("Matching viewport/render modifiers required")
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            offset = len(xyz)
            xyz.extend([list(obj.matrix_world @ v.co) for v in mesh.vertices])
            triangles.extend(
                [[offset + v for v in t.vertices] for t in mesh.loop_triangles]
            )
        finally:
            evaluated.to_mesh_clear()
    if not triangles:
        raise ValueError("Empty evaluated geometry")
    xyz = np.asarray(xyz)
    tree = BVHTree.FromPolygons(xyz.tolist(), triangles, all_triangles=True)
    x, y = np.meshgrid(np.arange(size[0]) + 0.5, np.arange(size[1]) + 0.5)
    pixels = np.column_stack((x.ravel(), y.ravel(), np.ones(x.size)))
    if camera.get("projection") == "perspective":
        if np.linalg.matrix_rank(matrix[:, :3]) != 3:
            raise ValueError("Singular perspective camera")
        inverse = np.linalg.inv(matrix[:, :3])
        center = -inverse @ matrix[:, 3]
        origins = np.broadcast_to(center, (len(pixels), 3))
        directions = pixels @ inverse.T
    elif camera.get("projection") == "orthographic":
        if not np.allclose(matrix[2], [0, 0, 0, 1], atol=1e-8):
            raise ValueError("Invalid orthographic projection")
        axes = matrix[:2, :3]
        if np.linalg.matrix_rank(axes) != 2:
            raise ValueError("Singular orthographic camera")
        direction = np.cross(axes[0], axes[1])
        direction /= np.linalg.norm(direction)
        origins = (pixels[:, :2] - matrix[:2, 3]) @ np.linalg.pinv(axes).T
        start = float((xyz @ direction).min() - 1)
        origins += start * direction
        directions = np.broadcast_to(direction, (len(pixels), 3)).copy()
    else:
        raise ValueError("Explicit projection type required")
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    actual = np.array(
        [
            tree.ray_cast(Vector(o), Vector(d))[0] is not None
            for o, d in zip(origins, directions)
        ],
        dtype=bool,
    )
    return actual.reshape(size[1], size[0])


def compare_masks(actual, expected, visible, bbox):
    """Score only declared visible pixels; contour excludes occlusion borders."""
    actual, expected, visible = map(np.asarray, (actual, expected, visible))
    if (
        actual.ndim != 2
        or actual.shape != expected.shape
        or actual.shape != visible.shape
        or any(m.dtype != bool for m in (actual, expected, visible))
        or max(actual.shape) > 1024
    ):
        raise ValueError("Matching boolean masks up to 1024 required")
    if (
        not visible.any()
        or not (actual & visible).any()
        or not (expected & visible).any()
    ):
        raise ValueError("Empty visible coverage")
    h, w = actual.shape
    box = _array(bbox, (4,), "object bounding box")
    if not (0 <= box[0] < box[2] <= w and 0 <= box[1] < box[3] <= h):
        raise ValueError("Invalid object bounding box")
    if any(
        m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()
        for m in (actual, expected)
    ):
        raise ValueError("Reference framing clips silhouette")
    safe = visible.copy()
    safe[1:] &= visible[:-1]
    safe[:-1] &= visible[1:]
    safe[:, 1:] &= visible[:, :-1]
    safe[:, :-1] &= visible[:, 1:]

    def boundary(mask):
        padded = np.pad(mask, 1)
        interior = (
            mask
            & padded[:-2, 1:-1]
            & padded[2:, 1:-1]
            & padded[1:-1, :-2]
            & padded[1:-1, 2:]
        )
        y, x = np.where(mask & ~interior & safe)
        return np.column_stack((x, y))

    a, b = boundary(actual), boundary(expected)
    if not len(a) or not len(b) or max(len(a), len(b)) > 20000:
        raise ValueError("Insufficient or excessive visible contour")

    def distance(p, q):
        return np.concatenate(
            [
                np.sqrt(((chunk[:, None, :] - q[None, :, :]) ** 2).sum(2).min(1))
                for chunk in np.array_split(p, max(1, (len(p) + 127) // 128))
            ]
        )

    distances = np.r_[distance(a, b), distance(b, a)]
    intersection = int((actual & expected & visible).sum())
    union = int(((actual | expected) & visible).sum())
    return {
        "iou": intersection / union,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "visible_pixels": int(visible.sum()),
        "excluded_pixels": int((~visible).sum()),
        "contour_samples": len(distances),
        "boundary_p95_pixels": float(np.percentile(distances, 95)),
        "boundary_p95_fraction": float(
            np.percentile(distances, 95) / np.linalg.norm(box[2:] - box[:2])
        ),
    }
