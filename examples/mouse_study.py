"""Asymmetric mouse design study. Factory Blender invocation: -- NEW_OUTPUT."""

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
    loft,
    shells,
    sections,
    regions,
    geometry,
    sculpt,
    reference,
    candidates,
    relief,
    attachments,
    precision,
    materials,
    construction,
    fairing,
)
from mesh_workbench.runner import camera

output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output.mkdir(parents=True, exist_ok=False)
spec = json.loads((ROOT / "examples/mouse-target.json").read_text())
ref = json.loads((ROOT / "examples/mouse-reference.json").read_text())
assert ref["source_brief_sha256"] == reference.fingerprint(spec)
(output / "target.json").write_text(json.dumps(spec, indent=2))
(output / "reference.json").write_text(json.dumps(ref, indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001


def hide(obj):
    obj.hide_render = True
    obj.hide_set(True)


def show(obj):
    obj.hide_render = False
    obj.hide_set(False)


def material(obj, name, color, metallic=0, roughness=0.4):
    materials.assign([obj], name, [*color, 1], metallic=metallic, roughness=roughness)


def matcopy(obj, source):
    for m in source.data.materials:
        obj.data.materials.append(m)


floor = construction.rounded_box(
    "Studio floor", [1800, 1800, 2], location=[0, 0, -1], radius=0.3
)
material(floor, "Studio", [0.055, 0.07, 0.09], roughness=0.65)
for name, pos, energy, size in [
    ("Key", [-150, -160, 240], 1600000, 160),
    ("Fill", [180, -20, 120], 900000, 160),
    ("Rim", [-20, 170, 190], 1900000, 150),
]:
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    scene.collection.objects.link(light)
    light.location = pos
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (
        (geometry.vector([0, 0, 15]) - light.location)
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
views = {
    "hero": {
        "position": [-175, -210, 165],
        "target": [0, 0, 21],
        "scale": 166,
        "size": [800, 800],
    },
    "top": {
        "position": [0, 0, 240],
        "target": [0, 0, 0],
        "scale": 100,
        "size": [600, 840],
    },
    "side": {
        "position": [-220, -5, 50],
        "target": [0, 0, 20],
        "scale": 145,
        "size": [840, 480],
    },
    "detail": {
        "position": [-150, -115, 75],
        "target": [-22, -15, 20],
        "scale": 78,
        "size": [720, 600],
    },
}


def render(label, view):
    if "--geometry-only" in sys.argv:
        return
    camera(**views[view])
    scene.cycles.samples = 32
    old = floor.hide_render
    if view == "top":
        floor.hide_render = True
    try:
        scene.render.filepath = str(output / (label + "-" + view + ".png"))
        bpy.ops.render.render(write_still=True)
    finally:
        floor.hide_render = old


def evaluate(label, obj):
    reports = []
    for key in ["top", "side", "front"]:
        result, a, e = reference.evaluate(obj, ref, key)
        reference.save_overlay(output / (label + "-" + key + "-error.png"), a, e)
        reports.append(result)
    measured = [
        sections.compare(sections.cut(obj, 1, c["y"]), c["bounds"])
        for c in ref["section_bounds"]
    ]
    row = {
        "name": label,
        "reports": reports,
        "sections": measured,
        "section_error_max": max(s["bound_error_max"] for s in measured),
        "nonmanifold_edges": geometry.inspect(obj)["nonmanifold_edges"],
        "overlap_candidates": fairing.overlap_candidates(obj),
    }
    row["constraint_violations"] = int(
        row["section_error_max"] > spec["acceptance"]["section_bound_error_max_mm"]
    )
    print(
        "MOUSE_CANDIDATE",
        json.dumps({k: v for k, v in row.items() if k != "sections"}),
        flush=True,
    )
    return row


# Baseline is deliberately a simpler symmetric guide loft, preserved verbatim.
coarse = json.loads(json.dumps(spec["sections"]))
for section in coarse:
    section["left"] = section["right"] = (section["left"] + section["right"]) / 2
    section["top"] = spec["seam_height"] + (section["top"] - spec["seam_height"]) * 0.86
baseline = loft.create("Baseline master", coarse, rows=72, segments=96)
material(baseline, "Baseline graphite", [0.08, 0.11, 0.14])
baseline_coords = sculpt.coordinates(baseline).copy()
rows = [evaluate("baseline", baseline)]
for v in ["hero", "top", "side"]:
    render("baseline", v)
hide(baseline)
master = loft.create(
    "Mouse master",
    spec["sections"],
    seam_height=spec["seam_height"],
    tilt=spec["tilt"],
    rows=128,
    segments=128,
    end_refinement=0.75,
)
material(master, "Body enamel", [0.10, 0.29, 0.30], metallic=0.18, roughness=0.32)
rows.append(evaluate("guided", master))
original = sculpt.coordinates(master).copy()
np.save(output / "master-before.npy", original)
edit = spec["local_edit"]
sel = geometry.selection(
    master, "VERT", sphere={"center": edit["center"], "radius": edit["radius"]}
)
regions.define(master, edit["name"], sel)
# Grip details are attached before the thumb recess, then regenerated after it.
points = [[-50, y, z] for y in [-32, -24, -16, -8, 0, 8, 16] for z in [14.5, 17.5]]
dots = relief.dots(
    master,
    points,
    "Grip before",
    radii=0.7,
    height=0.16,
    embed=0.06,
    clearance=0.08,
    segments=16,
    rings=2,
    direction=[1, 0, 0],
    max_distance=65,
    gap=0.4,
)
material(dots, "Grip rubber", [0.017, 0.028, 0.03], roughness=0.7)
attachments.bind_relief(master, dots, max_distance=0.1)
old_dots = sculpt.coordinates(dots).copy()
move = regions.radial_move(
    master,
    edit["name"],
    edit["center"],
    edit["radius"],
    edit["displacement"],
    label="Thumb recess",
)
assert attachments.status(master, dots)["status"] == "needs_refresh"
new_dots = attachments.refresh_relief(master, dots, "Grip fitted", max_distance=0.2)
hide(dots)
np.testing.assert_array_equal(old_dots, sculpt.coordinates(dots))
assert attachments.status(master, new_dots)["status"] == "current"
current = sculpt.coordinates(master).copy()
outside = sorted(set(range(len(original))) - set(sel["indices"]))
np.testing.assert_array_equal(current[outside], original[outside])
master.data.shape_keys.key_blocks[move["layer"]].value = 0
undo_error = float(np.max(np.abs(sculpt.coordinates(master) - original)))
assert undo_error < 1e-6
master.data.shape_keys.key_blocks[move["layer"]].value = 1
# Independent palm-height layer: retain the rejected height candidate disabled.
palm_selection = geometry.selection(
    master, "VERT", sphere={"center": [3, 22, 39], "radius": 22}
)
regions.define(master, "palm support", palm_selection)
thumb_state = sculpt.coordinates(master).copy()
palm_edit = regions.radial_move(
    master, "palm support", [3, 22, 39], 22, [0, 0, 2], label="Raised palm trial"
)
rows.append(evaluate("raised-palm", master))
palm_outside = sorted(set(range(len(thumb_state))) - set(palm_selection["indices"]))
np.testing.assert_array_equal(
    sculpt.coordinates(master)[palm_outside], thumb_state[palm_outside]
)
master.data.shape_keys.key_blocks[palm_edit["layer"]].value = 0
np.testing.assert_array_equal(sculpt.coordinates(master), thumb_state)
rows.append(evaluate("refined", master))
ranking = candidates.rank(
    rows,
    ["top", "side", "front"],
    min_iou=spec["acceptance"]["silhouette_iou_min"],
    max_boundary=0.5,
)
assert (
    rows[-1]["section_error_max"] <= spec["acceptance"]["section_bound_error_max_mm"]
), rows[-1]
assert next(r for r in ranking if r["name"] == "refined")["accepted"], ranking

params = json.loads(master["mw_loft_face_params"])
classes = {
    "Upper housing": [],
    "Lower housing": [],
    "Left button": [],
    "Right button": [],
}
opening = []
for i, (y, theta) in enumerate(params):
    if theta >= math.pi:
        part = "Lower housing"
    elif -52 <= y <= -10 and 0.33 <= theta <= 1.48:
        part = "Right button"
    elif -52 <= y <= -10 and 1.66 <= theta <= 2.79:
        part = "Left button"
    elif -44 <= y <= -28 and 1.48 < theta < 1.66:
        opening.append(i)
        continue
    else:
        part = "Upper housing"
    classes[part].append(i)
parts = {}
for name, ids in classes.items():
    part = shells.extract(
        master,
        geometry.selection(master, "FACE", indices=ids),
        name,
        thickness=1.6,
        trim=0.35,
    )
    parts[name] = part
    color = (
        [0.075, 0.095, 0.11]
        if name == "Lower housing"
        else ([0.15, 0.36, 0.36] if "button" in name else [0.10, 0.29, 0.30])
    )
    material(
        part,
        name + " material",
        color,
        metallic=0.12 if name != "Lower housing" else 0,
        roughness=0.34,
    )
hide(master)
thickness = [shells.thickness(p, method="nearest") for p in parts.values()]
normal_thickness = [shells.thickness(p, method="normal") for p in parts.values()]
(output / "normal-thickness.json").write_text(json.dumps(normal_thickness, indent=2))
gaps = [
    shells.gap(parts["Upper housing"], parts[n])
    for n in ["Lower housing", "Left button", "Right button"]
]
for label, values in [("THICKNESS", thickness), ("GAP", gaps)]:
    print(
        label,
        json.dumps([{k: v for k, v in r.items() if k != "violations"} for r in values]),
        flush=True,
    )
    (output / (label.lower() + ".json")).write_text(json.dumps(values, indent=2))
if not all(r["passed"] for r in thickness + gaps):
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "failed-gauges.blend"))
    raise AssertionError("Final gauges failed; see reports")

# Deliberately invalid thickness candidate, retained with native red location markers.
thin = shells.extract(
    master,
    geometry.selection(master, "FACE", indices=classes["Upper housing"]),
    "Rejected thin housing",
    thickness=0.7,
    trim=0.35,
)
matcopy(thin, parts["Upper housing"])
rejected = shells.thickness(thin)
assert not rejected["passed"]
markers = shells.markers("Thin wall violations", rejected, radius=0.9, limit=70)
material(markers, "Gauge failure", [0.9, 0.02, 0.01], roughness=0.5)
(output / "rejected-thickness.json").write_text(json.dumps(rejected, indent=2))
for p in parts.values():
    hide(p)
hide(new_dots)
render("rejected-thin", "hero")
hide(thin)
hide(markers)
for p in parts.values():
    show(p)
show(new_dots)

# Scroll wheel crosses an actual opening in the housing.
y = -36
wheel_z = sections.cut(master, 1, y)["bounds"][1][2] - 1.5
wheel = construction.revolve(
    "Scroll wheel",
    [(0.8, -2.2), (4.7, -2.2), (5.1, -1.8), (5.1, 1.8), (4.7, 2.2), (0.8, 2.2)],
    closed=True,
    segments=96,
)
wheel.rotation_euler = [0, math.pi / 2, 0]
wheel.location = [0, y, wheel_z]
material(wheel, "Wheel rubber", [0.014, 0.022, 0.025], roughness=0.64)
# Real circumferential grooves in the outer ring, preserving side rims.
for vertex in wheel.data.vertices:
    radius = math.hypot(vertex.co.x, vertex.co.y)
    if radius > 5.0:
        angle = math.atan2(vertex.co.y, vertex.co.x)
        scale = (radius - 0.22 * (0.5 + 0.5 * math.cos(32 * angle))) / radius
        vertex.co.x *= scale
        vertex.co.y *= scale
wheel.data.update()
button_point = [0, -14, 60]
from mesh_workbench import patterns

hit = patterns.project(master, [button_point], max_distance=60, direction=[0, 0, -1])[0]
button = relief.dots(
    master,
    [hit["position"]],
    "DPI button",
    radii=1.65,
    height=0.55,
    embed=0.12,
    clearance=0.05,
    segments=24,
    rings=3,
    max_distance=0.3,
)
material(button, "Warm accent", [0.78, 0.26, 0.07], metallic=0.25, roughness=0.3)
# A short crown accent remains entirely on the rear housing.
accent = precision.bound_seam(
    master,
    [[0, 10, 50], [0, 27, 50]],
    "Crown accent",
    radius=0.20,
    offset=0.13,
    max_distance=25,
    spacing=1,
)
material(accent, "Accent metal", [0.58, 0.29, 0.10], metallic=0.7, roughness=0.28)
from itertools import combinations

crossings = [
    shells.intersections(a, b)
    for a, b in combinations(list(parts.values()) + [wheel], 2)
]
(output / "assembly-intersections.json").write_text(json.dumps(crossings, indent=2))
assert all(r["triangle_pair_count"] == 0 for r in crossings), crossings
assembly_reports = []
for key in ["top", "side", "front"]:
    view = ref["views"][key]
    expected = reference.target_mask(view, ref["components"][key]["shapes"])
    actual = np.zeros_like(expected)
    for part in parts.values():
        actual |= reference.mesh_mask(part, view)
    # The wheel is intentionally excluded from shell-envelope measurements.
    result = reference.compare(actual, expected, view)
    result.update(
        component=key,
        target_sha256=reference.fingerprint(ref),
        sampling_size=view["size"],
    )
    assembly_reports.append(result)
    reference.save_overlay(
        output / ("assembly-" + key + "-error.png"), actual, expected
    )
assert all(
    r["iou"] >= spec["acceptance"]["silhouette_iou_min"] for r in assembly_reports
), assembly_reports
for v in ["hero", "top", "side", "detail"]:
    render("final", v)
# Exploded view exposes real wall thickness and separate button shells.
positions = {p.name: p.location.copy() for p in parts.values()}
for name, p in parts.items():
    if name == "Lower housing":
        p.location.z = -10
    elif "button" in name:
        p.location.z = 18
    else:
        p.location.z = 8
hide(new_dots)
hide(accent)
hide(button)
hide(wheel)
hide(floor)
render("exploded", "hero")
for p in parts.values():
    p.location = positions[p.name]
for o in [new_dots, accent, button, wheel, floor]:
    show(o)
np.testing.assert_array_equal(sculpt.coordinates(baseline), baseline_coords)
checks = []
for obj in scene.objects:
    if obj.type == "MESH" and not obj.hide_render and obj != floor:
        info = geometry.inspect(obj)
        info["overlap_candidates"] = fairing.overlap_candidates(obj)
        checks.append(info)
print(
    "FINAL_GEOMETRY",
    json.dumps(
        [(r["object"], r["nonmanifold_edges"], r["overlap_candidates"]) for r in checks]
    ),
    flush=True,
)
assert all(
    r["finite"] and r["nonmanifold_edges"] == 0 and r["overlap_candidates"] == 0
    for r in checks
)
np.save(output / "master-after.npy", sculpt.coordinates(master))
audit = {
    "blender": bpy.app.version_string,
    "target_sha256": reference.fingerprint(spec),
    "reference_sha256": reference.fingerprint(ref),
    "candidates": rows,
    "ranking": ranking,
    "local_edit": move,
    "palm_edit": palm_edit,
    "palm_trial_disabled": True,
    "unchanged_vertices": len(outside),
    "undo_error": undo_error,
    "attachment_status": attachments.status(master, new_dots),
    "rejected_thickness_violations": len(rejected["violations"]),
    "normal_ray_diagnostics": [
        {k: v for k, v in r.items() if k != "violations"} for r in normal_thickness
    ],
    "thickness": [{k: v for k, v in r.items() if k != "violations"} for r in thickness],
    "gaps": [{k: v for k, v in r.items() if k != "violations"} for r in gaps],
    "geometry": checks,
    "wheel_opening_faces": len(opening),
    "assembly_intersections": crossings,
    "assembly_silhouettes": assembly_reports,
    "limits": [
        "Authored target, not a scan or comfort assessment.",
        "Thickness uses sampled outer-to-inner nearest distances; normal-ray misses at finite rims are recorded separately. Gaps use sampled shared boundaries.",
        "Offset construction and triangle-overlap diagnostics are not a full manufacturing certificate.",
    ],
}
camera(**views["hero"])
scene.cycles.samples = 32
bpy.ops.wm.save_as_mainfile(filepath=str(output / "mouse.blend"))
audit["model_sha256"] = hashlib.sha256(
    (output / "mouse.blend").read_bytes()
).hexdigest()
(output / "audit.json").write_text(json.dumps(audit, indent=2))
print("MOUSE_STUDY_COMPLETE", flush=True)
