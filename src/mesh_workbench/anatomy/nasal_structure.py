"""Authored nasal volumes and real paired cavities on new static snapshots.

Faces -Y, Z up; coordinates in metres. This is procedural geometry, not a
population anatomy model. Source layers, masks and selections stay on source.
"""
import math
import json
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from . import sculpt


def _controls(settings):
    def mm(key,default,lo,hi):
        return sculpt.number(settings.get(key,default),lo,hi,key)/1000
    c={'base_z':sculpt.number(settings.get('base_z',1.603),-.5,3,'base_z'),
       'center_x':sculpt.number(settings.get('center_x',0),-1,1,'center_x'),
       'width':mm('width_mm',34,26,42),
       'projection':mm('tip_projection_mm',32,26,40),
       'alar':mm('alar_size_mm',5.5,4,8),
       'nostril_width':mm('nostril_width_mm',5.5,4,9),
       'nostril_height':mm('nostril_height_mm',9,5,11),
       'depth':mm('cavity_depth_mm',6,6,12)}
    if c['width']*.195-c['nostril_width']/2 < .002:
        raise ValueError('Nostril controls leave insufficient central tissue')
    return c


def _tree(obj):
    points=sculpt.coordinates(obj)
    return BVHTree.FromPolygons(points.tolist(),[list(p.vertices) for p in obj.data.polygons])


def _subtract(head,cutter):
    modifier=head.modifiers.new('Local nostril difference','BOOLEAN')
    modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    mesh=bpy.data.meshes.new_from_object(head.evaluated_get(graph),depsgraph=graph)
    head.modifiers.remove(modifier)
    previous=head.data;head.data=mesh
    if previous.users==0:bpy.data.meshes.remove(previous)


def build(source,settings=None,name='Nasal structure'):
    """Return (final_head, reversible_volume_stage, report), atomically.

    The intermediate stage has Basis and Nasal volumes shape keys. Cavities
    require a separate topology snapshot. Neither source visibility nor source
    selections change. No old topology-bound selections transfer to outputs.
    """
    sculpt.editable(source)
    c=_controls(settings or {})
    if name in bpy.data.objects or name+' volumes' in bpy.data.objects:
        raise ValueError('Output name already exists')
    old_objects=set(bpy.data.objects);old_meshes=set(bpy.data.meshes)
    bm=bmesh.new()
    try:
        x0,z0=c['center_x'],c['base_z']
        tree=_tree(source)
        side_depths=[]
        for sign in (-1,1):
            hit=tree.ray_cast(Vector((x0+sign*(c['width']/2+.007),-10,z0+.015)),Vector((0,1,0)))[0]
            if hit is None:raise ValueError('Nose support misses visible face')
            side_depths.append(hit.y)
        face_y=sum(side_depths)/2
        graph=bpy.context.evaluated_depsgraph_get()
        mesh=bpy.data.meshes.new_from_object(source.evaluated_get(graph),depsgraph=graph)
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm,matrix=source.matrix_world,verts=list(bm.verts))
        faces=[f for f in bm.faces if abs(f.calc_center_median().x-x0)<.027
               and z0-.004<f.calc_center_median().z<z0+.038
               and f.calc_center_median().y<face_y+.01]
        if not faces:raise ValueError('Empty nasal region')
        bmesh.ops.subdivide_edges(bm,edges=list({e for f in faces for e in f.edges}),cuts=1,use_grid_fill=True)
        bm.to_mesh(mesh);mesh.update()
        stage=bpy.data.objects.new(name+' volumes',mesh)
        bpy.context.collection.objects.link(stage)
        stage['mw_source']=source.name;stage['mw_topology_snapshot']=True
        stage.shape_key_add(name='Basis')
        layer=stage.shape_key_add(name='Nasal volumes')
        p=np.array([v.co[:] for v in mesh.vertices],dtype=float)
        x,z=p[:,0]-x0,p[:,2]
        # Compact support excludes the lips, philtrum base and the eye openings.
        radial=np.sqrt((x/.026)**2+((z-(z0+.016))/.023)**2)
        weight=np.clip((1-radial)/.30,0,1)
        weight=weight*weight*(3-2*weight)
        lower=np.clip((z-(z0+.001))/.005,0,1)
        weight*=lower*lower*(3-2*lower)
        weight*=p[:,1]<face_y+.01
        def bell(a,s):return np.exp(-.5*(a/s)**2)
        bridge=.021*bell(x,.0065)*bell(z-(z0+.034),.017)
        tip=(c['projection']-.011)*bell(x,.0085)*bell(z-(z0+.015),np.where(z<z0+.015,.006,.009))
        wings=sum(.0185*bell(x-sign*c['width']*.375,c['alar'])*bell(z-(z0+.007),.005)
                  for sign in (-1,1))
        column=.004*bell(x,.0028)*bell(z-(z0+.004),.004)
        crease=sum(.002*bell(x-sign*(c['width']*.375+c['alar']),.0018)*bell(z-(z0+.008),.006)
                   for sign in (-1,1))
        target_y=face_y-bridge-tip-wings-column+crease
        displacement=(target_y-p[:,1])*weight
        if not np.isfinite(displacement).all() or abs(displacement).max()>.012:
            raise ValueError('Nasal fit exceeds 12 mm movement; register a closer source')
        q=p.copy();q[:,1]+=displacement
        layer.data.foreach_set('co',q.astype(np.float32).ravel());layer.value=1
        stage['mw_layers']=json.dumps([{'name':layer.name,'topology':sculpt.topology(stage),
                                       'report':{'max_displacement':float(abs(displacement).max()),'controls':c}}])
        for polygon in mesh.polygons:polygon.use_smooth=True
        bpy.context.view_layer.update()
        shaped_mesh=bpy.data.meshes.new_from_object(stage.evaluated_get(graph),depsgraph=graph)
        head=bpy.data.objects.new(name,shaped_mesh)
        bpy.context.collection.objects.link(head)
        head['mw_source']=stage.name;head['mw_topology_snapshot']=True
        head['mw_nasal_controls']=json.dumps(settings or {})
        shaped_tree=_tree(head)
        normal=Vector((0,-.30,-.954)).normalized()
        horizontal=Vector((1,0,0));vertical=normal.cross(horizontal).normalized()
        openings=[]
        for sign in (-1,1):
            nominal=Vector((x0+sign*c['width']*.195,-10,z0+.004))
            hit=shaped_tree.ray_cast(nominal,Vector((0,1,0)))[0]
            if hit is None or not z0-.003<hit.z<z0+.014:
                raise ValueError('Nostril projection misses nasal underside')
            center=hit-normal*.001
            angle=math.radians(sign*18)
            across=horizontal*math.cos(angle)+vertical*math.sin(angle)
            along=vertical*math.cos(angle)-horizontal*math.sin(angle)
            cutter_mesh=bpy.data.meshes.new('Temporary nasal cavity')
            cutter_bm=bmesh.new()
            try:
                bmesh.ops.create_uvsphere(cutter_bm,u_segments=64,v_segments=32,radius=1)
                transform=Matrix((across*c['nostril_width']/2,
                                  along*c['nostril_height']/2,normal*c['depth'])).transposed().to_4x4()
                transform.translation=center
                bmesh.ops.transform(cutter_bm,matrix=transform,verts=list(cutter_bm.verts))
                bmesh.ops.recalc_face_normals(cutter_bm,faces=list(cutter_bm.faces))
                cutter_bm.to_mesh(cutter_mesh)
            finally:cutter_bm.free()
            cutter=bpy.data.objects.new('Temporary nasal cutter',cutter_mesh)
            bpy.context.collection.objects.link(cutter)
            _subtract(head,cutter)
            bpy.data.objects.remove(cutter,do_unlink=True)
            bpy.data.meshes.remove(cutter_mesh)
            openings.append({'entry':list(hit),'normal':list(normal)})
        bm.clear();bm.from_mesh(head.data);bm.normal_update()
        edges=[e for e in bm.edges if len(e.link_faces)==2 and e.calc_face_angle()>.45
               and any((e.verts[0].co-Vector(row['entry'])).length<.007 for row in openings)]
        if edges:
            bmesh.ops.bevel(bm,geom=edges,offset=.00035,segments=3,affect='EDGES',clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if any(not e.is_manifold for e in bm.edges):raise ValueError('Nasal result is not manifold')
        bm.to_mesh(head.data);head.data.update()
        for polygon in head.data.polygons:polygon.use_smooth=True
        final_tree=_tree(head)
        for row in openings:
            hit=Vector(row['entry'])
            cavity=final_tree.ray_cast(hit+normal*.02,-normal)[0]
            depth=(hit-cavity).dot(normal) if cavity is not None else -1
            if depth<.003:raise ValueError('Nostril did not create a visible cavity')
            row['measured_depth_mm']=depth*1000
        return head,stage,{'openings':openings,'maximum_volume_displacement_mm':float(abs(displacement).max()*1000),
                           'nonmanifold_edges':0,'beveled_rim_edges':len(edges),
                           'volume_layer':'Nasal volumes','controls':c,
                           'selection_policy':'Source selections remain on source; new topology snapshots.'}
    except Exception:
        for obj in set(bpy.data.objects)-old_objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in set(bpy.data.meshes)-old_meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
    finally:bm.free()
