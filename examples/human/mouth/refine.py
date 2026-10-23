"""Apply registered oral relief to the current preserved character; bounded review."""
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
from mesh_workbench import anatomy_fit,curve_fit,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Supported eyelid study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    def project(x,z):
        hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
        if hit is None:raise ValueError('Registration misses visible surface')
        return list(hit)
    target={'units':'m','knowledge_id':'oral-neutral-v1','landmarks':{
        'corner_left':project(-.021,1.579),'corner_right':project(.021,1.579),
        'nose_base':project(0,1.603),'chin_fold':project(0,1.562)}}
    diagram=anatomy_fit.compile_oral_relief(source,target)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    for invalid in (-1,float('nan'),3):
        try:anatomy_fit.compile_oral_relief(source,target,upper_mm=invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid amplitude accepted')
    bad=json.loads(json.dumps(target));bad['landmarks']['corner_left'][1]-=.02
    try:anatomy_fit.compile_oral_relief(source,bad)
    except ValueError:pass
    else:raise AssertionError('Off-surface registration accepted')
    with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected oral failure')):
        try:curve_fit.apply(source,diagram,'Oral relief study')
        except RuntimeError as exc:assert str(exc)=='Injected oral failure'
        else:raise AssertionError('Late failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=curve_fit.apply(source,diagram,'Oral relief study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    lo,hi=np.array(diagram['region']['min']),np.array(diagram['region']['max'])
    protected=~np.all((before>lo)&(before<hi),axis=1)
    np.testing.assert_array_equal(before[protected],after[protected])
    nose_eyes=before[:,2]>=1.604
    np.testing.assert_array_equal(before[nose_eyes],after[nose_eyes])
    sculpt.set_layer(result,report['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    sculpt.set_layer(result,report['layer'],1)
    actual=BVHTree.FromPolygons(after.tolist(),[list(p.vertices) for p in result.data.polygons])
    residuals={c['name']:actual.find_nearest(Vector(c['target']))[3]*1000 for c in diagram['controls']}
    assert max(residuals.values())<.2,residuals
    report.update(blender=bpy.app.version_string,source_preserved=True,topology_preserved=True,
                  protected_exact=True,nose_eye_vertices_preserved=int(nose_eyes.sum()),
                  rollback=True,invalid_cases=4,late_failure_atomic=True,
                  target_residual_mm=residuals,source_sha256=digest)
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2),encoding='utf-8')
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'oral-relief.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    result=bpy.data.objects['Oral relief study'];source=bpy.data.objects['Supported eyelid study']
    np.testing.assert_array_equal(after,sculpt.coordinates(result))
    print('ORAL_SAVED_READBACK_PASS',json.dumps(report),flush=True)
    for state in ('before','after'):
        source.hide_render=state=='after';result.hide_render=state=='before'
        for view,pos in [('front',(0,-4,1.582)),('oblique',(2.7,-4,1.59))]:
            camera(position=pos,target=(0,-.065,1.582),scale=.092,size=(640,640))
            scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
            scene.render.filepath=str(folder/(state+'-'+view+'.png'))
            bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ORAL_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
