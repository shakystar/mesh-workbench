"""Declared drill mechanism probes, with explicit contacts and limits."""

import math
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, actuators, sculpt, construction, mechanical, joints


def register():
    state = nested.load()
    parts = {
        k: r["object"]
        for k, r in state["outputs"].items()
        if state["nodes"][k].get("visible", True)
    }
    battery = [
        k
        for k in [
            "battery",
            "battery_latch",
            "latch_guide",
            "channel_left",
            "channel_right",
        ]
        if k in parts
    ]
    channels = {
        "trigger": {
            "limits": [0, 3],
            "rest": 0,
            "max_step": 0.25,
            "vectors": {"trigger": [-1, 0, 0]},
        },
        "latch": {
            "limits": [0, 2],
            "rest": 0,
            "max_step": 0.25,
            "vectors": {"battery_latch": [0, 0, -1]},
        },
        "battery": {
            "limits": [0, 40],
            "rest": 0,
            "max_step": 1,
            "vectors": {k: [-1, 0, 0] for k in battery},
        },
        "jaw_diameter": {
            "limits": [2, 10],
            "rest": 2,
            "max_step": 0.5,
            "vectors": {
                "jaw_" + str(i): [
                    0,
                    0.5 * math.cos(math.tau * i / 3),
                    0.5 * math.sin(math.tau * i / 3),
                ]
                for i in range(3)
            },
        },
    }
    actuators.register(
        parts,
        channels,
        [{"channel": "battery", "above": 0, "requires": "latch", "at_least": 2}],
    )
    return parts, channels


def verify(out, only=None):
    parts, channels = register()
    reports = {}
    for key in ["trigger", "latch", "battery", "jaw_diameter"]:
        if only and key != only:
            continue
        moving = list(channels[key]["vectors"])
        fixed = [p for p in parts if p not in moving]
        pairs = [[a, b] for a in moving for b in fixed]
        # Rigidly moving group internals do not change their contact relation.
        # Cross-jaw pairs do move and must also be checked.
        if key == "jaw_diameter":
            pairs.extend(
                [[moving[i], moving[j]] for i in range(3) for j in range(i + 1, 3)]
            )
        contacts = []
        if key == "trigger":
            contacts = [
                {"parts": ["trigger", "trigger_stop"], "at": 3, "max_penetration": 0.01}
            ]
        if key == "jaw_diameter":
            contacts = [
                {"parts": [k, "bit"], "at": 2, "max_penetration": 0.01} for k in moving
            ]
        print("SWEEP", key, len(pairs), flush=True)
        report = actuators.sweep(
            key,
            *channels[key]["limits"],
            pairs,
            base={"latch": 2} if key == "battery" else None,
            contacts=contacts,
        )
        reports[key] = report
        sculpt.dump(Path(out) / (key + ".json"), report)
        failures = [
            {
                "value": s["value"],
                "pair": p["parts"],
                "category": p["category"],
                "distance": p["minimum_distance"],
                "penetration": p["maximum_sampled_penetration"],
                "intersections": p["triangle_pairs"],
            }
            for s in report["samples"]
            for p in s["pairs"]
            if not p["passed"]
        ]
        print(
            "RESULT",
            key,
            report["passed"],
            "failures",
            len(failures),
            str(failures[:30]),
            flush=True,
        )
    nested.load()
    return reports


def verify_alternate_bits(out):
    parts, channels = register()
    state = actuators.load()
    reports = {}
    bit_spec = __import__("json").loads(
        (ROOT / "examples/drill-assembly-target.json").read_text(encoding="utf-8")
    )["construction"]["bit"]
    for diameter in [6, 10]:
        start = bit_spec["origin"]
        end = [start[0] + bit_spec["length"], start[1], start[2]]
        bit = construction.strut(
            "Inspection bit " + str(diameter),
            start,
            end,
            radius=diameter / 2,
            segments=96,
        )
        try:
            trial = {**parts, "bit": bit.name}
            actuators.register(trial, channels, state["interlocks"])
            moving = ["jaw_" + str(i) for i in range(3)]
            pairs = [[a, b] for a in moving for b in trial if b not in moving]
            pairs += [[moving[i], moving[j]] for i in range(3) for j in range(i + 1, 3)]
            contacts = [
                {"parts": [key, "bit"], "at": diameter, "max_penetration": 0.01}
                for key in moving
            ]
            report = actuators.sweep(
                "jaw_diameter", diameter, 10, pairs, contacts=contacts
            )
            reports[str(diameter)] = report
            sculpt.dump(Path(out) / ("bit-" + str(diameter) + ".json"), report)
            print("BIT", diameter, report["passed"], flush=True)
        finally:
            mechanical.remove(bit)
            actuators.register(parts, channels, state["interlocks"])
    return reports


def verify_failures(out):
    parts, channels = register()
    state = actuators.load()
    before = joints.snapshot(list(parts.values()))
    reports = {}
    for label, values in [
        ("overtravel", {"trigger": 3.1}),
        ("locked_battery", {"battery": 1}),
        ("jaw_overtravel", {"jaw_diameter": 10.5}),
    ]:
        rejected = False
        try:
            actuators.pose(values)
        except ValueError:
            rejected = True
        reports[label] = {
            "rejected": rejected,
            "unchanged": joints.snapshot(list(before)) == before,
        }
    blocker = mechanical.box(
        "Planted trigger obstruction", [2, 2, 2], [6, 0, 125], radius=0.1
    )
    try:
        actuators.register(
            {**parts, "blocker": blocker.name}, channels, state["interlocks"]
        )
        trial = actuators.sweep("trigger", 0, 3, [["trigger", "blocker"]])
        reports["planted_collision"] = {
            "rejected": not trial["passed"],
            "unchanged": trial["rest_restored"],
            "evidence": trial,
        }
    finally:
        mechanical.remove(blocker)
        actuators.register(parts, channels, state["interlocks"])
    reports["passed"] = all(r["rejected"] and r["unchanged"] for r in reports.values())
    sculpt.dump(Path(out) / "failures.json", reports)
    nested.load()
    return reports


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    bpy.ops.wm.open_mainfile(filepath=str(Path(args[0]).resolve()))
    out = Path(args[1])
    out.mkdir(parents=True, exist_ok=False)
    mode = args[2] if len(args) > 2 else None
    if mode == "alternate-bits":
        verify_alternate_bits(out)
    elif mode == "failures":
        verify_failures(out)
    else:
        verify(out, mode)
