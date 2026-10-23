"""Register explicit external rays as surface-brush-compatible landmarks."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt

def register(body,rows):
    sculpt.editable(body)
    if not rows or len(rows)>128:raise ValueError('One to 128 guide rays required')
    points=sculpt.coordinates(body)
    tree=BVHTree.FromPolygons(points.tolist(),[list(f.vertices) for f in body.data.polygons])
    landmarks={};groups={};provenance={}
    for row in rows:
        name=row['name'];group=row['region']
        if not name or name in landmarks:raise ValueError('Duplicate or empty guide name')
        origin=np.asarray(row['origin'],float);direction=np.asarray(row['direction'],float)
        lo,hi=np.asarray(row['bounds'],float)
        if origin.shape!=(3,) or direction.shape!=(3,) or lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([origin,direction,lo,hi]).all() or np.any(lo>=hi):
            raise ValueError('Invalid guide coordinates')
        norm=np.linalg.norm(direction)
        if norm<1e-8:raise ValueError('Guide direction is zero')
        direction/=norm
        hit,normal,_,distance=tree.ray_cast(Vector(origin),Vector(direction),2)
        if hit is None or normal.dot(Vector(direction))>=-.01:
            raise ValueError('Guide misses an entering visible surface: '+name)
        q=np.asarray(hit)
        if np.any(q<lo) or np.any(q>hi):raise ValueError('Guide hit outside registered bounds: '+name)
        landmarks[name]=q.tolist();groups.setdefault(group,[]).append(name)
        provenance[name]=row['evidence']
    regions={}
    for group,names in groups.items():
        q=np.asarray([landmarks[n] for n in names]);padding=np.array([.012,.015,.012])
        regions[group]={'min':(q.min(axis=0)-padding).tolist(),'max':(q.max(axis=0)+padding).tolist(),'feather':.003}
    return {'units':'m','landmarks':landmarks,'regions':regions,'paths':groups,
        'evidence':provenance,'registration':rows,
        'limits':'Manual skin targets with local protection boxes; names do not prove anatomical landmark accuracy. Re-register after geometry changes.'}
