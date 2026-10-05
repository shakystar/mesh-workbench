"""Comparable measured candidates and persistent reversible visibility switching."""

import json
import math
import bpy


def rank(entries, components, min_iou=0.99, max_boundary=0.012):
    if not entries or not components or len(set(components)) != len(components):
        raise ValueError("Candidates and unique required components needed")
    if (
        not math.isfinite(min_iou)
        or not 0 <= min_iou <= 1
        or not math.isfinite(max_boundary)
        or max_boundary < 0
    ):
        raise ValueError("Invalid acceptance thresholds")
    fingerprints = set()
    sampling = {c: set() for c in components}
    names = set()
    result = []
    for entry in entries:
        if entry["name"] in names:
            raise ValueError("Duplicate candidate")
        names.add(entry["name"])
        reports = entry["reports"]
        if len(reports) != len(components) or {r["component"] for r in reports} != set(
            components
        ):
            raise ValueError("Incomplete or duplicate component evaluation")
        for r in reports:
            if (
                not math.isfinite(r["iou"])
                or not 0 <= r["iou"] <= 1
                or not math.isfinite(r["boundary_mean"])
                or r["boundary_mean"] < 0
            ):
                raise ValueError("Invalid metric")
            fingerprints.add(r["target_sha256"])
            sampling[r["component"]].add(tuple(r.get("sampling_size", [])))
        valid = entry["nonmanifold_edges"] == 0 and entry["overlap_candidates"] == 0
        passed = valid and all(
            r["iou"] >= min_iou and r["boundary_mean"] <= max_boundary for r in reports
        )
        result.append(
            {
                "name": entry["name"],
                "accepted": passed,
                "geometry_valid": valid,
                "mean_iou": sum(r["iou"] for r in reports) / len(reports),
            }
        )
    if any(len(sizes) != 1 for sizes in sampling.values()):
        raise ValueError("Candidate sampling resolutions differ")
    if len(fingerprints) != 1:
        raise ValueError("Different reference targets cannot be ranked together")
    return sorted(
        result,
        key=lambda r: (
            not r["accepted"],
            not r["geometry_valid"],
            -r["mean_iou"],
            r["name"],
        ),
    )


def activate(objects, alternatives):
    """Switch candidate objects; caller explicitly supplies all alternatives.

    Shared parts not in alternatives are untouched. One pending snapshot at a time.
    """
    scene = bpy.context.scene
    if "mw_candidate_visibility" in scene:
        raise ValueError("Restore previous visibility transaction first")
    names = set(alternatives)
    if (
        not objects
        or not set(objects) <= names
        or any(n not in scene.objects for n in names)
    ):
        raise ValueError("Unknown candidate object")
    snapshot = {
        n: {
            "render": scene.objects[n].hide_render,
            "viewport": scene.objects[n].hide_get(),
        }
        for n in sorted(names)
    }
    scene["mw_candidate_visibility"] = json.dumps(snapshot)
    for n in names:
        obj = scene.objects[n]
        obj.hide_render = n not in objects
        obj.hide_set(n not in objects)
    return snapshot


def restore():
    scene = bpy.context.scene
    if "mw_candidate_visibility" not in scene:
        raise ValueError("No candidate transaction")
    snapshot = json.loads(scene["mw_candidate_visibility"])
    if any(n not in scene.objects for n in snapshot):
        raise ValueError("Candidate removed; cannot restore all visibility")
    for n, state in snapshot.items():
        scene.objects[n].hide_render = state["render"]
        scene.objects[n].hide_set(state["viewport"])
    del scene["mw_candidate_visibility"]
    return snapshot
