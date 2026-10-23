"""Fit bilateral knee transition sections and verify atomic rollback."""
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
from mesh_workbench.regions import leg
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Thigh knee study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    targets=[]
    for side in (-1,1):
        xs=sorted((side*.002,side*.20))
        targets.append({'side':side,'profile':'knee_transition','proximal':[side*.092,.012,.76],
            'knee':[side*.101,-.016,.505],'shin':[side*.102,-.002,.44],
            'region':{'min':[xs[0],-.13,.44],'max':[xs[1],.14,.58],'feather_mm':4}})
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    bad=[dict(t) for t in targets];bad[1]['knee']=bad[1]['shin']
    try:leg.apply_pair(source,bad,"Invalid knee registration probe")
    except ValueError as exc:assert str(exc)=='Descending finite leg axes required'
    else:raise AssertionError('Invalid registration accepted')
    original=curve_fit.apply;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('Injected second leg failure')
        return original(*args,**kwargs)
    with patch.object(leg.curve_fit,'apply',side_effect=fail_second):
        try:leg.apply_pair(source,targets,"Knee transition study")
        except RuntimeError as exc:assert str(exc)=='Injected second leg failure'
        else:raise AssertionError('Failure not exercised')
    assert len(calls)==2
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,diagrams,reports=leg.apply_pair(source,targets,"Knee transition study")
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    allowed=np.zeros(len(before),dtype=bool)
    for region in [d['region'] for d in diagrams]:
        allowed|=np.all((before>=region['min'])&(before<=region['max']),axis=1)
    np.testing.assert_array_equal(before[~allowed],after[~allowed])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    report={'blender':bpy.app.version_string,'source_preserved':True,'topology_preserved':True,
            'protected_vertices':int((~allowed).sum()),
            'rollback':True,'invalid_registration_rejected':True,'second_leg_failure_atomic':True,
            'maximum_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    actual=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
    residuals=[actual.find_nearest(Vector(c['target']))[3]*1000 for d in diagrams for c in d['controls']]
    assert max(residuals)<.2,residuals
    report['maximum_surface_residual_mm']=max(residuals)
    assert actual.ray_cast(Vector((0,-1,.65)),Vector((0,1,0)))[0] is None
    report['thigh_gap_open']=True
    changes=[]
    for diagram in diagrams:
        for section in diagram['sections']:
            old=np.asarray(section['source']);now=[]
            for point in old:
                hit=actual.ray_cast(Vector((point[0],-1,point[2])),Vector((0,1,0)))[0]
                assert hit is not None;now.append(hit.y)
            old_bend=float(np.abs(np.diff(old[:,1],n=2)).max()*1000)
            new_bend=float(np.abs(np.diff(now,n=2)).max()*1000)
            assert new_bend<old_bend,(old_bend,new_bend)
            changes.append({'before_second_difference_mm':old_bend,'after_second_difference_mm':new_bend})
    report['section_changes']=changes
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagrams,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'knee-transition.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Knee transition study']))
    print('TRANSITIONS_READBACK_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(0,-4,.60)),('oblique',(2.5,-4,.60))]:
        camera(position=pos,target=(0,0,.60),scale=.50,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        # Both renders use the same saved scene and camera; originals remain preserved.
        source=bpy.data.objects['Thigh knee study'];result=bpy.data.objects['Knee transition study']
        for label,original in [('before',True),('after',False)]:
            source.hide_render=not original;result.hide_render=original
            scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('TRANSITIONS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
