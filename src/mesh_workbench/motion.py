"""Discrete rigid-motion surface interference and sampled clearance reports."""

import math
import bpy
from mathutils import Matrix, Vector
from . import assembly, geometry, sculpt


def inspect(
    moving,
    obstacles,
    translation=(0, 0, 0),
    axis=(1, 0, 0),
    angle=0,
    pivot=None,
    steps=16,
    probe_limit=512,
    minimum=0,
):
    sculpt.editable(moving)
    if moving in obstacles or not obstacles:
        raise ValueError("Distinct moving part and obstacles required")
    if type(steps) is not int or not 1 <= steps <= 720:
        raise ValueError("Expected 1..720 motion intervals")
    if type(probe_limit) is not int or not 16 <= probe_limit <= 100000:
        raise ValueError("Expected 16..100000 clearance probes")
    translation = geometry.vector(translation)
    axis = geometry.vector(axis)
    if axis.length < 1e-8:
        raise ValueError("Invalid rotation axis")
    angle = sculpt.number(angle, -math.tau * 10, math.tau * 10, "rotation radians")
    minimum = sculpt.number(minimum, 0, 1e5, "minimum clearance")
    original = moving.matrix_world.copy()
    transform = {
        name: tuple(getattr(moving, name))
        for name in (
            "location",
            "rotation_euler",
            "rotation_quaternion",
            "rotation_axis_angle",
            "scale",
        )
    }

    pivot = (
        moving.matrix_world.translation.copy()
        if pivot is None
        else geometry.vector(pivot)
    )
    trees = [(obj, assembly._tree(obj)) for obj in obstacles]
    reports = []
    try:
        for i in range(steps + 1):
            t = i / steps
            moving.matrix_world = (
                Matrix.Translation(translation * t)
                @ Matrix.Translation(pivot)
                @ Matrix.Rotation(angle * t, 4, axis)
                @ Matrix.Translation(-pivot)
                @ original
            )
            bpy.context.view_layer.update()
            tree = assembly._tree(moving)
            coords = sculpt.coordinates(moving)
            stride = max(1, math.ceil(len(coords) / probe_limit))
            probes = coords[::stride]
            moving.data.calc_loop_triangles()
            for obstacle, target in trees:
                overlaps = tree.overlap(target)
                distances = [target.find_nearest(Vector(p))[3] for p in probes]
                j = min(range(len(distances)), key=distances.__getitem__)
                reports.append(
                    {
                        "fraction": t,
                        "obstacle": obstacle.name,
                        "triangle_pairs": len(overlaps),
                        "overlap_triangle_pairs_preview": [
                            list(pair) for pair in overlaps[:32]
                        ],
                        "moving_triangle_centers_preview": [
                            coords[list(moving.data.loop_triangles[a].vertices)]
                            .mean(axis=0)
                            .tolist()
                            for a, _ in overlaps[:32]
                        ],
                        "sampled_clearance": distances[j],
                        "position": probes[j].tolist(),
                        "probes": len(probes),
                        "passed": not overlaps and distances[j] >= minimum,
                    }
                )
    finally:
        for name, values in transform.items():
            setattr(moving, name, values)
        bpy.context.view_layer.update()
    return {
        "passed": all(r["passed"] for r in reports),
        "steps": steps,
        "translation_step": translation.length / steps,
        "angle_step": abs(angle) / steps,
        "minimum_sampled_clearance": min(r["sampled_clearance"] for r in reports),
        "samples": reports,
        "method": "discrete triangle overlaps and sampled vertex distances",
        "limits": "Not continuous collision detection; no full-containment test; sampled distance is not global minimum",
    }
