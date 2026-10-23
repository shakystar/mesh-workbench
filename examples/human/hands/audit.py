"""Read-only wrist/palm inspection before topology work."""
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
    obj=bpy.data.objects['Elbow relief study'];p=sculpt.coordinates(obj)
    faces=[list(f.vertices) for f in obj.data.polygons if np.all(p[list(f.vertices),0]>.24)]
    tree=BVHTree.FromPolygons(p.tolist(),faces);sections=[]
    for z,x in ((.94,.302),(.90,.310),(.875,.316),(.845,.322),(.815,.328),(.785,.333)):
        hits={}
        for name,origin,direction in [('front',(x,-1,z),(0,1,0)),('back',(x,1,z),(0,-1,0)),('outer',(1,.01,z),(-1,0,0)),('inner',(.24,.01,z),(1,0,0))]:
            hit=tree.ray_cast(Vector(origin),Vector(direction))[0]
            hits[name]=list(hit) if hit is not None and not (name=='inner' and hit.x>=x) else None
        sections.append({'z':z,'surfaces':hits})
    folder.mkdir(parents=True);(folder/'sections.json').write_text(json.dumps(sections,indent=2))
    print('TORSO_SECTIONS',json.dumps(sections),flush=True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    for view,pos in [('front',(.32,-4,.85)),('back',(.32,4,.85))]:
        camera(position=pos,target=(.32,0,.85),scale=.24,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    print('TORSO_AUDIT_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
