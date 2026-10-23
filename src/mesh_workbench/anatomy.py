"""Landmark-registered orthographic brushes with explicit regional protection.

Templates are artist-authored coordinates, not population anatomy measurements.
"""
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt, layers


def _point(value):
    p=np.asarray(value,dtype=float)
    if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ required')
    return p


def bind(obj, diagram):
    bpy.context.view_layer.update()
    sculpt.editable(obj)
    if diagram.get('units')!='m':raise ValueError('Diagram units must be metres')
    points={name:_point(p).tolist() for name,p in diagram['landmarks'].items()}
    if not points:raise ValueError('Landmarks required')
    regions={}
    for name,row in diagram['regions'].items():
        lo,hi=_point(row['min']),_point(row['max'])
        if np.any(lo>=hi):raise ValueError('Invalid region bounds')
        feather=sculpt.number(row.get('feather',.005),0,float(np.min(hi-lo)/2),'feather')
        regions[name]={'min':lo.tolist(),'max':hi.tolist(),'feather':feather}
    if not regions:raise ValueError('Regions required')
    record={'units':'m','landmarks':points,'regions':regions,'topology':sculpt.topology(obj),
            'matrix':[list(r) for r in obj.matrix_world]}
    obj['mw_anatomy_diagram']=json.dumps(record)
    return record


def stroke(obj, command):
    bpy.context.view_layer.update()
    sculpt.editable(obj)
    diagram=json.loads(obj.get('mw_anatomy_diagram','{}'))
    if (diagram.get('topology')!=sculpt.topology(obj) or
        diagram.get('matrix')!=[list(r) for r in obj.matrix_world]):
        raise ValueError('Missing or stale diagram binding; register again')
    view=command.get('view','front')
    if view not in ('front','side'):raise ValueError('Expected front or side diagram')
    label=command.get('label','Anatomy brush')
    if not isinstance(label,str) or not 1<=len(label)<=48:raise ValueError('Invalid layer label')
    mode=command.get('mode','smooth')
    if mode not in ('smooth','normal'):raise ValueError('Expected smooth or normal brush')
    region=diagram['regions'][command['region']]
    anchor=_point(diagram['landmarks'][command['anchor']])
    offset=np.asarray(command.get('offset_mm',[0,0]),dtype=float)
    if offset.shape!=(2,) or not np.isfinite(offset).all():raise ValueError('Finite diagram offset required')
    radius=sculpt.number(command['radius_mm'],.1,200,'radius')/1000
    strength=sculpt.number(command.get('strength',.5),0,1,'strength')
    limit=sculpt.number(command.get('max_displacement_mm',3),.01,10,'displacement limit')/1000
    distance=sculpt.number(command.get('distance_mm',1),-10,10,'distance')/1000
    steps=command.get('steps',1)
    if type(steps)!=int or not 1<=steps<=20:raise ValueError('Expected 1..20 brush steps')
    mirror=command.get('symmetry_x',True)
    if type(mirror)!=bool:raise ValueError('symmetry_x must be boolean')
    original=sculpt.coordinates(obj);coords=original.copy()
    lo,hi=np.asarray(region['min']),np.asarray(region['max'])
    allowed=np.all((original>=lo)&(original<=hi),axis=1)
    edge=np.minimum(original-lo,hi-original).min(axis=1)
    mask=allowed.astype(float)
    if region['feather']:mask*=np.clip(edge/region['feather'],0,1)
    mask*=1-sculpt.protection(obj,command.get('protect_mask'))
    tree=BVHTree.FromPolygons(original.tolist(),[list(p.vertices) for p in obj.data.polygons])
    horizontal,depth,sign=(0,1,-1) if view=='front' else (1,0,1)
    origin=anchor.copy();origin[horizontal]+=offset[0]/1000;origin[2]+=offset[1]/1000
    origin[depth]=original[:,depth].min()-1 if sign<0 else original[:,depth].max()+1
    direction=np.zeros(3);direction[depth]=-sign
    hit,normal,face,_=tree.ray_cast(Vector(origin),Vector(direction),float(np.ptp(original[:,depth])+2))
    if hit is None:raise ValueError('Diagram stroke misses surface')
    if np.any(np.asarray(hit)<lo) or np.any(np.asarray(hit)>hi):raise ValueError('Stroke outside selected region')
    centers=[(np.asarray(hit),np.asarray(normal))]
    if mirror and abs(hit.x)>1e-8:
        c=np.asarray(hit).copy();n=np.asarray(normal).copy();c[0]*=-1;n[0]*=-1
        centers.append((c,n))
    neighbors=sculpt.adjacency(obj,original)
    weights=np.zeros(len(coords));normals=np.zeros_like(coords)
    for c,n in centers:
        w=sculpt.neighborhood(original,neighbors,c,radius,'geodesic')*mask
        choose=w>weights;weights[choose]=w[choose];normals[choose]=n
    chosen=np.flatnonzero(weights)
    if not len(chosen):raise ValueError('No unprotected vertices in brush footprint')
    for _ in range(steps):
        delta=np.zeros_like(coords)
        for i in chosen:
            if mode=='smooth' and neighbors[i]:
                shift=coords[[j for j,_ in neighbors[i]]].mean(axis=0)-coords[i]
            elif mode=='normal':shift=normals[i]*distance
            else:continue
            delta[i]=shift*weights[i]*strength
        coords+=delta
        total=coords-original;length=np.linalg.norm(total,axis=1)
        over=length>limit
        coords[over]=original[over]+total[over]*(limit/length[over,None])
    delta=coords-original;changed=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-10)
    if not len(changed):raise ValueError('Stroke produced no deformation')
    key=layers.begin(obj)
    try:
        inv=obj.matrix_world.inverted()
        for i in changed:key.data[int(i)].co=inv@Vector(coords[i])
        layer=layers.finish(obj)
    except Exception:
        if obj.get('mw_pending'):layers.finish(obj,cancel=True)
        raise
    layer.name='MW '+label
    report={'layer':layer.name,'command':command,'hit_world':list(hit),
            'changed_vertices':len(changed),'max_displacement_mm':float(np.linalg.norm(delta,axis=1).max()*1000),
            'protected_max_displacement_mm':float(np.linalg.norm(delta[mask==0],axis=1).max()*1000) if np.any(mask==0) else 0}
    records=json.loads(obj.get('mw_layers','[]'))
    records.append({'name':layer.name,'topology':sculpt.topology(obj),'report':report})
    obj['mw_layers']=json.dumps(records)
    return report
