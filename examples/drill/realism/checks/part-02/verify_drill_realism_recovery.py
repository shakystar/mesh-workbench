"""Reopened native drill transaction rejection, late rollback and recovery."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT=_WORKSPACE
sys.path.insert(0,str(ROOT/"src"))
from mesh_workbench import assembly, geometry, nested, regions, registration, sculpt


def shape_keys(obj):
    result={}
    if obj.type=="MESH" and obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            points=np.empty(len(key.data)*3,dtype=np.float32)
            key.data.foreach_get("co",points)
            result[key.name]={"value":key.value,"coordinates_sha256":hashlib.sha256(points.tobytes()).hexdigest()}
    return result


def shader_state(material):
    if not material.use_nodes or not material.node_tree:
        return None
    def value(socket):
        item=socket.default_value
        if isinstance(item,(float,int,bool,str)) or item is None:
            return item
        try:
            return list(item)
        except TypeError:
            return repr(item)
    tree=material.node_tree
    return {"nodes":{node.name:{"type":node.bl_idname,
        "inputs":{s.identifier:value(s) for s in node.inputs if hasattr(s,"default_value")}}
        for node in tree.nodes},
        "links":sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier)
                       for l in tree.links)}


def snapshot():
    # The initial native load is validated by nested.load(). This snapshot
    # hashes every object itself; avoid doing the same full scan twice.
    state=json.loads(bpy.context.scene[nested.KEY])
    return {
        "graph":bpy.context.scene[nested.KEY],
        "objects":{obj.name:{
            "stamp":nested._stamp(obj) if obj.type=="MESH" else None,
            "shape_keys":shape_keys(obj),
            "strings":{k:obj[k] for k in obj.keys() if isinstance(obj[k],str)},
            "matrix":[list(row) for row in obj.matrix_world],
            "visibility":[obj.hide_get(),obj.hide_render,obj.hide_viewport,obj.select_get()]}
            for obj in bpy.data.objects},
        "meshes":sorted(m.name for m in bpy.data.meshes),
        "materials":{m.name:{"color":list(m.diffuse_color),"shader":shader_state(m),
            "strings":{k:m[k] for k in m.keys() if isinstance(m[k],str)}}
            for m in bpy.data.materials},
        "active":bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        "outputs":state["outputs"]}


def verify(source, output):
    output.mkdir(parents=True,exist_ok=False)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    baseline=snapshot()
    reports={}

    def rejected(name, action, expected=None, expected_state=None):
        try:
            action()
        except (ValueError,assembly.Rejected) as exc:
            intact=snapshot()==(baseline if expected_state is None else expected_state)
            reports[name]={"rejected":True,"state_preserved":intact,
                           "reason":str(exc),"detail":getattr(exc,"report",None)}
            if expected is not None and expected.lower() not in str(exc).lower():
                raise RuntimeError("Wrong native rejection path: "+name) from exc
            if not intact:
                raise RuntimeError("Rejected edit changed native state: "+name) from exc
        else:
            raise RuntimeError("Invalid native edit was accepted: "+name)
        print("NATIVE_REJECTION",name,"preserved",flush=True)
        (output/"rejections.json").write_text(json.dumps(reports,indent=2)+"\n")

    rejected("out_of_range",lambda:nested.update({"head_width":state["ranges"]["head_width"][1]+1}))
    housing=bpy.data.objects[state["outputs"]["housing_left"]["object"]]
    camera={"size":[16,16],"projection":"perspective",
            "matrix":[[1,0,0,0],[0,1,0,0],[0,0,float("nan"),0]]}
    rejected("nonfinite_camera",lambda:registration.silhouette([housing],camera),
             "projection matrix")
    camera["matrix"]=[[0,0,0,0],[0,0,0,0],[0,0,0,0]]
    rejected("singular_camera",lambda:registration.silhouette([housing],camera),
             "Singular perspective camera")
    stale=geometry.selection(housing,indices=[0])
    # Use the actual pre-hollow topology signature as an obsolete selection.
    stock=bpy.data.objects[state["outputs"]["master_stock"]["object"]]
    stale["topology"]=geometry.signature(stock)
    if stale["topology"]==geometry.signature(housing):
        raise RuntimeError("Stale-region setup did not change topology")
    rejected("stale_region_definition",lambda:regions.define(housing,"Obsolete region",stale),
             "Stale or foreign selection")
    # Model a named region retained from the real pre-hollow topology. Compare
    # the operation against that injected input state before restoring setup.
    old_regions=housing.get("mw_regions")
    obsolete=json.loads(old_regions or "{}")
    obsolete["Obsolete region"]={"topology":stale["topology"],"indices":[0]}
    housing["mw_regions"]=json.dumps(obsolete)
    try:
        invalid_region_state=snapshot()
        rejected("stale_named_region",lambda:regions.resolve(housing,"Obsolete region"),
                 "Region topology changed",invalid_region_state)
    finally:
        if old_regions is None:
            del housing["mw_regions"]
        else:
            housing["mw_regions"]=old_regions
    if snapshot()!=baseline:
        raise RuntimeError("Stale-region setup restoration changed native state")
    reports["stale_named_region"]["setup_restored"]=True

    for case in ("missing_surface_role","excessive_seam_depth","invalid_material_scale",
                 "cage_displacement","cage_foldover","missing_marking_anchor"):
        nodes=copy.deepcopy(state["nodes"])
        expected=None
        if case=="missing_surface_role":
            nodes["housing_seam_front_grip"]["args"]["query"]={"materials":[999],"components":1}
        elif case=="excessive_seam_depth":
            nodes["housing_seam_front_grip"]["args"]["overlap"]=20
        elif case=="invalid_material_scale":
            nodes["direction_switch"]["material"]["finish"]={
                "role":"plastic","color":[.4,.4,.4,1],"roughness":.4,
                "variation":.1,"grain_mm":0,"bump_mm":.01,"seed":1}
        elif case=="cage_displacement":
            nodes["master"]["args"]["controls"][1][1][1]=[1e6,0,0]
        elif case=="cage_foldover":
            controls=np.zeros((4,4,4,3))
            for j in range(4):
                controls[:,j,:,1]=-180*(j/3-.5)
            nodes["master"]["args"]["controls"]=controls.tolist()
            nodes["master"]["args"]["max_displacement"]=100
            expected="foldover"
        else:
            nodes["texture_left"]={"kind":"surface_marking","visible":True,
                "deps":[{"id":"housing_left","use":"geometry"}],
                "args":{"text":"1","origin":[10000,-27,160],
                        "horizontal":[1,0,0],"vertical":[0,0,1],
                        "query":{"materials":[0],"components":1},
                        "projection_axis":1,"side":-1,"max_distance":5}}
            expected="project"
        rejected(case,lambda:nested.reconfigure(nodes),expected)

    nodes=copy.deepcopy(state["nodes"])
    nodes["direction_switch"]["args"]["radius"] = .45
    before_control=sculpt.coordinates(bpy.data.objects[state["outputs"]["direction_switch"]["object"]]).copy()
    checkpoint=nested._checkpoint
    phases=[]
    def fail(phase):
        phases.append(phase)
        if phase=="after_commit":
            raise RuntimeError("Injected native drill post-commit failure")
    nested._checkpoint=fail
    try:
        rejected("late_commit",lambda:nested.reconfigure(nodes))
    finally:
        nested._checkpoint=checkpoint
    if "after_commit" not in phases:
        raise RuntimeError("Failure injection did not reach the commit checkpoint")
    expected_updates={"direction_switch"}
    while True:
        expanded=expected_updates | {key for key,node in nodes.items()
            if any(dep["id"] in expected_updates and dep.get("use","geometry")=="geometry"
                   for dep in node.get("deps",[]))}
        if expanded==expected_updates:
            break
        expected_updates=expanded
    recovered=nested.reconfigure(nodes)
    if not recovered["passed"] or set(recovered["updated"])!=expected_updates:
        raise RuntimeError("Native drill recovery updated unexpected parts")
    current=nested.load()
    after_control=sculpt.coordinates(bpy.data.objects[current["outputs"]["direction_switch"]["object"]])
    if before_control.shape!=after_control.shape:
        raise RuntimeError("Unexpected selector bevel topology change")
    displacement=float(np.linalg.norm(after_control-before_control,axis=1).max())
    if not 1e-6 < displacement < .1:
        raise RuntimeError("Recovered selector bevel lacks its expected geometric change")
    preserved=digest==hashlib.sha256(source.read_bytes()).hexdigest()
    result={"blender":bpy.app.version_string,"source_sha256":digest,"source_preserved":preserved,
            "rejections":reports,"recovery":recovered,"late_failure_phases":phases,
            "expected_recovery_updates":sorted(expected_updates),
            "recovered_control_displacement_mm":displacement,
            "scope":"Twelve native failures and selective recovery, including named-region resolution on an injected obsolete topology signature; recovered material and marking readback included when present; full visual acceptance remains separate",
            "passed":preserved and all(r["rejected"] and r["state_preserved"] for r in reports.values())}
    if not result["passed"]:
        raise RuntimeError("Native input was changed")
    recovered_file=output/"recovered.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(recovered_file.resolve()))
    if any("finish" in node.get("material",{}) for node in nodes.values()):
        sys.path.insert(0,str(ROOT/"examples"))
        from verify_drill_realism_finishes import verify as verify_finishes
        finish_report=output/"recovered-finishes.json"
        verify_finishes(recovered_file,finish_report)
        result["finish_verification"]=json.loads(finish_report.read_text())
    (output/"verification.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    verify(*map(Path,sys.argv[sys.argv.index("--")+1:]))
