"""Surface-normal diagram strokes and constrained volume-preserving relaxation.

All strokes create reversible layers on one new snapshot. No anatomy inference.
"""
import heapq
import json
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import anatomy, sculpt, layers


def _triangles(obj):
    obj.data.calc_loop_triangles()
    return np.asarray([t.vertices[:] for t in obj.data.loop_triangles],dtype=int)


def _gradient(points,triangles,origin):
    p=points-origin
    a,b,c=(p[triangles[:,i]] for i in range(3))
    gradient=np.zeros_like(points)
    for i,value in enumerate((np.cross(b,c),np.cross(c,a),np.cross(a,b))):
        np.add.at(gradient,triangles[:,i],value/6)
    volume=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    return volume,gradient


def _normals(points,triangles):
    normal=np.zeros_like(points)
    cross=np.cross(points[triangles[:,1]]-points[triangles[:,0]],
                   points[triangles[:,2]]-points[triangles[:,0]])
    for i in range(3):np.add.at(normal,triangles[:,i],cross)
    length=np.linalg.norm(normal,axis=1)
    return normal/np.maximum(length[:,None],1e-20)


def _stroke(obj,source,diagram,command):
    mode=command.get('mode')
    if mode not in ('ridge','crease','relax_volume'):raise ValueError('Unknown surface brush')
    radius=sculpt.number(command.get('radius_mm',4),.2,20,'radius')/1000
    distance=sculpt.number(command.get('distance_mm',.3),0,3,'distance')/1000
    cap=sculpt.number(command.get('max_displacement_mm',1),.01,3,'displacement cap')/1000
    strength=sculpt.number(command.get('strength',.25),.01,.8,'strength')
    iterations=command.get('iterations',3)
    if type(iterations)!=int or not 1<=iterations<=12:raise ValueError('Iterations must be 1..12')
    label=command.get('label',mode)
    if not isinstance(label,str) or not 1<=len(label)<=48:raise ValueError('Invalid layer label')
    anchors=command.get('anchors',[])
    if not 2<=len(anchors)<=64:raise ValueError('At least two path anchors required')
    path=np.asarray([diagram['landmarks'][key] for key in anchors],dtype=float)
    if np.any(np.linalg.norm(np.diff(path,axis=0),axis=1)<1e-7):raise ValueError('Repeated path anchor')
    view=anatomy._point(command.get('view_direction',[0,1,0]))
    if np.linalg.norm(view)<1e-8:raise ValueError('Zero view direction')
    view/=np.linalg.norm(view)
    points=sculpt.coordinates(obj);triangles=_triangles(obj)
    tree=BVHTree.FromPolygons(points.tolist(),[list(p.vertices) for p in obj.data.polygons])
    region=diagram['regions'][command['region']]
    lo,hi=np.asarray(region['min']),np.asarray(region['max'])
    allowed=np.all((points>=lo)&(points<=hi),axis=1)
    mask=allowed.astype(float)*(1-sculpt.protection(source,command.get('protect_mask')))
    if region['feather']:
        mask*=np.clip(np.minimum(points-lo,hi-points).min(axis=1)/region['feather'],0,1)
    # The first visible sheet is a traversal barrier, not just a final mask.
    for i in np.flatnonzero(mask>0):
        hit=tree.ray_cast(Vector(points[i]-view),Vector(view))[0]
        if hit is None or np.linalg.norm(np.asarray(hit)-points[i])>2e-5:mask[i]=0
    graph=[[] for _ in points]
    for e in obj.data.edges:
        a,b=e.vertices
        if mask[a]>0 and mask[b]>0:
            length=float(np.linalg.norm(points[a]-points[b]))
            graph[a].append((b,length));graph[b].append((a,length))
    distances=np.full(len(points),np.inf);queue=[];samples=[]
    for a,b in zip(path[:-1],path[1:]):
        count=max(2,int(np.ceil(np.linalg.norm(b-a)/(radius*.3)))+1)
        for t in np.linspace(0,1,count):
            p=a+(b-a)*t
            hit,_,face,_=tree.ray_cast(Vector(p-view),Vector(view))
            if hit is None or np.linalg.norm(np.asarray(hit)-p)>.003:
                raise ValueError('Path registration exceeds 3 mm surface tolerance')
            hit=np.asarray(hit)
            if np.any(hit<lo) or np.any(hit>hi):raise ValueError('Path leaves region')
            samples.append(hit.tolist())
            seeds=[i for i in obj.data.polygons[face].vertices if mask[i]>0]
            if not seeds:raise ValueError('Path enters protected or hidden surface')
            for i in seeds:
                d=float(np.linalg.norm(points[i]-hit))
                if d<distances[i]:distances[i]=d;heapq.heappush(queue,(d,int(i)))
    while queue:
        d,i=heapq.heappop(queue)
        if d!=distances[i] or d>=radius:continue
        for j,length in graph[i]:
            nd=d+length
            if nd<min(radius,distances[j]):distances[j]=nd;heapq.heappush(queue,(nd,j))
    weight=np.maximum(0,1-(np.minimum(distances,radius)/radius)**2)**2*mask
    editable=weight>1e-12
    if not editable.any():raise ValueError('Brush has no surface footprint')
    result=points.copy();origin=points.mean(axis=0)
    volume_before,_=_gradient(points,triangles,origin)
    if mode=='relax_volume':
        bm=bmesh.new()
        try:
            bm.from_mesh(obj.data)
            if any(not e.is_manifold or not e.is_contiguous for e in bm.edges):
                raise ValueError('Volume relaxation requires an oriented closed mesh')
        finally:bm.free()
        neighbors=[list({j for j,_ in row}) for row in graph]
        for _ in range(iterations):
            delta=np.zeros_like(points)
            for i in np.flatnonzero(editable):
                if neighbors[i]:delta[i]=(result[neighbors[i]].mean(axis=0)-result[i])*weight[i]*strength
            result+=delta
            # Restore the signed enclosed volume, only through editable vertices.
            for _ in range(8):
                value,gradient=_gradient(result,triangles,origin)
                error=value-volume_before
                if abs(error)<1e-14:break
                direction=gradient*weight[:,None]
                denominator=float(np.sum(gradient*direction))
                if denominator<1e-24:raise ValueError('Insufficient editable area for volume correction')
                result-=direction*(error/denominator)
            else:raise ValueError('Volume correction did not converge')
    else:
        sign=1 if mode=='ridge' else -1
        result+=_normals(points,triangles)*(sign*distance*weight[:,None])
    delta=result-points
    maximum=float(np.linalg.norm(delta,axis=1).max())
    if not np.isfinite(result).all() or maximum>cap:raise ValueError('Surface brush exceeds displacement cap')
    np.testing.assert_array_equal(points[~editable],result[~editable])
    # Compare real polygon area vectors, including all changed faces. Virtual
    # tessellation triangles of n-gons are accumulated before checking orientation.
    polygon_ids=np.asarray([t.polygon_index for t in obj.data.loop_triangles])
    def areas(p):
        cross=np.cross(p[triangles[:,1]]-p[triangles[:,0]],p[triangles[:,2]]-p[triangles[:,0]])
        value=np.zeros((len(obj.data.polygons),3));np.add.at(value,polygon_ids,cross)
        return value
    old_area,new_area=areas(points),areas(result)
    changed=np.zeros(len(old_area),dtype=bool)
    np.logical_or.at(changed,polygon_ids,np.any(editable[triangles],axis=1))
    ratios=np.linalg.norm(new_area,axis=1)/np.maximum(np.linalg.norm(old_area,axis=1),1e-30)
    failed=changed & ((np.einsum('ij,ij->i',old_area,new_area)<=0)|(ratios<.15))
    if failed.any():raise ValueError('Surface brush folds or collapses polygon '+str(np.flatnonzero(failed)[0]))
    key=layers.begin(obj)
    try:
        inv=obj.matrix_world.inverted()
        for i in np.flatnonzero(editable):key.data[int(i)].co=inv@Vector(result[i])
        layer=layers.finish(obj)
    except Exception:
        if obj.get('mw_pending'):layers.finish(obj,cancel=True)
        raise
    layer.name='MW '+label
    actual=sculpt.coordinates(obj)
    volume_after,_=_gradient(actual,triangles,origin)
    # Shape-key storage is float32; report its real readback, not just float64 math.
    if mode=='relax_volume' and abs(volume_after-volume_before)>1e-10:
        raise ValueError('Stored layer exceeds 0.1 mm3 volume tolerance')
    report={'layer':layer.name,'mode':mode,'command':command,'projected_path':samples,
            'minimum_changed_polygon_area_ratio':float(ratios[changed].min()),
            'changed_vertices':int(np.count_nonzero(np.linalg.norm(actual-points,axis=1)>1e-9)),
            'max_displacement_mm':maximum*1000,'protected_max_displacement_mm':0,
            'volume_change_mm3':(volume_after-volume_before)*1e9}
    records=json.loads(obj.get('mw_layers','[]'))
    records.append({'name':layer.name,'topology':sculpt.topology(obj),'report':report})
    obj['mw_layers']=json.dumps(records)
    return report


def apply(source,diagram,commands,name='Surface brush result'):
    """Return new object and reports; any failed stroke removes the whole batch."""
    sculpt.editable(source)
    if not isinstance(commands,list) or not 1<=len(commands)<=16:raise ValueError('Expected 1..16 strokes')
    if name in bpy.data.objects:raise ValueError('Output already exists')
    graph=bpy.context.evaluated_depsgraph_get()
    mesh=bpy.data.meshes.new_from_object(source.evaluated_get(graph),depsgraph=graph)
    output=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(output);output.matrix_world=source.matrix_world.copy()
    try:
        registered=anatomy.bind(output,diagram)
        reports=[_stroke(output,source,registered,c) for c in commands]
        output['mw_source']=source.name
        return output,reports
    except Exception:
        bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
