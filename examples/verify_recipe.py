"""Compare a saved recipe model with its audit. Use -- RUN_DIRECTORY."""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mesh_workbench import fairing, geometry

root = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
audit = json.loads((root / "audit.json").read_text())
bpy.ops.wm.open_mainfile(
    filepath=str(root / "result.blend"), load_ui=False, use_scripts=False
)
checked = []
for operation in audit["operations"]:
    if operation["op"] == "diagnose":
        expected = operation["result"]
        o = bpy.data.objects[expected["object"]]
        actual = geometry.inspect(o)
        for key in ["vertices", "faces", "nonmanifold_edges"]:
            assert actual[key] == expected[key]
        assert (
            fairing.components(o) == expected["components"]
            and fairing.overlap_candidates(o) == expected["overlap_candidates"]
        )
        checked.append(o.name)
for command in audit["recipe"]["operations"]:
    if command["op"] == "visible" and command.get("viewport"):
        for name in command["objects"]:
            o = bpy.data.objects[name]
            assert o.hide_render == o.hide_get() == (not command["value"])
visible = [
    o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render
]
all_closed = all(geometry.inspect(o)["nonmanifold_edges"] == 0 for o in visible)
report = {
    "audit_status": audit["status"],
    "operations": len(audit["operations"]),
    "diagnostics_match": checked,
    "visible_mesh_parts": len(visible),
    "viewport_matches_recipe": True,
    "all_visible_parts_manifold": all_closed,
}
(root / "reopen-verification.json").write_text(json.dumps(report, indent=2))
print("RECIPE_MODEL_REOPEN_OK", report)
