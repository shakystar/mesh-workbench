"""Freeze authored guide evidence and ray-selected landmarks before candidates."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "examples"))
from drill_realism_guides import camera_basis, project, resolve_parts, rings


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trees(parts):
    result = {}
    for key, design in parts.items():
        sections = rings(design)
        vertices = np.concatenate(sections).tolist()
        n = len(sections[0])
        faces = []
        for i in range(len(sections)-1):
            for j in range(n):
                a, b = i*n+j, i*n+(j+1)%n
                faces.extend([(a, b, b+n), (a, b+n, a+n)])
        for offset in (0, (len(sections)-1)*n):
            faces.extend((offset, offset+j, offset+j+1) for j in range(1,n-1))
        result[key] = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    return result


def freeze(directory):
    output = directory / "freeze.json"
    if output.exists():
        raise ValueError("Existing freeze must be preserved")
    target_path = ROOT / "examples/drill/realism/recipes/part-01/drill-realism-target.json"
    sections_path = ROOT / "examples/drill/realism/recipes/part-01/drill-realism-guide-sections.json"
    target = json.loads(target_path.read_text())
    guide = json.loads(sections_path.read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["target_sha256"] != sha(target_path) or manifest["sections_sha256"] != sha(sections_path):
        raise ValueError("Guide evidence is stale")
    for view in manifest["views"].values():
        for item in view["parts"].values():
            for prefix in ("", "visible_"):
                if sha(directory / item[prefix+"path"]) != item[prefix+"sha256"]:
                    raise ValueError("Guide mask changed")
        if sha(directory / view["assembly_path"]) != view["assembly_sha256"]:
            raise ValueError("Guide assembly mask changed")
    references = trees(resolve_parts(guide, target))
    landmarks = []
    for query in target["landmark_queries"]:
        hit = references[query["part"]].ray_cast(Vector(query["origin"]), Vector(query["direction"]), 1000)
        if hit[0] is None:
            raise ValueError("Missing authored landmark " + query["id"])
        landmarks.append({**query, "expected_xyz": list(hit[0])})
    views = {}
    for name in target["comparison"]["primary_views"]:
        view = target["capture"]["views"][name]
        right, up, _ = camera_basis(view)
        outward = Vector(np.cross(right, up))
        visible, hidden = [], []
        for item in landmarks:
            origin = Vector(item["expected_xyz"]) + outward*.01
            occluded = any(tree.ray_cast(origin, outward, 1000)[0] is not None
                           for tree in references.values())
            (hidden if occluded else visible).append(item["id"])
        if len(visible) < 3:
            raise ValueError("Too few visible authored landmarks: " + name)
        views[name] = {"visible_landmarks": visible, "occluded_landmarks": hidden,
                       "count": len(visible),
                       "expected_pixels": {item["id"]: project([item["expected_xyz"]], view, manifest["size"][0])[0].tolist()
                                           for item in landmarks if item["id"] in visible}}
    files = ["examples/drill/realism/recipes/part-01/drill-realism-target.json", "examples/drill/realism/recipes/part-01/drill-realism-guide-sections.json",
             "examples/drill/realism/scripts/part-01/drill_realism_guides.py", "examples/drill/surface/recipes/drill-surface-target.json"]
    report = {"schema": 1, "kind": "original-design evaluation freeze; not candidate acceptance",
              "blender": bpy.app.version_string,
              "inputs": {file: sha(ROOT / file) for file in files},
              "guide_manifest_sha256": sha(directory / "manifest.json"),
              "landmarks": landmarks, "views": views,
              "policy": target["comparison"]["scoring_policy"],
              "commercial_photo_calibration": "unavailable; no metric claim",
              "baseline_preserved": sha(ROOT / "runs/drill/drill-surface-06/drill.blend") == target["baseline_sha256"]}
    if not report["baseline_preserved"]:
        raise ValueError("Baseline hash differs")
    output.write_text(json.dumps(report, indent=2)+"\n")
    print("AUTHORED_FREEZE", json.dumps({"landmarks": len(landmarks), "visible_per_view":
          {k:v["count"] for k,v in views.items()}, "baseline_preserved": True}), flush=True)


if __name__ == "__main__":
    freeze(Path(sys.argv[sys.argv.index("--")+1]))
