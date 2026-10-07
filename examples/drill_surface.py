"""Build the frozen M6 surface candidate without modifying the assembly baseline."""

import hashlib
import json
import math
import copy
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, sculpt
from drill_assembly import blueprint


def surface_blueprint(spec):
    base_spec = copy.deepcopy(spec)
    for key in list(base_spec["frame_z_parameter_rules"]):
        if key.startswith("battery_cover_"):
            del base_spec["frame_z_parameter_rules"][key]
    nodes, checks = blueprint(base_spec)
    for key in ["chuck_body", "torque_ring"]:
        design = spec["surface_phase"]["detail_design"][
            "chuck" if key == "chuck_body" else "torque_ring"
        ]
        if "profile" in design:
            nodes[key]["kind"] = "profiled_ring"
            nodes[key]["args"] = {
                "start": spec["construction"][key]["start"],
                "profile": design["profile"],
                "flutes": design["grip_flutes"],
                "depth": design["flute_depth"],
                "segments": design["grip_flutes"] * 12,
                "ticks": design.get("index_ticks", 0),
                "tick_depth": design.get("tick_depth", 0),
                "tick_range": design.get("tick_range"),
            }

    if spec["surface_phase"].get("sharp_cut_roles", False):
        for side in ["left", "right"]:
            nodes["housing_" + side]["args"]["sharp_roles"] = True
    rubber = spec["surface_phase"]["detail_design"]["rubber"]
    guide = spec["construction"]["grip"]["guide"]
    from drill_assembly import parameter

    for side, sign in [("left", -1), ("right", 1)]:
        cx, _, cz = guide["center"]
        nodes["grip_" + side]["args"]["query"].update(
            {
                "seed": [cx, sign * 16, parameter("grip_length", cz, -0.5)],
                "seed_distance": 5,
            }
        )
        rx, rz = rubber["perimeter_radii"]
        border = []
        for i in range(96):
            theta = math.tau * i / 96
            dz = rz * math.sin(theta)
            border.append(
                [
                    cx + rx * math.cos(theta) + guide["shear"] * dz,
                    0,
                    parameter("grip_length", cz + dz, -0.5),
                ]
            )
        paths = [
            {
                "points": border,
                "closed": True,
                "width": rubber["edge_width"],
                "height": rubber["perimeter_height"],
            }
        ]
        for z in range(
            *[guide["pattern_z"][0], guide["pattern_z"][1] + 1, guide["pattern_z"][2]]
        ):
            half = (
                rx * math.sqrt(max(0, 1 - ((z - cz) / rz) ** 2)) - rubber["rib_margin"]
            )
            center = cx + guide["shear"] * (z - cz)
            paths.append(
                {
                    "points": [
                        [center - half, 0, parameter("grip_length", z, -0.5)],
                        [center + half, 0, parameter("grip_length", z, -0.5)],
                    ],
                    "width": rubber["rib_width"],
                    "height": rubber["rib_height"],
                }
            )
        node = nodes["texture_" + side]
        node["kind"] = "surface_paths"
        node["args"] = {
            "query": {"normal": [0, sign, 0], "normal_min": 0.7, "components": 1},
            "paths": paths,
            "projection_axis": 1,
            "side": sign,
            "width": 0.6,
            "height": 0.4,
            "embed": 0.12,
            "spacing": 0.7,
            "cross_samples": 6,
        }
    trigger = copy.deepcopy(nodes["trigger"])
    trigger["visible"] = False
    nodes["trigger_stock"] = trigger
    t = spec["surface_phase"]["detail_design"]["trigger"]
    nodes["trigger"]["kind"] = "surface_paths"
    nodes["trigger"]["deps"] = [{"id": "trigger_stock", "use": "geometry"}]
    nodes["trigger"]["args"] = {
        "query": {"normal": [1, 0, 0], "normal_min": 0.8, "components": 1},
        "paths": [
            {"points": [[0, t["groove_y"][0], z], [0, t["groove_y"][1], z]]}
            for z in t["groove_z"]
        ],
        "projection_axis": 0,
        "side": 1,
        "width": t["groove_width"],
        "height": 0.2,
        "embed": t["groove_depth"],
        "mode": "groove",
        "spacing": 1,
        "cross_samples": 4,
    }
    for i, cover in enumerate(
        spec["surface_phase"]["detail_design"]["battery_shroud"]["covers"]
    ):
        args = copy.deepcopy(cover)
        args["center"][2] = parameter("grip_length", args["center"][2], -1)
        nodes["battery_cover_" + str(i)] = {
            "kind": "edge_box",
            "args": {k: v for k, v in args.items() if k != "radius"},
            "frame": {
                "origin": args["center"],
                "x": [1, 0, 0],
                "y": [0, 1, 0],
                "z": [0, 0, 1],
            },
            "deps": [{"id": "battery", "use": "frame"}],
            "visible": True,
            "material": copy.deepcopy(nodes["battery"]["material"]),
        }

    return nodes, checks


def build(out, previous=None):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    path = ROOT / "examples/drill-surface-target.json"
    spec = json.loads(path.read_text())
    source = ROOT / spec["provenance"]["baseline"]
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    if before != spec["provenance"]["baseline_sha256"]:
        raise ValueError("Baseline changed")
    if previous:
        previous = Path(previous).resolve()
        previous_hash = hashlib.sha256(previous.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(previous))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    nodes, checks = surface_blueprint(spec)

    try:
        report = (
            nested.reconfigure(nodes, checks=checks)
            if previous
            else nested.initialize(
                "Surface refined drill",
                nodes,
                spec["parameters"],
                spec["parameter_ranges"],
                checks,
            )
        )
    except Exception as exc:
        sculpt.dump(out / "rejected.json", getattr(exc, "report", {"reason": str(exc)}))
        raise
    state = nested.load()
    master = bpy.data.objects[state["outputs"]["master"]["object"]]
    report.update(
        {
            "stage": "M7 candidate; visual and motion acceptance pending",
            "specification_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "section_shape": json.loads(master.get("mw_section_shape", "null")),
            "baseline_preserved": hashlib.sha256(source.read_bytes()).hexdigest()
            == before,
        }
    )
    if previous:
        report["previous_file_preserved"] = (
            hashlib.sha256(previous.read_bytes()).hexdigest() == previous_hash
        )
    sculpt.dump(out / "build.json", report)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
    print("SURFACE_BUILT", report["passed"], flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    build(args[0], args[1] if len(args) > 1 else None)
