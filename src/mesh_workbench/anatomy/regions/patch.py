"""Rebuild a bounded, XY-projectable folded patch as a single-sheet height field."""
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from .. import sculpt


def rebuild(source,bounds,name='Reconstructed surface patch',spacing_mm=1.5):
    """New topology snapshot; boundary/outside coordinates fixed, source untouched.

    Only simple single-loop XY boundaries are supported. No arbitrary remeshing.
    Old topology-bound selections/masks remain on source and are not transferred.
    """
    sculpt.editable(source)
    if name in bpy.data.objects:raise ValueError('Output already exists')
    lo,hi=np.asarray(bounds[0],float),np.asarray(bounds[1],float)
    if lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([lo,hi]).all() or np.any(lo>=hi):
        raise ValueError('Finite ordered patch bounds required')
    spacing=sculpt.number(spacing_mm,.5,4,'patch spacing')/1000
    points=sculpt.coordinates(source);bm=bmesh.new();mesh=None;output=None
    try:
        bm.from_mesh(source.data);bm.verts.ensure_lookup_table()
        for v,p in zip(bm.verts,points):v.co=Vector(p)
        selected={f for f in bm.faces if all(np.all((np.asarray(v.co)>=lo)&(np.asarray(v.co)<=hi)) for v in f.verts)}
        if not selected:raise ValueError('Patch selection is empty')
        boundary=[e for e in bm.edges if sum(f in selected for f in e.link_faces)==1]
        adjacent={}
        for e in boundary:
            a,b=e.verts;adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
        if not adjacent or any(len(v)!=2 for v in adjacent.values()):raise ValueError('Expected closed simple patch boundary')
        loop=[next(iter(adjacent))];previous=None;current=loop[0]
        while True:
            following=next(v for v in adjacent[current] if v!=previous)
            if following==loop[0]:break
            if following in loop:raise ValueError('Patch boundary repeats')
            loop.append(following);previous,current=current,following
        if len(loop)!=len(adjacent):raise ValueError('Patch has multiple boundary loops')
        fixed=np.array([v.co[:] for v in loop]);uv=fixed[:,:2]
        signed=np.sum(uv[:,0]*np.roll(uv[:,1],-1)-uv[:,1]*np.roll(uv[:,0],-1))
        if signed<0:loop.reverse();fixed=fixed[::-1].copy();uv=fixed[:,:2]
        def inside(p):
            x,y=p;count=False
            for a,b in zip(uv,np.roll(uv,-1,axis=0)):
                if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:count=not count
            return count
        grid=[(x,y) for x in np.arange(uv[:,0].min()+spacing,uv[:,0].max(),spacing)
              for y in np.arange(uv[:,1].min()+spacing,uv[:,1].max(),spacing) if inside((x,y))]
        if len(grid)>6000:raise ValueError('Patch exceeds local vertex budget')
        vertices=[Vector(p) for p in [*uv,*grid]]
        verts,edges,faces,orig,_,_=delaunay_2d_cdt(vertices,[],[list(range(len(loop)))],1,1e-9,True)
        mapping={};seen=set()
        for i,ids in enumerate(orig):
            matches=[j for j in ids if j<len(loop)]
            if len(matches)>1:raise ValueError('Boundary vertices merged in projection')
            if matches:mapping[i]=matches[0];seen.add(matches[0])
        if len(seen)!=len(loop):raise ValueError('Projected boundary was not preserved')
        xy=np.asarray(verts);n=len(verts);z=np.zeros(n);pinned=np.zeros(n,dtype=bool)
        for i,j in mapping.items():z[i]=fixed[j,2];pinned[i]=True
        # Positive graph weights give a bounded harmonic fill with a fixed seam.
        src=np.array([i for a,b in edges for i in (a,b)]);dst=np.array([i for a,b in edges for i in (b,a)])
        degree=np.bincount(src,minlength=n)
        if np.any(degree==0):raise ValueError('Disconnected patch vertex')
        z[~pinned]=fixed[:,2].mean()
        for iteration in range(2000):
            average=np.bincount(src,weights=z[dst],minlength=n)/degree
            change=np.max(np.abs(average[~pinned]-z[~pinned]))
            z[~pinned]=average[~pinned]
            if change<1e-8:break
        else:raise ValueError('Patch height solve did not converge')
        boundary_set=set(loop)
        protected={v:tuple(v.co) for v in bm.verts if v in boundary_set or any(f not in selected for f in v.link_faces)}
        count=len(selected);bmesh.ops.delete(bm,geom=list(selected),context='FACES_ONLY')
        for e in list(bm.edges):
            if not e.link_faces:bm.edges.remove(e)
        for v in list(bm.verts):
            if not v.link_edges and v not in boundary_set:bm.verts.remove(v)
        out=[]
        for i,p in enumerate(xy):out.append(loop[mapping[i]] if i in mapping else bm.verts.new((p[0],p[1],z[i])))
        for face in faces:
            if len(face)!=3:raise ValueError('Triangular patch required')
            bm.faces.new([out[i] for i in reversed(face)])
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bad=[e for e in bm.edges if not e.is_manifold or not e.is_contiguous]
        if bad:raise ValueError('Patch seam is not oriented and closed: '+str([(len(e.link_faces),[tuple(v.co) for v in e.verts]) for e in bad[:4]]))
        if any(tuple(v.co)!=p for v,p in protected.items()):raise ValueError('Protected coordinates changed')
        if bm.verts.layers.deform.active:bm.verts.layers.deform.remove(bm.verts.layers.deform.active)
        for elements in (bm.verts,bm.edges,bm.faces):
            for element in elements:element.select_set(False)
        mesh=bpy.data.meshes.new(name);bm.to_mesh(mesh);mesh.update()
        for mat in source.data.materials:mesh.materials.append(mat)
        for polygon in mesh.polygons:polygon.use_smooth=True
        for attr in list(mesh.attributes):
            if attr.name.startswith('mw_'):mesh.attributes.remove(attr)
        output=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(output)
        output['mw_source']=source.name
        output['mw_selection_policy']='Source-only; new topology snapshot has no transferred masks or selections.'
        return output,{'boundary_vertices':len(loop),'protected_vertices':len(protected),
            'removed_faces':count,'new_faces':len(faces),'solve_iterations':iteration+1,
            'boundary_coordinates':fixed.tolist(),'limits':'Single simple XY height-field patch, no arbitrary retopology.'}
    except Exception:
        if output:bpy.data.objects.remove(output,do_unlink=True)
        if mesh and mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
    finally:bm.free()
