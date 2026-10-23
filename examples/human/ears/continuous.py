"""Local ear subdivision and continuous surface paths; preserve the face input."""
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
from mesh_workbench import anatomy_ear,geometry,surface_brush,sculpt
from mesh_workbench.runner import camera

def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Chin contour study'];before=sculpt.coordinates(source)
    targets=json.loads((ROOT/'examples/human/recipes/human-ear-targets.json').read_text())['targets']
    def register(obj):
        xyz=sculpt.coordinates(obj)
        tree=BVHTree.FromPolygons(xyz.tolist(),[list(f.vertices) for f in obj.data.polygons])
        for target in targets:
            sign=-1 if target['side']=='negative_x' else 1
            for key,p in target['landmarks'].items():
                hit=tree.ray_cast(Vector((sign,p[1],p[2])),Vector((-sign,0,0)))[0]
                if hit is None:raise ValueError('Ear reference misses skin')
                target['landmarks'][key]=list(hit)
    register(source)
    guides=[anatomy_ear.compile_ear(source,t,tolerance_mm=.1) for t in targets]
    selected=set()
    for guide in guides:
        r=next(iter(guide['regions'].values()))
        selected.update(geometry.selection(source,'FACE',box=[r['min'],r['max']])['indices'])
    selection=geometry.selection(source,'FACE',indices=sorted(selected))
    refined=geometry.edit_topology(source,selection,'subdivide','Refined ear source',cuts=2)
    for face in refined.data.polygons:face.use_smooth=True
    original=sculpt.coordinates(refined)
    # All original vertices survive subdivision; no source or old selection mutated.
    positions={tuple(p) for p in original}
    assert all(tuple(p) in positions for p in before)
    register(refined)
    diagram,commands=anatomy_ear.compile_surface_paths(refined,targets)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try:anatomy_ear.compile_surface_paths(refined,[targets[0],targets[0]])
    except ValueError as exc:assert 'overlap' in str(exc)
    else:raise AssertionError('Overlapping ears accepted')
    # Exercise batch cleanup after the first ear, at second-ear layer creation.
    begin=surface_brush.layers.begin;calls=0
    def injected(*a,**kw):
        nonlocal calls
        calls+=1
        if calls==8:raise RuntimeError('Injected second-ear failure')
        return begin(*a,**kw)
    with patch.object(surface_brush.layers,'begin',side_effect=injected):
        try:surface_brush.apply(refined,diagram,commands)
        except RuntimeError as exc:assert str(exc)=='Injected second-ear failure'
        else:raise AssertionError('Late failure not exercised')
    assert calls==8
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,reports=surface_brush.apply(refined,diagram,commands,'Continuous auricle study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    np.testing.assert_array_equal(original,sculpt.coordinates(refined))
    assert sculpt.topology(refined)==sculpt.topology(result)
    allowed=np.zeros(len(original),dtype=bool)
    for r in diagram['regions'].values():allowed|=np.all((original>=r['min'])&(original<=r['max']),axis=1)
    np.testing.assert_array_equal(original[~allowed],after[~allowed])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_allclose(original,sculpt.coordinates(result),rtol=0,atol=2e-7)
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    info=geometry.inspect(result)
    assert info['finite'] and info['nonmanifold_edges']==0
    report={'blender':bpy.app.version_string,'source_preserved':True,'original_vertices_retained':True,
            'vertices_before':len(before),'vertices_refined':len(original),
            'protected_vertices':int((~allowed).sum()),'all_layer_rollback':True,
            'overlap_rejected':True,'second_ear_failure_atomic':True,'nonmanifold_edges':0,
            'max_displacement_mm':float(np.linalg.norm(after-original,axis=1).max()*1000),
            'brushes':reports,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'commands.json').write_text(json.dumps(commands,indent=2))
    for obj in (source,refined):obj.hide_render=True;obj.hide_set(True)
    result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'continuous-ears.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Continuous auricle study']))
    print('CONTINUOUS_EARS_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k!='brushes'}),flush=True)
    for view,pos,target in [('right',(4,.012,1.628),(.085,.012,1.628)),
                            ('left',(-4,-1.2,1.65),(-.085,.012,1.628))]:
        camera(position=pos,target=target,scale=.085,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('CONTINUOUS_EARS_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
