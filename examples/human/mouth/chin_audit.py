"""Inspect the preserved chin profile before authoring its contour controls."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt
from mesh_workbench.runner import camera

def run(source_path,output_path):
    folder=Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh folder required')
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    obj=bpy.data.objects['Oral transition study'];xyz=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(xyz.tolist(),[list(p.vertices) for p in obj.data.polygons])
    samples=[]
    for x in (0,.014,.028,.042):
        for z in (1.53,1.538,1.546,1.554):
            hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
            samples.append(list(hit) if hit else None)
    folder.mkdir(parents=True);(folder/'samples.json').write_text(json.dumps(samples,indent=2))
    print('CHIN_SAMPLES',json.dumps(samples),flush=True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    for view,pos in [('front',(0,-4,1.57)),('profile',(4,-.03,1.57))]:
        camera(position=pos,target=(0,-.03,1.57),scale=.18,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
