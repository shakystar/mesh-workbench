"""Persisted rigid group hinges; sampled cross-group and fixed-part interference."""

import json
import math
from itertools import combinations
import bpy
from mathutils import Matrix, Vector
from . import geometry, sculpt, assembly

KEY = "mw_hinge_joints"
CHANNELS = (
    "location",
    "rotation_euler",
    "rotation_quaternion",
    "rotation_axis_angle",
    "scale",
)


def register(joints):
    if not 1 <= len(joints) <= 32:
        raise ValueError("Expected 1..32 hinge joints")
    joints = json.loads(json.dumps(joints))
    seen = set()
    for joint in joints:
        axis = geometry.vector(joint["axis"])
        geometry.vector(joint["pivot"])
        low, high = joint["limits"]
        if (
            axis.length < 1e-8
            or not math.isfinite(low + high)
            or low > 0
            or high < 0
            or low >= high
        ):
            raise ValueError("Finite hinge range containing zero required")
        if not joint["objects"]:
            raise ValueError("Empty hinge group")
        joint["rest_matrices"] = {}
        for name in joint["objects"]:
            if name in seen:
                raise ValueError("Object belongs to multiple hinges")
            obj = assembly._object(name)
            seen.add(name)
            joint["rest_matrices"][name] = [list(row) for row in obj.matrix_world]
    if len({j["name"] for j in joints}) != len(joints):
        raise ValueError("Duplicate hinge name")
    bpy.context.scene[KEY] = json.dumps(joints)
    return {"joints": len(joints), "objects": len(seen)}


def _plan(angles):
    joints = json.loads(bpy.context.scene[KEY])
    if set(angles) != {j["name"] for j in joints}:
        raise ValueError("One angle per registered hinge required")
    for j in joints:
        value = angles[j["name"]]
        sculpt.number(value, j["limits"][0], j["limits"][1], "hinge angle")
        for name in j["objects"]:
            assembly._object(name)
    return joints


def snapshot(names):
    return {
        name: {k: tuple(getattr(bpy.data.objects[name], k)) for k in CHANNELS}
        for name in names
    }


def restore(state):
    for name, channels in state.items():
        obj = bpy.data.objects[name]
        for k, v in channels.items():
            setattr(obj, k, v)
    bpy.context.view_layer.update()


def pose(angles):
    joints = _plan(angles)
    state = snapshot([name for j in joints for name in j["objects"]])
    try:
        for j in joints:
            p = Vector(j["pivot"])
            matrix = (
                Matrix.Translation(p)
                @ Matrix.Rotation(angles[j["name"]], 4, Vector(j["axis"]))
                @ Matrix.Translation(-p)
            )
            for name in j["objects"]:
                obj = bpy.data.objects[name]
                obj.matrix_world = matrix @ Matrix(j["rest_matrices"][name])
        bpy.context.view_layer.update()
        return state
    except Exception:
        restore(state)
        raise


def inspect(angles, fixed, steps=24, ignore_pairs=None, probe_limit=128):
    plan = _plan(angles)
    if type(steps) is not int or not 1 <= steps <= 360:
        raise ValueError("Invalid hinge intervals")
    if type(probe_limit) is not int or not 16 <= probe_limit <= 4096:
        raise ValueError("Invalid probe limit")
    groups = [j["objects"] for j in plan]
    moving = [name for group in groups for name in group]
    if len(set(fixed)) != len(fixed) or set(moving) & set(fixed):
        raise ValueError("Fixed and moving parts must be distinct")
    for name in fixed:
        assembly._object(name)
    pairs = [(a, b) for group in groups for a in group for b in fixed]
    for ga, gb in combinations(groups, 2):
        pairs.extend((a, b) for a in ga for b in gb)
    ignored = {tuple(sorted(p)) for p in (ignore_pairs or [])}
    if not ignored.issubset({tuple(sorted(p)) for p in pairs}):
        raise ValueError("Unknown ignored interface")
    pairs = [p for p in pairs if tuple(sorted(p)) not in ignored]
    if not pairs:
        raise ValueError("No hinge collision pairs")
    initial = snapshot(moving)
    samples = []
    try:
        for i in range(steps + 1):
            restore(initial)
            pose({name: value * i / steps for name, value in angles.items()})
            names = set(n for p in pairs for n in p)
            coords = {n: sculpt.coordinates(bpy.data.objects[n]) for n in names}
            trees = {n: assembly._tree(bpy.data.objects[n]) for n in names}
            hits = []
            minimum = float("inf")
            near = None
            for a, b in pairs:
                overlaps = trees[a].overlap(trees[b])
                if overlaps:
                    hits.append(
                        {
                            "objects": [a, b],
                            "triangle_pairs": len(overlaps),
                            "preview": [list(p) for p in overlaps[:8]],
                        }
                    )
                stride = max(1, math.ceil(len(coords[a]) / probe_limit))
                for point in coords[a][::stride]:
                    distance = trees[b].find_nearest(Vector(point))[3]
                    if distance < minimum:
                        minimum = distance
                        near = {"objects": [a, b], "position": point.tolist()}
            samples.append(
                {
                    "fraction": i / steps,
                    "passed": not hits,
                    "collisions": hits,
                    "sampled_clearance": minimum,
                    "nearest_probe": near,
                }
            )
    finally:
        restore(initial)
    return {
        "passed": all(s["passed"] for s in samples),
        "steps": steps,
        "angles": angles,
        "angular_step_max": max(abs(v) for v in angles.values()) / steps,
        "pairs": len(pairs),
        "ignored_interfaces": [list(p) for p in sorted(ignored)],
        "samples": samples,
        "minimum_sampled_clearance": min(s["sampled_clearance"] for s in samples),
        "limits": "Discrete triangle-overlap candidates and sampled vertex distances; not continuous collision or full containment testing",
    }
