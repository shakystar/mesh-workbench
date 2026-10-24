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
