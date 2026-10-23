"""Manual standing-leg registration and atomic bilateral skin relief."""
import json
from importlib.resources import files
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt,curve_fit

def compile_controls(source,target):
    sculpt.editable(source)
    profile=target.get('profile','leg')
    if profile=='knee_transition':return compile_knee_transition(source,target)
    if profile not in ('leg','calf'):raise ValueError('Unknown leg profile')
    side=target['side']
    if side not in (-1,1):raise ValueError('Side must be -1 or 1')
    keys=('knee','calf','ankle') if profile=='calf' else ('proximal','knee','shin')
    refs=np.asarray([target[n] for n in keys],float)
    if refs.shape!=(3,3) or not np.isfinite(refs).all() or not refs[0,2]>refs[1,2]>refs[2,2]:
        raise ValueError('Descending finite leg axes required')
    if np.any(refs[:,0]*side<=0):raise ValueError('Leg axes cross body midline')
    k=json.loads(files('mesh_workbench').joinpath('knowledge/body/leg-surface-v1.json').read_text())
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[]
    directions=tuple((side*np.sin(angle),-np.cos(angle),0) for angle in np.arange(8)*np.pi/4)
    for i,row in enumerate(k['calf_stations'] if profile=='calf' else k['stations']):
        a,b=refs[:2] if row['segment']=='upper' else refs[1:]
        center=a*(1-row['t'])+b*row['t']
        for j,direction in enumerate(directions):
            direction=Vector(direction);hit,normal,_,distance=tree.ray_cast(Vector(center),direction)
            if hit is None or normal.dot(direction)<=0 or not .008<distance<.13:
                raise ValueError('Leg axis must be inside the registered limb')
            q=np.asarray(hit);end=q+np.asarray(direction)*row['depths_mm'][j]/1000
            controls.append({'name':f'leg_{side}_{i}_{j}','source':q.tolist(),'target':end.tolist()})
    return {'units':'m','label':profile+' '+str(side),'surface_interpolation':True,'radius_mm':75 if profile=='calf' else 45,
        'max_displacement_mm':5,'region':target['region'],'controls':controls,'registration':target,'knowledge':k}

def apply_pair(source,targets,name='Leg relief study'):
    if len(targets)!=2 or {t['side'] for t in targets}!={-1,1}:raise ValueError('Two opposing legs required')
    if name in bpy.data.objects:raise ValueError('Output exists')
    diagrams=[compile_controls(source,t) for t in targets]
    a,b=[d['region'] for d in diagrams]
    if np.all(np.maximum(a['min'],b['min'])<np.minimum(a['max'],b['max'])):raise ValueError('Leg regions overlap')
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


def compile_knee_transition(source,target):
    """Fit longitudinal anterior skin sections with fixed sample endpoints."""
    sculpt.editable(source)
    side=target['side']
    if side not in (-1,1):raise ValueError('Side must be -1 or 1')
    refs=np.asarray([target[n] for n in ('proximal','knee','shin')],float)
    if refs.shape!=(3,3) or not np.isfinite(refs).all() or not refs[0,2]>refs[1,2]>refs[2,2]:
        raise ValueError('Descending finite leg axes required')
    if np.any(refs[:,0]*side<=0):raise ValueError('Leg axes cross body midline')
    center=refs[1];p=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[];sections=[];t=np.linspace(0,1,9)
    basis=np.column_stack((t*(1-t),t*t*(1-t)))
    for j,u in enumerate((-.025,-.0125,0,.0125,.025)):
        points=[]
        for z in np.linspace(center[2]-.05,center[2]+.06,9):
            hit,normal,_,distance=tree.ray_cast(Vector((center[0]+side*u,center[1],z)),Vector((0,-1,0)))
            if hit is None or normal.y>=0 or not .008<distance<.10:
                raise ValueError('Knee section must exit anterior skin from inside')
            points.append(np.asarray(hit))
        a=np.asarray(points);chord=a[0,1]*(1-t)+a[-1,1]*t
        fitted=chord+basis@np.linalg.lstsq(basis,a[:,1]-chord,rcond=None)[0]
        y=a[:,1]+.65*(fitted-a[:,1])
        if np.max(np.abs(y-a[:,1]))>.004:raise ValueError('Knee transition exceeds 4 mm local limit')
        for i,point in enumerate(a):
            end=point.copy();end[1]=y[i]
            controls.append({'name':f'knee_section_{side}_{j}_{i}','source':point.tolist(),'target':end.tolist()})
        sections.append({'source':a.tolist(),'target_y':y.tolist()})
    return {'units':'m','label':'knee transition '+str(side),'surface_interpolation':True,
        'radius_mm':22,'max_displacement_mm':5,'region':target['region'],'controls':controls,
        'registration':target,'sections':sections,
        'limits':'Endpoint-preserving skin continuity fit; not a reconstructed patella or inferred bone outline.'}
