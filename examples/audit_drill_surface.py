"""Require measured native, CLI, render and cross-platform evidence for M6-M10."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
            "battery_cover_0",
            "battery_cover_1",
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


def build(args):
    run = ROOT / args.run_root
    specpath = ROOT / "examples/drill-surface-target.json"
    spec = read(specpath)
    brief = read(ROOT / "docs/audits/DRILL_SURFACE_BRIEF.json")
    require(
        brief["sha256"] == digest(specpath), "Brief differs from current specification"
    )
    require(brief["guide_sha256"] == digest(ROOT / brief["guide"]), "Guide changed")
    require(
        digest(ROOT / spec["provenance"]["baseline"])
        == spec["provenance"]["baseline_sha256"],
        "Baseline changed",
    )
    require(
        all(not r["gates_changed"] for r in spec["design_revisions"]),
        "Acceptance gates changed",
    )
    gate = spec["surface_phase"]["acceptance"]
    build = read(run / "build.json")
    require(
        build["passed"]
        and build["baseline_preserved"]
        and build["previous_file_preserved"],
        "Build failed",
    )
    require(
        build["specification_sha256"] == digest(specpath),
        "Candidate built from different spec",
    )
    require(len(build["objects"]) == 73, "Missing graph nodes")
    reopen = read(run / "reopen/reopen.json")
    require(
        all(
            reopen[k]
            for k in [
                "passed",
                "recipe_matches",
                "unknown_parameter_rejected_unchanged",
                "late_commit_rollback",
                "source_preserved",
            ]
        ),
        "Reopen/rollback failed",
    )
    require(
        reopen["attributes_before"]["passed"] and reopen["attributes_after"]["passed"],
        "Attribute loss",
    )
    natives = {}
    for label, file, folder, checks in [
        ("native", run / "drill.blend", run, build["checks"]),
        (
            "followup",
            run / "reopen/followup.blend",
            run / "reopen",
            reopen["followup"]["checks"],
        ),
    ]:
        g = read(folder / "geometry/geometry.json")
        require(
            g["passed"]
            and g["source_preserved"]
            and g["source_sha256"] == digest(file),
            "Native geometry/source mismatch",
        )
        require(
            g["units"]["passed"] and all(f["passed"] for f in g["frames"]),
            "Frame or units failed",
        )
        require(
            len(g["solids"]) == 37 and all(s["passed"] for s in g["solids"].values()),
            "Visible solid failure",
        )
        require(g["silhouette"]["iou"] >= gate["outline_iou_min"], "Outline failure")
        require(
            all(
                r["passed"] and r["error"] <= gate["section_surface_error_max_mm"]
                for r in g["sections"]
            ),
            "Section failure",
        )
        require(
            all(
                j["passed"] and j["normal_degrees"] <= gate["normal_step_max_degrees"]
                for j in g["junctions"]
            ),
            "Normal join failure",
        )
        require(
            len(checks) == 3 and all(c["passed"] for c in checks),
            "Wall/gap checks missing",
        )
        for c in checks:
            lo, hi = (1.6, 2.6) if c["kind"] == "wall" else (0.5, 1.1)
            require(
                c["min"] >= lo
                and c["max"] <= hi
                and not c.get("missing_or_invalid", 0),
                "Wall/gap range",
            )
        motions = {}
        for ch, low, high, step in [
            ("trigger", 0, 3, 0.25),
            ("latch", 0, 2, 0.25),
            ("battery", 0, 40, 1),
            ("jaw_diameter", 2, 10, 0.5),
        ]:
            motions[ch] = motion(
                folder / "motion" / (ch + ".json"),
                ch,
                list(g["solids"]),
                low,
                high,
                step,
            )
        inter = read(folder / "interfaces/interfaces.json")
        require(
            inter["passed"] and inter["rest_restored"], "Physical interface failure"
        )
        natives[label] = dict(
            path=str(file.relative_to(ROOT)).replace("\\", "/"),
            sha256=digest(file),
            geometry=g,
            wall_gap=checks,
            motion=motions,
            interfaces=inter,
        )
    details = read(run / "details-02/details.json")
    require(
        details["passed"]
        and details["source_preserved"]
        and details["source_sha256"] == digest(run / "drill.blend"),
        "Detail geometry mismatch",
    )
    require(
        len(details["checks"]) == 27 and all(c["passed"] for c in details["checks"]),
        "Incomplete actual detail checks",
    )
    patch = read(ROOT / "runs/drill-surface-patch-03/patch.json")
    require(
        patch["passed"] and patch["source_preserved"] and patch["patch"]["passed"],
        "Root patch rebuild failure",
    )
    r = patch["patch"]["report"]
    require(
        r["sampled_error_max"] <= gate["patch_drift_max_mm"]
        and r["pinned_error"] <= 1e-5,
        "Patch coordinate drift",
    )
    require(
        r["patch_after"]["quality_p10"] > r["patch_before"]["quality_p10"]
        and r["patch_after"]["edge_length_cv"] < r["patch_before"]["edge_length_cv"],
        "Patch did not improve",
    )
    require(
        r["preserved_polygons"] == 17018 and r["operations"]["relax"] > 0,
        "Unedited polygons not retained",
    )
    failures = read(run / "failures/failures.json")
    require(failures["passed"], "Negative motion tests failed")
    bits = {}
    for diameter in [6, 10]:
        bits[str(diameter)] = motion(
            run / "bits" / ("bit-" + str(diameter) + ".json"),
            "jaw_diameter",
            list(natives["native"]["geometry"]["solids"]),
            diameter,
            10,
            0.5,
        )
    cli = ROOT / args.cli_root
    cli_audit = read(cli / "audit.json")
    require(
        cli_audit["status"] == "complete" and cli_audit["source_preserved"],
        "CLI failed",
    )
    require(
        cli_audit["recipe"] == read(ROOT / "examples/drill-surface.json"),
        "CLI recipe stale",
    )
    require(
        [o["op"] for o in cli_audit["operations"]]
        == ["nested_initialize", "nested_update", "nested_update", "nested_status"],
        "CLI coverage changed",
    )
    cg = read(cli / "geometry/geometry.json")
    require(
        cg["passed"]
        and cg["source_sha256"] == digest(cli / "result.blend")
        and cg["units"]["passed"],
        "CLI native verification failed",
    )
    rej = read(ROOT / args.rejected_root / "verification.json")
    require(
        rej["passed"]
        and rej["source_sha256"] == digest(cli / "result.blend")
        and rej["source_preserved"]
        and rej["no_result"],
        "CLI rejection changed input",
    )
    require("Invalid grip_width" in rej["error"], "CLI failed for wrong reason")
    before = read(ROOT / "runs/drill-surface-before/review/renders.json")
    after = read(run / "review/renders.json")
    views = {
        "hero",
        "left",
        "right",
        "front",
        "rear",
        "top",
        "bottom",
        "stripes-hero",
        "curvature-hero",
        "chuck-detail",
        "grip-detail",
        "trigger-detail",
        "battery-detail",
    }
    require(
        before["source_sha256"] == spec["provenance"]["baseline_sha256"]
        and after["source_sha256"] == digest(run / "drill.blend"),
        "Render source mismatch",
    )
    assets = {}
    for label, manifest, folder in [
        ("before", before, ROOT / "runs/drill-surface-before/review"),
        ("after", after, run / "review"),
    ]:
        require(
            manifest["source_preserved"]
            and {v["view"] for v in manifest["views"]} == views,
            "Render set incomplete",
        )
        for v in manifest["views"]:
            camera = v["view"].removeprefix("stripes-").removeprefix("curvature-")
            require(
                v["camera"] == spec["surface_phase"]["cameras"][camera],
                "Camera changed",
            )
            name = "drill-surface-" + label + "-" + v["view"] + ".png"
            require(
                digest(folder / (v["view"] + ".png"))
                == v["sha256"]
                == digest(ROOT / "docs/assets" / name),
                "Render copy mismatch",
            )
            assets[name] = v["sha256"]
    for name in ["topology-before", "topology-after"]:
        public = "drill-surface-" + name + ".png"
        require(
            digest(run / "review" / (name + ".png"))
            == digest(ROOT / "docs/assets" / public),
            "Topology copy mismatch",
        )
        assets[public] = digest(ROOT / "docs/assets" / public)
    visual = read(ROOT / "docs/audits/DRILL_SURFACE_VISUAL.json")
    require(
        visual["passed_for_declared_milestones"]
        and visual["images"] == assets
        and visual["source_sha256"] == digest(run / "drill.blend"),
        "Visual review stale",
    )
    win = Path(args.windows_log).read_text(encoding="utf-8")
    result = re.findall(r"MESH_WORKBENCH_TEST_RESULT (\{[^\n]+\})", win)
    require(bool(result), "No Windows test result")
    tests = json.loads(result[-1])
    require(tests == dict(tests=46, failures=0, errors=0), "Windows regression failed")
    host = Path(args.host_log).read_text(encoding="utf-8")
    require(
        "Ran 3 tests" in host and "OK" in host and "FAILED" not in host,
        "Host regression failed",
    )
    ci = read(args.ci_json)
    require(
        ci["conclusion"] == "success" and ci["status"] == "completed",
        "Linux CI unfinished",
    )
    linux = Path(args.linux_log).read_text(encoding="utf-8")
    require(
        'MESH_WORKBENCH_TEST_RESULT {"tests": 46, "failures": 0, "errors": 0}' in linux
        and "Blender 4.0.2" in linux
        and "Ran 3 tests" in linux,
        "Linux count/version evidence missing",
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", ci["headSha"], "HEAD"],
        cwd=ROOT,
        check=True,
    )
    changed = subprocess.check_output(
        ["git", "diff", ci["headSha"], "--", "src", "tests"], cwd=ROOT, text=True
    )
    require(not changed, "Runtime differs from tested CI commit")
    audit = dict(
        status="complete",
        specification_revision=spec["revision"],
        specification_sha256=digest(specpath),
        guide_sha256=brief["guide_sha256"],
        runtime_commit=ci["headSha"],
        milestones={
            k: dict(passed=True, evidence=v)
            for k, v in {
                "M6": "Frozen six-view/detail guide, revision history, camera and unchanged numerical gates",
                "M7": "Native and followup outline, section, normal, solid, frame, wall and gap measurements; six directional visual reviews",
                "M8": "27 measured detail checks, physical interfaces, ten bounded motion sweeps with restored rest transforms",
                "M9": "Actual rebuilt grip patch, preserved polygons/pins/UV/masks, variable bevel and projected paths; reopened edit and late-commit recovery",
                "M10": "Native files, 28 render previews, CLI success and rejection, 46 Windows/Linux integration tests, 3 host tests and reproducible documentation",
            }.items()
        },
        graph_nodes=73,
        declared_part_frames=len(spec["parts"]),
        visible_solids=37,
        natives=natives,
        details=details,
        patch=r,
        reopen=reopen,
        alternate_bits=bits,
        negative_cases={
            k: {a: v[a] for a in ["rejected", "unchanged"] if a in v}
            for k, v in failures.items()
            if k != "passed"
        },
        cli=dict(
            path=str((cli / "result.blend").relative_to(ROOT)).replace("\\", "/"),
            sha256=digest(cli / "result.blend"),
            recipe_sha256=digest(ROOT / "examples/drill-surface.json"),
            geometry=cg,
            rejection={
                k: rej[k]
                for k in [
                    "passed",
                    "exit_code",
                    "source_preserved",
                    "no_result",
                    "audit_status",
                ]
            },
            rejection_reason="Invalid grip_width",
        ),
        windows=dict(
            blender="5.2.2 LTS", result=tests, log_sha256=digest(args.windows_log)
        ),
        host=dict(tests=3, log_sha256=digest(args.host_log)),
        linux_ci=ci,
        linux_log_sha256=digest(args.linux_log),
        assets=assets,
        visual_review=visual,
        limits=[
            "Original authored model, not a manufacturer replica or manufacturing certification.",
            "Discrete collision and sampled error/clearance; no continuous collision or strength proof.",
            "Mixed polygon/triangle patch reconstruction; arbitrary seam-crossing or quad retopology unsupported.",
            "A later parameter update regenerates the procedural root, not arbitrary hand edits; prior objects/files remain preserved.",
            "Visible fixed-land curvature, split light leaks and faceted groove highlights remain; no Class-A or photorealism claim.",
        ],
    )
    Path(args.output).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print("SURFACE_AUDIT_COMPLETE", args.output)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for key in [
        "run-root",
        "cli-root",
        "rejected-root",
        "ci-json",
        "windows-log",
        "host-log",
        "linux-log",
        "output",
    ]:
        p.add_argument("--" + key, required=True)
    build(p.parse_args())
