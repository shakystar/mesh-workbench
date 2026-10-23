"""Source-preserving placement of an explicit character mesh assembly."""
import bpy
import numpy as np
from mathutils import Vector
from .. import sculpt

def _duplicate(source,collection,name,delta):
    obj=source.copy();obj.data=source.data.copy();obj.name=name
    collection.objects.link(obj)
    obj.matrix_world.translation+=Vector(delta)
    obj.hide_render=False;obj.hide_set(False)
    return obj

def ground(body,attachments=(),floor_z=0,name='Grounded character'):
    floor_z=sculpt.number(floor_z,-100,100,'floor height')
    sources=[body,*attachments]
    if len(set(sources))!=len(sources):raise ValueError('Duplicate assembly member')
    if name in bpy.data.collections:raise ValueError('Output collection exists')
    for obj in sources:
        sculpt.editable(obj)
        if obj.parent is not None:raise ValueError('Unparented mesh assembly required')
    points=sculpt.coordinates(body);shift=floor_z-float(points[:,2].min())
    if abs(shift)>.05:raise ValueError('Grounding exceeds 50 mm placement limit')
    delta=np.array([0.,0.,shift])
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
    try:
        result=[_duplicate(obj,collection,name+(' body' if i==0 else ' attachment '+str(i)),delta) for i,obj in enumerate(sources)]
        for old,new in zip(sources,result):
            np.testing.assert_allclose(sculpt.coordinates(new),sculpt.coordinates(old)+delta,atol=2e-7,rtol=0)
            if sculpt.topology(old)!=sculpt.topology(new):raise ValueError('Assembly topology changed')
            new['mw_source']=old.name
        return result,{'translation_m':delta.tolist(),'members':[o.name for o in result],
            'sources':[o.name for o in sources],'floor_z':floor_z,
            'limits':'Rigid translation of explicit unparented meshes; no deformation, pose solve or rig validation.'}
    except Exception:
        for obj in set(bpy.data.objects)-objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in set(bpy.data.meshes)-meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        raise
