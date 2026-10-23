"""Bounded height-dependent character proportion fields with reversible layers."""
import json
import bpy
import numpy as np
from mathutils import Vector
from .. import sculpt,layers

def transform(points,profile):
    p=np.asarray(points,float);rows=np.asarray(profile['sections'],float)
    height=float(profile['height_scale'])
    if rows.ndim!=2 or rows.shape[1]!=4 or len(rows)<2 or not np.isfinite(rows).all() or not np.all(np.diff(rows[:,0])>0):raise ValueError('Ordered finite variant sections required')
    if not .8<=height<=1.2 or np.any(rows[:,1:3]<.75) or np.any(rows[:,1:3]>1.25) or np.any(np.abs(rows[:,3])>.015):raise ValueError('Variant parameters exceed limits')
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():raise ValueError('Finite XYZ points required')
    z=p[:,2];i=np.clip(np.searchsorted(rows[:,0],z)-1,0,len(rows)-2)
    t=np.clip((z-rows[i,0])/(rows[i+1,0]-rows[i,0]),0,1);t=t*t*(3-2*t)
    values=rows[i,1:]*(1-t[:,None])+rows[i+1,1:]*t[:,None]
    lateral=float(profile.get('lateral_width',1.0))
    if not .75<=lateral<=1.25:raise ValueError('Variant parameters exceed limits')
    # Keep waist/hip width changes from bending hanging arms at the same height.
    blend=np.clip((np.abs(p[:,0])-.18)/.06,0,1);blend=blend*blend*(3-2*blend)
    values[:,0]=values[:,0]*(1-blend)+lateral*blend
    q=p.copy();q[:,0]*=values[:,0];q[:,1]=q[:,1]*values[:,1]+values[:,2];q[:,2]*=height
    return q

def _apply(source,q,name):
    output=source.copy();output.data=source.data.copy();output.name=name;bpy.context.collection.objects.link(output)
    key=layers.begin(output);inv=output.matrix_world.inverted()
    for v,p in zip(key.data,q):v.co=inv@Vector(p)
    layer=layers.finish(output);layer.name='MW proportions'
    records=json.loads(output.get('mw_layers','[]'));records.append({'name':layer.name,'topology':sculpt.topology(output)})
    output['mw_layers']=json.dumps(records);output['mw_source']=source.name
    output.hide_render=False;output.hide_set(False)
    return output,layer.name

def apply(sources,profile,name='Variant B'):
    if not sources or len(set(sources))!=len(sources):raise ValueError('Distinct assembly sources required')
    names=[name+' '+str(i) for i in range(len(sources))]
    if any(n in bpy.data.objects for n in names):raise ValueError('Variant output exists')
    targets=[];ratios=[]
    for obj in sources:
        sculpt.editable(obj);p=sculpt.coordinates(obj);q=transform(p,profile)
        obj.data.calc_loop_triangles();tri=np.asarray([t.vertices[:] for t in obj.data.loop_triangles]);ids=np.asarray([t.polygon_index for t in obj.data.loop_triangles])
        old=np.zeros((len(obj.data.polygons),3));new=np.zeros_like(old)
        for pts,out in [(p,old),(q,new)]:np.add.at(out,ids,np.cross(pts[tri[:,1]]-pts[tri[:,0]],pts[tri[:,2]]-pts[tri[:,0]]))
        a=np.linalg.norm(old,axis=1);b=np.linalg.norm(new,axis=1)
        if np.any(np.einsum('ij,ij->i',old,new)<=0) or np.any(b<a*.3):raise ValueError('Variant folds or collapses polygons')
        targets.append(q);ratios.append(float((b/a).min()))
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try:
        result=[];keys=[]
        for obj,q,n in zip(sources,targets,names):
            out,key=_apply(obj,q,n);result.append(out);keys.append(key)
        return result,{'layers':keys,'minimum_polygon_area_ratios':ratios,'profile':profile,
            'limits':'Authored continuous proportion field; transformed eyes are not rigid spheres, no anatomy or rig guarantee.'}
    except Exception:
        for obj in set(bpy.data.objects)-objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in set(bpy.data.meshes)-meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
