"""Replace the measured folded underside patch while preserving its boundary."""
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch as mock
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt,geometry
from mesh_workbench.regions import patch
from mesh_workbench.runner import camera

def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh output required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Neck transition study'];before=sculpt.coordinates(source)
    bounds=[[-.023,-.058,1.520],[.023,-.043,1.537]]
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try:patch.rebuild(source,[[0,0,0],[.001,.001,.001]])
    except ValueError:pass
    else:raise AssertionError('Empty patch accepted')
    with mock.object(patch,'delaunay_2d_cdt',side_effect=RuntimeError('Injected triangulation failure')):
        try:patch.rebuild(source,bounds)
        except RuntimeError as exc:assert str(exc)=='Injected triangulation failure'
        else:raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=patch.rebuild(source,bounds,'Rebuilt underside study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    assert geometry.inspect(result)['nonmanifold_edges']==0
    def crossings(obj,x,y):
        p=sculpt.coordinates(obj)
        fs=[list(f.vertices) for f in obj.data.polygons if np.all((p[list(f.vertices),2]>1.49)&(p[list(f.vertices),2]<1.55))]
        tree=BVHTree.FromPolygons(p.tolist(),fs);cursor=1.48;hits=[]
        for _ in range(12):
            hit=tree.ray_cast(Vector((x,y,cursor)),Vector((0,0,1)))[0]
            if hit is None or hit.z>1.55:break
            hits.append(hit.z);cursor=hit.z+.0000005
        return hits
    samples=[]
    for x in (-.01,0,.01):
        for y in (-.053,-.052,-.0518,-.051):
            old,new=crossings(source,x,y),crossings(result,x,y)
            assert len(new)==1,(x,y,new)
            samples.append({'x':x,'y':y,'before':old,'after':new})
    report.update(blender=bpy.app.version_string,source_preserved=True,
        invalid_empty_patch=True,injected_failure_atomic=True,nonmanifold_edges=0,
        sections=samples,source_sha256=digest,bounds=bounds)
    folder.mkdir(parents=True)
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'rebuilt-underside.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Rebuilt underside study']))
    print('PATCH_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k not in ('boundary_coordinates','sections')}),flush=True)
    for view,pos,target,scale in [('front',(0,-4,1.49),(0,-.025,1.49),.34),
                                  ('profile',(4,-.03,1.52),(0,-.03,1.52),.20)]:
        camera(position=pos,target=target,scale=scale,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('PATCH_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
