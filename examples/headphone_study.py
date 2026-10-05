"""Native headphone study: Blender --python examples/headphone_study.py -- NEW_OUTPUT [--quick]."""

import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    geometry,
    sculpt,
    quality,
    refinement,
    pathmodel,
    joints,
    attachments,
    relief,
    regions,
    construction,
    materials,
    reference,
    fairing,
)
from mesh_workbench.runner import camera

output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output.mkdir(parents=True, exist_ok=False)
quick = "--quick" in sys.argv
spec = json.loads((ROOT / "examples/headphone-target.json").read_text())
sculpt.dump(output / "target.json", spec)
audit = {
    "target_sha256": reference.fingerprint(spec),
    "blender": bpy.app.version_string,
    "variants": {},
}


def hide(obj):
    obj.hide_render = True
    obj.hide_set(True)


def material(obj, name, color, metal=0, rough=0.4):
    materials.assign([obj], name, [*color, 1], metallic=metal, roughness=rough)


def cup(name, cx):
    vertices = []
    faces = []
    segments = 96
    rows = 48
    vertices.append([cx + 11, 0, 55])
    for i in range(1, rows):
        p = math.pi * i / rows
        for j in range(segments):
            t = math.tau * j / segments
            vertices.append(
                [
                    cx + 11 * math.cos(p),
                    34 * math.sin(p) * math.cos(t),
                    55 + 45 * math.sin(p) * math.sin(t),
                ]
            )
    end = len(vertices)
    vertices.append([cx - 11, 0, 55])
    for j in range(segments):
        k = (j + 1) % segments
        faces.append((0, 1 + j, 1 + k))
        faces.append(
            (end, 1 + (rows - 2) * segments + k, 1 + (rows - 2) * segments + j)
        )
    for i in range(rows - 2):
        for j in range(segments):
            a = 1 + i * segments + j
            b = 1 + i * segments + (j + 1) % segments
            faces.append((a, a + segments, b + segments, b))
    return pathmodel._mesh(name, vertices, faces)


def render(folder, label, kind="hero"):
    if quick:
        return
    views = {
        "hero": dict(
            position=[-290, -330, 235], target=[0, 0, 94], scale=280, size=[900, 900]
        ),
        "detail": dict(
            position=[-300, -105, 100], target=[-84, 0, 57], scale=112, size=[800, 800]
        ),
    }
    camera(**views[kind])
    bpy.context.scene.camera.data.clip_end = 10000
    bpy.context.scene.cycles.samples = 24
    bpy.context.scene.render.filepath = str(folder / (label + ".png"))
    bpy.ops.render.render(write_still=True)


def ellipse(center, rx, ry, n=192):
    return [
        [
            center[0] + rx * math.cos(i * math.tau / n),
            center[1] + ry * math.sin(i * math.tau / n),
        ]
        for i in range(n)
    ]


def compare(obj, view, polygon, label, folder):
    target = reference.target_mask(view, [{"kind": "polygon", "points": polygon}])
    actual = reference.mesh_mask(obj, view)
    report = reference.compare(actual, target, view)
    reference.save_overlay(folder / (label + "-error.png"), actual, target)
    return report


for label, span in spec["variants"].items():
    folder = output / label
    folder.mkdir()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    floor = construction.rounded_box(
        "Studio floor", [6000, 6000, 2], location=[0, 0, -1], radius=0.2
    )
    material(floor, "Studio", [0.055, 0.069, 0.085], rough=0.7)
    for name, pos, power, size in [
        ("Key", [-230, -200, 330], 2200000, 190),
        ("Fill", [200, -50, 200], 1500000, 150),
        ("Rim", [50, 170, 300], 2200000, 150),
    ]:
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        scene.collection.objects.link(lamp)
        lamp.location = pos
        lamp.data.energy = power
        lamp.data.shape = "DISK"
        lamp.data.size = size
        lamp.rotation_euler = (
            (Vector([0, 0, 90]) - lamp.location).to_track_quat("-Z", "Y").to_euler()
        )
    half = span / 2
    report = {"span": span}
    clean = cup("Left cup clean guide", -half)
    material(clean, "Cup enamel", [0.065, 0.19, 0.22], metal=0.35, rough=0.27)
    original = sculpt.coordinates(clean).copy()
    hide(clean)
    before = geometry.fork(clean, "Left cup defective")
    for v in before.data.vertices:
        x, y, z = v.co
        if x < -half - 4:
            e = max(0, 1 - (y / 27) ** 2 - ((z - 55) / 36) ** 2) ** 2
            v.co.x -= 0.85 * math.sin(y * 0.7) * math.cos((z - 55) * 0.55) * e
    before.data.update()
    hide(before)
    fixed = geometry.fork(before, "Left cup repaired")
    selection = geometry.selection(
        fixed, "VERT", box=[[-half - 12, -29, 17], [-half - 3, 29, 93]]
    )
    regions.define(fixed, "cup refinement", selection)
    pre = sculpt.coordinates(fixed).copy()
    report["fairing"] = quality.fair_patch(
        fixed,
        selection,
        iterations=5,
        strength=0.8,
        max_shift=2,
        method="quadratic",
        fit_radius=7,
    )
    corrected = sculpt.coordinates(fixed)
    chosen = np.asarray(selection["indices"])
    report["shape_error_before"] = float(
        np.sqrt(np.mean(np.sum((pre[chosen] - original[chosen]) ** 2, axis=1)))
    )
    report["shape_error_after"] = float(
        np.sqrt(np.mean(np.sum((corrected[chosen] - original[chosen]) ** 2, axis=1)))
    )
    sculpt.dump(folder / "surface-trial.json", report)
    print("SURFACE_TRIAL", json.dumps(report), flush=True)
    assert report["fairing"]["pinned_error"] == 0
    assert (
        report["fairing"]["after"]["roughness_rms"]
        < report["fairing"]["before"]["roughness_rms"]
        * spec["acceptance"]["roughness_ratio_max"]
    )
    assert report["shape_error_after"] < spec["acceptance"]["rms_shape_error_max"]
    # Mask and region follow explicitly supported triangle-centroid subdivision.
    group = fixed.vertex_groups.new(name="MW protect edge")
    for i in selection["indices"]:
        group.add([i], 0.6, "REPLACE")
    fixed["mw_masks"] = json.dumps(
        {"edge": {"group": group.name, "topology": sculpt.topology(fixed)}}
    )
    points = [[-half - 20, y, 55 + z] for y in [-9, 0, 9] for z in [-13, 0, 13]]
    dots = relief.dots(
        fixed,
        points,
        "Detail before subdivision",
        radii=0.7,
        height=0.12,
        embed=0.04,
        clearance=0.06,
        segments=12,
        rings=2,
        direction=[1, 0, 0],
        max_distance=25,
        gap=0.8,
    )
    attachments.bind_relief(fixed, dots, max_distance=0.2)
    binding = json.loads(dots["mw_surface_binding"])
    old_hits = attachments.resolve(fixed, binding)
    faces = geometry.selection(
        fixed, "FACE", box=[[-half - 12, -24, 24], [-half - 5, 24, 86]]
    )
    refined = refinement.split(fixed, faces, "Left cup")
    transferred = refinement.transfer_binding(fixed, refined, binding)
    hits = attachments.resolve(refined, transferred)
    report["binding_transfer_error"] = float(
        np.max(
            np.linalg.norm(
                np.asarray([h["position"] for h in hits])
                - np.asarray([h["position"] for h in old_hits]),
                axis=1,
            )
        )
    )
    assert report["binding_transfer_error"] < 1e-5
    transferred_sel = refinement.transfer_selection(fixed, refined, selection)
    assert len(transferred_sel["indices"]) > len(selection["indices"])
    assert len(regions.resolve(refined, "cup refinement")["indices"]) == len(
        transferred_sel["indices"]
    )
    report["refined_vertices"] = len(refined.data.vertices)
    report["transferred_region_vertices"] = len(transferred_sel["indices"])
    report["mask_max"] = float(sculpt.protection(refined, "edge").max())
    pattern = refinement.transfer_pattern(fixed, refined, dots, "Left detail")
    pattern["mw_surface_binding"] = json.dumps(transferred)
    pattern["mw_attachment_revision"] = attachments.revision(refined)
    material(pattern, "Vent inlay", [0.015, 0.025, 0.03], rough=0.6)
    hide(dots)
    hide(fixed)
    # Curvature values are stored as a Blender point attribute for inspection.
    quality.curvature(refined, attribute="MW mean curvature")
    right = cup("Right cup", half)
    material(right, "Right enamel", [0.065, 0.19, 0.22], metal=0.35, rough=0.27)
    ts = np.linspace(-math.pi / 2, math.pi / 2, 65)
    centers = [[half * math.sin(t), 0, 110 + 80 * math.cos(t)] for t in ts]
    radii = [[11, 2.2]] * len(centers)
    band_source = pathmodel.create(
        "Headband source",
        [[84 * math.sin(t), 0, 110 + 80 * math.cos(t)] for t in ts],
        radii,
        segments=24,
        reference=[0, 1, 0],
    )
    band = pathmodel.reshape(band_source, centers, "Headband")
    hide(band_source)
    material(band, "Band metal", [0.06, 0.08, 0.10], metal=0.7, rough=0.3)
    pad_centers = [
        [half * math.sin(t), 0, 106 + 80 * math.cos(t)]
        for t in np.linspace(-1.32, 1.32, 57)
    ]
    pad = pathmodel.create(
        "Headband pad",
        pad_centers,
        [[9.5, 2.5]] * len(pad_centers),
        segments=24,
        reference=[0, 1, 0],
    )
    material(pad, "Soft pad", [0.022, 0.028, 0.035], rough=0.75)
    report["band_sections"] = pathmodel.sections(band)
    assert report["band_sections"]["radius_error_max"] < 1e-4
    groups = {}
    for side, name, shell in [(-1, "Left", refined), (1, "Right", right)]:
        cx = side * half
        pts = [
            [cx - side * 15, 27 * math.cos(t), 55 + 37 * math.sin(t)]
            for t in np.linspace(0, math.tau, 96, endpoint=False)
        ]
        cushion = pathmodel.create(
            name + " cushion",
            pts,
            [[7, 6]] * 96,
            segments=24,
            reference=[1, 0, 0],
            closed=True,
        )
        material(cushion, name + " leather", [0.025, 0.033, 0.04], rough=0.65)
        report[name.lower() + "_cushion_sections"] = pathmodel.sections(cushion)
        driver = construction.revolve(
            name + " driver", [(1, -0.5), (1, 0.5)], segments=96
        )
        # Revolve unit disc lies in XY, then rotate normal from Z to X.
        driver.rotation_euler = [0, math.pi / 2, 0]
        driver.scale = [32, 22, 1]
        driver.location = [cx - side * 15, 0, 55]
        sculpt.bake(driver)
        material(driver, name + " fabric", [0.035, 0.047, 0.06], rough=0.95)
        start = [
            [cx + 4 * math.cos(t), 4 * math.sin(t), 102]
            for t in np.linspace(0, math.tau, 24, endpoint=False)
        ]
        end = [
            [cx + side * 12 + 4 * math.cos(t), 5 * math.sin(t), 76]
            for t in np.linspace(0, math.tau, 24, endpoint=False)
        ]
        arm = pathmodel.bridge(
            name + " yoke", start, end, [[0, 0, -26]] * 24, [[0, 0, -26]] * 24, rows=24
        )
        report[name.lower() + "_bridge"] = pathmodel.bridge_report(arm)
        assert report[name.lower() + "_bridge"]["endpoint_position_error"] < 1e-5
        material(arm, name + " brushed alloy", [0.22, 0.25, 0.27], metal=0.8, rough=0.3)
        hinge = construction.revolve(
            name + " hinge", [(4.7, -6), (5, -5.7), (5, 5.7), (4.7, 6)], segments=48
        )
        hinge.rotation_euler = [math.pi / 2, 0, 0]
        hinge.location = [cx, 0, 104]
        sculpt.bake(hinge)
        material(
            hinge, name + " hinge bronze", [0.5, 0.27, 0.105], metal=0.75, rough=0.28
        )
        group_objects = [shell, cushion, driver, arm, hinge]
        if side == -1:
            group_objects.append(pattern)
        groups[name] = [o.name for o in group_objects]
    joints.register(
        [
            {
                "name": name,
                "objects": names,
                "pivot": [(-1 if name == "Left" else 1) * half, 0, 104],
                "axis": [0, 1, 0],
                "limits": [-math.pi / 3, math.pi / 3],
            }
            for name, names in groups.items()
        ]
    )
    report["fold"] = joints.inspect(
        {"Left": -math.pi / 4, "Right": math.pi / 4}, [band.name, pad.name], steps=18
    )
    assert report["fold"]["passed"], report["fold"]
    # Fixed orthographic analytic drawings, independent of generated mesh data.
    view = {
        "size": [400, 480],
        "bounds": [-42, 42, 3, 107],
        "horizontal": [0, 1, 0],
        "vertical": [0, 0, 1],
        "direction": [1, 0, 0],
        "depth": [-140, 0],
    }
    report["cup_reference"] = compare(
        refined, view, ellipse([0, 55], 34, 45), "cup", folder
    )
    band_view = {
        "size": [640, 400],
        "bounds": [-105, 105, 102, 198],
        "horizontal": [1, 0, 0],
        "vertical": [0, 0, 1],
        "direction": [0, 1, 0],
        "depth": [-25, 25],
    }
    polygon = []
    for sign, angles in [
        (1, np.linspace(-math.pi / 2, math.pi / 2, 257)),
        (-1, np.linspace(math.pi / 2, -math.pi / 2, 257)),
    ]:
        for t in angles:
            n = np.array([80 * math.sin(t), half * math.cos(t)])
            n /= np.linalg.norm(n)
            polygon.append(
                (
                    np.array([half * math.sin(t), 110 + 80 * math.cos(t)])
                    + sign * 2.2 * n
                ).tolist()
            )
    report["band_reference"] = compare(band, band_view, polygon, "band", folder)
    assert report["cup_reference"]["iou"] >= 0.985
    assert report["band_reference"]["iou"] >= 0.97
    report["geometry"] = {}
    for obj in [band, pad] + [
        bpy.data.objects[n] for names in groups.values() for n in names
    ]:
        info = geometry.inspect(obj)
        overlaps = fairing.overlap_candidates(obj)
        report["geometry"][obj.name] = {
            "nonmanifold_edges": info["nonmanifold_edges"],
            "overlap_candidates": overlaps,
        }
        assert info["nonmanifold_edges"] == 0 and overlaps == 0, (
            obj.name,
            info,
            overlaps,
        )
    render(folder, "open")
    state = joints.pose({"Left": -math.pi / 4, "Right": math.pi / 4})
    render(folder, "folded")
    joints.restore(state)
    if label == "standard":
        # Diagnostic copies: actual reflected-view-direction bands on the mesh.
        zebra_before = geometry.fork(before, "Before bands")
        quality.reflection_bands(zebra_before)
        hide(refined)
        hide(pattern)
        render(folder, "surface-before", "detail")
        hide(zebra_before)
        zebra_after = geometry.fork(fixed, "After bands")
        quality.reflection_bands(zebra_after)
        render(folder, "surface-after", "detail")
        hide(zebra_after)
        curve_before = geometry.fork(before, "Before curvature")
        quality.curvature_material(curve_before)
        render(folder, "curvature-before", "detail")
        hide(curve_before)
        curve_after = geometry.fork(fixed, "After curvature")
        quality.curvature_material(curve_after)
        render(folder, "curvature-after", "detail")
        hide(curve_after)
        refined.hide_render = False
        refined.hide_set(False)
        pattern.hide_render = False
        pattern.hide_set(False)
    np.save(folder / "cup.npy", sculpt.coordinates(refined))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "headphones.blend"))
    sculpt.dump(folder / "audit.json", report)
    audit["variants"][label] = report
    print(
        "HEADPHONE_VARIANT",
        label,
        json.dumps(
            {
                "roughness": report["fairing"],
                "fold_passed": report["fold"]["passed"],
                "shape_error": report["shape_error_after"],
            }
        ),
        flush=True,
    )
sculpt.dump(output / "audit.json", audit)
print("HEADPHONE_COMPLETE", flush=True)
