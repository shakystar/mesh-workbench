"""Usage: Blender --python examples/assembly_mouse.py -- BASE_BLEND NEW_OUTPUT [--quick]."""

import hashlib
import json
import math
import sys
from itertools import combinations
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import assembly, attachments, motion, sculpt
from mesh_workbench.runner import camera

args = sys.argv[sys.argv.index("--") + 1 :]
source, output = Path(args[0]).resolve(), Path(args[1]).resolve()
output.mkdir(parents=True, exist_ok=False)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
quick = "--quick" in args


def setup():
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    master = bpy.data.objects["Mouse master"]
    classes = {
        name: []
        for name in ["Upper housing", "Lower housing", "Left button", "Right button"]
    }
    for i, (y, theta) in enumerate(json.loads(master["mw_loft_face_params"])):
        if theta >= math.pi:
            name = "Lower housing"
        elif -52 <= y <= -10 and 0.33 <= theta <= 1.48:
            name = "Right button"
        elif -52 <= y <= -10 and 1.66 <= theta <= 2.79:
            name = "Left button"
        elif -44 <= y <= -28 and 1.48 < theta < 1.66:
            continue
        else:
            name = "Upper housing"
        classes[name].append(i)
    nodes = {"master": {"kind": "source", "object": master.name}}
    ids = {
        "upper": "Upper housing",
        "lower": "Lower housing",
        "left": "Left button",
        "right": "Right button",
    }
    for key, name in ids.items():
        nodes[key] = {
            "kind": "shell",
            "object": name,
            "deps": ["master"],
            "faces": classes[name],
            "options": {"thickness": 1.6, "trim": 0.35},
        }
    for key, name in [
        ("grip", "Grip fitted"),
        ("dpi", "DPI button"),
        ("accent", "Crown accent"),
    ]:
        obj = bpy.data.objects[name]
        if key != "accent":
            attachments.bind_relief(master, obj, max_distance=0.3)
        nodes[key] = {
            "kind": "seam" if key == "accent" else "relief",
            "object": name,
            "deps": ["master"],
            "binding": json.loads(obj["mw_surface_binding"]),
            "options": json.loads(
                obj["mw_seam_settings" if key == "accent" else "mw_relief_settings"]
            ),
        }
    wheel = bpy.data.objects["Scroll wheel"]
    binding = attachments.bind(master, [list(wheel.location)], max_distance=10)
    anchor = attachments.resolve(master, binding)[0]["position"]
    nodes["wheel"] = {
        "kind": "anchor",
        "object": wheel.name,
        "deps": ["master"],
        "binding": binding,
        "offset": (np.asarray(wheel.location) - anchor).tolist(),
    }
    checks = [{"kind": "thickness", "nodes": [k]} for k in ids]
    checks += [
        {"kind": "gap", "nodes": ["upper", k]} for k in ["lower", "left", "right"]
    ]
    checks += [{"kind": "clearance", "nodes": [k, "upper"]} for k in ["grip", "dpi"]]
    checks += [
        {"kind": "intersection", "nodes": [a, b]}
        for a, b in combinations([*ids, "wheel"], 2)
    ]
    assembly.register("Asymmetric mouse", nodes, checks)
    return master


def render(path):
    if quick:
        return
    camera(position=[-175, -210, 165], target=[0, 0, 21], scale=166, size=[800, 800])
    bpy.context.scene.cycles.samples = 24
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


variants = {
    "width": {"kind": "dimension", "axis": 0, "delta": 6},
    "height": {"kind": "dimension", "axis": 2, "delta": 4},
    "thumb": {
        "kind": "radial",
        "center": [-31, -14, 14],
        "radius": 24,
        "delta": [2, 0, 0],
        "normalize_peak": True,
    },
}
audit = {
    "blender": bpy.app.version_string,
    "source_sha256": source_hash,
    "variants": {},
}
for label, edit in variants.items():
    master = setup()
    folder = output / label
    folder.mkdir()
    before = sculpt.coordinates(master).copy()
    if label == "width":
        render(output / "before.png")
    report = assembly.update("master", edit)
    after = sculpt.coordinates(master)
    report["before_dimensions"] = np.ptp(before, axis=0).tolist()
    report["after_dimensions"] = np.ptp(after, axis=0).tolist()
    report["maximum_vertex_shift"] = float(np.linalg.norm(after - before, axis=1).max())
    if edit["kind"] == "dimension":
        assert (
            abs(
                (np.ptp(after, axis=0) - np.ptp(before, axis=0))[edit["axis"]]
                - edit["delta"]
            )
            < 1e-4
        )
    else:
        outside = (
            np.linalg.norm(before - np.asarray(edit["center"]), axis=1)
            >= edit["radius"]
        )
        np.testing.assert_array_equal(before[outside], after[outside])
        report["pinned_vertices"] = int(outside.sum())
        assert abs(report["maximum_vertex_shift"] - 2) < 1e-4
    np.save(folder / "master.npy", after)
    graph = assembly.load()
    # Reject excessive deformation after a successful commit; preserve all current state.
    state = {
        k: (
            o.data,
            sculpt.coordinates(o).copy(),
            o.matrix_world.copy(),
            o.hide_render,
            o.hide_get(),
            assembly._props(o),
        )
        for k, n in graph["nodes"].items()
        for o in [bpy.data.objects[n["object"]]]
    }
    graph_text = bpy.context.scene[assembly.KEY]
    names = set(bpy.data.objects.keys())
    try:
        assembly.update("master", {"kind": "dimension", "axis": 0, "delta": -65})
    except assembly.Rejected as exc:
        report["rejected_update"] = exc.report
    else:
        raise AssertionError("Expected invalid narrowed shell to fail")
    assert bpy.context.scene[assembly.KEY] == graph_text
    assert set(bpy.data.objects.keys()) == names
    for k, (mesh, coords, matrix, hr, hv, props) in state.items():
        obj = bpy.data.objects[graph["nodes"][k]["object"]]
        assert (
            obj.data == mesh
            and obj.matrix_world == matrix
            and obj.hide_render == hr
            and obj.hide_get() == hv
        )
        assert assembly._props(obj) == props
        np.testing.assert_array_equal(sculpt.coordinates(obj), coords)
    report["exact_rollback_verified"] = True
    obstacles = [
        bpy.data.objects[n]
        for n in ["Upper housing", "Lower housing", "Right button", "Scroll wheel"]
    ]
    report["button_motion"] = motion.inspect(
        bpy.data.objects["Left button"], obstacles, translation=[0, 0, -0.6], steps=12
    )
    report["button_short_motion"] = motion.inspect(
        bpy.data.objects["Left button"], obstacles, translation=[0, 0, -0.15], steps=12
    )
    report["wheel_motion"] = motion.inspect(
        bpy.data.objects["Scroll wheel"],
        [
            bpy.data.objects[n]
            for n in ["Upper housing", "Lower housing", "Left button", "Right button"]
        ],
        angle=math.tau,
        axis=[1, 0, 0],
        steps=32,
    )
    render(folder / "after.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "model.blend"))
    sculpt.dump(folder / "audit.json", report)
    audit["variants"][label] = {
        "updated": report["updated"],
        "unchanged": report["unchanged"],
        "dimensions": report["after_dimensions"],
        "button_motion_passed": report["button_motion"]["passed"],
        "wheel_motion_passed": report["wheel_motion"]["passed"],
        "rollback": True,
    }
    print("ASSEMBLY_VARIANT", label, json.dumps(audit["variants"][label]), flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
sculpt.dump(output / "audit.json", audit)
print("ASSEMBLY_MOUSE_COMPLETE", flush=True)
