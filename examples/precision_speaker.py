"""Refine an existing speaker against a fixed authored target; -- SOURCE OUTPUT.

Preserves source bytes and old objects. Run the original field-speaker recipe
first, then pass its result.blend. No external assets or synthetic render images.
"""

import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    precision,
    reference,
    regions,
    candidates,
    geometry,
    models,
    sculpt,
    fairing,
    construction,
    attachments,
    sweep,
)
from mesh_workbench.runner import camera

source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output = Path(sys.argv[sys.argv.index("--") + 2]).resolve()
output.mkdir(parents=True, exist_ok=False)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
spec = json.loads((ROOT / "examples/speaker-target.json").read_text())
reference_hash = reference.fingerprint(spec)
(output / "target.json").write_text(json.dumps(spec, indent=2))
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
views = {
    "hero": {
        "position": [4, -7, 3.8],
        "target": [0, 0, 1.3],
        "scale": 4.5,
        "size": [768, 768],
    },
    "front": {
        "position": [0, -7, 1.3],
        "target": [0, 0, 1.3],
        "scale": 3.6,
        "size": [720, 640],
    },
    "detail": {
        "position": [3, -5, 3.8],
        "target": [0.72, 0, 2.12],
        "scale": 2.0,
        "size": [640, 640],
    },
}


def render(label, view):
    camera(**views[view])
    scene.cycles.samples = 32
    scene.render.filepath = str(output / (label + "-" + view + ".png"))
    floor = bpy.data.objects["Floor"]
    was_hidden = floor.hide_render
    try:
        if view == "front":
            floor.hide_render = True
        bpy.ops.render.render(write_still=True)
    finally:
        floor.hide_render = was_hidden


def hidden(obj):
    obj.hide_render = True
    obj.hide_set(True)


def material_from(obj, original):
    for m in bpy.data.objects[original].data.materials:
        obj.data.materials.append(m)


def assess(label, case, panel):
    reports = []
    for component, obj in [
        ("case_front", case),
        ("panel_front", panel),
        ("case_side", case),
    ]:
        report, actual, expected = reference.evaluate(
            obj, spec, component, supersample=2
        )
        reference.save_overlay(
            output / (label + "-" + component + ".png"), actual, expected
        )
        reports.append(report)
    checked = [case, panel]
    row = {
        "name": label,
        "reports": reports,
        "nonmanifold_edges": sum(
            geometry.inspect(o)["nonmanifold_edges"] for o in checked
        ),
        "overlap_candidates": sum(fairing.overlap_candidates(o) for o in checked),
    }
    print("CANDIDATE", json.dumps(row), flush=True)
    return row


baseline = assess("before", bpy.data.objects["Case"], bpy.data.objects["Plate R"])
for view in views:
    render("before", view)
original_coords = {
    n: sculpt.coordinates(bpy.data.objects[n]).copy()
    for n in ["Case", "Plate R", "Handle", "Grip"]
}
variant_objects = {}
rows = [baseline]
for label, case_radius, panel_radius in [("soft", 0.42, 0.34), ("fitted", 0.30, 0.23)]:
    c = dict(spec["construction"]["case"], corner_radius=case_radius)
    case = precision.rounded_panel(label + " case", **c)
    material_from(case, "Case")
    p = dict(spec["construction"]["panel"], corner_radius=panel_radius)
    base = precision.rounded_panel(label + " panel source", **p)
    material_from(base, "Plate R")
    cut = models.boolean(
        base, bpy.data.objects["Cutter L"], "DIFFERENCE", label + " panel L"
    )
    panel = models.boolean(
        cut, bpy.data.objects["Cutter R"], "DIFFERENCE", label + " panel"
    )
    for obj in [base, cut]:
        hidden(obj)
    variant_objects[label] = [case.name, panel.name]
    rows.append(assess(label, case, panel))
    hidden(case)
    hidden(panel)
ranking = candidates.rank(
    rows,
    list(spec["components"]),
    min_iou=spec["acceptance"]["component_iou_min"],
    max_boundary=spec["acceptance"]["boundary_mean_max_units"],
)
assert ranking[0]["name"] == "fitted" and ranking[0]["accepted"], ranking
alternatives = ["Case", "Plate R"] + sum(variant_objects.values(), [])
# Preserve the rejected alternative and an exact reversible visibility snapshot.
for label in ["soft", "fitted"]:
    candidates.activate(variant_objects[label], alternatives)
    render(label, "front")
    candidates.restore()
candidates.activate(variant_objects["fitted"], alternatives)
# Leave this transaction available for explicit restoration in the final .blend.
case = bpy.data.objects["fitted case"]
panel = bpy.data.objects["fitted panel"]

# Explicit G1 cubic handle, with mounting seats rather than an unsupported tube.
h = spec["construction"]["handle"]
w, t, r, b = h["half_width"], h["top"], h["corner_radius"], h["bottom"]
k = 4 * (math.sqrt(2) - 1) / 3
controls = [
    [
        [-w, 0, b],
        [-w, 0, b + (t - r - b) / 3],
        [-w, 0, b + 2 * (t - r - b) / 3],
        [-w, 0, t - r],
    ],
    [[-w, 0, t - r], [-w, 0, t - r + k * r], [-w + r - k * r, 0, t], [-w + r, 0, t]],
    [[-w + r, 0, t], [(-w + r) / 3, 0, t], [(w - r) / 3, 0, t], [w - r, 0, t]],
    [[w - r, 0, t], [w - r + k * r, 0, t], [w, 0, t - r + k * r], [w, 0, t - r]],
    [
        [w, 0, t - r],
        [w, 0, t - r - (t - r - b) / 3],
        [w, 0, t - r - 2 * (t - r - b) / 3],
        [w, 0, b],
    ],
]
handle = precision.bezier_tube(
    "Refined handle", controls, radius=h["tube_radius"], samples=16, segments=32
)
material_from(handle, "Handle")
hidden(bpy.data.objects["Handle"])
grip_centers = [[float(x), 0, t] for x in np.linspace(-0.58, 0.58, 41)]
grip = sweep.sweep(
    "Refined grip",
    grip_centers,
    [[0.085, 0.085]] * len(grip_centers),
    segments=48,
    reference=[0, 0, 1],
)
material_from(grip, "Grip")
hidden(bpy.data.objects["Grip"])
regions.define(grip, "grip crown", geometry.selection(grip, "VERT"))
seam = precision.bound_seam(
    grip,
    [[-0.53, -0.075, t + 0.035], [0, -0.075, t + 0.035], [0.53, -0.075, t + 0.035]],
    "Grip seam before",
    radius=0.004,
    offset=0.002,
    spacing=0.025,
)
material_from(seam, "Bezel L")
old_seam = sculpt.coordinates(seam).copy()
grip_before = sculpt.coordinates(grip).copy()
edit = regions.profile(
    grip, "grip crown", 0, 2, [[-0.58, 0], [0, 0.025], [0.58, 0]], label="Grip crown"
)
assert attachments.status(grip, seam)["status"] == "needs_refresh"
new_seam = precision.refresh_seam(grip, seam, "Grip seam fitted")
assert attachments.status(grip, new_seam)["status"] == "current"
np.testing.assert_array_equal(old_seam, sculpt.coordinates(seam))
hidden(seam)
# Undo proves the whole cross section moved together, retaining paired thickness.
grip.data.shape_keys.key_blocks[edit["layer"]].value = 0
undo_error = float(np.max(np.abs(sculpt.coordinates(grip) - grip_before)))
np.testing.assert_allclose(sculpt.coordinates(grip), grip_before, atol=1e-7)
grip.data.shape_keys.key_blocks[edit["layer"]].value = 1
for sign in [-1, 1]:
    seat = precision.rounded_panel(
        "Handle seat " + str(sign),
        [0.24, 0.28, 0.10],
        0.043,
        0.022,
        location=[sign * w, 0, 1.983],
    )
    material_from(seat, "Back gasket")
    collar = construction.revolve(
        "Handle collar " + str(sign),
        [(0.056, 0), (0.081, 0), (0.085, 0.008), (0.075, 0.07), (0.056, 0.07)],
        closed=True,
        segments=64,
        location=[sign * w, 0, 2.02],
    )
    material_from(collar, "Handle")
# Seated screw heads with real screwdriver slots; retain all original hardware.
for side, x in [("L", -1.1152), ("R", 1.1152)]:
    for z in [0.45, 1.65]:
        name = "Seated screw " + side + str(z)
        screw = construction.strut(
            name + " source", [x, -0.537, z], [x, -0.559, z], radius=0.032, segments=32
        )
        material_from(screw, "Bezel L")
        cutter = models.primitive(
            "cube", name + " slot", location=[x, -0.562, z], scale=[0.023, 0.009, 0.006]
        )
        head = models.boolean(screw, cutter, "DIFFERENCE", name)
        hidden(screw)
        hidden(cutter)
        hidden(bpy.data.objects["Screw " + side + str(z)])

# Use a frame behind the panel as a controlled dark perimeter reveal.
gasket = precision.rounded_panel(
    "Front gasket", [2.732, 0.022, 1.662], 0.246, 0.005, location=[0, -0.478, 1.05]
)
material_from(gasket, "Back gasket")

for name, coords in original_coords.items():
    np.testing.assert_array_equal(sculpt.coordinates(bpy.data.objects[name]), coords)
report = {
    "target_sha256": reference_hash,
    "source_sha256": source_hash,
    "blender": bpy.app.version_string,
    "candidates": rows,
    "ranking": ranking,
    "selected": "fitted",
    "grip_edit": edit,
    "seam_status": attachments.status(grip, new_seam),
    "source_objects_unchanged": True,
    "undo_max_error": undo_error,
    "limits": spec["limitations"],
}
checks = []
for obj in scene.objects:
    if obj.type == "MESH" and not obj.hide_render and obj.name != "Floor":
        info = geometry.inspect(obj)
        info["overlap_candidates"] = fairing.overlap_candidates(obj)
        checks.append(info)
report["geometry"] = checks
assert all(
    v["nonmanifold_edges"] == 0 and v["overlap_candidates"] == 0 for v in checks
), [(v["object"], v["nonmanifold_edges"], v["overlap_candidates"]) for v in checks]
for view in views:
    render("after", view)
camera(**views["hero"])
scene.cycles.samples = 32
bpy.ops.wm.save_as_mainfile(filepath=str(output / "refined-speaker.blend"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
assert (
    reference.fingerprint(
        json.loads((ROOT / "examples/speaker-target.json").read_text())
    )
    == reference_hash
)
(output / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PRECISION_SPEAKER_COMPLETE", json.dumps(ranking), flush=True)
