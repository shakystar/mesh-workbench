"""Reopen both relief variants, independently sample clearance and source preservation."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import fairing, geometry, patterns, sculpt

args = sys.argv[sys.argv.index("--") + 1 :]
source = Path(args[0]).resolve()
folder = Path(args[1]).resolve()
report = json.loads((folder / "report.json").read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest() == report["source_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
original = sculpt.coordinates(bpy.data.objects["Ray body"]).copy()
result = {}
for variant in ["dense", "sparse"]:
    bpy.ops.wm.open_mainfile(
        filepath=str(folder / (variant + ".blend")), load_ui=False, use_scripts=False
    )
    body = bpy.data.objects["Ray body"]
    ob = bpy.data.objects["Pattern " + variant]
    np.testing.assert_array_equal(sculpt.coordinates(body), original)
    count = ob["mw_relief_count"]
    block = len(ob.data.vertices) // count
    half = block // 2
    assert fairing.components(ob) == [block] * count
    tree = patterns.tree(body)
    coords = [ob.matrix_world @ v.co for v in ob.data.vertices]
    probes = [p for i, p in enumerate(coords) if i % block < half]
    probes.extend(
        (coords[e.vertices[0]] + coords[e.vertices[1]]) / 2
        for e in ob.data.edges
        if all(i % block < half for i in e.vertices)
    )
    probes.extend(
        sum((coords[i] for i in f.vertices), Vector()) / len(f.vertices)
        for f in ob.data.polygons
        if all(i % block < half for i in f.vertices)
    )
    distances = []
    for p in probes:
        hit, n, _, _ = tree.find_nearest(p)
        distances.append((p - hit).dot(n))
    assert min(distances) > 0
    anchors = np.array(ob["mw_relief_anchors"]).reshape(-1, 3)
    bounds = [
        max(
            (Vector(p) - Vector(anchors[i])).length
            for p in coords[i * block : (i + 1) * block]
        )
        for i in range(count)
    ]
    gap = min(
        float(np.linalg.norm(anchors[i] - anchors[j])) - bounds[i] - bounds[j]
        for i in range(count)
        for j in range(i)
    )
    assert gap >= ob["mw_relief_gap"] - 1e-6
    assert (
        geometry.inspect(ob)["nonmanifold_edges"] == 0
        and fairing.overlap_candidates(ob) == 0
    )
    result[variant] = {
        "probes": len(probes),
        "minimum_clearance": min(distances),
        "minimum_bounding_sphere_gap": gap,
        "body_unchanged": True,
        "components": count,
    }
(folder / "reopen-verification.json").write_text(json.dumps(result, indent=2))
print("RELIEF_REOPEN_VERIFIED", result)
