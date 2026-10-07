"""Export the frozen surface graph as a standalone public CLI recipe."""

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
from drill_surface import surface_blueprint

spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())
nodes, checks = surface_blueprint(spec)
recipe = {
    "version": 1,
    "units": "mm",
    "operations": [
        {
            "op": "nested_initialize",
            "name": "Detailed cordless drill",
            "nodes": nodes,
            "parameters": spec["parameters"],
            "ranges": spec["parameter_ranges"],
            "checks": checks,
        },
        {"op": "nested_update", "parameters": {"grip_width": 0.25}},
        {
            "op": "nested_update",
            "remesh_request": {
                "part": "master",
                "method": "rebuild",
                "query": {
                    "box": [[-43, -40, 72], [-12, -5, 109]],
                    "normal": [0, -1, 0],
                    "normal_min": 0.8,
                    "components": 1,
                },
                "options": {
                    "target_length": 2,
                    "iterations": 6,
                    "relaxation": 0.5,
                    "max_error": 0.09,
                },
            },
        },
        {"op": "nested_status"},
    ],
}
(ROOT / "examples/drill-surface.json").write_text(json.dumps(recipe, indent=2) + "\n")
rejected = {
    "version": 1,
    "source": "../runs/drill-surface-cli-08/result.blend",
    "operations": [{"op": "nested_update", "parameters": {"grip_width": 100}}],
}
(ROOT / "examples/drill-surface-rejected.json").write_text(
    json.dumps(rejected, indent=2) + "\n"
)
print("SURFACE_RECIPES_EXPORTED")
