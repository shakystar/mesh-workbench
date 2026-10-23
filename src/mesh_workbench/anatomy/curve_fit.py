"""Registered surface-control deformation. Coordinates are authored, not anatomy truth."""
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt, layers


def _kernel(distance):
    r = np.clip(distance, 0, 1)
    return (1-r)**4*(4*r+1)


def apply(source, diagram, name='Curve fitted surface'):
    """Fit named controls with compact RBF; preserve topology, keys and masks.

    All coordinates are world metres. Every source control must be on the mesh.
    A hard region with a smooth interior collar protects unrelated surfaces.
    """
    sculpt.editable(source)
    label = diagram.get('label', 'lower nose curves')
    if not isinstance(label,str) or not 1<=len(label)<=48:
        raise ValueError('Invalid layer label')
    if name in bpy.data.objects:
        raise ValueError('Output already exists')
    radius = sculpt.number(diagram['radius_mm'], 1, 150, 'radius')/1000
    cap = sculpt.number(diagram['max_displacement_mm'], .01, 8, 'cap')/1000
    region = diagram['region']
    lo, hi = np.asarray(region['min'], float), np.asarray(region['max'], float)
    feather = sculpt.number(region['feather_mm'], .1, 30, 'feather')/1000
    if lo.shape != (3,) or hi.shape != (3,) or not np.isfinite([lo, hi]).all() or np.any(hi-lo<=2*feather):
        raise ValueError('Invalid region')
    controls = diagram['controls']
    if not 4 <= len(controls) <= 128 or len({c['name'] for c in controls}) != len(controls):
        raise ValueError('Expected distinct named controls')
    a = np.asarray([c['source'] for c in controls], float)
    b = np.asarray([c['target'] for c in controls], float)
    if a.shape != (len(controls), 3) or b.shape != a.shape or not np.isfinite([a,b]).all():
        raise ValueError('Invalid control coordinates')
    if np.any(a < lo+feather) or np.any(a > hi-feather):
        raise ValueError('Controls must lie inside unfeathered region')
    points = sculpt.coordinates(source)
    tree = BVHTree.FromPolygons(points.tolist(), [list(p.vertices) for p in source.data.polygons])
    if any(tree.find_nearest(Vector(p))[3] > .00005 for p in a):
        raise ValueError('Source control is not registered on surface')
    distances = np.linalg.norm(a[:,None]-a[None,:], axis=2)
    if np.any(distances[np.triu_indices(len(a),1)] < .0001):
        raise ValueError('Overlapping controls')
    matrix = _kernel(distances/radius)
    if diagram.get('surface_interpolation', False):
        # Fit the sampled mesh surface, not only an ideal continuous RBF field.
        # Barycentric interpolation accounts for controls between sparse vertices.
        source.data.calc_loop_triangles()
        triangles = [list(t.vertices) for t in source.data.loop_triangles]
        surface = BVHTree.FromPolygons(points.tolist(),triangles,all_triangles=True)
        rows=[]
        for p in a:
            hit,_,index,_=surface.find_nearest(Vector(p))
            corners=points[triangles[index]]
            uv=np.linalg.lstsq((corners[1:]-corners[0]).T,np.asarray(hit)-corners[0],rcond=None)[0]
            bary=np.array([1-uv.sum(),uv[0],uv[1]])
            taper=np.clip(np.minimum(corners-lo,hi-corners).min(axis=1)/feather,0,1)
            taper=taper*taper*(3-2*taper)
            rows.append((bary*taper) @ _kernel(np.linalg.norm(corners[:,None]-a[None,:],axis=2)/radius))
        matrix=np.asarray(rows)
    if np.linalg.cond(matrix) > 1e7:
        raise ValueError('Ill-conditioned controls')
    coefficients = np.linalg.solve(matrix, b-a)
    weight = np.clip(np.minimum(points-lo,hi-points).min(axis=1)/feather,0,1)
    weight = weight*weight*(3-2*weight)
    delta = np.zeros_like(points)
    selected = np.flatnonzero(weight > 0)
    for block in np.array_split(selected, max(1, len(selected)//2048+1)):
        delta[block] = (_kernel(np.linalg.norm(points[block,None]-a[None,:],axis=2)/radius) @ coefficients)*weight[block,None]
    if not np.isfinite(delta).all() or np.linalg.norm(delta,axis=1).max() > cap:
        raise ValueError('Curve fit exceeds displacement cap')
    # Check actual polygon area vectors. N-gon tessellation contains virtual,
    # nearly collinear triangles whose sign is not a mesh-face orientation.
    source.data.calc_loop_triangles()
    tri = np.asarray([t.vertices[:] for t in source.data.loop_triangles])
    q = points+delta
    def cross(p): return np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
    polygon_ids = np.asarray([t.polygon_index for t in source.data.loop_triangles])
    old = np.zeros((len(source.data.polygons),3)); new = np.zeros_like(old)
    np.add.at(old,polygon_ids,cross(points)); np.add.at(new,polygon_ids,cross(q))
    area = np.linalg.norm(old,axis=1)
    changed = np.zeros(len(old),dtype=bool)
    np.logical_or.at(changed,polygon_ids,np.any(np.linalg.norm(delta[tri],axis=2)>1e-10,axis=1))
    failed = changed & ((np.einsum('ij,ij->i',old,new)<=0) | (np.linalg.norm(new,axis=1)<area*.15))
    if failed.any():
        i = int(np.flatnonzero(failed)[0])
        raise ValueError(f'Curve fit folds or collapses polygon {i}: area={area[i]}, new_area={np.linalg.norm(new[i])}')
    output = source.copy()
    output.data = source.data.copy()
    output.name = name
    bpy.context.collection.objects.link(output)
    mesh = output.data
    try:
        key = layers.begin(output)
        inv = output.matrix_world.inverted()
        for i in selected:
            key.data[int(i)].co = inv @ Vector(q[i])
        layer = layers.finish(output)
        layer.name = 'MW '+label
        report = {'layer':layer.name, 'controls':len(controls),
                  'surface_interpolation':bool(diagram.get('surface_interpolation',False)),
                  'max_displacement_mm':float(np.linalg.norm(delta,axis=1).max()*1000),
                  'protected_vertices':int(np.count_nonzero(weight==0)),
                  'changed_vertices':int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-9)),
                  'minimum_changed_polygon_area_ratio':float((np.linalg.norm(new,axis=1)[changed]/area[changed]).min()),
                  'limits':'Authored registered controls, not an anatomy solver; no global collision guarantee.'}
        records = json.loads(output.get('mw_layers','[]'))
        records.append({'name':layer.name,'topology':sculpt.topology(output),'report':report})
        output['mw_layers'] = json.dumps(records)
        output['mw_source'] = source.name
        return output, report
    except Exception:
        bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users == 0: bpy.data.meshes.remove(mesh)
        raise
