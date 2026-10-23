"""Fair front/back wrist seams while preserving fingers."""
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
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Hands grafted study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    diagram={'units':'m','landmarks':{},'regions':{}};commands=[]
    for side in (-1,1):
        for view in (-1,1):
            name='wrist '+str(side)+' '+str(view);keys=[]
            for i,offset in enumerate(np.linspace(-.017,.017,7)):
                x=side*.31+offset;z=.901
                hit=tree.ray_cast(Vector((x,view,z)),Vector((0,-view,0)))[0]
                if hit is None:raise ValueError('Wrist path misses surface')
                key=name+'_'+str(i);diagram['landmarks'][key]=list(hit);keys.append(key)
            xs=sorted((side*.27,side*.35))
            diagram['regions'][name]={'min':[xs[0],-.08,.875],'max':[xs[1],.08,.932],'feather':.005}
            commands.append({'mode':'relax_volume','label':name,'anchors':keys,'region':name,
                'view_direction':[0,-view,0],'radius_mm':20,'strength':.12,'iterations':3,'max_displacement_mm':3})
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    # The first stroke succeeds, then an invalid second stroke must remove it.
    try:surface_brush.apply(source,diagram,[commands[0],{**commands[1],'mode':'invalid'}])
    except ValueError as exc:assert str(exc)=='Unknown surface brush',str(exc)
    else:raise AssertionError('Invalid second stroke accepted')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    with patch.object(surface_brush.layers,'finish',side_effect=RuntimeError('Injected failure')):
        try:surface_brush.apply(source,diagram,commands)
        except RuntimeError as exc:assert str(exc)=='Injected failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,reports=surface_brush.apply(source,diagram,commands,'Wrist transition study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    allowed=np.zeros(len(before),dtype=bool)
    for region in diagram['regions'].values():
        allowed|=np.all((before>=region['min'])&(before<=region['max']),axis=1)
    np.testing.assert_array_equal(before[~allowed],after[~allowed])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    report={'blender':bpy.app.version_string,'source_preserved':True,'topology_preserved':True,
            'protected_vertices':int((~allowed).sum()),
            'rollback':True,'invalid_second_stroke_atomic':True,'injected_failure_atomic':True,
            'maximum_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'commands.json').write_text(json.dumps(commands,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'wrist-transitions.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Wrist transition study']))
    print('TRANSITIONS_READBACK_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(.32,-4,.89)),('oblique',(2.32,-4,.89))]:
        camera(position=pos,target=(.32,0,.89),scale=.19,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        # Both renders use the same saved scene and camera; originals remain preserved.
        source=bpy.data.objects['Hands grafted study'];result=bpy.data.objects['Wrist transition study']
        for label,original in [('before',True),('after',False)]:
            source.hide_render=not original;result.hide_render=original
            scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('TRANSITIONS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
