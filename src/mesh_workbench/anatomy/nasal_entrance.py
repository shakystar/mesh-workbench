"""Replace registered blind nasal cutouts with continuous rim/interior patches.

Authored example geometry, not an anatomical airway or cartilage reconstruction.
"""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from . import sculpt


def _replace(bm, reference, spec):
    center=np.asarray(spec['center'],float)
    n=np.asarray(spec['normal'],float); n/=np.linalg.norm(n)
    u=np.asarray(spec['across'],float); u-=n*np.dot(n,u); u/=np.linalg.norm(u)
    v=np.cross(n,u)
    width=sculpt.number(spec['width_mm'],3,12,'width')/2000
    length=sculpt.number(spec['length_mm'],4,16,'length')/2000
    cut=sculpt.number(spec.get('cut_scale',1.65),1.3,2.2,'cut scale')
    depth=sculpt.number(spec.get('depth_mm',5.5),3,9,'depth')/1000
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    selected=[]
    for f in bm.faces:
        # Newly generated faces are never candidates for another patch.
        if any(p.index<0 or p.index>=len(reference) for p in f.verts): continue
        p=np.mean([reference[p.index] for p in f.verts],axis=0)-center
        r=math.hypot(np.dot(p,u)/width,np.dot(p,v)/length)
        if r<cut and -.009<np.dot(p,n)<.006: selected.append(f)
    if not selected: raise ValueError('Registered entrance patch misses mesh')
    face_set=set(selected)
    boundary=[e for e in bm.edges if sum(f in face_set for f in e.link_faces)==1 and len(e.link_faces)==2]
    adjacent={}
    for e in boundary:
        a,b=e.verts; adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    if not adjacent or any(len(row)!=2 for row in adjacent.values()):
        raise ValueError('Entrance boundary must be one simple loop')
    start=next(iter(adjacent)); loop=[start]; prev=None; current=start
    while True:
        nxt=next(p for p in adjacent[current] if p!=prev)
        if nxt==start: break
        if nxt in loop: raise ValueError('Repeated boundary vertex')
        loop.append(nxt);prev,current=current,nxt
    if len(loop)!=len(adjacent): raise ValueError('Multiple entrance boundary loops')
    outer=np.asarray([p.co[:] for p in loop])
    skin_normals=np.asarray([sum((f.normal for f in p.link_faces if f not in face_set),Vector()).normalized() for p in loop])
    original=np.asarray([reference[p.index] for p in loop])
    # Transfer the registration to the deformed source using boundary motion.
    center=center+(outer-original).mean(axis=0)+np.asarray(spec.get('offset_mm',[0,0,0]))/1000
    # Parameterize by perimeter, not polar angle: irregular old triangulation
    # must not produce duplicate inner-ring vertices.
    edges=np.linalg.norm(np.roll(outer,-1,axis=0)-outer,axis=1)
    if edges.min()<1e-8: raise ValueError('Degenerate boundary edge')
    theta0=math.atan2(np.dot(outer[0]-center,v)/length,np.dot(outer[0]-center,u)/width)
    signed=sum(np.dot(np.cross(a-center,b-center),n) for a,b in zip(outer,np.roll(outer,-1,axis=0)))
    direction=1 if signed>0 else -1
    arc=2*math.pi*np.r_[0,np.cumsum(edges[:-1])]/edges.sum()
    polar=np.unwrap(np.arctan2((outer-center)@v/length,(outer-center)@u/width))
    progress=direction*(polar-polar[0])
    if np.all(np.diff(np.r_[progress,2*math.pi])>1e-5):
        theta=theta0+direction*(progress*.85+arc*.15)
    else:
        theta=theta0+direction*arc
    # Carry the surrounding skin's low-frequency height into the lip. A flat
    # ring here would cut a crater into the sloping tip/alar skin.
    design=np.column_stack([np.ones(len(polar)),np.cos(polar),np.sin(polar),np.cos(2*polar),np.sin(2*polar)])
    coefficients=np.linalg.lstsq(design,(outer-center)@n,rcond=None)[0]
    center=center+n*coefficients[0]
    harmonic1=coefficients[1]*np.cos(theta)+coefficients[2]*np.sin(theta)
    harmonic2=coefficients[3]*np.cos(2*theta)+coefficients[4]*np.sin(2*theta)
    # A rounded asymmetric aperture: these dimensions are authored controls.
    radial=(np.cos(theta)[:,None]*u*width*(1+.12*np.sin(theta))[:,None]
            +np.sin(theta)[:,None]*v*length)
    shape=float(spec.get('aperture_scale',.88))
    if not .65<=shape<=1.1: raise ValueError('Invalid aperture scale')
    radial*=shape
    # Shoulder -> rolled lip -> throat -> short blind interior.
    ratio=shape/cut
    aperture=center+radial+n*(.0001+harmonic1[:,None]*ratio+harmonic2[:,None]*ratio**2)
    span=aperture-outer
    tangent=span-skin_normals*np.sum(span*skin_normals,axis=1)[:,None]
    tangent*=np.linalg.norm(span,axis=1)[:,None]/np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-12)
    # Hermite shoulder starts tangent to preserved exterior faces, so the
    # old jagged cut boundary does not become a visible annular seam.
    positions_list=[]
    for t in (.25,.5,.75,1):
        positions_list.append((2*t**3-3*t*t+1)*outer+(t**3-2*t*t+t)*tangent
                              +(-2*t**3+3*t*t)*aperture+(t**3-t*t)*span)
    profiles=[(.96,-.0008),(1.03,-depth*.48),(.75,-depth*.88),(.30,-depth)]
    for scale,axial in profiles:
        ratio=scale*shape/cut
        skin_height=(harmonic1*ratio+harmonic2*ratio**2)*max(0,1+axial/depth)
        positions_list.append(center+radial*scale+n*(axial+skin_height[:,None]))
    bmesh.ops.delete(bm,geom=selected,context='FACES_ONLY')
    previous=loop
    created=[]
    shoulder_vertices=list(loop)
    exterior_neighbors={neighbor for p in loop for edge in p.link_edges for neighbor in edge.verts
                        if neighbor not in loop and any(f not in face_set for f in neighbor.link_faces)}
    for row_index,positions in enumerate(positions_list):
        ring=[bm.verts.new(Vector(p)) for p in positions]
        if row_index<3: shoulder_vertices.extend(ring)
        for i in range(len(loop)):
            created.append(bm.faces.new((previous[i],previous[(i+1)%len(loop)],ring[(i+1)%len(loop)],ring[i])))
        previous=ring
    cap=bm.verts.new(Vector(center-n*(depth+.0003)))
    for i in range(len(loop)):
        created.append(bm.faces.new((previous[i],previous[(i+1)%len(loop)],cap)))
    # Remove only the now-unused old cavity elements.
    for e in list(bm.edges):
        if not e.link_faces: bm.edges.remove(e)
    for p in list(bm.verts):
        if not p.link_edges: bm.verts.remove(p)
    # The source cut boundary follows coarse faces and is not a fair curve.
    # Fair only the shoulder and its immediate exterior collar; keep the
    # aperture and interior rings fixed so the opening is not blurred shut.
    weighted={p:.34 for p in shoulder_vertices}
    weighted.update({p:.14 for p in exterior_neighbors if p.is_valid})
    smoothing_before={p:p.co.copy() for p in weighted}
    for _ in range(6):
        changes={}
        for p,weight in weighted.items():
            neighbors=[e.other_vert(p).co for e in p.link_edges]
            changes[p]=p.co.lerp(sum(neighbors,Vector())/len(neighbors),weight)
        for p,value in changes.items(): p.co=value
    collar_motion=max((p.co-old).length for p,old in smoothing_before.items())*1000
    return {'name':spec['name'],'boundary_vertices':len(loop),'removed_faces':len(selected),
            'new_faces':len(created),'entry_center':center.tolist(),'normal':n.tolist(),
            'aperture_width_mm':2*width*shape*1000,'aperture_length_mm':2*length*shape*1000,
            'interior_depth_mm':depth*1000,'shoulder':'Exterior-tangent Hermite transition',
            'maximum_collar_fairing_mm':collar_motion,
            'minimum_transition_span_mm':float(np.linalg.norm(span,axis=1).min()*1000),
            'boundary':outer.tolist()}


def build(source, patches, name='Nasal entrance study', reference_key='Basis'):
    """Return a new topology snapshot; source keys/selections remain on source."""
    sculpt.editable(source)
    if name in bpy.data.objects: raise ValueError('Output already exists')
    if not 1<=len(patches)<=2: raise ValueError('Expected one or two entrances')
    if not source.data.shape_keys or reference_key not in source.data.shape_keys.key_blocks:
        raise ValueError('Missing registration reference key')
    reference=np.asarray([source.matrix_world @ p.co for p in source.data.shape_keys.key_blocks[reference_key].data])
    points=sculpt.coordinates(source)
    bm=bmesh.new(); mesh=None; output=None
    try:
        bm.from_mesh(source.data)
        bm.verts.ensure_lookup_table()
        for vertex,p in zip(bm.verts,points): vertex.co=Vector(p)
        bm.normal_update()
        reports=[_replace(bm,reference,spec) for spec in patches]
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if any(not e.is_manifold or not e.is_contiguous for e in bm.edges):
            raise ValueError('Entrance replacement is not oriented and closed')
        if any(f.calc_area()<1e-14 for f in bm.faces):
            raise ValueError('Entrance replacement contains degenerate faces')
        if bm.verts.layers.deform.active:
            bm.verts.layers.deform.remove(bm.verts.layers.deform.active)
        for elements in (bm.verts,bm.edges,bm.faces):
            for element in elements: element.select_set(False)
        mesh=bpy.data.meshes.new(name)
        bm.to_mesh(mesh);mesh.update()
        for material in source.data.materials: mesh.materials.append(material)
        for polygon in mesh.polygons: polygon.use_smooth=True
        # Topology-bound attributes cannot silently masquerade as valid output masks.
        for attr in list(mesh.attributes):
            if attr.name.startswith('mw_'): mesh.attributes.remove(attr)
        output=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(output)
        output['mw_source']=source.name;output['mw_topology_snapshot']=True
        output['mw_selection_policy']='Source-only; topology-bound masks and selections are not transferred.'
        return output,{'patches':reports,'nonmanifold_edges':0,
                       'limits':'Authored rolled entrance and short blind interior; no airway or anatomical accuracy claim.'}
    except Exception:
        if output: bpy.data.objects.remove(output,do_unlink=True)
        if mesh and mesh.users==0: bpy.data.meshes.remove(mesh)
        raise
    finally: bm.free()
