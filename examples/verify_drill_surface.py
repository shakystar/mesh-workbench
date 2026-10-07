"""Measure actual surface rays against the frozen authored section constraints."""

import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import (
    nested,
    assembly,
    reference,
    sculpt,
    sections,
    geometry,
    fairing,
    quality,
    enclosure,
    mechanical,
)
from drill_assembly_geometry import drawing, x_limits, mechanical_frames


def verify(source, out):
    source = Path(source).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())
    state = nested.load()
    objects = {k: bpy.data.objects[v["object"]] for k, v in state["outputs"].items()}
    master = objects["master"]
    profile = drawing(spec, state["parameters"])
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
    sil = reference.compare(actual, expected, view)
    sil["passed"] = sil["iou"] >= spec["surface_phase"]["acceptance"]["outline_iou_min"]
    reference.save_overlay(out / "silhouette.png", actual, expected)
    reference_args = {
        k: v for k, v in spec["envelope"].items() if k != "section_controls"
    }
    reference_args.update(
        grip_width=state["parameters"]["grip_width"],
        grip_length=state["parameters"]["grip_length"],
    )
    unshaped = enclosure.create("Independent unwarped envelope", **reference_args)
    unshaped_tree = assembly._tree(unshaped)
    tree = assembly._tree(master)
    rays = []
    joins = []
    cuts = []
    rows = spec["envelope"]["section_controls"]["rows"]
    pins = spec["envelope"]["section_controls"]["pins"]
    length = state["parameters"]["grip_length"]

    def smooth(t):
        t = max(0, min(1, t))
        return t * t * (3 - 2 * t)

    def ease(t):
        t = max(0, min(1, t))
        return 6 * t**5 - 15 * t**4 + 10 * t**3

    for row in rows[1:-1]:
        original_z, rear, front, crown = row
        z = original_z - length * smooth((140 - original_z) / 40)
        lo, hi = x_limits(profile, z)
        cuts.append(sections.cut(master, 2, z))
        a, b = spec["envelope"]["transition_z"]
        t = smooth((z - a) / (b - a))
        base = (
            spec["envelope"]["grip_half_width"] + state["parameters"]["grip_width"] / 2
        ) * (1 - t) + spec["envelope"]["head_half_width"] * t
        if hi - lo < 14:
            continue
        for x in np.linspace(lo + 7, hi - 7, 7):
            u = (x - lo) / (hi - lo)
            delta = (1 - u) * rear + u * front + 4 * u * (1 - u) * crown
            for px, pz, fixed, release in pins:
                pz -= length * smooth((140 - pz) / 40)
                delta *= ease((math.hypot(x - px, z - pz) - fixed) / (release - fixed))
            for sign in [-1, 1]:
                p, n, _, _ = tree.ray_cast(
                    Vector((x, sign * 60, z)), Vector((0, -sign, 0)), 120
                )
                if p is None:
                    rays.append({"passed": False, "reason": "missing section ray"})
                    continue
                base_hit = unshaped_tree.ray_cast(
                    Vector((x, sign * 60, z)), Vector((0, -sign, 0)), 120
                )[0]
                if base_hit is None:
                    rays.append(
                        {"passed": False, "reason": "missing unwarped reference ray"}
                    )
                    continue
                expected_y = base_hit.y + sign * delta * (base_hit.y / base) ** 2
                error = float(abs(p.y - expected_y))
                rays.append(
                    {
                        "x": float(x),
                        "z": z,
                        "side": sign,
                        "expected_y": float(expected_y),
                        "actual_y": p.y,
                        "error": error,
                        "passed": error
                        <= spec["surface_phase"]["acceptance"][
                            "section_surface_error_max_mm"
                        ],
                    }
                )
                pair = [
                    tree.ray_cast(
                        Vector((x, sign * 60, z + dz)), Vector((0, -sign, 0)), 120
                    )
                    for dz in [-0.001, 0.001]
                ]
                if any(h[0] is None for h in pair):
                    joins.append({"passed": False, "reason": "missing transition ray"})
                    continue
                angle = math.degrees(
                    math.acos(float(np.clip(pair[0][1].dot(pair[1][1]), -1, 1)))
                )
                joins.append(
                    {
                        "x": float(x),
                        "z": z,
                        "side": sign,
                        "normal_degrees": angle,
                        "passed": angle
                        <= spec["surface_phase"]["acceptance"][
                            "normal_step_max_degrees"
                        ],
                    }
                )
    solids = {}
    for k, o in objects.items():
        if state["nodes"][k].get("visible", True):
            info = geometry.inspect(o)
            overlaps = fairing.overlap_candidates(o)
            solids[k] = {
                "nonmanifold_edges": info["nonmanifold_edges"],
                "overlap_candidates": overlaps,
                "passed": info["finite"]
                and info["nonmanifold_edges"] == 0
                and not overlaps,
            }
    curvature = quality.curvature(master)
    curvature.pop("values", None)
    frames = mechanical_frames(objects, spec, state)
    for key, part in spec["parts"].items():
        expected = json.loads(json.dumps(part["frame"]))
        for parameter, scale in spec["frame_z_parameter_rules"].get(key, {}).items():
            expected["origin"][2] += state["parameters"][parameter] * scale
        actual = state["outputs"][key]["frame"]
        frames.append(
            {
                "part": key,
                "declared_frame_matches": actual == expected,
                "passed": actual == expected,
            }
        )
    for key in ["battery_cover_0", "battery_cover_1"]:
        x = sculpt.coordinates(objects[key])
        center = (x.min(axis=0) + x.max(axis=0)) / 2
        error = float(
            np.linalg.norm(center - np.array(state["outputs"][key]["frame"]["origin"]))
        )
        frames.append(
            {
                "part": key,
                "actual_center_error": error,
                "passed": error <= spec["gates"]["frame_position"],
            }
        )
    units = {
        "system": bpy.context.scene.unit_settings.system,
        "scale_length": bpy.context.scene.unit_settings.scale_length,
    }
    units["passed"] = (
        units["system"] == "METRIC" and abs(units["scale_length"] - 0.001) < 1e-9
    )
    report = {
        "specification_revision": spec["revision"],
        "source_sha256": before,
        "frames": frames,
        "units": units,
        "silhouette": sil,
        "sections": rays,
        "junctions": joins,
        "solids": solids,
        "curvature_descriptive_only": curvature,
        "source_preserved": before == hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    report["passed"] = (
        units["passed"]
        and all(f["passed"] for f in frames)
        and sil["passed"]
        and bool(rays)
        and all(v["passed"] for v in rays + joins + list(solids.values()))
        and report["source_preserved"]
    )
    report["section_reference"] = (
        "Ray through separately built unwarped frozen envelope, including rounded rim; independent scalar evaluation of section controls at ray location."
    )
    mechanical.remove(unshaped)
    sculpt.dump(out / "geometry.json", report)
    sculpt.dump(out / "cuts.json", cuts)
    print(
        "SURFACE_GEOMETRY",
        report["passed"],
        "max_section",
        max((r.get("error", 1e9) for r in rays), default=1e9),
        "max_normal",
        max((r.get("normal_degrees", 1e9) for r in joins), default=1e9),
        flush=True,
    )
    if not report["passed"]:
        raise AssertionError("Surface acceptance failed")
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    verify(args[0], args[1])
