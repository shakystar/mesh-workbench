"""Explicit metadata/recipe revision; preserve all original native objects."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import sys, json, hashlib
from pathlib import Path
import bpy

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, attachments, sculpt
from drill_assembly import blueprint


def migrate(source, output):
    source = Path(source).resolve()
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    state = nested.load()
    old = {
        key: (r["object"], attachments.revision(bpy.data.objects[r["object"]]))
        for key, r in state["outputs"].items()
    }
    path = ROOT / "examples/drill/assembly/recipes/drill-assembly-target.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    nodes, checks = blueprint(spec)
    result = nested.reconfigure(nodes, checks)
    result["original_objects_preserved"] = all(
        attachments.revision(bpy.data.objects[name]) == revision
        for name, revision in old.values()
    )
    current = nested.load()
    result["same_geometry"] = {
        key: attachments.revision(bpy.data.objects[r["object"]]) == old[key][1]
        for key, r in current["outputs"].items()
    }
    if not result["original_objects_preserved"] or not all(
        result["same_geometry"].values()
    ):
        raise AssertionError("Frame-only migration changed geometry")
    bpy.context.scene["mw_drill_spec_sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
    result["source_preserved"] = (
        hashlib.sha256(source.read_bytes()).hexdigest() == digest
    )
    result["spec_revision"] = spec["revision"]
    sculpt.dump(out / "migration.json", result)
    print("MIGRATED", out, "updated", result["updated"], flush=True)


if __name__ == "__main__":
    migrate(*sys.argv[sys.argv.index("--") + 1 :])
