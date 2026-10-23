"""Fit the current character's lids to explicit globe supports and align gaze."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import eyelid_fit,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Tip and alar study'];before=sculpt.coordinates(source)
    old_settings=json.loads(bpy.data.objects['Open-eye head']['mw_eye_settings'])
    balls=[bpy.data.objects[f'Open-eye head globe {i+1}'] for i in range(2)]
    ball_before={ball.name:sculpt.coordinates(ball) for ball in balls}
    eyes=[{**row,'center':list(ball.location),'target_upper_mm':4.7,'target_lower_mm':3.4,'clearance_mm':.30}
          for row,ball in zip(old_settings,balls)]
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    bad=copy.deepcopy(eyes);bad[1]['center'][0]+=.2
    for invalid in (bad,[eyes[0],eyes[0]]):
        try:eyelid_fit.fit(source,invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid eye registration accepted')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    with patch.object(eyelid_fit.layers,'finish',side_effect=RuntimeError('Injected layer failure')):
        try:eyelid_fit.fit(source,eyes)
        except RuntimeError as exc:assert str(exc)=='Injected layer failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=eyelid_fit.fit(source,eyes,'Supported eyelid study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    protected_nose=(np.abs(before[:,0])<.024)&(before[:,2]<1.635)
    np.testing.assert_array_equal(before[protected_nose],after[protected_nose])
    assert sculpt.topology(source)==sculpt.topology(result)
    sculpt.set_layer(result,report['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    sculpt.set_layer(result,report['layer'],1)
    gaze=[]
    for ball in balls:
        clone=ball.copy();clone.data=ball.data.copy();clone.name=ball.name+' forward gaze'
        bpy.context.collection.objects.link(clone)
        clone.rotation_euler.z=0
        ball.hide_render=True;ball.hide_set(True)
        clone.hide_render=False;clone.hide_set(False)
        np.testing.assert_array_equal(ball_before[ball.name],sculpt.coordinates(ball))
        gaze.append(clone.name)
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    report.update(source_preserved=True,source_globes_preserved=True,topology_preserved=True,
                  nose_vertices_preserved=int(protected_nose.sum()),layer_rollback=True,
                  invalid_registration_cases=2,late_failure_atomic=True,blender=bpy.app.version_string,
                  source_sha256=digest,gaze_objects=gaze,gaze_yaw_degrees=0,
                  limits='Spherical static support; no tear lake, blink rig, tissue model or anatomical validation.')
    folder.mkdir(parents=True)
    for filename,value in [('registration.json',eyes),('verification.json',report)]:
        (folder/filename).write_text(json.dumps(value,indent=2),encoding='utf-8')
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    camera(position=(0,-4,1.63),target=(0,-.075,1.63),scale=.11,size=(640,640))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    native=folder/'supported-lids.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Supported eyelid study']))
    print('EYELID_SAVED_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k!='eyes'}),flush=True)
    for name,position,target,scale in [
        ('front',(0,-4,1.63),(0,-.075,1.63),.11),
        ('oblique',(1.5,-4,1.65),(0,-.045,1.642),.145)]:
        camera(position=position,target=target,scale=scale,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('EYELID_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
