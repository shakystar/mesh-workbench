"""Dimensioned continuous drill assembly and reproducible nested variants.
Run with factory-startup Blender: --python examples/drill_assembly.py -- NEW_OUTPUT.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, sculpt


def parameter(name, offset=0, scale=1):
    return {"param": name, "offset": offset, "scale": scale}


def blueprint(spec):
    nodes = {}
    c = spec["construction"]
    g = spec["gates"]
    yellow = {
        "name": "DA ochre polymer",
        "color": [0.82, 0.37, 0.025],
        "roughness": 0.32,
    }
    dark = {
        "name": "DA graphite rubber",
        "color": [0.022, 0.029, 0.034],
        "roughness": 0.66,
    }
    steel = {
        "name": "DA machined steel",
        "color": [0.38, 0.43, 0.48],
        "metallic": 0.85,
        "roughness": 0.23,
    }
    accent = {
        "name": "DA warm indicator",
        "color": [0.9, 0.055, 0.012],
        "roughness": 0.35,
    }

    def add(
        key,
        kind,
        args,
        parent=None,
        mode="geometry",
        visible=True,
        material=None,
        frame=None,
    ):
        nodes[key] = {"kind": kind, "args": copy.deepcopy(args), "visible": visible}
        if parent:
            nodes[key]["deps"] = [{"id": parent, "use": mode}]
        if material:
            nodes[key]["material"] = material
        if key in spec["parts"]:
            nodes[key]["frame"] = copy.deepcopy(spec["parts"][key]["frame"])
        if frame:
            nodes[key]["frame"] = frame
        return key

    add(
        "master",
        "enclosure",
        {
            **spec["envelope"],
            "grip_width": parameter("grip_width"),
            "grip_length": parameter("grip_length"),
        },
        visible=False,
    )
    add("skin", "hollow", {"thickness": g["wall_nominal"]}, "master", visible=False)
    for side, sign in [("left", -1), ("right", 1)]:
        source = add(
            "shell_" + side,
            "partition",
            {"side": side, "offset": parameter("split_shift"), "gap": g["gap_nominal"]},
            "skin",
            visible=False,
        )
        v = c["vents"]
        for i, x in enumerate(v["x"]):
            source = add(
                "vent_" + side + "_" + str(i),
                "cut_box",
                {
                    "dimensions": [v["width"], v["depth"], v["height"]],
                    "center": [x, sign * v["center_abs_y"], v["z"]],
                    "radius": v["corner_radius"],
                },
                source,
                visible=False,
            )
        source = add(
            "trigger_cut_" + side,
            "cut_box",
            c["trigger_opening"],
            source,
            visible=False,
        )
        source = add(
            "front_bore_" + side, "cut_cylinder", c["front_bore"], source, visible=False
        )
        for i in range(3):
            x, _, z = spec["parts"]["boss_" + str(i)]["frame"]["origin"]
            z = parameter("grip_length", z, -1) if z < 100 else z
            key = (
                "housing_" + side if i == 2 else "fastener_bore_" + side + "_" + str(i)
            )
            source = add(
                key,
                "cut_cylinder",
                {
                    "start": [x, -40, z],
                    "end": [x, 40, z],
                    "radius": c["fastener"]["clearance_radius"],
                },
                source,
                visible=i == 2,
                material=yellow if i == 2 else None,
            )
        low = [-55, -40 if sign < 0 else 0, parameter("grip_length", 53, -1)]
        high = [5, 0 if sign < 0 else 40, 120]
        query = {
            "box": [low, high],
            "normal": [0, sign, 0],
            "normal_min": 0.7,
            "materials": [0],
            "components": 1,
        }
        guide = c["grip"]["guide"]
        center = guide["center"].copy()
        center[2] = parameter("grip_length", center[2], -0.5)
        add(
            "grip_" + side,
            "insert",
            {
                "query": query,
                "center": center,
                "radii": [
                    guide["radii"][0],
                    parameter("grip_length", guide["radii"][1], 0.5),
                ],
                "shear": guide["shear"],
                "side": sign,
                "rings": guide["rings"],
                "segments": guide["segments"],
                "offset": c["grip"]["outer_offset"],
                "thickness": c["grip"]["thickness"],
            },
            "housing_" + side,
            material=dark,
        )
        points = []
        for z in range(
            guide["pattern_z"][0], guide["pattern_z"][1] + 1, guide["pattern_z"][2]
        ):
            for dx in guide["pattern_x"]:
                points.append(
                    [
                        guide["center"][0]
                        + guide["shear"] * (z - guide["center"][2])
                        + dx,
                        sign * 35,
                        parameter("grip_length", z, -0.5),
                    ]
                )
        add(
            "texture_" + side,
            "relief",
            {
                "query": {"normal": [0, sign, 0], "normal_min": 0.7, "components": 1},
                "points": points,
                "direction": [0, -sign, 0],
                "max_distance": 40,
                "radii": c["grip"]["pattern_radius"],
                "height": c["grip"]["pattern_height"],
                "embed": c["grip"]["pattern_embed"],
                "clearance": c["grip"]["pattern_clearance"],
                "segments": 16,
                "rings": 3,
            },
            "grip_" + side,
            material=dark,
        )
    add("rear_cover", "box", c["rear_cover"], "master", "frame", material=dark)
    for key in ["torque_ring", "chuck_body"]:
        add(
            key, "annulus", c[key], spec["parts"][key]["parent"], "frame", material=dark
        )
    add("jaw_cage", "cage", c["jaw_cage"], "chuck_body", "frame", material=steel)
    for i in range(3):
        add(
            "jaw_" + str(i),
            "jaw",
            {**c["jaw"], "angle": i * 120, "diameter": 2},
            "jaw_cage",
            "frame",
            material=steel,
        )
    bit = c["bit"]
    end = bit["origin"].copy()
    end[0] += bit["length"]
    add(
        "bit",
        "cylinder",
        {
            "start": bit["origin"],
            "end": end,
            "radius": bit["diameter"] / 2,
            "segments": 96,
        },
        "chuck_body",
        "frame",
        material=steel,
    )
    for i in range(3):
        key = "boss_" + str(i)
        x, _, z = spec["parts"][key]["frame"]["origin"]
        half = (
            spec["envelope"]["grip_half_width"]
            if z < 100
            else spec["envelope"]["head_half_width"]
        )
        y = -half + g["wall_nominal"] - c["bosses"]["embed"]
        width_factor = -0.5 if z < 100 else 0
        start = [
            x,
            parameter("grip_width", y, width_factor),
            parameter("grip_length", z, -1) if z < 100 else z,
        ]
        length = parameter("grip_width", c["bosses"]["end_y"] - y, -width_factor)
        add(
            key,
            "annulus",
            {
                "outer_radius": c["bosses"]["outer_radius"],
                "inner_radius": c["bosses"]["inner_radius"],
                "start": start,
                "length": length,
                "axis": [0, 1, 0],
            },
            "housing_left",
            material=yellow,
        )
        add(
            "receiver_" + str(i),
            "annulus",
            {
                "outer_radius": c["bosses"]["outer_radius"],
                "inner_radius": c["bosses"]["inner_radius"],
                "start": [x, -c["bosses"]["end_y"], start[2]],
                "length": length,
                "axis": [0, 1, 0],
            },
            "housing_right",
            material=yellow,
        )
        fast = c["fastener"]
        top = parameter("grip_width", -half, width_factor)
        shaft = add(
            "shaft_" + str(i),
            "cylinder",
            {
                "start": [
                    x,
                    parameter("grip_width", -half - 0.6, width_factor),
                    start[2],
                ],
                "end": [x, parameter("grip_width", half - 1, -width_factor), start[2]],
                "radius": fast["shaft_radius"],
                "segments": 48,
            },
            key,
            "frame",
            visible=False,
        )
        head = add(
            "head_" + str(i),
            "cylinder",
            {
                "start": [
                    x,
                    parameter(
                        "grip_width", -half - fast["head_thickness"], width_factor
                    ),
                    start[2],
                ],
                "end": [x, top, start[2]],
                "radius": fast["head_radius"],
                "segments": 48,
            },
            key,
            "frame",
            visible=False,
        )
        head = add(
            "slotted_head_" + str(i),
            "cut_box",
            {
                "dimensions": [
                    fast["slot_length"],
                    fast["slot_depth"],
                    fast["slot_width"],
                ],
                "center": [
                    x,
                    parameter(
                        "grip_width",
                        -half - fast["head_thickness"] + 0.15,
                        width_factor,
                    ),
                    start[2],
                ],
                "radius": 0.1,
            },
            head,
            visible=False,
        )
        add("fastener_" + str(i), "union", {}, head, material=steel)
        nodes["fastener_" + str(i)]["deps"].append({"id": shaft, "use": "geometry"})
    for i, center in enumerate(c["trigger_guide"]["centers"]):
        add(
            "trigger_guide" if i == 0 else "trigger_guide_right",
            "box",
            {
                "dimensions": c["trigger_guide"]["rail_dimensions"],
                "center": center,
                "radius": c["trigger_guide"]["radius"],
            },
            "housing_left",
            "frame",
            material=steel,
        )
    add(
        "trigger_stop",
        "box",
        c["trigger_stop"],
        "trigger_guide",
        "frame",
        material=steel,
    )
    add("trigger", "box", c["trigger"], "trigger_guide", "frame", material=accent)

    def descend(data, field="center"):
        result = copy.deepcopy(data)
        result[field][2] = parameter("grip_length", result[field][2], -1)
        return result

    add("foot_stock", "box", descend(c["foot"]), "master", "frame", visible=False)
    seat = {
        "dimensions": c["latch"]["seat_dimensions"],
        "center": c["latch"]["center"],
        "radius": 0.3,
    }
    add("foot", "cut_box", descend(seat), "foot_stock", material=yellow)
    add("battery", "box", descend(c["battery"]), "foot", "frame", material=dark)
    add(
        "battery_latch",
        "box",
        descend({k: v for k, v in c["latch"].items() if k != "seat_dimensions"}),
        "battery",
        "frame",
        material=accent,
    )
    guide = c["latch_guide"]
    add(
        "latch_guide_stock",
        "box",
        descend({k: v for k, v in guide.items() if k != "bore_dimensions"}),
        "battery",
        "frame",
        visible=False,
    )
    add(
        "latch_guide",
        "cut_box",
        descend(
            {
                "dimensions": guide["bore_dimensions"],
                "center": guide["center"],
                "radius": 0.15,
            }
        ),
        "latch_guide_stock",
        material=steel,
    )
    for kind, parent in [("rail", "foot"), ("channel", "battery")]:
        for i, origin in enumerate(c[kind]["origins"]):
            key = kind + "_" + ["left", "right"][i]
            add(
                key,
                "prism",
                descend(
                    {
                        "origin": origin,
                        "length": c[kind]["length"],
                        "section_yz": c[kind]["section_yz"],
                    },
                    "origin",
                ),
                parent,
                "frame",
                material=steel,
            )
    # Explicit derived world frames follow their dependent physical interfaces.
    for key, rules in spec["frame_z_parameter_rules"].items():
        for name, scale in rules.items():
            nodes[key]["frame"]["origin"][2] = parameter(
                name, spec["parts"][key]["frame"]["origin"][2], scale
            )
    checks = [
        {
            "kind": "wall",
            "parts": ["housing_" + side],
            "options": {"minimum": g["wall_min"], "maximum": g["wall_max"]},
        }
        for side in ["left", "right"]
    ]
    checks.append(
        {
            "kind": "gap",
            "parts": ["housing_left", "housing_right"],
            "options": {"minimum": g["gap_range"][0], "maximum": g["gap_range"][1]},
        }
    )
    return nodes, checks


def main():
    out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    path = ROOT / "examples/drill-assembly-target.json"
    spec = json.loads(path.read_text(encoding="utf-8-sig"))
    nodes, checks = blueprint(spec)

    def progress(phase):
        if phase == "after_build":
            print("BUILT", len(bpy.data.objects), flush=True)

    nested._checkpoint = progress
    try:
        report = nested.initialize(
            "Precision cordless drill",
            nodes,
            spec["parameters"],
            spec["parameter_ranges"],
            checks,
        )
    except Exception as exc:
        sculpt.dump(out / "rejected.json", getattr(exc, "report", {"reason": str(exc)}))
        raise
    report.update(
        {
            "blender": bpy.app.version_string,
            "spec_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    sculpt.dump(out / "build.json", report)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
    print("SAVED", str(out / "drill.blend"), flush=True)


if __name__ == "__main__":
    main()
