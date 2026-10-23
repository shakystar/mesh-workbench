"""Three-view torso inspection and visible-surface section measurements."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
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
    obj=bpy.data.objects['Rebuilt underside study'];p=sculpt.coordinates(obj)
    faces=[list(f.vertices) for f in obj.data.polygons if np.all(np.abs(p[list(f.vertices),0])<.19)]
    tree=BVHTree.FromPolygons(p.tolist(),faces);sections=[]
    for z in (.98,1.04,1.11,1.18,1.27,1.35,1.40):
        hits={}
        for name,origin,direction in [('front',(0,-1,z),(0,1,0)),('back',(0,1,z),(0,-1,0)),('side',(1,0,z),(-1,0,0))]:
            hit=tree.ray_cast(Vector(origin),Vector(direction))[0]
            hits[name]=list(hit) if hit else None
        sections.append({'z':z,'surfaces':hits})
    folder.mkdir(parents=True);(folder/'sections.json').write_text(json.dumps(sections,indent=2))
    print('TORSO_SECTIONS',json.dumps(sections),flush=True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    for view,pos in [('front',(0,-4,1.19)),('side',(4,0,1.19)),('back',(0,4,1.19))]:
        camera(position=pos,target=(0,0,1.19),scale=.68,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    print('TORSO_AUDIT_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
