"""Bounded hand replacement with exact retained vertices and explicit seam."""
from collections import Counter,defaultdict
import bpy,bmesh
import numpy as np
from .. import sculpt

def _loop(faces,points):
    counts=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
    edges=[e for e,n in counts.items() if n==1];graph=defaultdict(list)
    for a,b in edges:graph[a].append(b);graph[b].append(a)
    if len(edges)<8 or any(len(v)!=2 for v in graph.values()):raise ValueError('Single simple wrist boundary required')
    start=next(iter(graph));loop=[start];previous=None;current=start
    while True:
        nxt=next(v for v in graph[current] if v!=previous)
        if nxt==start:break
        if nxt in loop:raise ValueError('Boundary repeats')
        loop.append(nxt);previous,current=current,nxt
    if len(loop)!=len(graph):raise ValueError('Multiple boundaries unsupported')
    q=points[loop];area=np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))
    if area<0:loop.reverse()
    q=points[loop];center=q[:,:2].mean(axis=0)
    index=int(np.argmin(np.abs(np.arctan2(q[:,1]-center[1],q[:,0]-center[0]))))
    return loop[index:]+loop[:index]

def replace_hand(source,stock,side,name='Grafted hand body',body_cut=.905,stock_cut=.89):
    sculpt.editable(source);sculpt.editable(stock)
    if side not in (-1,1):raise ValueError('Invalid side')
    if name in bpy.data.objects:raise ValueError('Output exists')
    if not .002<body_cut-stock_cut<.03:raise ValueError('Expected separated wrist cuts')
    p=sculpt.coordinates(source);q=sculpt.coordinates(stock)
    faces=[list(f.vertices) for f in source.data.polygons]
    removed=[f for f in faces if np.all(p[f,0]*side>.24) and np.any(p[f,2]<body_cut)]
    kept=[f for f in faces if not (np.all(p[f,0]*side>.24) and np.any(p[f,2]<body_cut))]
    patch=[list(f.vertices) for f in stock.data.polygons if np.all(q[list(f.vertices),2]<stock_cut)]
    if not removed or not patch:raise ValueError('Empty replacement')
    a=_loop(kept,p);b=_loop(patch,q)
    if np.min(p[a,2])<=np.max(q[b,2]):raise ValueError('Wrist boundaries overlap in height')
    used=sorted({v for f in kept for v in f});usedq=sorted({v for f in patch for v in f})
    remap={v:i for i,v in enumerate(used)};mapq={v:i+len(used) for i,v in enumerate(usedq)}
    verts=np.concatenate((p[used],q[usedq]));outfaces=[[remap[v] for v in f] for f in kept]+[[mapq[v] for v in f] for f in patch]
    a=[remap[v] for v in a];b=[mapq[v] for v in b]
    def steps(loop):
        v=verts[loop];length=np.linalg.norm(np.roll(v,-1,axis=0)-v,axis=1)
        if np.any(length<1e-8):raise ValueError('Collapsed boundary edge')
        return np.r_[0,np.cumsum(length)]/length.sum()
    sa,sb=steps(a),steps(b);i=j=0;seam=[]
    while i<len(a) or j<len(b):
        if j==len(b) or (i<len(a) and sa[i+1]<=sb[j+1]):
            seam.append([a[i%len(a)],b[j%len(b)],a[(i+1)%len(a)]]);i+=1
        else:
            seam.append([a[i%len(a)],b[j%len(b)],b[(j+1)%len(b)]]);j+=1
    for tri in seam:
        v=verts[tri]
        if np.linalg.norm(np.cross(v[1]-v[0],v[2]-v[0]))<1e-12:raise ValueError('Collapsed seam triangle')
    mesh=bpy.data.meshes.new(name);output=None
    try:
        mesh.from_pydata(verts.tolist(),[],outfaces+seam);mesh.update()
        bm=bmesh.new()
        try:
            bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            if any(not e.is_manifold or not e.is_contiguous for e in bm.edges):raise ValueError('Graft is not closed and oriented')
            bm.to_mesh(mesh)
        finally:bm.free()
        output=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(output)
        for material in source.data.materials:mesh.materials.append(material)
        for face in mesh.polygons:face.use_smooth=True
        np.testing.assert_array_equal(sculpt.coordinates(output)[:len(used)],p[used])
        output['mw_source']=source.name;output['mw_graft_stock']=stock.name
        report={'retained_vertices':len(used),'body_boundary_vertices':len(a),'stock_boundary_vertices':len(b),'seam_triangles':len(seam),'closed_oriented':True,'retained_exact':True,'source_topology_unchanged':True,'limits':'New topology snapshot; masks and layers are retained only on original source. No general graft or global intersection guarantee.'}
        return output,report
    except Exception:
        if output:bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
