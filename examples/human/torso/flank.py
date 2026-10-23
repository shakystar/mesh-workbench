"""Fit lateral waist and upper-pelvis envelope on the current character; preserve vertices outside the torso box."""
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import curve_fit,sculpt
from mesh_workbench.regions import torso
from mesh_workbench.runner import camera

def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Axillary transition study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    target={'half_width_m':.13,'region':{'min':[-.19,-.13,.98],'max':[.19,.13,1.25],'feather_mm':15}}
    for name,z in [('sternum',1.31),('waist',1.11),('pelvis',1.0)]:
        target[name]=list(tree.ray_cast(Vector((0,-1,z)),Vector((0,1,0)))[0])
    diagram=torso.compile_controls(source,target,profile="flank")
    try:torso.compile_controls(source,target,profile='unknown')
    except ValueError:pass
    else:raise AssertionError('Unknown profile accepted')
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    bad={**target,'sternum':target['pelvis']}
    try:torso.compile_controls(source,bad,profile="flank")
    except ValueError:pass
    else:raise AssertionError('Invalid reference order accepted')
    with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected torso failure')):
        try:curve_fit.apply(source,diagram)
        except RuntimeError as exc:assert str(exc)=='Injected torso failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=curve_fit.apply(source,diagram,'Flank transition study');after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    r=target['region'];protected=~np.all((before>=r['min'])&(before<=r['max']),axis=1)
    np.testing.assert_array_equal(before[protected],after[protected])
    sculpt.set_layer(result,report['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    sculpt.set_layer(result,report['layer'],1)
    actual=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
    residuals={c['name']:actual.find_nearest(Vector(c['target']))[3]*1000 for c in diagram['controls']}
    assert max(residuals.values())<.2,residuals
    report.update(blender=bpy.app.version_string,source_preserved=True,topology_preserved=True,
        protected_exact=True,rollback=True,invalid_order_rejected=True,late_failure_atomic=True,
        target_surface_distance_mm=residuals,source_sha256=digest)
    folder.mkdir(parents=True);(folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'flank-transition.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Flank transition study']))
    print('TORSO_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k!='target_surface_distance_mm'}),flush=True)
    for view,pos in [('front',(0,-4,1.11)),('oblique',(2.8,-4,1.11))]:
        camera(position=pos,target=(0,0,1.11),scale=.48,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        source=bpy.data.objects['Axillary transition study'];result=bpy.data.objects['Flank transition study']
        for label,original in [('before',True),('after',False)]:
            source.hide_render=not original;result.hide_render=original
            scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('TORSO_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
