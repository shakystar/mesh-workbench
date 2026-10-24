"""Explicitly registered lower-nose surface controls; no anatomical inference."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .. import sculpt, curve_fit


def compile_controls(source, registration, *, tip_mm=1.0, ala_mm=.8, columella_mm=.6):
    """Compile three independently weighted paths from external skin rays.

    Each row has name, group, origin, direction and unit displacement vector.
    Region bounds and rays are manually registered in world metres. Values are
    authored surface offsets, not cartilage dimensions or population norms.
    """
    gains = dict(tip=tip_mm, ala=ala_mm, columella=columella_mm)
    for key, value in gains.items():
        gains[key] = sculpt.number(value, -2, 2, key)/1000
    rows = registration['rays']
    if not 4 <= len(rows) <= 128 or len({r['name'] for r in rows}) != len(rows):
        raise ValueError('Distinct nasal rays required')
    if {r['group'] for r in rows} != set(gains):
        raise ValueError('Tip, ala and columella groups required')
    points = sculpt.coordinates(source)
    tree = BVHTree.FromPolygons(points.tolist(), [list(p.vertices) for p in source.data.polygons])
    controls = []
    for row in rows:
        origin, direction, offset = [np.asarray(row[k], float) for k in ('origin','direction','offset')]
        if any(v.shape != (3,) for v in (origin,direction,offset)) or not np.isfinite([origin,direction,offset]).all():
            raise ValueError('Finite nasal vectors required')
        length = np.linalg.norm(direction)
        if length < 1e-9 or np.linalg.norm(offset) > 1.001:
            raise ValueError('Invalid nasal direction or offset')
        hit, normal, _, distance = tree.ray_cast(Vector(origin),Vector(direction/length),2)
        if hit is None or normal.dot(Vector(direction/length)) >= -.01:
            raise ValueError('Nasal ray misses entering skin')
        p = np.asarray(hit)
        controls.append(dict(name=row['name'],source=p.tolist(),target=(p+offset*gains[row['group']]).tolist()))
    return dict(units='m',label='nasal tip ala columella',radius_mm=registration.get('radius_mm',9),
                max_displacement_mm=4,surface_interpolation=True,region=registration['region'],
                controls=controls,groups={g:[r['name'] for r in rows if r['group']==g] for g in gains},
                evidence='https://elementsofmorphology.nih.gov/anatomy-nose.shtml')


def apply(source, registration, name='Nasal connections study', **amounts):
    return curve_fit.apply(source, compile_controls(source,registration,**amounts),name)


def compile_attachment(source, registration, *, fairing=.25, volume_mm=.2):
    """Fair registered lateral rows while keeping the medial nose outside bounds.

    Sample X stations must run from ala toward cheek. Endpoint skin depth is
    retained; interior depth blends toward a smooth endpoint interpolation.
    Volume is an independent shallow outward offset on the alar half.
    """
    blend = sculpt.number(fairing,0,1,'fairing')
    volume = sculpt.number(volume_mm,-1,1,'volume')/1000
    side=registration['side']
    xs=np.asarray(registration['stations'],float)
    zs=np.asarray(registration['heights'],float)
    if side not in (-1,1) or xs.ndim!=1 or not 4<=len(xs)<=10 or not np.isfinite(xs).all() or np.any(np.diff(xs)<=0) or xs[0]<=0:
        raise ValueError('Ordered positive alar stations required')
    if zs.ndim!=1 or not 2<=len(zs)<=10 or not np.isfinite(zs).all() or np.any(np.diff(zs)<=0):
        raise ValueError('Ordered attachment heights required')
    points=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(points.tolist(),[list(p.vertices) for p in source.data.polygons])
    controls=[]
    t=(xs-xs[0])/(xs[-1]-xs[0]);smooth=t*t*(3-2*t)
    for row,z in enumerate(zs):
        hits=[]
        for x in xs:
            hit,normal,_,_=tree.ray_cast(Vector((side*x,-1,z)),Vector((0,1,0)),2)
            if hit is None or normal.y>=-.01:raise ValueError('Attachment ray misses entering skin')
            hits.append(np.asarray(hit))
        hits=np.asarray(hits)
        target_y=hits[0,1]*(1-smooth)+hits[-1,1]*smooth
        for i,p in enumerate(hits):
            q=p.copy();q[1]+=blend*(target_y[i]-p[1])-volume*np.sin(np.pi*t[i])**2*(1-t[i])
            controls.append(dict(name=f'attachment_{side}_{row}_{i}',source=p.tolist(),target=q.tolist()))
    return dict(units='m',label=f'alar cheek {side}',radius_mm=12,max_displacement_mm=3,
                surface_interpolation=True,region=registration['region'],controls=controls)


def apply_attachments(source, registrations, name='Alar cheek study', **amounts):
    if len(registrations)!=2 or {r['side'] for r in registrations}!={-1,1}:
        raise ValueError('Two distinct alar sides required')
    diagrams=[compile_attachment(source,r,**amounts) for r in registrations]
    left,right=[d['region'] for d in diagrams]
    if np.all(np.maximum(left['min'],right['min'])<np.minimum(left['max'],right['max'])):
        raise ValueError('Alar regions overlap')
    created=[];reports=[]
    try:
        for i,diagram in enumerate(diagrams):
            obj,report=curve_fit.apply(created[-1] if created else source,diagram,name if i==1 else name+' temporary')
            created.append(obj);reports.append(report)
        interim=created.pop(0);mesh=interim.data
        import bpy
        bpy.data.objects.remove(interim,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        return created[0],diagrams,reports
    except Exception:
        import bpy
        for obj in reversed(created):
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
