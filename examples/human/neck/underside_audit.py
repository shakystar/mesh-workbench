"""Read lower-chin cross sections from an explicit local surface, without edits."""
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

def run(source_path,output_path):
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    obj=bpy.data.objects['Neck transition study'];p=sculpt.coordinates(obj)
    faces=[list(f.vertices) for f in obj.data.polygons if np.all((p[list(f.vertices),2]>1.49)&(p[list(f.vertices),2]<1.54))]
    tree=BVHTree.FromPolygons(p.tolist(),faces)
    rows={}
    for x in (0,.01,.02,.03):
        rows[str(x)]=[]
        for y in np.linspace(-.07,-.02,51):
            hit=tree.ray_cast(Vector((x,y,1.48)),Vector((0,0,1)))[0]
            if hit:rows[str(x)].append(list(hit))
    crossings={}
    for y in (-.054,-.053,-.052,-.0518,-.051,-.050):
        cursor=1.48;hits=[]
        for _ in range(12):
            hit,normal,face,_=tree.ray_cast(Vector((0,y,cursor)),Vector((0,0,1)))
            if hit is None or hit.z>1.54:break
            hits.append({'z':hit.z,'normal':list(normal),'local_face':face})
            cursor=hit.z+.0000005
        crossings[str(y)]=hits
    out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True)
    report={'sections':rows,'vertical_crossings':crossings,
            'center_step_mm':abs(rows['0'][17][2]-rows['0'][18][2])*1000}
    out.write_text(json.dumps(report,indent=2))
    print('UNDERSIDE_CROSSINGS',json.dumps(crossings),flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
