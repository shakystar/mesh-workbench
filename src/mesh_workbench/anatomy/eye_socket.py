"""Static eye openings and fitted lids on a NEW mesh; sources stay untouched.

Authored modeling controls, not population anatomy or an eyelid rig. Faces must
face -Y, Z up. Topology-bound selections/layers remain on the source only.
"""
import math
import json
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt


def _settings(row):
    c = row.get('center_xz', [])
    if len(c) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in c):
        raise ValueError('Finite center_xz required')
    width = sculpt.number(row.get('width_mm', 28), 18, 36, 'eye width') / 1000
    upper = sculpt.number(row.get('upper_mm', 6), 2, 10, 'upper opening') / 1000
    lower = sculpt.number(row.get('lower_mm', 4), 1, 8, 'lower opening') / 1000
    radius = sculpt.number(row.get('radius_mm', 15), 10, 20, 'globe radius') / 1000
    tilt = math.radians(sculpt.number(row.get('tilt_degrees', 0), -15, 15, 'tilt'))
    yaw = math.radians(sculpt.number(row.get('yaw_degrees', 25), -40, 40, 'yaw'))
    if radius <= max(width / 2, upper, lower) + .0005:
        raise ValueError('Globe must contain the opening plus lid clearance')
    return dict(x=c[0], z=c[1], half=width/2, upper=upper, lower=lower,
                radius=radius, tilt=tilt, yaw=yaw)


def _loop(faces):
    chosen = set(faces)
    edges = {e for f in faces for e in f.edges if sum(g in chosen for g in e.link_faces) == 1}
    if not edges:
        raise ValueError('Empty eye patch')
    neighbors = {}
    for e in edges:
        a, b = e.verts
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    if any(len(v) != 2 for v in neighbors.values()):
        raise ValueError('Eye patch must have one simple boundary')
    start = min(neighbors, key=lambda v: (v.co.z, v.co.x))
    chain = [start]
    previous, current = None, start
    while True:
        nxt = next(v for v in neighbors[current] if v != previous)
        if nxt == start:
            break
        if nxt in chain:
            raise ValueError('Eye patch boundary loops back')
        chain.append(nxt)
        previous, current = current, nxt
    if len(chain) != len(neighbors):
        raise ValueError('Eye patch contains multiple boundaries')
    return chain


def build(source, settings, name='Open-eye head'):
    """Return (new_head, eyeballs, report). Roll back all new data on failure.

    Settings are a list of center_xz, width_mm, upper_mm, lower_mm, radius_mm,
    tilt_degrees and yaw_degrees dictionaries. No source visibility is changed.
    """
    sculpt.editable(source)
    if not settings:
        raise ValueError('At least one eye required')
    configs = [_settings(row) for row in settings]
    for i, c in enumerate(configs):
        for d in configs[:i]:
            if math.hypot(c['x']-d['x'], c['z']-d['z']) < max(c['half']+.008,.020)+max(d['half']+.008,.020):
                raise ValueError('Eye patches overlap')
    original = sculpt.coordinates(source)
    tree = BVHTree.FromPolygons(original.tolist(), [list(p.vertices) for p in source.data.polygons])
    bm = bmesh.new()
    new_objects, new_meshes = [], []
    try:
        # Evaluate existing reversible layers into a separate topology snapshot.
        graph = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(source.evaluated_get(graph), depsgraph=graph)
        new_meshes.append(mesh)
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm, matrix=source.matrix_world, verts=list(bm.verts))
        reports = []
        for c in configs:
            x, z, half, radius = c['x'], c['z'], c['half'], c['radius']
            hit = tree.ray_cast(Vector((x, -10, z)), Vector((0, 1, 0)))[0]
            if hit is None:
                raise ValueError('Eye center misses front surface')
            yaw, tilt = c['yaw'], c['tilt']
            u = Vector((math.cos(yaw), math.sin(yaw), 0))
            up = Vector((0, 0, 1))
            u, up = u*math.cos(tilt)+up*math.sin(tilt), up*math.cos(tilt)-u*math.sin(tilt)
            normal = u.cross(up).normalized()
            center = hit - normal*(radius-.004)
            # Cut only the visible anterior sheet. Keep the posterior head intact.
            faces = []
            for f in bm.faces:
                p = f.calc_center_median()
                dx, dz = p.x-x, p.z-z
                a = dx*math.cos(tilt)+dz*math.sin(tilt)
                b = -dx*math.sin(tilt)+dz*math.cos(tilt)
                if (a/(half+.008))**2+(b/(.020 if b>=0 else .016))**2 < 1 and abs(p.y-hit.y) < .025:
                    visible = tree.ray_cast(Vector((p.x, -10, p.z)), Vector((0, 1, 0)))[0]
                    if visible is not None and abs(p.y-visible.y) < .002:
                        faces.append(f)
            chain = _loop(faces)
            boundary = [v.co.copy() for v in chain]
            # Include a narrow band of adjacent source vertices so the old/new
            # junction can share a tangent instead of forming a radial crease.
            seam=set(chain)
            for _ in range(2):
                seam.update(e.other_vert(v) for v in list(seam) for e in v.link_edges)
            seam={v for v in seam if abs(v.co.x-x)<half+.009
                  and z-.017<v.co.z<z+.021 and abs(v.co.y-hit.y)<.025}
            # Fit only the unedited boundary; do not copy old relief ridges into
            # the new lid transition. Residuals fade rapidly away from the seam.
            def basis(p):
                a,b=(p.x-x)/.02,(p.z-z)/.014
                # A quadratic fitted to an elliptical boundary is nearly rank
                # deficient and can bulge inside it. A plane remains bounded.
                return [1,a,b]
            coefficients=np.linalg.lstsq(np.asarray([basis(p) for p in boundary]),
                                        np.asarray([p.y for p in boundary]),rcond=None)[0]
            def skin_depth(p):return float(np.dot(basis(p),coefficients))
            # Arc-length parameter preserves boundary ordering even on a grid.
            lengths = [(boundary[(i+1)%len(chain)]-p).length for i,p in enumerate(boundary)]
            perimeter = sum(lengths)
            start_angle = math.atan2((boundary[0].z-z)/.016, (boundary[0].x-x)/(half+.008))
            signed = sum(p.x*boundary[(i+1)%len(chain)].z-boundary[(i+1)%len(chain)].x*p.z for i,p in enumerate(boundary))
            direction = 1 if signed > 0 else -1
            angles, distance = [], 0
            for length in lengths:
                angles.append(start_angle+direction*2*math.pi*distance/perimeter)
                distance += length
            bmesh.ops.delete(bm, geom=faces, context='FACES_ONLY')
            for e in list(bm.edges):
                if not e.link_faces:
                    bm.edges.remove(e)
            for v in list(bm.verts):
                if not v.link_edges and v not in chain:
                    bm.verts.remove(v)
            seam={v for v in seam if v.is_valid}
            inner = []
            for a in angles:
                du = half*math.cos(a)
                dv = (c['upper'] if math.sin(a)>=0 else c['lower'])*math.sin(a)
                depth = math.sqrt(radius*radius-du*du-dv*dv)
                inner.append(center+u*du+up*dv+normal*(depth+.00045))
            previous = chain
            for step in range(1, 13):
                t = step/12
                ring = []
                for p, q, a in zip(boundary, inner, angles):
                    point = p.lerp(q, t)
                    blend = t*t*(3-2*t)
                    point.y = skin_depth(point)*(1-blend)+q.y*blend+(p.y-skin_depth(p))*(1-t)**4
                    # Subtle upper-lid fold, tapered at corners and both boundaries.
                    fold = .0007*math.exp(-((t-.56)/.12)**2)*max(0,math.sin(a))
                    point -= normal*fold
                    ring.append(bm.verts.new(point))
                for j in range(len(chain)):
                    k=(j+1)%len(chain)
                    bm.faces.new((previous[j], previous[k], ring[k], ring[j]))
                if step<=9:seam.update(ring)
                previous = ring
            # Inner return creates actual lid thickness and a closed socket cavity.
            for depth in (.0009, radius*1.8):
                ring = [bm.verts.new(p-normal*depth) for p in inner]
                for j in range(len(chain)):
                    k=(j+1)%len(chain)
                    bm.faces.new((previous[j],previous[k],ring[k],ring[j]))
                previous=ring
            bm.faces.new(tuple(reversed(previous)))
            initial={v:v.co.copy() for v in seam}
            for _ in range(20):
                updates={v:v.co.lerp(sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges),.35)
                         for v in seam}
                for v,p in updates.items():
                    delta=p-initial[v]
                    if delta.length>.002:delta=delta.normalized()*.002
                    v.co=initial[v]+delta
            reports.append({'removed_faces':len(faces),'rim_vertices':len(chain),
                            'center':list(center),'radius':radius,'settings':c,
                            'seam_smoothing_cap_mm':2})
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if any(not e.is_manifold for e in bm.edges):
            raise ValueError('Output head is not manifold')
        bm.to_mesh(mesh)
        mesh.update()
        head=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(head)
        new_objects.append(head)
        head['mw_source']=source.name
        head['mw_topology_snapshot']=True
        head['mw_eye_settings']=json.dumps(settings)
        for p in mesh.polygons:p.use_smooth=True
        balls=[]
        for index,report in enumerate(reports):
            ballmesh=bpy.data.meshes.new(name+' globe mesh')
            new_meshes.append(ballmesh)
            sphere=bmesh.new()
            try:
                bmesh.ops.create_uvsphere(sphere,u_segments=64,v_segments=32,radius=report['radius'])
                sphere.to_mesh(ballmesh)
            finally:sphere.free()
            ball=bpy.data.objects.new(name+f' globe {index+1}',ballmesh)
            bpy.context.collection.objects.link(ball)
            new_objects.append(ball);balls.append(ball)
            ball.location=report['center']
            ball.rotation_euler.z=report['settings']['yaw']
            for p in ballmesh.polygons:p.use_smooth=True
        return head,balls,{'eyes':reports,'source_preserved':True,'nonmanifold_edges':0,
                           'selection_policy':'New topology; source selections and layers stay on source.'}
    except Exception:
        for obj in new_objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in new_meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
    finally:bm.free()
