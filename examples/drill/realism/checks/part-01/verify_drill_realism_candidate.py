"""Fresh-process reversible cage checks on the actual drill, without saving it."""
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

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, sculpt


def verify(source, output):
    if output.exists():
        raise ValueError("Use a fresh verification path")
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    stock = bpy.data.objects[state["outputs"]["master_stock"]["object"]]
    master = bpy.data.objects[state["outputs"]["master"]["object"]]
    original = sculpt.coordinates(stock)
    active = sculpt.coordinates(master)
    history = json.loads(master["mw_layers"])
    cage = next(row for row in history if row["operation"] == "form_cage")
    layer = master.data.shape_keys.key_blocks[cage["name"]]
    initial_value = layer.value
    try:
        layer.value = 0
        restored = sculpt.coordinates(master)
    finally:
        layer.value = initial_value
    enabled = sculpt.coordinates(master)
    pin_ids = np.zeros(len(original), bool)
    for pin in cage["settings"]["pins"]:
        pin_ids |= np.linalg.norm(original-np.array(pin["center"]), axis=1) <= pin["fixed_radius"]
    if not pin_ids.any():
        raise ValueError("No vertices covered by declared pin neighborhoods")
    form = json.loads(master["mw_form_report"])
    report = {"blender": bpy.app.version_string,
              "scope": "native cage restoration and pin checks only; editing/motion gates remain",
              "disabled_error_mm": float(np.linalg.norm(restored-original, axis=1).max()),
              "reenabled_error_mm": float(np.linalg.norm(enabled-active, axis=1).max()),
              "pinned_vertices": int(pin_ids.sum()),
              "pin_error_mm": float(np.linalg.norm(active[pin_ids]-original[pin_ids], axis=1).max()),
              "maximum_displacement_mm": float(np.linalg.norm(active-original, axis=1).max()),
              "minimum_sampled_jacobian": form["minimum_sampled_jacobian"],
              "source_preserved": before_hash == hashlib.sha256(source.read_bytes()).hexdigest()}
    report["passed"] = (max(report[k] for k in ("disabled_error_mm", "reenabled_error_mm", "pin_error_mm")) <= 1e-5
                        and report["maximum_displacement_mm"] > 0
                        and report["minimum_sampled_jacobian"] > .05 and report["source_preserved"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print("NATIVE_CAGE_CHECK", json.dumps(report), flush=True)
    if not report["passed"]:
        raise ValueError("Native cage check failed")


if __name__ == "__main__":
    verify(*map(Path, sys.argv[sys.argv.index("--")+1:]))
