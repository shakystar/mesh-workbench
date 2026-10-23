"""Manual hanging-arm registration and atomic bilateral skin relief."""
import json
from importlib.resources import files
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt,curve_fit

def compile_controls(source,target):
    sculpt.editable(source)
    profile=target.get('profile','arm')
    if profile not in ('arm','elbow'):raise ValueError('Unknown arm profile')
    side=target['side']
    if side not in (-1,1):raise ValueError('Side must be -1 or 1')
    refs=np.asarray([target[n] for n in ('proximal','elbow','wrist')],float)
    if refs.shape!=(3,3) or not np.isfinite(refs).all() or not refs[0,2]>refs[1,2]>refs[2,2]:
        raise ValueError('Descending finite arm axes required')
    if np.any(refs[:,0]*side<=0):raise ValueError('Arm axes cross body midline')
    k=json.loads(files('mesh_workbench').joinpath('knowledge/arm-surface-v1.json').read_text())
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[]
    directions=((0,-1,0),(0,1,0),(side,0,0))
    if profile=='elbow':directions+=((-side,0,0),)
    for i,row in enumerate(k['stations' if profile=='arm' else 'elbow_stations']):
        a,b=refs[:2] if row['segment']=='upper' else refs[1:]
        center=a*(1-row['t'])+b*row['t']
        for j,direction in enumerate(directions):
            direction=Vector(direction);hit,normal,_,distance=tree.ray_cast(Vector(center),direction)
            if hit is None or normal.dot(direction)<=0 or not .008<distance<.09:
                raise ValueError('Arm axis must be inside the registered limb')
            q=np.asarray(hit);end=q+np.asarray(direction)*row['depths_mm'][j]/1000
            controls.append({'name':f'arm_{side}_{i}_{j}','source':q.tolist(),'target':end.tolist()})
    return {'units':'m','label':profile+' '+str(side),'surface_interpolation':True,'radius_mm':48 if profile=='arm' else 26,
        'max_displacement_mm':5,'region':target['region'],'controls':controls,'registration':target,'knowledge':k}

def apply_pair(source,targets,name='Arm relief study'):
    if len(targets)!=2 or {t['side'] for t in targets}!={-1,1}:raise ValueError('Two opposing arms required')
    if name in bpy.data.objects:raise ValueError('Output exists')
    diagrams=[compile_controls(source,t) for t in targets]
    a,b=[d['region'] for d in diagrams]
    if np.all(np.maximum(a['min'],b['min'])<np.minimum(a['max'],b['max'])):raise ValueError('Arm regions overlap')
    created=[];reports=[];current=source
    def remove(obj):
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    try:
        for i,diagram in enumerate(diagrams):
            current,report=curve_fit.apply(current,diagram,name if i==1 else name+' temporary')
            created.append(current);reports.append(report)
        remove(created[0]);created.pop(0)
        current['mw_source']=source.name
        return current,diagrams,reports
    except Exception:
        for obj in reversed(created):remove(obj)
        raise
