"""Read-only lower-limb surface registration on the current saved character."""
import hashlib,json,sys
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
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    obj=bpy.data.objects['Rounded fingertip study'];p=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in obj.data.polygons])
    sections=[]
    # Construction axes explicitly registered; no inferred joint locations.
    for side in (-1,1):
        for label,z,x,y in [('thigh',.76,.092,.012),('lower thigh',.62,.096,0),
                ('knee',.505,.101,-.016),('calf',.37,.104,.018),('shin',.19,.104,.021),('ankle',.13,.103,.018)]:
            origin=Vector((side*x,y,z));hits={}
            for name,d in [('front',(0,-1,0)),('back',(0,1,0)),('outer',(side,0,0)),('inner',(-side,0,0))]:
                direction=Vector(d);hit,normal,_,distance=tree.ray_cast(origin,direction)
                if hit is None or normal.dot(direction)<=0 or not .005<distance<.15:
                    raise ValueError('Invalid interior leg registration: '+label+' '+name)
                hits[name]={'point':list(hit),'distance_mm':distance*1000}
            sections.append({'side':side,'label':label,'axis':list(origin),'surfaces':hits})
    assert tree.ray_cast(Vector((0,-1,.65)),Vector((0,1,0)))[0] is None
    np.testing.assert_array_equal(p,sculpt.coordinates(obj))
    folder.mkdir(parents=True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    for view,pos in [('front',(0,-4,.48)),('oblique',(2.5,-4,.48))]:
        camera(position=pos,target=(0,0,.48),scale=1.10,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report={'blender':bpy.app.version_string,'source_sha256':digest,'source_unchanged':True,
        'lower_thigh_gap_open':True,'sections':sections,
        'limits':'Surface exits from authored construction axes; not bone detection. No model edits.'}
    (folder/'audit.json').write_text(json.dumps(report,indent=2))
    print('LOWER_LIMB_AUDIT_COMPLETE',flush=True)
if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
