"""Versioned visual evidence with fixed capture settings and content hashes."""

import hashlib
import json
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(manifest, root, reference=None, require_closed=False):
    root = Path(root).resolve()
    if (
        manifest.get("schema") != 1
        or not isinstance(manifest.get("captures"), list)
        or not manifest["captures"]
    ):
        raise ValueError("Nonempty versioned capture manifest required")
    if manifest.get("settings_sha256") != fingerprint(manifest.get("settings")):
        raise ValueError("Capture settings changed")
    if reference is not None and manifest.get("reference_sha256") != fingerprint(
        reference
    ):
        raise ValueError("Frozen reference changed")
    names = set()
    for capture in manifest["captures"]:
        name = capture.get("id")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("Unique capture IDs required")
        names.add(name)
        path = (root / capture["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or unconfined capture")
        if file_hash(path) != capture.get("sha256"):
            raise ValueError("Capture content changed")
        if capture.get("settings_sha256") != manifest["settings_sha256"]:
            raise ValueError("Mismatched capture settings")
    required = set(manifest["settings"].get("required_captures", []))
    if not required or names != required:
        raise ValueError("Capture set differs from frozen requirements")
    defects = manifest.get("defects", [])
    if not defects or len({d.get("id") for d in defects}) != len(defects):
        raise ValueError("Nonempty unique defect register required")
    for defect in defects:
        if (
            defect.get("status") not in ("open", "resolved", "limitation")
            or type(defect.get("mandatory")) is not bool
        ):
            raise ValueError("Explicit defect status and priority required")
        roi = defect.get("roi_normalized", [])
        if (
            len(roi) != 4
            or not all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in roi)
            or not roi[0] < roi[2]
            or not roi[1] < roi[3]
        ):
            raise ValueError("Valid defect ROI required")
        if defect["status"] == "resolved" and (
            defect.get("evidence_capture") not in names or not defect.get("review_note")
        ):
            raise ValueError(
                "Resolved defects require inspected capture and review note"
            )
        if require_closed and defect["mandatory"] and defect["status"] != "resolved":
            raise ValueError("Unresolved mandatory defect: " + defect["id"])
    return {
        "captures": len(names),
        "open_mandatory": sum(
            d["mandatory"] and d["status"] != "resolved" for d in defects
        ),
        "integrity_passed": True,
        "visual_completion": all(
            not d["mandatory"] or d["status"] == "resolved" for d in defects
        ),
    }


def compare(before, after):
    """Compare manifests after independent file validation; do not score beauty."""
    if (
        before["settings_sha256"] != after["settings_sha256"]
        or before["reference_sha256"] != after["reference_sha256"]
    ):
        raise ValueError("Before/after cameras, lighting or references differ")
    if {c["id"] for c in before["captures"]} != {c["id"] for c in after["captures"]}:
        raise ValueError("Before/after view sets differ")
    return {
        "settings_match": True,
        "views": len(after["captures"]),
        "different_models": before["source_sha256"] != after["source_sha256"],
    }
