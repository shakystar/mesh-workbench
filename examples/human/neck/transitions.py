"""Registered submental fairing and lower-neck/clavicle surface transitions."""
import copy
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
from mesh_workbench import surface_brush,sculpt
from mesh_workbench.regions import neck
from mesh_workbench.runner import camera

def run(source_path,output_path,baseline_path=None):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh output folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Continuous auricle study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(f.vertices) for f in source.data.polygons])
    registration={'units':'m','protect_above_z':1.535,'paths':[]}
    def path_row(name,xz,region,brush):
        points=[]
        for x,z in xz:
            hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
            if hit is None:raise ValueError('Neck registration misses skin')
            points.append(list(hit))
        registration['paths'].append({'name':name,'points':points,'region':region,'brush':brush})
    path_row('submental transition',[(x,1.522) for x in (-.022,-.011,0,.011,.022)],
        {'min':[-.05,-.1,1.495],'max':[.05,-.005,1.535],'feather':.003},
        {'mode':'relax_volume','view_direction':[0,.8,.6],'radius_mm':16,'strength':.5,'iterations':12,'max_displacement_mm':2})
    region={'min':[-.16,-.13,1.415],'max':[.16,.005,1.532],'feather':.004}
    for sign,side in [(-1,'left'),(1,'right')]:
        path_row(side+' lower SCM',[(sign*x,z) for x,z in [(.040,1.523),(.033,1.509),(.026,1.49),(.018,1.47),(.012,1.451)]],
            region,{'mode':'ridge','radius_mm':7,'distance_mm':.7,'max_displacement_mm':.8})
        path_row(side+' clavicle transition',[(sign*x,z) for x,z in [(.022,1.448),(.047,1.443),(.077,1.438),(.11,1.43),(.14,1.421)]],
            region,{'mode':'relax_volume','radius_mm':12,'strength':.35,'iterations':5,'max_displacement_mm':1.5})
    diagram,commands=neck.compile_paths(source,registration)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    invalid=copy.deepcopy(registration);invalid['paths'][0]['region']['max'][2]=1.6
    bad=copy.deepcopy(registration);bad['paths'][0]['points'][0][1]-=.02
    for item in (invalid,bad):
        try:neck.compile_paths(source,item)
        except ValueError:pass
        else:raise AssertionError('Invalid neck registration accepted')
    begin=surface_brush.layers.begin;calls=0
    def injected(*a,**kw):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('Injected neck failure')
        return begin(*a,**kw)
    with patch.object(surface_brush.layers,'begin',side_effect=injected):
        try:surface_brush.apply(source,diagram,commands)
        except RuntimeError as exc:assert str(exc)=='Injected neck failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,reports=surface_brush.apply(source,diagram,commands,'Neck transition study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    allowed=np.zeros(len(before),dtype=bool)
    for r in diagram['regions'].values():allowed|=np.all((before>=r['min'])&(before<=r['max']),axis=1)
    np.testing.assert_array_equal(before[~allowed],after[~allowed])
    face=before[:,2]>=1.535;np.testing.assert_array_equal(before[face],after[face])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    report={'blender':bpy.app.version_string,'source_preserved':True,'topology_preserved':True,
            'protected_vertices':int((~allowed).sum()),'face_ear_vertices_preserved':int(face.sum()),
            'all_layer_rollback':True,'invalid_cases':2,'late_failure_atomic':True,
            'max_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'registration.json').write_text(json.dumps(registration,indent=2))
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'neck-transitions.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    source=bpy.data.objects['Continuous auricle study'];result=bpy.data.objects['Neck transition study']
    np.testing.assert_array_equal(after,sculpt.coordinates(result))
    print('NECK_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k!='brushes'}),flush=True)
    states=('before','after')
    if baseline_path:
        import shutil
        baseline=Path(baseline_path)
        assert json.loads((baseline/'verification.json').read_text())['source_sha256']==digest
        for view in ('front','profile'):shutil.copyfile(baseline/('before-'+view+'.png'),folder/('before-'+view+'.png'))
        states=('after',)
    for state in states:
        source.hide_render=state=='after';result.hide_render=state=='before'
        for view,pos,target,scale in [('front',(0,-4,1.49),(0,-.025,1.49),.34),
                                       ('profile',(4,-.03,1.52),(0,-.03,1.52),.20)]:
            camera(position=pos,target=target,scale=scale,size=(640,640))
            scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
            scene.render.filepath=str(folder/(state+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('NECK_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
