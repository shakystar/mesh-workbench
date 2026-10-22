"""Build a new native drill candidate against a previously frozen authored brief."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested
from drill_surface import surface_blueprint
from drill_realism_seams import definitions as seam_definitions
from drill_realism_controls import add_direction_switch
from drill_realism_chuck import add_nose_support, add_drill_bit
from drill_realism_finishes import apply_finishes
from drill_realism_markings import add_torque_markings, add_control_markings, add_torque_pointer
from drill_realism_vents import add_vent_baffles
from drill_realism_seats import add_front_seat, add_supported_seats
from drill_realism_grip import add_grip_wrap
from drill_realism_trigger import add_trigger_grooves


def merge(base, changes):
    result = copy.deepcopy(base)
    for key, value in changes.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(output, frozen):
    if output.exists():
        raise ValueError("Use a fresh candidate directory")
    freeze = json.loads((frozen / "freeze.json").read_text())
    for name, expected in freeze["inputs"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Frozen design input changed: " + name)
    if sha(frozen / "manifest.json") != freeze["guide_manifest_sha256"]:
        raise ValueError("Frozen guide manifest changed")
    target = json.loads((ROOT / "examples/drill-realism-target.json").read_text())
    source = ROOT / "runs/drill-surface-06/drill.blend"
    before = sha(source)
    if before != target["baseline_sha256"]:
        raise ValueError("Baseline changed")
    spec = merge(json.loads((ROOT / "examples/drill-surface-target.json").read_text()), target["overrides"])
    spec["parameters"]["head_width"] = 0
    spec["parameter_ranges"]["head_width"] = [-1, 2]
    # Reserve width for the rubber insert/relief instead of adding it outside
    # the target envelope. Remove the preceding short-grip crown compensation.
    spec["envelope"]["grip_half_width"] = 14.5
    spec["envelope"]["rim_radius"] = 10
    spec["envelope"]["section_controls"]["rows"] = [
        [40,0,0,0], [60,0,0,0], [85,0,0,0], [110,0,0,0],
        [123,.8,.8,0], [130,-2,-.8,0], [145,-.5,-1,.3],
        [165,0,0,0], [180,0,0,0], [195,-1,-1,0]]
    # The longer, forward-sloping grip moves its side-panel center forward.
    # Keep projection/chart checks intact; relocate the original patch guides.
    spec["construction"]["grip"]["guide"]["center"][0] = -22
    # Leave exposed polymer around the lower screw access. Keep the upper
    # grip boundary fixed while raising its lower edge by 10 mm; regenerate
    # its perimeter and ribs from the same revised guide.
    grip = spec["construction"]["grip"]
    grip["guide"]["center"][2] += 5
    grip["guide"]["radii"][1] -= 5
    grip["z_range"][0] += 10
    grip["guide"]["pattern_z"][0] += 10
    spec["surface_phase"]["detail_design"]["rubber"]["perimeter_radii"][1] -= 5
    # The old 30 mm opening intersects the new sloping front wall. A 20 mm
    # internal drive aperture retains the existing coaxial interface frame.
    spec["construction"]["front_bore"]["radius"] = 10
    # Match the frozen 22 mm torque envelope and 19 -> 11 mm chuck taper.
    # Keep the coaxial mating frames and a >=9.5 mm nose bore for jaw travel.
    spec["surface_phase"]["detail_design"]["torque_ring"]["profile"] = [
        [0,21.6,14.5,0], [.6,22,14,0], [2,22,14,1],
        [12,22,14,1], [13,22,14,0], [15,19,14.5,0]]
    spec["surface_phase"]["detail_design"]["chuck"]["profile"] = [
        [0,18.6,12.5,0], [.6,19,12,0], [2,19,12,1],
        [23,18,12,1], [25,17.4,12,0], [33,15,10.5,0], [39,11,9.5,0]]
    nodes, checks = surface_blueprint(spec)
    nodes["master"]["args"]["head_half_width"] = {
        "param": "head_width", "offset": spec["envelope"]["head_half_width"], "scale": .5}
    # Reversible roof compression before hollowing; downstream cuts and details
    # rebuild from the deformed master rather than detaching from its surface.
    nodes["master_stock"] = copy.deepcopy(nodes["master"])
    controls = []
    for _ in range(4):
        plane = []
        for y in (-60, -20, 20, 60):
            # Reduce the compression gradient around the fixed rear screw land.
            plane.append([[0, y*factor, 0] for factor in (0, -.025, -.25, -.175)])
        controls.append(plane)
    nodes["master"] = {
        "kind": "form_cage", "visible": False,
        "deps": [{"id": "master_stock", "use": "geometry"}],
        "frame": copy.deepcopy(nodes["master_stock"]["frame"]),
        "args": {"selection": {}, "bounds": [[-100,-60,175],[80,60,205]],
                 "controls": controls, "feather": .15, "max_displacement": 60,
                 "pins": [{"center": [-50,sign*27,178], "fixed_radius": 6,
                           "release_radius": 14} for sign in (-1,1)],
                 "label": "Rounded motor roof"}}
    # Moving battery side shrouds enclose the rails but keep their forward
    # exit open. The rear bridge moves away from the fixed rails on removal.
    nodes["battery"]["kind"] = "section_stock"
    nodes["battery"]["args"] = {
        "sections":[[z,-32,0,x,y] for z,x,y in [
            (-25,35,23),(-24.6,36.5,24.3),(-23.6,38.2,25.8),
            (-22,39,26.5),(-1,39,26.5),(1,37.8,25.8),
            (3,35,24),(4,27,20),(5,27,20)]],
        "origin":[0,0,{"param":"grip_length","offset":28,"scale":-1}],
        "exponent":6,"segments":128}
    nodes["foot_stock"]["kind"] = "section_stock"
    nodes["foot_stock"]["args"] = {
        "sections":[[13,-32,0,25.5,18.5],[14,-32,0,27,20],[18,-32,0,24,17]],
        "origin":[0,0,{"param":"grip_length","offset":28,"scale":-1}],
        "exponent":6,"segments":128}
    nodes["rear_cover"]["args"]["dimensions"][1] = 36
    for i,sign in enumerate((-1,1)):
        node = nodes["battery_cover_"+str(i)]
        node["args"]["dimensions"] = [54,3.2,7.4]
        node["args"]["center"] = [-32,sign*18.6,{"param":"grip_length","offset":36.7,"scale":-1}]
        node["frame"]["origin"] = copy.deepcopy(node["args"]["center"])
    rear = copy.deepcopy(nodes["battery_cover_0"])
    rear["args"]["dimensions"] = [3.2,36,7.4]
    rear["args"]["center"][0:2] = [-57.4,0]
    rear["frame"]["origin"] = copy.deepcopy(rear["args"]["center"])
    nodes["battery_cover_2"] = rear
    nodes.update(seam_definitions())
    add_direction_switch(nodes)
    add_vent_baffles(nodes)
    add_front_seat(nodes)
    add_supported_seats(nodes)
    add_nose_support(nodes)
    add_drill_bit(nodes)
    add_grip_wrap(nodes)
    add_trigger_grooves(nodes)
    apply_finishes(nodes)
    add_torque_markings(nodes)
    add_control_markings(nodes)
    add_torque_pointer(nodes)
    recipe = {"version": 1, "units": "mm", "operations": [{
        "op": "nested_initialize", "name": "Original realism drill candidate",
        "nodes": nodes, "parameters": spec["parameters"],
        "ranges": spec["parameter_ranges"], "checks": checks}, {"op": "nested_status"}]}
    output.mkdir(parents=True)
    (output / "recipe.json").write_text(json.dumps(recipe, indent=2)+"\n")
    (output / "resolved-design.json").write_text(json.dumps(spec, indent=2)+"\n")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = .001
    try:
        report = nested.initialize("Original realism drill candidate", nodes,
                                   spec["parameters"], spec["parameter_ranges"], checks)
    except Exception as exc:
        rejection = {"reason": str(exc), "detail": getattr(exc, "report", None),
                     "baseline_preserved": sha(source) == before,
                     "freeze_sha256": sha(frozen / "freeze.json")}
        (output / "rejected.json").write_text(json.dumps(rejection, indent=2)+"\n")
        raise
    if sha(source) != before:
        raise ValueError("Baseline changed during candidate generation")
    report.update({"stage": "M12 initial candidate; silhouette, detail, motion and visual gates pending",
                   "baseline_preserved": True, "freeze_sha256": sha(frozen / "freeze.json"),
                   "blender": bpy.app.version_string})
    (output / "build.json").write_text(json.dumps(report, indent=2)+"\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve() / "drill.blend"))
    print("REALISM_CANDIDATE", json.dumps({"passed_build_checks": report["passed"],
          "baseline_preserved": True, "output": str(output)}), flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    build(Path(args[0]), Path(args[1]))
