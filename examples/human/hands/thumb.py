"""Fit bilateral thumb outlines and verify atomic rollback."""
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
from mesh_workbench.regions import hand
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Hand transition study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    centers=[-.32,.32]
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try:hand.apply_palms(source,[.32,.32],name="Invalid thumb probe",profile="thumb")
    except ValueError as exc:assert str(exc)=='Palm center must match side'
    else:raise AssertionError('Invalid side accepted')
    original=curve_fit.apply;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('Injected second arm failure')
        return original(*args,**kwargs)
    with patch.object(curve_fit,'apply',side_effect=fail_second):
        try:hand.apply_palms(source,centers,name="Thumb outline study",profile="thumb")
        except RuntimeError as exc:assert str(exc)=='Injected second arm failure'
        else:raise AssertionError('Failure not exercised')
    assert len(calls)==2
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,diagrams,reports=hand.apply_palms(source,centers,name="Thumb outline study",profile="thumb")
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
            'rollback':True,'invalid_registration_rejected':True,'second_arm_failure_atomic':True,
            'maximum_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    actual=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
    residuals=[actual.find_nearest(Vector(c['target']))[3]*1000 for d in diagrams for c in d['controls']]
    assert max(residuals)<.2,residuals
    report['maximum_surface_residual_mm']=max(residuals)
    for side in (-1,1):
        for offset in (-.017,0,.017):
            x=side*(.31+.2*(.90-.79)+offset)
            assert actual.ray_cast(Vector((x,-1,.79)),Vector((0,1,0)))[0] is None
    report['six_finger_gap_rays_open']=True
    changes=[]
    for d in diagrams:
        side=d['registration']['side'];center=d['registration']['center_x']
        for section in d['sections']:
            old=np.array(section['source']);now=[]
            for point in old:
                hit=actual.ray_cast(Vector((center,point[1],point[2])),Vector((-side,0,0)))[0]
                assert hit is not None;now.append(hit.x)
            before_bend=float(np.max(np.abs(np.diff(old[:,0],n=2)))*1000)
            after_bend=float(np.max(np.abs(np.diff(now,n=2)))*1000)
            assert after_bend<before_bend,(before_bend,after_bend)
            changes.append({'side':side,'y':section['y'],'before_second_difference_mm':before_bend,'after_second_difference_mm':after_bend})
    report['section_continuity']=changes
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagrams,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'thumb-outline.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Thumb outline study']))
    print('TRANSITIONS_READBACK_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(.32,-4,.84)),('oblique',(2.32,-4,.84))]:
        camera(position=pos,target=(.32,0,.84),scale=.25,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        # Both renders use the same saved scene and camera; originals remain preserved.
        source=bpy.data.objects['Hand transition study'];result=bpy.data.objects['Thumb outline study']
        for label,original in [('before',True),('after',False)]:
            source.hide_render=not original;result.hide_render=original
            scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('TRANSITIONS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
