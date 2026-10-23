"""Bilateral registered auricle relief on the current preserved character."""
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
from mesh_workbench import anatomy_ear,curve_fit,sculpt
from mesh_workbench.runner import camera

def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Chin contour study'];before=sculpt.coordinates(source)
    targets=json.loads((ROOT/'examples/human/recipes/human-ear-targets.json').read_text())['targets']
    tree=BVHTree.FromPolygons(before.tolist(),[list(f.vertices) for f in source.data.polygons])
    for target in targets:
        sign=-1 if target['side']=='negative_x' else 1
        for key,p in target['landmarks'].items():
            hit=tree.ray_cast(Vector((sign,p[1],p[2])),Vector((-sign,0,0)))[0]
            if hit is None:raise ValueError('Ear reference misses skin')
            target['landmarks'][key]=list(hit)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    for bad in ([targets[0],targets[0]],[{**targets[0],'side':'unknown'}]):
        try:anatomy_ear.apply_relief(source,bad)
        except ValueError:pass
        else:raise AssertionError('Invalid registration accepted')
    finish=curve_fit.layers.finish;calls=0
    def injected(*a,**kw):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('Injected second-ear failure')
        return finish(*a,**kw)
    with patch.object(curve_fit.layers,'finish',side_effect=injected):
        try:anatomy_ear.apply_relief(source,targets)
        except RuntimeError as exc:assert str(exc)=='Injected second-ear failure'
        else:raise AssertionError('Late failure not exercised')
    assert calls==2
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,diagrams,reports=anatomy_ear.apply_relief(source,targets)
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert sculpt.topology(source)==sculpt.topology(result)
    allowed=np.zeros(len(before),dtype=bool)
    for diagram in diagrams:
        r=diagram['region'];allowed|=np.all((before>=r['min'])&(before<=r['max']),axis=1)
    np.testing.assert_array_equal(before[~allowed],after[~allowed])
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    actual=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
    residuals=[{c['name']:actual.find_nearest(Vector(c['target']))[3]*1000 for c in d['controls']} for d in diagrams]
    assert max(v for r in residuals for v in r.values())<.2,residuals
    report={'blender':bpy.app.version_string,'source_preserved':True,'topology_preserved':True,
            'protected_vertices':int((~allowed).sum()),'paired_rollback':True,
            'invalid_cases':2,'second_ear_failure_atomic':True,'target_surface_distance_mm':residuals,
            'max_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'fits':reports,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'diagrams.json').write_text(json.dumps(diagrams,indent=2))
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'auricle-relief.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    source=bpy.data.objects['Chin contour study'];result=bpy.data.objects['Auricle relief study']
    np.testing.assert_array_equal(after,sculpt.coordinates(result))
    print('AURICLE_READBACK_PASS',json.dumps(report),flush=True)
    for state in ('before','after'):
        source.hide_render=state=='after';result.hide_render=state=='before'
        for view,pos,target in [('right',(4,.012,1.628),(.085,.012,1.628)),
                                ('left',(-4,-1.2,1.65),(-.085,.012,1.628))]:
            camera(position=pos,target=target,scale=.085,size=(640,640))
            scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
            scene.render.filepath=str(folder/(state+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('AURICLE_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
