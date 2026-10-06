"""Native cordless drill with remeshed housing, real vents and assembly transfer.
Blender --background --factory-startup --python examples/drill_study.py -- NEW_OUTPUT [--quick]
"""

import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import (
    construction,
    sculpt,
    geometry,
    models,
    shells,
    pathmodel,
    materials,
    relief,
    attachments,
    assembly,
    regions,
    fairing,
)
from mesh_workbench.runner import camera

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
out.mkdir(parents=True, exist_ok=False)
quick = "--quick" in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001
report = {
    "blender": bpy.app.version_string,
    "units": "mm",
    "brief": {
        "kind": "original authored cordless drill, not a replica",
        "head_x": [-60, 45],
        "head_center_z": 160,
        "wall": 2,
        "split_trim": 0.4,
        "vents": 6,
        "remesh_limit": 0.09,
    },
}


def hide(o):
    o.hide_render = True
    o.hide_set(True)


def show(o):
    o.hide_render = False
    o.hide_set(False)


def mat(o, name, color, metal=0, rough=0.4):
    if name in bpy.data.materials:
        o.data.materials.clear()
        o.data.materials.append(bpy.data.materials[name])
    else:
        materials.assign([o], name, [*color, 1], metallic=metal, roughness=rough)


def bake(o):
    sculpt.bake(o)
    return o


def box(name, dims, location, radius=1):
    return bake(
        construction.rounded_box(name, dims, location, radius=radius, segments=4)
    )


def axial(name, profile, z=160):
    o = construction.revolve(name, profile, segments=64)
    o.rotation_euler.y = math.pi / 2
    o.location.z = z
    return bake(o)


def render(name, position, target, scale, size=(1000, 850)):
    if quick:
        return
    camera(position=position, target=target, scale=scale, size=size)
    scene.camera.data.clip_end = 10000
    scene.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)


# Smooth head envelope, sampled independently from the remesh target edge length.
profile = []
for i in range(43):
    x = -60 + 105 * i / 42
    radius = 26 - 3 * (i / 42) + 2 * math.sin(math.pi * i / 42)
    profile.append((radius, x))
master = axial("Head master", profile)
for f in master.data.polygons:
    f.use_smooth = len(f.vertices) == 4
left = shells.extract(
    master,
    geometry.selection(master, "FACE", box=[[-100, -50, 100], [100, -0.001, 210]]),
    "Left housing before vents",
    thickness=2,
    trim=0.4,
)
right = shells.extract(
    master,
    geometry.selection(master, "FACE", box=[[-100, 0.001, 100], [100, 50, 210]]),
    "Right housing",
    thickness=2,
    trim=0.4,
)
hide(master)
# Slots pass through the actual two millimetre wall; retained cutters are hidden.
for i in range(6):
    cutter = box(
        "Vent cutter %02d" % i, [3.3, 20, 18], [-48 + i * 5.4, -25, 161], radius=1.5
    )
    cut = models.boolean(left, cutter, "DIFFERENCE", "Vented housing %02d" % i)
    hide(left)
    hide(cutter)
    left = cut
left.name = "Housing baseline"
mat(left, "Saffron enamel", [0.63, 0.28, 0.045], metal=0.22, rough=0.3)
mat(right, "Saffron enamel", [0.63, 0.28, 0.045], metal=0.22, rough=0.3)
# Planar per-corner UVs deliberately transfer across changed polygon indices.
uv = left.data.uv_layers.new(name="HousingUV")
coords = sculpt.coordinates(left)
for loop in left.data.loops:
    p = coords[loop.vertex_index]
    uv.data[loop.index].uv = (p[0] / 120, (p[2] - 130) / 60)
patch = geometry.selection(left, "FACE", box=[[-8, -40, 141], [37, -15, 183]])
regions.define(
    left,
    "service_panel",
    geometry.selection(left, "VERT", box=[[-8, -40, 141], [37, -15, 183]]),
)
group = left.vertex_groups.new(name="panel_weight")
for i, p in enumerate(coords):
    w = max(0, 1 - abs(p[0] - 15) / 24) * max(0, 1 - abs(p[2] - 160) / 22)
    if w:
        group.add([i], w, "REPLACE")
left["mw_masks"] = json.dumps(
    {"panel": {"group": "panel_weight", "topology": sculpt.topology(left)}}
)
# Four raised fastener heads migrate through the remeshed panel.
points = [[x, -30, z] for x in (1, 30) for z in (150, 175)]
fasteners = relief.dots(
    left,
    points,
    "Fasteners baseline",
    radii=1.45,
    height=0.65,
    embed=0.2,
    segments=16,
    rings=2,
    max_distance=12,
    gap=0.3,
    clearance=0.08,
)
mat(fasteners, "Graphite fasteners", [0.025, 0.032, 0.04], metal=0.75)
attachments.bind_relief(left, fasteners, max_distance=0.1)
nodes = {
    "housing": {"kind": "source", "object": left.name},
    "fasteners": {
        "kind": "relief",
        "object": fasteners.name,
        "deps": ["housing"],
        "binding": json.loads(fasteners["mw_surface_binding"]),
        "options": json.loads(fasteners["mw_relief_settings"]),
    },
}
assembly.register(
    "Drill service housing",
    nodes,
    [
        {
            "kind": "clearance",
            "nodes": ["fasteners", "housing"],
            "options": {"minimum": 0.03},
        }
    ],
)
report["assembly"] = assembly.remesh_source(
    "housing", patch, "Housing refined", target_length=4.0, iterations=1, max_error=0.09
)
assert report["assembly"]["remesh"]["operations"]["collapse"] > 0, report["assembly"][
    "remesh"
]
final = bpy.data.objects[report["assembly"]["objects"]["housing"]]
final_fasteners = bpy.data.objects[report["assembly"]["objects"]["fasteners"]]
rear = axial("Rear cover", [(25.5, -63), (26.2, -61), (26, -59)])
mat(rear, "Graphite polymer", [0.025, 0.03, 0.038], rough=0.45)
# Chuck, torque ring and jaws, separate native mesh parts.
collar = axial(
    "Torque collar", [(23.5, 44), (23.5, 47), (24, 48), (24, 58), (22.5, 60)]
)
mat(collar, "Graphite polymer", [0.025, 0.03, 0.038], rough=0.45)
chuck = axial("Chuck", [(20, 59), (21, 62), (20, 78), (15.5, 88), (13, 90)])
mat(chuck, "Chuck steel", [0.13, 0.16, 0.19], metal=0.85, rough=0.32)
for i in range(32):
    a = math.tau * i / 32
    rib = construction.strut(
        "Chuck flute %02d" % i,
        [63, 20.25 * math.sin(a), 160 + 20.25 * math.cos(a)],
        [77, 19.8 * math.sin(a), 160 + 19.8 * math.cos(a)],
        radius=0.5,
        segments=8,
    )
    mat(rib, "Flute rubber", [0.018, 0.023, 0.027], rough=0.48)
nose = axial("Nose ring", [(13, 88), (13, 92), (9, 93)])
mat(nose, "Nose steel", [0.28, 0.31, 0.35], metal=0.9, rough=0.23)
bit = construction.strut("Hex bit", [89, 0, 160], [117, 0, 160], radius=3.2, segments=6)
mat(bit, "Bit steel", [0.34, 0.38, 0.42], metal=0.9, rough=0.26)
# Grip sweep retains elliptical cross sections and distinct rubber surface.
centers = [[-32 + 18 * t, 0, 48 + 90 * t] for t in np.linspace(0, 1, 25)]
grip = pathmodel.create(
    "Grip core",
    centers,
    [
        [15 - 2 * math.sin(math.pi * t), 18 - 2 * math.sin(math.pi * t)]
        for t in np.linspace(0, 1, 25)
    ],
    segments=48,
    reference=[0, 1, 0],
)
mat(grip, "Grip rubber", [0.024, 0.035, 0.04], rough=0.64)
# Following tactile pads on the visible side, spaced to avoid motif overlaps.
grid = [
    [-32 + 18 * ((z - 48) / 90) + dx, -20, z]
    for z in range(62, 126, 7)
    for dx in (-5, 0, 5)
]
grit = relief.dots(
    grip,
    grid,
    "Grip tactile pads",
    radii=1.25,
    height=0.45,
    embed=0.2,
    segments=12,
    rings=2,
    max_distance=12,
    gap=0.3,
    clearance=0.025,
)
mat(grit, "Grip raised texture", [0.045, 0.057, 0.062], rough=0.72)
attachments.bind_relief(grip, grit, max_distance=0.1)
boot = box("Battery slide", [49, 41, 11], [-31, 0, 42], radius=3)
mat(boot, "Saffron enamel", [0.63, 0.28, 0.045], metal=0.22, rough=0.3)
tongue = box("Battery tongue", [40, 32, 8], [-31, 0, 35], radius=2)
mat(tongue, "Graphite polymer", [0.025, 0.03, 0.038], rough=0.45)
battery = box("Battery pack", [76, 53, 29], [-28, 0, 20], radius=5)
mat(battery, "Graphite polymer", [0.025, 0.03, 0.038], rough=0.45)
base = box("Battery bumper", [77, 54, 7], [-28, 0, 5], radius=2)
mat(base, "Grip rubber", [0.024, 0.035, 0.04], rough=0.64)
latch = box("Battery release", [23, 3, 10], [-28, -27, 27], radius=1)
mat(latch, "Saffron enamel", [0.63, 0.28, 0.045], metal=0.22, rough=0.3)
trigger = box("Trigger", [13, 25, 20], [-0.5, 0, 129], radius=3)
mat(trigger, "Trigger", [0.075, 0.085, 0.095], rough=0.35)
switch = box("Direction switch", [9, 39, 6], [-4, 0, 143], radius=1)
mat(switch, "Graphite polymer", [0.025, 0.03, 0.038], rough=0.45)
for x in (-49, -7):
    rail = box("Battery rail " + str(x), [3, 2, 16], [x, -27, 17], radius=0.8)
    mat(rail, "Battery detail", [0.09, 0.105, 0.115], rough=0.45)
# Authored model evidence: six clear rays through cut housing and nearby wall hits.
world = sculpt.coordinates(final)
final.data.calc_loop_triangles()
tree = BVHTree.FromPolygons(
    world.tolist(),
    [tuple(t.vertices) for t in final.data.loop_triangles],
    all_triangles=True,
)
vents = []
for i in range(6):
    x = -48 + i * 5.4
    clear = tree.ray_cast(Vector([x, -60, 161]), Vector([0, 1, 0]), 60)[0] is None
    wall = (
        tree.ray_cast(Vector([x + 2.5, -60, 161]), Vector([0, 1, 0]), 60)[0] is not None
    )
    vents.append({"x": x, "through_ray_clear": clear, "adjacent_wall_hit": wall})
assert all(v["through_ray_clear"] and v["adjacent_wall_hit"] for v in vents), vents
report["vents"] = vents
report["geometry"] = {}
visible = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
for o in visible:
    info = geometry.inspect(o)
    overlap = fairing.overlap_candidates(o)
    report["geometry"][o.name] = {
        "vertices": len(o.data.vertices),
        "nonmanifold_edges": info["nonmanifold_edges"],
        "overlap_candidates": overlap,
    }
    assert info["nonmanifold_edges"] == 0 and overlap == 0, (o.name, info, overlap)
np.save(out / "housing.npy", sculpt.coordinates(final))
report["housing"] = final.name
report["source"] = left.name
report["binding"] = json.loads(final_fasteners["mw_surface_binding"])
report["bounds"] = {
    "min": np.min(
        np.concatenate([sculpt.coordinates(o) for o in visible]), axis=0
    ).tolist(),
    "max": np.max(
        np.concatenate([sculpt.coordinates(o) for o in visible]), axis=0
    ).tolist(),
}
# Native studio renders.
floor = box("Studio floor", [6000, 6000, 2], [0, 0, -1], radius=0.2)
mat(floor, "Studio", [0.042, 0.054, 0.07], rough=0.72)
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.world = bpy.data.worlds.new("Studio world")
scene.world.color = (0.18, 0.18, 0.18)
for name, pos, power, size in [
    ("Key", [-180, -220, 340], 2200000, 200),
    ("Fill", [230, -60, 180], 1600000, 150),
    ("Rim", [0, 200, 290], 2400000, 180),
]:
    lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    scene.collection.objects.link(lamp)
    lamp.location = pos
    lamp.data.energy = power
    lamp.data.size = size
    lamp.rotation_euler = (
        (Vector([0, 0, 100]) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    )
render("hero", [270, -400, 230], [15, 0, 100], 280)
render("side", [0, -500, 105], [12, 0, 102], 265)
# Before/after wire overlays on the same selected housing, native Blender.
for o in visible:
    if o not in (final,):
        hide(o)
hide(final_fasteners)
hide(final)
for label, obj in [("before", left), ("after", final)]:
    show(obj)
    wire = obj.copy()
    wire.data = obj.data.copy()
    wire.name = label + " wire"
    scene.collection.objects.link(wire)
    wire.hide_render = False
    wire.hide_set(False)
    wire.data.materials.clear()
    mat(wire, "Wire", [0.018, 0.024, 0.03], rough=0.8)
    mod = wire.modifiers.new("Topology overlay", "WIREFRAME")
    mod.thickness = 0.075
    mod.use_replace = True
    mod.use_even_offset = False
    render("topology-" + label, [10, -240, 178], [10, -20, 161], 90, (900, 650))
    hide(obj)
    hide(wire)
for o in visible:
    show(o)
hide(left)
hide(fasteners)
# Explode only in the preview; restore exact transforms before saving.
left_state = final.matrix_world.copy()
right_state = right.matrix_world.copy()
fastener_state = final_fasteners.matrix_world.copy()
final.location.y -= 22
final_fasteners.location.y -= 22
right.location.y += 22
render("exploded", [260, -400, 235], [10, 0, 100], 300)
final.matrix_world = left_state
right.matrix_world = right_state
final_fasteners.matrix_world = fastener_state
camera(position=[270, -400, 230], target=[15, 0, 100], scale=280, size=[1000, 850])
scene.camera.data.clip_end = 10000
bpy.ops.wm.save_as_mainfile(filepath=str(out / "drill.blend"))
sculpt.dump(out / "audit.json", report)
print("DRILL_COMPLETE", json.dumps(report["assembly"]["remesh"]), flush=True)
