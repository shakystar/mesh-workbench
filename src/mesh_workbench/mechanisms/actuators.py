"""Absolute prismatic/radial mechanisms and sampled contact classification.

No simulation handlers or continuous-collision claims. Every sweep restores the
original Blender transform channels even if a pose or measurement raises.
"""

import hashlib
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Vector
from . import assembly, geometry, joints, sculpt

KEY = "mw_actuators"


def _shape(obj):
    h = hashlib.sha256(sculpt.topology(obj).encode())
    h.update(np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32).tobytes())
    return h.hexdigest()


def register(parts, channels, interlocks=None):
    """parts maps stable IDs to objects; channels contain limits/rest/vectors.

    Each vectors entry is world translation per unit of that channel. A part
    may participate in several channels, e.g. latch release plus battery slide.
    """
    if not parts or not channels:
        raise ValueError("Parts and channels required")
    if len(set(parts.values())) != len(parts):
        raise ValueError("Duplicate physical part")
    state = {
        "version": 1,
        "parts": {},
        "channels": channels,
        "interlocks": interlocks or [],
    }
    for key, name in parts.items():
        obj = assembly._object(name)
        sculpt.editable(obj)
        state["parts"][key] = {
            "object": name,
            "rest_matrix": [list(row) for row in obj.matrix_world],
            "shape": _shape(obj),
        }
    for name, c in channels.items():
        low, high = c["limits"]
        if low >= high:
            raise ValueError("Increasing travel range required")
        sculpt.number(c["rest"], low, high, "rest position")
        sculpt.number(c["max_step"], 1e-6, 1e4, "maximum travel step")
        if not c["vectors"] or set(c["vectors"]) - set(parts):
            raise ValueError("Unknown or empty actuator parts")
        for v in c["vectors"].values():
            if geometry.vector(v).length < 1e-8:
                raise ValueError("Nonzero actuator direction required")
    for rule in state["interlocks"]:
        if (
            set(rule) != {"channel", "above", "requires", "at_least"}
            or rule["channel"] not in channels
            or rule["requires"] not in channels
        ):
            raise ValueError("Invalid interlock")
    bpy.context.scene[KEY] = json.dumps(state, allow_nan=False)
    return {"parts": len(parts), "channels": list(channels)}


def load():
    state = json.loads(bpy.context.scene[KEY])
    for key, r in state["parts"].items():
        obj = assembly._object(r["object"])
        if _shape(obj) != r["shape"]:
            raise ValueError("Actuator part geometry changed: " + key)
    return state


def _values(state, values):
    channels = state["channels"]
    if set(values) - set(channels):
        raise ValueError("Unknown actuator channel")
    result = {k: values.get(k, c["rest"]) for k, c in channels.items()}
    for k, c in channels.items():
        sculpt.number(result[k], *c["limits"], k + " travel")
    for r in state["interlocks"]:
        if result[r["channel"]] > r["above"] and result[r["requires"]] < r["at_least"]:
            raise ValueError(
                "Actuator interlock: " + r["channel"] + " requires " + r["requires"]
            )
    return result


def _pose(state, values):
    values = _values(state, values)
    for key, r in state["parts"].items():
        delta = Vector((0, 0, 0))
        for k, c in state["channels"].items():
            if key in c["vectors"]:
                delta += Vector(c["vectors"][key]) * (values[k] - c["rest"])
        bpy.data.objects[r["object"]].matrix_world = Matrix.Translation(delta) @ Matrix(
            r["rest_matrix"]
        )
    bpy.context.view_layer.update()


def pose(values):
    state = load()
    _values(state, values)
    before = joints.snapshot([r["object"] for r in state["parts"].values()])
    try:
        _pose(state, values)
    except Exception:
        joints.restore(before)
        raise
    return before


def _probes(obj):
    x = sculpt.coordinates(obj)
    obj.data.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in obj.data.loop_triangles]
    edges = {tuple(sorted((a, b))) for t in triangles for a, b in zip(t, t[1:] + t[:1])}
    return (
        list(x)
        + [(x[a] + x[b]) / 2 for a, b in edges]
        + [x[list(t)].mean(axis=0) for t in triangles]
    )


def _inside(tree, point, bounds):
    """Three non-axis ray parity votes; disagreements reject the measurement."""
    p = np.asarray(point)
    if np.any(p < bounds[0] - 1e-6) or np.any(p > bounds[1] + 1e-6):
        return False, False
    votes = []
    epsilon = max(1e-6, float(np.max(np.abs(bounds))) * np.finfo(np.float32).eps * 16)
    if epsilon > 0.01:
        return False, True
    reach = float(np.linalg.norm(bounds[1] - bounds[0]) * 3 + 1)
    for raw in [(1, 0.371, 0.619), (0.293, 1, 0.537), (0.419, 0.257, 1)]:
        direction = Vector(raw).normalized()
        origin = Vector(point)
        hits = 0
        remaining = reach
        for _ in range(4096):
            location, normal, index, d = tree.ray_cast(origin, direction, remaining)
            if location is None:
                break
            hits += 1
            advance = float(d) + epsilon
            remaining -= advance
            if remaining <= 0:
                break
            origin = location + direction * epsilon
        else:
            return False, True
        votes.append(hits % 2 == 1)
    return votes[0], len(set(votes)) != 1


def _winding(triangles, point):
    v = triangles - np.asarray(point, dtype=np.float64)
    lengths = np.linalg.norm(v, axis=2)
    numerator = np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2]))
    denominator = np.prod(lengths, axis=1)
    denominator += np.einsum("ij,ij->i", v[:, 0], v[:, 1]) * lengths[:, 2]
    denominator += np.einsum("ij,ij->i", v[:, 1], v[:, 2]) * lengths[:, 0]
    denominator += np.einsum("ij,ij->i", v[:, 2], v[:, 0]) * lengths[:, 1]
    winding = abs(float(np.arctan2(numerator, denominator).sum() / (2 * math.pi)))
    if winding < 1e-4:
        return False, False
    if abs(winding - 1) < 1e-4:
        return True, False
    return False, True


def pair(a, b, minimum=0.2, contact=None):
    """Bidirectional vertex/edge/face probes and triangle-overlap candidates.

    Ray parity detects sampled containment; nearest-face distance measures depth.
    Contact has an explicit maximum sampled penetration; it never ignores a pair.
    """
    minimum = sculpt.number(minimum, 0, 10000, "minimum clearance")
    if a == b:
        raise ValueError("Distinct contact solids required")
    xa, xb = sculpt.coordinates(a), sculpt.coordinates(b)
    separation = np.maximum(
        0, np.maximum(xa.min(axis=0) - xb.max(axis=0), xb.min(axis=0) - xa.max(axis=0))
    )
    lower = float(np.linalg.norm(separation))
    if not contact and lower >= minimum:
        return {
            "passed": True,
            "category": "noncontact clearance",
            "minimum_distance": lower,
            "distance_kind": "AABB lower bound",
            "maximum_sampled_penetration": 0.0,
            "triangle_pairs": 0,
            "probes": 0,
            "missing": 0,
            "nearest_probe": None,
            "objects": [a.name, b.name],
        }
    ta, tb = assembly._tree(a), assembly._tree(b)
    overlaps = ta.overlap(tb)
    distance = float("inf")
    penetration = 0.0
    missing = 0
    ambiguous = 0
    samples = 0
    point = None
    for source, target, target_obj, bounds in (
        (a, tb, b, (xb.min(axis=0), xb.max(axis=0))),
        (b, ta, a, (xa.min(axis=0), xa.max(axis=0))),
    ):
        triangles = None
        probes = np.asarray(_probes(source), dtype=np.float64)
        # Bounds provide a conservative distance for every skipped probe. They
        # cannot hide containment or a clearance violation inside the box.
        lower_bounds = np.linalg.norm(
            np.maximum(0, np.maximum(bounds[0] - probes, probes - bounds[1])), axis=1
        )
        nearby = lower_bounds <= max(minimum, 0.01) + 1e-5
        samples += len(probes)
        if np.any(~nearby):
            index = int(np.argmin(np.where(nearby, np.inf, lower_bounds)))
            if lower_bounds[index] < distance:
                distance = float(lower_bounds[index])
                point = probes[index].tolist()
        for p in probes[nearby]:
            hit, n, index, d = target.find_nearest(Vector(p))
            if hit is None:
                missing += 1
                continue
            if d < distance:
                distance = float(d)
                point = list(p)
            if d > 1e-5:
                inside, uncertain = _inside(target, p, bounds)
                if uncertain:
                    if triangles is None:
                        target_obj.data.calc_loop_triangles()
                        x = sculpt.coordinates(target_obj)
                        triangles = x[
                            [list(t.vertices) for t in target_obj.data.loop_triangles]
                        ]
                    inside, uncertain = _winding(triangles, p)
                ambiguous += int(uncertain)
                if inside:
                    penetration = max(penetration, float(d))
    if contact:
        passed = (
            missing == 0
            and ambiguous == 0
            and penetration <= contact["max_penetration"] + 1e-5
            and distance <= contact.get("max_separation", 0.01) + 1e-5
        )
        category = "intentional contact"
    else:
        passed = (
            missing == 0
            and ambiguous == 0
            and not overlaps
            and penetration <= 1e-5
            and distance >= minimum - 1e-5
        )
        category = "noncontact clearance"
    return {
        "passed": bool(passed),
        "category": category,
        "minimum_distance": distance,
        "distance_kind": "measured or conservative AABB lower bound",
        "maximum_sampled_penetration": penetration,
        "triangle_pairs": len(overlaps),
        "probes": samples,
        "missing": missing,
        "ambiguous": ambiguous,
        "nearest_probe": point,
        "objects": [a.name, b.name],
    }


def sweep(channel, start, end, pairs, base=None, step=None, contacts=None):
    state = load()
    if channel not in state["channels"]:
        raise ValueError("Unknown actuator channel")
    c = state["channels"][channel]
    step = (
        c["max_step"]
        if step is None
        else sculpt.number(step, 1e-6, c["max_step"], "travel step")
    )
    _values(state, {**(base or {}), channel: start})
    _values(state, {**(base or {}), channel: end})
    if not pairs or any(
        a == b or a not in state["parts"] or b not in state["parts"] for a, b in pairs
    ):
        raise ValueError("Distinct registered collision pairs required")
    contacts = contacts or []
    for rule in contacts:
        if tuple(rule["parts"]) not in [tuple(p) for p in pairs]:
            raise ValueError("Unknown contact pair")
        sculpt.number(rule["max_penetration"], 0, 0.01, "contact penetration")
    count = max(1, math.ceil(abs(end - start) / step))
    samples = []
    before = joints.snapshot([r["object"] for r in state["parts"].values()])
    try:
        for i in range(count + 1):
            value = start + (end - start) * i / count
            _pose(state, {**(base or {}), channel: value})
            results = []
            for a, b in pairs:
                active = [
                    r
                    for r in contacts
                    if list(r["parts"]) == [a, b] and abs(value - r["at"]) <= 1e-7
                ]
                if len(active) > 1:
                    raise ValueError("Ambiguous contact rule")
                result = pair(
                    bpy.data.objects[state["parts"][a]["object"]],
                    bpy.data.objects[state["parts"][b]["object"]],
                    contact=active[0] if active else None,
                )
                result["parts"] = [a, b]
                results.append(result)
            samples.append(
                {
                    "value": value,
                    "passed": all(r["passed"] for r in results),
                    "pairs": results,
                }
            )
    finally:
        joints.restore(before)
    return {
        "passed": all(s["passed"] for s in samples),
        "channel": channel,
        "intervals": count,
        "step": abs(end - start) / count,
        "samples": samples,
        "rest_restored": joints.snapshot(list(before)) == before,
        "method": "discrete triangle overlap; bidirectional vertices, edge midpoints and triangle centroids; three-ray parity containment with float64 solid-angle fallback",
        "limits": "Sampled geometry and penetration, not continuous collision or a global minimum-distance proof.",
    }
