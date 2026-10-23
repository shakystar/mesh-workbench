"""Explicit front-visible neck path registration with protected facial height."""
import json
from importlib.resources import files
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt


def knowledge():
    return json.loads(files('mesh_workbench').joinpath('knowledge/neck-transition-v1.json').read_text())


def compile_paths(source,registration):
    """Compile source-projected paths only; all dimensions are explicit metres/mm."""
    sculpt.editable(source)
    if registration.get('units')!='m':raise ValueError('Registration units must be metres')
    top=sculpt.number(registration['protect_above_z'],-100,100,'protected height')
    points=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(points.tolist(),[list(p.vertices) for p in source.data.polygons])
    diagram={'units':'m','landmarks':{},'regions':{},'knowledge':knowledge()};commands=[]
    paths=registration['paths']
    if not isinstance(paths,list) or not 1<=len(paths)<=8:raise ValueError('Expected 1..8 neck paths')
    if len({r['name'] for r in paths})!=len(paths):raise ValueError('Distinct path names required')
    for row in paths:
        name=row['name'];p=np.asarray(row['points'],float)
        if p.ndim!=2 or p.shape[1]!=3 or not 2<=len(p)<=48 or not np.isfinite(p).all():
            raise ValueError('Finite registered XYZ path required')
        lo,hi=np.asarray(row['region']['min'],float),np.asarray(row['region']['max'],float)
        if lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([lo,hi]).all() or np.any(lo>=hi) or hi[2]>top:
            raise ValueError('Neck region crosses facial protection or has invalid bounds')
        keys=[]
        for i,point in enumerate(p):
            hit=tree.ray_cast(Vector((point[0],points[:,1].min()-1,point[2])),Vector((0,1,0)))[0]
            if hit is None or np.linalg.norm(np.asarray(hit)-point)>.0001:
                raise ValueError('Neck reference off visible surface')
            if np.any(np.asarray(hit)<lo) or np.any(np.asarray(hit)>hi):raise ValueError('Path leaves region')
            key=name+'_'+str(i);diagram['landmarks'][key]=list(hit);keys.append(key)
        diagram['regions'][name]={**row['region']}
        commands.append({**row['brush'],'label':name,'region':name,'anchors':keys})
    return diagram,commands
