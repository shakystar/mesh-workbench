"""Audit native study files; -- MANIFEST_JSON NEW_OUTPUT_JSON."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import fairing, geometry

args = sys.argv[sys.argv.index("--") + 1 :]
manifest = Path(args[0]).resolve()
output = Path(args[1]).resolve()
if output.exists():
    raise ValueError("Audit output exists")
items = json.loads(manifest.read_text())
report = {"blender": bpy.app.version_string, "designs": []}
for entry in items:
    path = (manifest.parent / entry["model"]).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    parts = []
    for obj in bpy.context.scene.objects:
        if (
            obj.type != "MESH"
            or obj.hide_render
            or obj.name in entry.get("exclude", [])
            or obj.name.startswith("Studio floor")
        ):
            continue
        stats = geometry.inspect(obj)
        stats["overlap_candidates"] = fairing.overlap_candidates(obj)
        assert stats["finite"] and stats["vertices"] > 0
        parts.append(stats)
    assert parts and path.stat().st_size > 0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    report["designs"].append(
        {
            "name": entry["name"],
            "model": entry["model"],
            "sha256": digest,
            "bytes": path.stat().st_size,
            "parts": parts,
            "part_count": len(parts),
            "vertices": sum(p["vertices"] for p in parts),
            "nonmanifold_edges": sum(p["nonmanifold_edges"] for p in parts),
            "overlap_candidates": sum(p["overlap_candidates"] for p in parts),
        }
    )
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    "STUDY_AUDIT",
    [
        (d["name"], d["part_count"], d["nonmanifold_edges"], d["overlap_candidates"])
        for d in report["designs"]
    ],
)
