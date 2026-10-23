"""Registered spherical-support eyelid fitting; static, reversible and bilateral."""
import json
import math
from importlib.resources import files
import bpy
import numpy as np
from mathutils import Vector
from . import sculpt,layers


def knowledge():
    """Source relationships and explicit modeling limits; no shape-standard claim."""
    return json.loads(files('mesh_workbench').joinpath('knowledge/eyelid-support-v1.json').read_text())


def fit(source,eyes,name='Fitted eyelids'):
    sculpt.editable(source)
    if name in bpy.data.objects: raise ValueError('Output already exists')
    if not 1<=len(eyes)<=2: raise ValueError('Expected one or two registered eyes')
    p=sculpt.coordinates(source); q=p.copy(); touched=np.zeros(len(p),bool); reports=[]
    source.data.calc_loop_triangles()
    source_tri=np.asarray([t.vertices[:] for t in source.data.loop_triangles])
    e1=p[source_tri[:,1]]-p[source_tri[:,0]];e2=p[source_tri[:,2]]-p[source_tri[:,0]]
    longest=np.maximum.reduce([np.sum(e1*e1,axis=1),np.sum(e2*e2,axis=1),np.sum((e1-e2)**2,axis=1)])
    # Pin slivers with altitude below 1% of their longest edge. This limits
    # smoothing support; the polygon rejection threshold below is unchanged.
    thin=np.linalg.norm(np.cross(e1,e2),axis=1)<longest*.01
    collar_guard=np.zeros(len(p),bool);collar_guard[source_tri[thin].ravel()]=True
    neighbors=[[] for _ in p]
    for edge in source.data.edges:
        a,b=edge.vertices;neighbors[a].append(b);neighbors[b].append(a)
    for eye in eyes:
        center=np.asarray(eye['center'],float)
        if center.shape!=(3,) or not np.isfinite(center).all(): raise ValueError('Invalid globe center')
        radius=sculpt.number(eye['radius_mm'],10,20,'radius')/1000
        half=sculpt.number(eye['width_mm'],18,36,'width')/2000
        upper=sculpt.number(eye['upper_mm'],2,10,'source upper')/1000
        lower=sculpt.number(eye['lower_mm'],1,8,'source lower')/1000
        target_u=sculpt.number(eye['target_upper_mm'],2,10,'target upper')/1000
        target_l=sculpt.number(eye['target_lower_mm'],1,8,'target lower')/1000
        gap=sculpt.number(eye.get('clearance_mm',.30),.05,.6,'clearance')/1000
        if max(half,upper,lower,target_u,target_l)+.0005>=radius: raise ValueError('Aperture exceeds spherical support')
        yaw=math.radians(sculpt.number(eye['yaw_degrees'],-40,40,'orbital yaw'))
        tilt=math.radians(sculpt.number(eye.get('tilt_degrees',0),-15,15,'tilt'))
        u=np.array([math.cos(yaw),math.sin(yaw),0.]); up=np.array([0.,0.,1.])
        u,up=u*math.cos(tilt)+up*math.sin(tilt),up*math.cos(tilt)-u*math.sin(tilt)
        n=np.cross(u,up); relative=p-center
        a,b,d=relative@u,relative@up,relative@n
        r=np.sqrt((a/half)**2+(b/np.where(b>=0,upper,lower))**2)
        support=np.sqrt(np.maximum(0,radius**2-a*a-b*b))
        clearance=d-support
        rim=(np.abs(r-1)<.0001)&(np.abs(clearance-.00045)<.00002)
        if rim.sum()<24: raise ValueError('Source lid margin does not match registration')
        w=np.clip((1.8-r)/.8,0,1);w=w*w*(3-2*w)
        spherical=np.clip((radius-np.sqrt(a*a+b*b))/.0005,0,1)
        w*=spherical*spherical*(3-2*spherical)
        w*= (r>.92)&(clearance>-.001)&(clearance<.006)
        new_b=b+(b*np.where(b>=0,target_u/upper,target_l/lower)-b)*w
        new_support=np.sqrt(np.maximum(0,radius**2-a*a-new_b*new_b))
        # Outer and inner return margins approach the support without placing
        # the inner return inside the analytic globe. Interior cavity stays put.
        margin=np.clip((1.15-r)/.15,0,1)
        target_gap=np.where(clearance<0,.00005,gap)
        new_d=d+(new_support-support)*w+(target_gap-clearance)*margin*w
        delta=(new_b-b)[:,None]*up+(new_d-d)[:,None]*n
        # Diffuse displacement, not source geometry. Keep the registered rim
        # and return fixed while tapering the edit through the skin collar.
        collar=(r>1.03)&(w>0)&(d>0)&~collar_guard
        free=np.flatnonzero(collar)
        initial=delta.copy()
        for _ in range(12):
            updates=np.asarray([delta[neighbors[i]].mean(axis=0) for i in free])
            delta[free]=delta[free]*.55+updates*.45
        active=np.linalg.norm(delta,axis=1)>1e-12
        if np.any(active&touched): raise ValueError('Registered eye influence overlaps')
        touched|=active
        q+=delta
        if np.linalg.norm(delta,axis=1).max()>.003: raise ValueError('Lid fit exceeds 3 mm cap')
        reports.append({'rim_indices':np.flatnonzero(rim).tolist(),'center':center.tolist(),
                        'radius_mm':radius*1000,'target_upper_mm':target_u*1000,
                        'target_lower_mm':target_l*1000,'frame_normal':n.tolist(),
                        'model_clearance_mm':gap*1000,'changed_vertices':int(active.sum()),
                        'collar_vertices':len(free),
                        'thin_face_guard_vertices':int(np.count_nonzero(collar_guard&(w>0))),
                        'maximum_collar_delta_adjustment_mm':float(np.linalg.norm(delta-initial,axis=1).max()*1000)})
    source.data.calc_loop_triangles()
    tri=np.asarray([t.vertices[:] for t in source.data.loop_triangles])
    ids=np.asarray([t.polygon_index for t in source.data.loop_triangles])
    def area(points):
        out=np.zeros((len(source.data.polygons),3))
        np.add.at(out,ids,np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]]))
        return out
    old,new=area(p),area(q)
    affected=np.zeros(len(old),bool);np.logical_or.at(affected,ids,np.any(touched[tri],axis=1))
    failed=affected&((np.einsum('ij,ij->i',old,new)<=0)|(np.linalg.norm(new,axis=1)<np.linalg.norm(old,axis=1)*.15))
    if failed.any():
        i=int(np.flatnonzero(failed)[0])
        vertices=list(source.data.polygons[i].vertices)
        raise ValueError(f'Lid fit reverses or collapses polygon {i}; source {p[vertices].tolist()}; old area {np.linalg.norm(old[i])}; guard {collar_guard[vertices].tolist()}; area ratio {np.linalg.norm(new[i])/np.linalg.norm(old[i])}')
    output=source.copy();output.data=source.data.copy();output.name=name
    bpy.context.collection.objects.link(output);mesh=output.data
    try:
        key=layers.begin(output);inv=output.matrix_world.inverted()
        for i in np.flatnonzero(touched): key.data[int(i)].co=inv@Vector(q[i])
        layer=layers.finish(output);layer.name='MW spherical lid fit'
        actual=sculpt.coordinates(output)
        np.testing.assert_array_equal(p[~touched],actual[~touched])
        for row in reports:
            distances=np.linalg.norm(actual[row['rim_indices']]-row['center'],axis=1)-row['radius_mm']/1000
            if distances.min()<0 or distances.max()>.00065: raise ValueError('Stored lid margin leaves supported clearance')
            row['radial_clearance_range_mm']=(distances[[distances.argmin(),distances.argmax()]]*1000).tolist()
            row['rim_points']=actual[row['rim_indices']].tolist()
        report={'layer':layer.name,'knowledge_id':knowledge()['id'],'eyes':reports,'protected_vertices':int((~touched).sum()),
                'max_displacement_mm':float(np.linalg.norm(actual-p,axis=1).max()*1000)}
        records=json.loads(output.get('mw_layers','[]'))
        records.append({'name':layer.name,'topology':sculpt.topology(output),'report':report})
        output['mw_layers']=json.dumps(records);output['mw_source']=source.name
        return output,report
    except Exception:
        bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
