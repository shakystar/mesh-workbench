"""Independent outline/section and actual surface-junction measurements."""

import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    nested,
    reference,
    sections,
    sculpt,
    assembly,
    geometry,
    fairing,
)


def drawing(spec, parameters):
    # Independently dense quadratic drawing, not mesh vertices or builder output.
    p = np.array(spec["envelope"]["profile_xz"], dtype=float)
    t = np.clip((140 - p[:, 1]) / 40, 0, 1)
    p[:, 1] -= parameters["grip_length"] * t * t * (3 - 2 * t)
    corners = []
    for i, q in enumerate(p):
        before = p[(i - 1) % len(p)] - q
        after = p[(i + 1) % len(p)] - q
        trim = min(
            spec["envelope"]["corner_trim"],
            0.45 * np.linalg.norm(before),
            0.45 * np.linalg.norm(after),
        )
        corners.append(
            (
                q + before / np.linalg.norm(before) * trim,
                q,
                q + after / np.linalg.norm(after) * trim,
            )
        )
    points = []
    for i, (a, b, c) in enumerate(corners):
        for t in np.linspace(0, 1, 128, endpoint=False):
            points.append(a * (1 - t) ** 2 + b * (2 * t * (1 - t)) + c * t * t)
        points.append(c)
    return np.array(points)


def x_limits(profile, z):
    values = []
    for a, b in zip(profile, np.roll(profile, -1, axis=0)):
        if min(a[1], b[1]) <= z < max(a[1], b[1]):
            values.append(float(a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1])))
    if len(values) != 2:
        raise ValueError("Ambiguous authored section")
    return min(values), max(values)


def verify(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(
        (ROOT / "examples/drill-assembly-target.json").read_text(encoding="utf-8")
    )
    state = nested.load()
    params = state["parameters"]
    objects = {k: bpy.data.objects[r["object"]] for k, r in state["outputs"].items()}
    master = objects["master"]
    profile = drawing(spec, params)
    g = spec["gates"]
    view = {
        "size": [512, 640],
        "bounds": [-72, 57, 30, 198],
        "horizontal": [1, 0, 0],
        "vertical": [0, 0, 1],
        "direction": [0, 1, 0],
        "depth": [-60, 60],
    }
    actual = reference.mesh_mask(master, view)
    expected = reference.target_mask(
        view, [{"kind": "polygon", "points": profile.tolist()}]
    )
    silhouette = reference.compare(actual, expected, view)
    silhouette["passed"] = silhouette["iou"] >= g["side_silhouette_iou"]
    reference.save_overlay(out / "silhouette.png", actual, expected)
    cuts = []
    for z in [65, 85, 105, 125, 145, 165, 180]:
        lo, hi = x_limits(profile, z)
        a, b = spec["envelope"]["transition_z"]
        t = np.clip((z - a) / (b - a), 0, 1)
        t = t * t * (3 - 2 * t)
        half = (spec["envelope"]["grip_half_width"] + params["grip_width"] / 2) * (
            1 - t
        ) + spec["envelope"]["head_half_width"] * t
        section = sections.cut(master, 2, z)
        report = sections.compare(section, [[lo, -half, z], [hi, half, z]])
        report["passed"] = report["bound_error_max"] <= g["section_error"]
        cuts.append(report)
        sculpt.dump(out / ("section-" + str(z) + ".json"), section)
    # Paired actual surface probes on both sides of the two width-transition
    # boundaries. The envelope is welded, not two overlapping solids.
    tree = assembly._tree(master)
    joins = []
    for z in spec["envelope"]["transition_z"]:
        lo, hi = x_limits(profile, z)
        for x in np.linspace(lo + 6, hi - 6, 9):
            for side in [-1, 1]:
                hits = [
                    tree.ray_cast(
                        Vector((x, side * 60, z + dz)), Vector((0, -side, 0)), 120
                    )
                    for dz in [-0.001, 0.001]
                ]
                if any(h[0] is None for h in hits):
                    joins.append({"passed": False, "reason": "junction probe missed"})
                    continue
                position = (hits[0][0] - hits[1][0]).length
                angle = math.degrees(
                    math.acos(float(np.clip(hits[0][1].dot(hits[1][1]), -1, 1)))
                )
                joins.append(
                    {
                        "x": float(x),
                        "z": z,
                        "side": side,
                        "position_gap": position,
                        "normal_degrees": angle,
                        "passed": position <= g["junction_position"]
                        and angle <= g["junction_normal_degrees"],
                    }
                )
    solids = {}
    for key, obj in objects.items():
        if not state["nodes"][key].get("visible", True):
            continue
        result = geometry.inspect(obj)
        result["overlap_candidates"] = fairing.overlap_candidates(obj)
        result["passed"] = (
            result["finite"]
            and result["nonmanifold_edges"] == 0
            and result["overlap_candidates"] == 0
        )
        solids[key] = result
    # Native axis-aligned mechanical geometry is measured in the declared frame.
    frames = []
    for key in ["torque_ring", "chuck_body", "jaw_cage", "bit"]:
        x = sculpt.coordinates(objects[key])
        center = (x.min(axis=0) + x.max(axis=0)) / 2
        expected = np.array(spec["parts"][key]["frame"]["origin"], dtype=float)
        radial_error = float(np.linalg.norm(center[1:] - expected[1:]))
        frames.append(
            {
                "part": key,
                "radial_axis_error": radial_error,
                "passed": radial_error <= g["frame_position"],
            }
        )
    report = {
        "passed": silhouette["passed"]
        and all(c["passed"] for c in cuts)
        and all(j["passed"] for j in joins)
        and all(r["passed"] for r in solids.values())
        and all(r["passed"] for r in frames),
        "parameters": params,
        "silhouette": silhouette,
        "sections": cuts,
        "junction_samples": joins,
        "solids": solids,
        "frames": frames,
        "limits": "Raster outline; sampled section bounds, junction normals and radial frame centers. Additional mating, travel and reopening evidence is required.",
    }
    sculpt.dump(out / "geometry.json", report)
    print(
        "GEOMETRY",
        report["passed"],
        "IoU",
        silhouette["iou"],
        "section max",
        max(c["bound_error_max"] for c in cuts),
        "junction max",
        max(j.get("normal_degrees", 180) for j in joins),
        flush=True,
    )
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    source = Path(args[0]).resolve()
    out = Path(args[1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    verify(out)
