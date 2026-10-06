"""Fresh-process drill checks and subsequent assembly editing, without overwriting input."""

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import sculpt, geometry, attachments, assembly, regions, remesh

folder = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
path = folder / "drill.blend"
digest = hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
audit = json.loads((folder / "audit.json").read_text())
obj = bpy.data.objects[audit["housing"]]
source = bpy.data.objects[audit["source"]]
np.testing.assert_array_equal(sculpt.coordinates(obj), np.load(folder / "housing.npy"))
state = remesh._state(source, obj)
source_xyz = sculpt.coordinates(source)
target_xyz = sculpt.coordinates(obj)
for a, b in state["pinned_pairs"]:
    np.testing.assert_array_equal(source_xyz[a], target_xyz[b])
mask = json.loads(obj["mw_masks"])["panel"]
assert mask["topology"] == sculpt.topology(obj)
source_group = source.vertex_groups["panel_weight"]
target_group = obj.vertex_groups[mask["group"]]


def weight(group, i):
    try:
        return group.weight(i)
    except RuntimeError:
        return 0.0


mask_error = max(
    abs(
        weight(target_group, i)
        - sum(weight(source_group, v) * w for v, w in zip(r["vertices"], r["weights"]))
    )
    for i, r in enumerate(state["mapping"])
)
assert mask_error < 1e-6, mask_error
uv_error = 0
for loop in obj.data.loops:
    p = target_xyz[loop.vertex_index]
    actual = np.array(obj.data.uv_layers["HousingUV"].data[loop.index].uv)
    uv_error = max(
        uv_error, float(np.linalg.norm(actual - [p[0] / 120, (p[2] - 130) / 60]))
    )
assert uv_error < 1e-5, uv_error
region = regions.resolve(obj, "service_panel")
assert region["indices"]
graph = assembly.load()
pattern = bpy.data.objects[graph["nodes"]["fasteners"]["object"]]
binding = json.loads(pattern["mw_surface_binding"])
old_points = np.array([h["position"] for h in attachments.resolve(obj, binding)])
assert attachments.status(obj, pattern)["status"] == "current"
# Acceptance failure must leave graph, objects, mesh pointers and coordinates intact.
old_graph = bpy.context.scene[assembly.KEY]
old_objects = set(bpy.data.objects)
old_meshes = set(bpy.data.meshes)
with patch.object(assembly, "validate", return_value=[{"passed": False}]):
    try:
        assembly.update(
            "housing",
            {
                "kind": "radial",
                "center": [15, -25, 160],
                "radius": 30,
                "delta": [0, -0.15, 0],
            },
        )
    except assembly.Rejected as exc:
        assert exc.report["rolled_back"]
    else:
        raise AssertionError("Injected failure unexpectedly committed")
assert old_graph == bpy.context.scene[assembly.KEY]
assert old_objects == set(bpy.data.objects) and old_meshes == set(bpy.data.meshes)
np.testing.assert_array_equal(sculpt.coordinates(obj), target_xyz)
result = assembly.update(
    "housing",
    {"kind": "radial", "center": [15, -25, 160], "radius": 30, "delta": [0, -0.15, 0]},
)
assert result["passed"] and set(result["updated"]) == {"housing", "fasteners"}, result
new_points = np.array(
    [
        h["position"]
        for h in attachments.resolve(obj, json.loads(pattern["mw_surface_binding"]))
    ]
)
movement = float(np.linalg.norm(new_points - old_points, axis=1).max())
assert movement > 0.025, movement
assert geometry.inspect(obj)["nonmanifold_edges"] == 0
assembly.load()
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
# Independent reversible manual edit on a fork of the remeshed housing.
copy = geometry.fork(obj, "Follow-up edit fork")
before = sculpt.coordinates(copy).copy()
selection = (
    regions.resolve(copy, "service_panel")
    if "mw_regions" in copy
    else geometry.selection(copy, "VERT", box=[[0, -40, 145], [30, -15, 175]])
)
geometry.move(copy, selection, [0, -0.04, 0], label="Reopen detail edit")
copy.data.shape_keys.key_blocks[-1].value = 0
bpy.context.view_layer.update()
np.testing.assert_allclose(sculpt.coordinates(copy), before, atol=1e-5)
output = {
    "passed": True,
    "blender": bpy.app.version_string,
    "sha256": digest,
    "pinned_vertices": len(state["pinned_pairs"]),
    "pinned_error": 0,
    "mask_error": mask_error,
    "uv_error": uv_error,
    "region_vertices": len(region["indices"]),
    "source_preserved": True,
    "assembly_failure_rollback": True,
    "follow_up_assembly": result,
    "attachment_movement": movement,
    "reversible_edit": True,
}
sculpt.dump(folder / "reopen-verification.json", output)
print("DRILL_REOPEN_COMPLETE", json.dumps(output), flush=True)
