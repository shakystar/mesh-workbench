"""Replace the lantern handle's overlapping rods with a continuous sweep."""

import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import construction, geometry
from mesh_workbench.runner import camera
from mesh_workbench.sweep import sweep

args = sys.argv[sys.argv.index("--") + 1 :]
source = Path(args[0]).resolve()
out = Path(args[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
for ob in bpy.data.objects:
    if ob.name.startswith(("Handle upright", "Handle grip")):
        ob.hide_render = True
        ob.hide_set(True)
points = [(-0.73, 0, 2.17), (-0.73, 0, 2.6)]
for j in range(9):
    a = math.pi - j * math.pi / 16
    points.append((-0.57 + 0.16 * math.cos(a), 0, 2.78 + 0.16 * math.sin(a)))
points.append((0.57, 0, 2.94))
for j in range(1, 9):
    a = math.pi / 2 - j * math.pi / 16
    points.append((0.57 + 0.16 * math.cos(a), 0, 2.78 + 0.16 * math.sin(a)))
points.extend([(0.73, 0, 2.6), (0.73, 0, 2.17)])
handle = sweep("Continuous handle", points, [(0.045, 0.045)] * len(points), 32)
handle.data.materials.append(bpy.data.materials["Machined aluminium"])
grip = construction.strut("Short grip", (-0.53, 0, 2.94), (0.53, 0, 2.94), 0.085, 64)
grip.data.materials.append(bpy.data.materials["Graphite elastomer"])
report = geometry.inspect(handle)
assert report["nonmanifold_edges"] == 0
for view, pos, target, scale in [
    ("front", (4, -6, 3.7), (0, 0, 1.45), 4.5),
    ("handle-detail", (3, -5, 3.7), (0, 0, 2.73), 2.0),
]:
    camera(pos, target, scale, (640, 640))
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.use_denoising = True
    bpy.context.scene.render.filepath = str(out / (view + ".png"))
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / "lantern.blend"))
(out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
