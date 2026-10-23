"""Registered front/back torso control planes, separate from anatomical inference."""
import json
from importlib.resources import files
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt

def knowledge():
    return json.loads(files('mesh_workbench').joinpath('knowledge/torso-surface-v1.json').read_text())

def compile_controls(source,target,relief=1,profile="planes"):
    if profile not in ("planes", "abdomen", "back"):
        raise ValueError("Unknown torso profile")
    sculpt.editable(source)
    half=sculpt.number(target['half_width_m'],.08,.16,'torso half width')
    relief=sculpt.number(relief,.1,1.5,'torso relief')
    refs=np.asarray([target[n] for n in ('sternum','waist','pelvis')],float)
    if refs.shape!=(3,3) or not np.isfinite(refs).all():raise ValueError('Finite torso references required')
    if not refs[0,2]>refs[1,2]>refs[2,2]:raise ValueError('Torso reference heights must descend')
    if np.max(np.abs(refs[:,0]-refs[0,0]))>.001:raise ValueError('Align torso midline references')
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    def project(x,z,view):
        sign=-1 if view=='front' else 1
        hit=tree.ray_cast(Vector((x,sign*(abs(p[:,1]).max()+1),z)),Vector((0,-sign,0)))[0]
        if hit is None:raise ValueError('Torso control misses surface')
        return np.asarray(hit)
    for r in refs:
        if np.linalg.norm(project(r[0],r[2],'front')-r)>.0001:raise ValueError('Torso reference off visible skin')
    controls=[]
    for row in knowledge()[{'planes':'controls','abdomen':'abdominal_controls','back':'posterior_controls'}[profile]]:
        v=row['v'];z=refs[1,2]+v*(refs[0,2]-refs[1,2] if v>=0 else refs[1,2]-refs[2,2])
        a=project(refs[0,0]+row['u']*half,z,row['view']);b=a.copy()
        b[1]+=(1 if row['view']=='back' else -1)*row['depth_mm']*relief/1000
        controls.append({'name':row['name'],'source':a.tolist(),'target':b.tolist()})
    return {'units':'m','label':'torso '+profile,'surface_interpolation':True,
        'radius_mm':half*1000*(.7 if profile=='planes' else .55),'max_displacement_mm':8,
        'region':target['region'],'controls':controls,'registration':target,'knowledge':knowledge()}
