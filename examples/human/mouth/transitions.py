"""Fair registered philtrum/lower-fold transitions, preserving lips and source."""
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
from mesh_workbench import anatomy_fit,surface_brush,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Oral relief study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    target=json.loads((path.parent/'diagram.json').read_text())['registration']['target']
    for key,p in target['landmarks'].items():
        hit=tree.ray_cast(Vector((p[0],-1,p[2])),Vector((0,1,0)))[0]
        if hit is None:raise ValueError('Target misses surface')
        target['landmarks'][key]=list(hit)
    diagram,commands=anatomy_fit.compile_oral_transitions(source,target)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    # The first stroke succeeds, then an invalid second stroke must remove it.
    try:surface_brush.apply(source,diagram,[commands[0],{**commands[1],'mode':'invalid'}])
    except ValueError:pass
    else:raise AssertionError('Invalid second stroke accepted')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    with patch.object(surface_brush.layers,'finish',side_effect=RuntimeError('Injected failure')):
        try:surface_brush.apply(source,diagram,commands)
        except RuntimeError as exc:assert str(exc)=='Injected failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,reports=surface_brush.apply(source,diagram,commands,'Oral transition study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    allowed=np.zeros(len(before),dtype=bool)
    for region in diagram['regions'].values():
        allowed|=np.all((before>=region['min'])&(before<=region['max']),axis=1)
    np.testing.assert_array_equal(before[~allowed],after[~allowed])
    lips=(before[:,2]>=diagram['regions']['lower_fold']['max'][2])&(before[:,2]<=diagram['regions']['philtrum']['min'][2])
    np.testing.assert_array_equal(before[lips],after[lips])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    report={'blender':bpy.app.version_string,'source_preserved':True,'topology_preserved':True,
            'protected_vertices':int((~allowed).sum()),'lip_band_vertices':int(lips.sum()),
            'rollback':True,'invalid_second_stroke_atomic':True,'injected_failure_atomic':True,
            'maximum_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'commands.json').write_text(json.dumps(commands,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'oral-transitions.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Oral transition study']))
    print('TRANSITIONS_READBACK_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(0,-4,1.582)),('oblique',(2.7,-4,1.59))]:
        camera(position=pos,target=(0,-.065,1.582),scale=.092,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('TRANSITIONS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
