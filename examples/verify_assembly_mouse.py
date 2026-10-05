"""Fresh-process verification: -- ASSEMBLY_OUTPUT."""

import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import assembly, sculpt, geometry, fairing, motion

root = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
results = {}
for label in ("width", "height", "thumb"):
    folder = root / label
    path = folder / "model.blend"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    graph = assembly.load()
    assert graph["revision"] == 1
    np.testing.assert_array_equal(
        sculpt.coordinates(bpy.data.objects["Mouse master"]),
        np.load(folder / "master.npy"),
    )
    reports = assembly.validate(graph)
    assert all(r["passed"] for r in reports)
    assert not any(o.name.startswith("MW stage ") for o in bpy.data.objects)
    for node in graph["nodes"].values():
        obj = bpy.data.objects[node["object"]]
        assert not geometry.inspect(obj)["nonmanifold_edges"]
        assert not fairing.overlap_candidates(obj)
    saved_revisions = {
        k: assembly.attachments.revision(bpy.data.objects[n["object"]])
        for k, n in graph["nodes"].items()
    }
    moving = bpy.data.objects["Left button"]
    obstacles = [
        bpy.data.objects[n]
        for n in ("Upper housing", "Lower housing", "Right button", "Scroll wheel")
    ]
    button_report = motion.inspect(
        moving, obstacles, translation=[0, 0, -0.6], steps=12
    )
    assert not button_report["passed"]
    assert any(r["moving_triangle_centers_preview"] for r in button_report["samples"])
    for k, n in graph["nodes"].items():
        assert (
            assembly.attachments.revision(bpy.data.objects[n["object"]])
            == saved_revisions[k]
        )
    sculpt.dump(folder / "reopened-motion.json", button_report)
    # Reopened graph remains operational; another local edit traverses saved recipes.
    followup = assembly.update(
        "master",
        {
            "kind": "radial",
            "center": [-31, -14, 14],
            "radius": 24,
            "delta": [0.1, 0, 0],
        },
    )
    assert followup["passed"] and followup["revision"] == 2
    assert "right" in followup["unchanged"] and "wheel" in followup["unchanged"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    results[label] = {
        "sha256": digest,
        "coordinates_match": True,
        "checks_passed": len(reports),
        "followup_updated": followup["updated"],
        "followup_unchanged": followup["unchanged"],
        "saved_file_unchanged": True,
    }
sculpt.dump(root / "reopen-verification.json", results)
print("ASSEMBLY_REOPEN_OK", json.dumps(results), flush=True)
