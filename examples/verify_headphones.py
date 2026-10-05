"""Reopen and continue editing each native headphone: -- STUDY_OUTPUT."""

import hashlib, json, math, sys
from pathlib import Path
import bpy, numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    assembly,
    attachments,
    geometry,
    sculpt,
    refinement,
    pathmodel,
    joints,
    regions,
    fairing,
)

root = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
results = {}
for label in ("compact", "standard", "wide"):
    folder = root / label
    path = folder / "headphones.blend"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    audit = json.loads((folder / "audit.json").read_text())
    cup = bpy.data.objects["Left cup"]
    fixed = bpy.data.objects["Left cup repaired"]
    pattern = bpy.data.objects["Left detail"]
    np.testing.assert_array_equal(sculpt.coordinates(cup), np.load(folder / "cup.npy"))
    before = bpy.data.objects["Left cup defective"]
    key = fixed.data.shape_keys.key_blocks[audit["fairing"]["layer"]]
    key.value = 0
    np.testing.assert_array_equal(sculpt.coordinates(fixed), sculpt.coordinates(before))
    key.value = 1
    state = refinement._state(fixed, cup)
    source_weights = sculpt.protection(fixed, "edge")
    target_weights = sculpt.protection(cup, "edge")
    expected = np.asarray(
        [
            sum(source_weights[int(i)] * w for i, w in r.items())
            for r in state["provenance"]
        ]
    )
    np.testing.assert_allclose(target_weights, expected, atol=1e-7)
    # Independent spatial check: newly introduced points stay on the source triangle surface.
    tree = assembly._tree(fixed)
    coords = sculpt.coordinates(cup)
    distance = max(tree.find_nearest(Vector(p))[3] for p in coords)
    # BVH nearest-point arithmetic is float32 and can report a few ULPs even
    # at existing vertices. Also verify the stored barycentric provenance in float64.
    spatial_tolerance = float(np.spacing(np.float32(np.abs(coords).max())) * 8)
    assert distance < spatial_tolerance, (distance, spatial_tolerance)
    source_coords = sculpt.coordinates(fixed)
    provenance_coords = np.asarray(
        [
            sum((source_coords[int(i)] * w for i, w in record.items()), np.zeros(3))
            for record in state["provenance"]
        ]
    )
    provenance_error = float(np.linalg.norm(coords - provenance_coords, axis=1).max())
    assert provenance_error < 1e-5, provenance_error
    binding = json.loads(
        bpy.data.objects["Detail before subdivision"]["mw_surface_binding"]
    )
    migrated = refinement.transfer_binding(fixed, cup, binding)
    old = attachments.resolve(fixed, binding)
    new = attachments.resolve(cup, migrated)
    error = float(
        np.max(
            np.linalg.norm(
                np.asarray([h["position"] for h in old])
                - np.asarray([h["position"] for h in new]),
                axis=1,
            )
        )
    )
    assert error < 1e-5, error
    names = [n for j in json.loads(bpy.context.scene[joints.KEY]) for n in j["objects"]]
    snapshots = {n: sculpt.coordinates(bpy.data.objects[n]).copy() for n in names}
    fold = joints.inspect(
        {"Left": -math.pi / 4, "Right": math.pi / 4},
        ["Headband", "Headband pad"],
        steps=18,
    )
    assert fold["passed"]
    for n, arr in snapshots.items():
        np.testing.assert_array_equal(arr, sculpt.coordinates(bpy.data.objects[n]))
    try:
        joints.pose({"Left": -2, "Right": 2})
    except ValueError:
        pass
    else:
        raise AssertionError("Angle limit was not enforced")
    for n, arr in snapshots.items():
        np.testing.assert_array_equal(arr, sculpt.coordinates(bpy.data.objects[n]))
    # A subsequent edit moves the remapped anchors; refresh follows the refined topology.
    half = audit["span"] / 2
    edit = regions.radial_move(
        cup,
        "cup refinement",
        [-half - 10, 0, 55],
        20,
        [-0.2, 0, 0],
        label="Reopened refinement",
    )
    assert attachments.status(cup, pattern)["status"] == "needs_refresh"
    refreshed = attachments.refresh_relief(
        cup, pattern, "Reopened detail", max_distance=0.3
    )
    assert attachments.status(cup, refreshed)["status"] == "current"
    shift = float(
        np.max(
            np.linalg.norm(
                sculpt.coordinates(refreshed) - sculpt.coordinates(pattern), axis=1
            )
        )
    )
    assert shift > 0.05
    cup.data.shape_keys.key_blocks[edit["layer"]].value = 0
    np.testing.assert_array_equal(sculpt.coordinates(cup), np.load(folder / "cup.npy"))
    band = bpy.data.objects["Headband"]
    settings = json.loads(band["mw_path"])
    reshaped = pathmodel.reshape(
        band, [[x * 1.02, y, z] for x, y, z in settings["centers"]], "Reopened band"
    )
    measured = pathmodel.sections(reshaped)
    assert measured["radius_error_max"] < 1e-4
    for name in audit["geometry"]:
        obj = bpy.data.objects[name]
        assert geometry.inspect(obj)["nonmanifold_edges"] == 0
        assert fairing.overlap_candidates(obj) == 0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    results[label] = {
        "sha256": digest,
        "coordinates_match": True,
        "source_surface_sample_error": distance,
        "spatial_float32_tolerance": spatial_tolerance,
        "provenance_coordinate_error": provenance_error,
        "binding_transfer_error": error,
        "masks_verified": True,
        "fairing_undo_verified": True,
        "fold_passed": True,
        "motion_restored_exactly": True,
        "limits_enforced": True,
        "refined_followup_pattern_shift": shift,
        "reshaped_band_sections": measured,
        "saved_file_unchanged": True,
    }
    print("HEADPHONE_REOPEN", label, json.dumps(results[label]), flush=True)
sculpt.dump(root / "reopen-verification.json", results)
