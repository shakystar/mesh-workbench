"""Build the public completion audit only after all required evidence passes."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["baseline", "grip-width", "grip-length", "split-shift", "remesh"]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def motion(path, channel, parts, low, high, maximum_step):
    value = read(path)
    require(value["passed"] and value["rest_restored"], str(path) + " failed")
    samples = value["samples"]
    require(
        abs(samples[0]["value"] - low) < 1e-7
        and abs(samples[-1]["value"] - high) < 1e-7,
        "Incomplete travel",
    )
    require(value["step"] <= maximum_step + 1e-8, "Coarse travel sampling")
    moving = {
        "trigger": ["trigger"],
        "latch": ["battery_latch"],
        "battery": [
            "battery",
            "battery_latch",
            "latch_guide",
            "channel_left",
            "channel_right",
        ],
        "jaw_diameter": ["jaw_0", "jaw_1", "jaw_2"],
    }[channel]
    expected = {(a, b) for a in moving for b in parts if b not in moving}
    if channel == "jaw_diameter":
        expected |= {(moving[i], moving[j]) for i in range(3) for j in range(i + 1, 3)}
    noncontact = []
    contacts = []
    for sample in samples:
        require(
            sample["passed"]
            and {tuple(p["parts"]) for p in sample["pairs"]} == expected,
            "Missing or failed collision pair",
        )
        for pair in sample["pairs"]:
            require(
                pair["passed"]
                and not pair.get("missing", 0)
                and not pair.get("ambiguous", 0),
                "Unverified probe",
            )
            if pair["category"] == "intentional contact":
                require(
                    pair["maximum_sampled_penetration"] <= 0.01001,
                    "Contact penetration",
                )
                contacts.append(pair)
            else:
                require(
                    pair["minimum_distance"] >= 0.2 - 1e-5
                    and pair["triangle_pairs"] == 0,
                    "Noncontact clearance",
                )
                noncontact.append(pair["minimum_distance"])
    if channel == "trigger":
        require(
            any(p["parts"] == ["trigger", "trigger_stop"] for p in contacts),
            "Missing trigger stop contact",
        )
    if channel == "jaw_diameter":
        require(
            {tuple(p["parts"]) for p in contacts} == {(k, "bit") for k in moving},
            "Missing jaw contacts",
        )
    return {
        "sha256": digest(path),
        "poses": len(samples),
        "pairs_per_pose": len(expected),
        "step": value["step"],
        "minimum_noncontact_bound": min(noncontact),
        "contacts": len(contacts),
        "rest_restored": True,
    }


def build(run, ci_path, windows_log, host_log, output):
    run = Path(run).resolve()
    spec_path = ROOT / "examples/drill-assembly-target.json"
    spec = read(spec_path)
    brief = read(ROOT / "docs/audits/DRILL_ASSEMBLY_BRIEF.json")
    require(brief["sha256"] == digest(spec_path), "Brief hash mismatch")
    require(
        brief["guide_sha256"] == digest(ROOT / "docs/assets/drill-assembly-target.svg"),
        "Guide hash mismatch",
    )
    require(
        digest(ROOT / spec["provenance"]["baseline"])
        == spec["provenance"]["baseline_sha256"],
        "Previous drill modified",
    )
    deliveries = {
        mode: read(run / ("delivery-" + mode + ".json"))
        for mode in ["native", "followup"]
    }
    variants = {}
    for mode, index in deliveries.items():
        require(
            index["passed"]
            and index["status"] == "complete"
            and set(index["records"]) == set(NAMES),
            "Incomplete native inspection",
        )
        require(
            index["specification_sha256"] == digest(spec_path),
            "Wrong delivered specification",
        )
    for name in NAMES:
        migration = read(run / name / "migration.json")
        require(
            migration["passed"]
            and migration["source_preserved"]
            and migration["original_objects_preserved"]
            and all(migration["same_geometry"].values()),
            "Migration changed source geometry",
        )
        reopen = read(run / ("reopen-" + name) / "reopen.json")
        require(
            reopen["status"] == "complete"
            and reopen["passed"]
            and reopen["recipe_matches"]
            and reopen["source_preserved"],
            "Reopening failed",
        )
        require(
            reopen["unknown_part_rejected_unchanged"]
            and reopen["stale_attribute_detected"],
            "Missing reopen failure checks",
        )
        if name == "baseline":
            require(
                reopen.get("late_commit_rollback"), "Missing actual commit rollback"
            )
        records = {}
        for mode, index in deliveries.items():
            record = index["records"][name]
            require(
                record["passed"]
                and record["source_preserved"]
                and all(record["declared_frames"].values()),
                "Failed delivered file",
            )
            require(
                record["sha256"] == digest(ROOT / record["source"]),
                "Delivered file changed after verification",
            )
            folder = run / name if mode == "native" else run / ("reopen-" + name)
            geometry = record["geometry"]
            require(
                geometry["passed"] and geometry["units"]["passed"],
                "Geometry or units failed",
            )
            require(
                geometry["silhouette"]["iou"] >= spec["gates"]["side_silhouette_iou"],
                "Silhouette gate failed",
            )
            parts = set(geometry["solids"])
            motions = {}
            for channel, low, high, step in [
                ("trigger", 0, 3, 0.25),
                ("latch", 0, 2, 0.25),
                ("battery", 0, 40, 1),
                ("jaw_diameter", 2, 10, 0.5),
            ]:
                motions[channel] = motion(
                    folder / "motion" / (channel + ".json"),
                    channel,
                    parts,
                    low,
                    high,
                    step,
                )
            records[mode] = {
                "file": record["source"],
                "sha256": record["sha256"],
                "parameters": record["parameters"],
                "solid_count": len(parts),
                "declared_frame_count": len(record["declared_frames"]),
                "silhouette": geometry["silhouette"],
                "section_error_max": max(
                    s["bound_error_max"] for s in geometry["sections"]
                ),
                "junction_normal_max": max(
                    s["normal_degrees"] for s in geometry["junction_samples"]
                ),
                "interfaces": record["interfaces"],
                "motion": motions,
            }
        checks = reopen["followup"]["checks"]
        require(
            all(c["passed"] and not c.get("missing_or_invalid", 0) for c in checks),
            "Follow-up wall/gap rejected",
        )
        records["followup_edit"] = {
            k: reopen["followup"][k] for k in ["updated", "unchanged", "checks"]
        }
        records["attributes"] = {
            k: reopen[k] for k in ["attributes_before", "attributes_after"]
        }
        require(
            all(v["passed"] for v in records["attributes"].values()),
            "Attribute transfer failed",
        )
        variants[name] = records
    bits = {}
    parts = set(deliveries["native"]["records"]["baseline"]["geometry"]["solids"])
    for diameter in [6, 10]:
        bits[str(diameter)] = motion(
            run / "baseline/alternate-bits" / ("bit-" + str(diameter) + ".json"),
            "jaw_diameter",
            parts,
            diameter,
            10,
            0.5,
        )
    failures = read(run / "baseline/failures/failures.json")
    require(failures["passed"], "Actual failure fixtures failed")
    cli = read(ROOT / "runs/drill-assembly-cli/audit.json")
    native_cli = read(ROOT / "runs/drill-assembly-cli/native.json")
    rejected = read(ROOT / "runs/drill-assembly-cli-rejected/proof.json")
    require(
        cli["status"] == "complete" and native_cli["passed"],
        "Actual CLI success missing",
    )
    require(
        rejected["exit_code"] != 0
        and rejected["status"] == "failed"
        and rejected["source_preserved"]
        and rejected["no_result_saved"],
        "Actual CLI rejection missing",
    )
    log = Path(windows_log).read_text(encoding="utf-8", errors="replace")
    result_match = re.search(r"MESH_WORKBENCH_TEST_RESULT (\{[^\n]+\})", log)
    require(result_match is not None, "Missing Windows completion marker")
    tests = json.loads(result_match.group(1))
    require(
        tests["tests"] >= 37 and tests["failures"] == 0 and tests["errors"] == 0,
        "Windows regression failed",
    )
    host = Path(host_log).read_text(encoding="utf-8", errors="replace")
    require("Ran 3 tests" in host and "OK" in host, "Host tests incomplete")
    ci = read(ci_path)
    require(
        ci["status"] == "completed"
        and ci["conclusion"] == "success"
        and all(j["conclusion"] == "success" for j in ci["jobs"]),
        "Linux CI incomplete",
    )
    require(
        ci.get("integration_results")
        and all(
            v["tests"] >= 37 and v["failures"] == 0 and v["errors"] == 0
            for v in ci["integration_results"]
        ),
        "Linux regression evidence incomplete",
    )
    assets = {
        p.name: digest(p) for p in (ROOT / "docs/assets").glob("drill-assembly-*.png")
    }
    required = [
        "hero",
        "side",
        "exploded",
        "section-85",
        "section-165",
        "clearance",
        "topology-before",
        "topology-after",
        "grip-width",
        "grip-length",
        "split-shift",
    ]
    require(
        all("drill-assembly-" + name + ".png" in assets for name in required),
        "Missing required preview",
    )
    scenario_paths = {
        "grip-width": "runs/drill-assembly-06/grip-width/variant.json",
        "grip-length": "runs/drill-assembly-06/grip-length/variant.json",
        "split-shift": "runs/drill-assembly-08/split-shift/variant.json",
        "remesh": "runs/drill-assembly-07/remesh/variant.json",
    }
    scenarios = {}
    for name, path in scenario_paths.items():
        r = read(ROOT / path)
        require(
            r["passed"] and all(r["independent_parts_unchanged"].values()),
            "Selective regeneration failed",
        )
        scenarios[name] = {
            k: r[k]
            for k in ["updated", "unchanged", "checks", "independent_parts_unchanged"]
        }
        if name == "remesh":
            metrics = r["remesh"]
            require(
                metrics["sampled_error_max"] <= 0.09
                and metrics["pinned_error"] <= 1e-5,
                "Remesh drift gate",
            )
            scenarios[name]["remesh"] = metrics
    audit = {
        "status": "complete",
        "specification_revision": spec["revision"],
        "specification_sha256": digest(spec_path),
        "guide_sha256": brief["guide_sha256"],
        "milestones": {
            k: {"passed": True, "evidence": v}
            for k, v in {
                "M0": "Frozen brief, guide, 38 declared part frames and native mm units",
                "M1": "All native and follow-up silhouette, section, junction and mesh measurements",
                "M2": "Native separate solids, actual frame/axis checks, rail sections, physical latch blocking and disengagement",
                "M3": "Four selective change scenarios, source-preserving frame migration, attribute bindings, staged recovery fixtures",
                "M4": "All native and follow-up constrained sweeps; 2/6/10 mm bit cases; planted collision, travel and lock failures",
                "M5": "All files reopened and edited in new processes; actual CLI success/rejection; Windows/Linux regression; native renders and public evidence",
            }.items()
        },
        "variants": variants,
        "scenarios": scenarios,
        "alternate_bits": bits,
        "negative_cases": {
            k: {"rejected": v["rejected"], "unchanged": v["unchanged"]}
            for k, v in failures.items()
            if k != "passed"
        },
        "windows": {
            "blender": deliveries["native"]["blender"],
            "tests": tests,
            "log_sha256": digest(windows_log),
        },
        "host": {"tests": 3, "log_sha256": digest(host_log)},
        "linux_ci": ci,
        "cli": {
            "success": native_cli,
            "rejection": rejected,
            "recipe_sha256": digest(ROOT / "examples/drill-assembly.json"),
        },
        "assets": assets,
        "limits": [
            "Original authored design, not a manufacturer replica or production tolerance certificate.",
            "Discrete collision and sampled distance/penetration bounds; no continuous collision or strength proof.",
            "Local remeshing bakes the whole source to triangles; the demonstrated patch changes 80 to 78 triangles.",
            "Projected inserts reject UV/material discontinuities; arbitrary seam-aware patch retopology is not implemented.",
        ],
    }
    Path(output).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print("AUDIT_COMPLETE", output)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run-root", required=True)
    p.add_argument("--ci-json", required=True)
    p.add_argument("--windows-log", required=True)
    p.add_argument("--host-log", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    build(a.run_root, a.ci_json, a.windows_log, a.host_log, a.output)
