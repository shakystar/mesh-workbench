"""Replace the included procedural nose's two cutouts with rolled entrance patches."""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import nasal_entrance,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists(): raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Lower nose curve study']; before=sculpt.coordinates(source)
    n=Vector((0,-.30,-.954)).normalized(); h=Vector((1,0,0)); v=n.cross(h)
    specs=[]
    for sign,side,y in [(-1,'left',-.08661651611328125),(1,'right',-.08659648895263672)]:
        angle=math.radians(sign*18)
        specs.append({'name':side,'center':[sign*.00663,y,1.607],'normal':list(n),
                      'across':list(h*math.cos(angle)+v*math.sin(angle)),
                      'width_mm':5.5,'length_mm':9,'depth_mm':5.5,'cut_scale':1.65,
                      'aperture_scale':.88,'offset_mm':[0,.4,-.2]})
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    bad=copy.deepcopy(specs);bad[0]['center'][2]=2.5
    try: nasal_entrance.build(source,bad)
    except ValueError: pass
    else: raise AssertionError('Missing registration accepted')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    original=nasal_entrance._replace; calls=0
    def fail_second(*args):
        nonlocal calls
        calls+=1
        if calls==2: raise RuntimeError('Injected second patch failure')
        return original(*args)
    with patch.object(nasal_entrance,'_replace',fail_second):
        try: nasal_entrance.build(source,specs)
        except RuntimeError as exc: assert str(exc)=='Injected second patch failure'
        else: raise AssertionError('Late failure not exercised')
    assert calls==2 and set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=nasal_entrance.build(source,specs)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    after=sculpt.coordinates(result)
    protected=(np.abs(before[:,0])>.023)|(before[:,2]<1.596)|(before[:,2]>1.63)|(before[:,1]>-.055)
    retained={tuple(p) for p in after}
    assert all(tuple(p) in retained for p in before[protected])
    tree=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
    for row in report['patches']:
        center=Vector(row['entry_center']); normal=Vector(row['normal'])
        hit=tree.ray_cast(center+normal*.02,-normal)[0]
        assert hit is not None
        measured=(center-hit).dot(normal)*1000
        assert 4<measured<8, measured
        row['measured_central_depth_mm']=measured
    report.update(source_preserved=True,protected_vertices=int(protected.sum()),
                  invalid_registration_rejected=True,late_failure_atomic=True,
                  blender=bpy.app.version_string,source_sha256=digest)
    folder.mkdir(parents=True)
    for filename,value in [('registration.json',specs),('verification.json',report)]:
        (folder/filename).write_text(json.dumps(value,indent=2),encoding='utf-8')
    source.hide_render=True;source.hide_set(True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    camera(position=(0,-4,1.63),target=(0,-.075,1.63),scale=.11,size=(640,640))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'nasal-entrances.blend'))
    print('NASAL_ENTRANCES_PASS',json.dumps({k:v for k,v in report.items() if k!='patches'}),flush=True)
    for name,position,target,scale in [
        ('front',(0,-4,1.63),(0,-.075,1.63),.11),
        ('profile',(4,-.075,1.63),(0,-.075,1.63),.11),
        ('basal',(0,-1.5,.05),(0,-.078,1.613),.105)]:
        camera(position=position,target=target,scale=scale,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    print('NASAL_ENTRANCE_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
