"""Refine a registered sagittal nose/philtrum/lip/chin profile on a new local mesh.

blender -b --factory-startup -t 2 --python examples/human_lower_face.py -- INPUT.blend OUTPUT_DIR
Input: human_guided_brush.py output; source objects and keys remain preserved.
"""
import json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy,sculpt,geometry,layers
from mesh_workbench.runner import camera


def build(source_path,output):
    output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory')
    spec=json.loads((ROOT/'examples/human-lower-face.json').read_text(encoding='utf-8-sig'))
    rows=np.asarray(spec['profile_z_y_half_width'],dtype=float)
    if rows.ndim!=2 or rows.shape[1]!=3 or not np.isfinite(rows).all() or np.any(np.diff(rows[:,0])<=0) or np.any(rows[:,2]<=0):
        raise ValueError('Ordered finite Z/Y/width profile required')
    cap=sculpt.number(spec['max_displacement_mm'],.1,25,'profile displacement cap')/1000
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects['Anatomy guided cranium'];source_before=sculpt.coordinates(source).copy()
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    region=spec['regions']['lower_face'];lo=np.asarray(region['min']);hi=np.asarray(region['max'])
    selected=geometry.selection(source,'FACE',box=[lo,hi])
    obj=geometry.edit_topology(source,selected,'subdivide','Lower face refinement',cuts=2)
    source.hide_render=True;source.hide_set(True)
    for face in obj.data.polygons:face.use_smooth=True
    original=sculpt.coordinates(obj)
    anatomy.bind(obj,spec)
    def tree(xyz):return BVHTree.FromPolygons(xyz.tolist(),[list(f.vertices) for f in obj.data.polygons])
    def anterior(bvh,z):
        hit=bvh.ray_cast(Vector((0,-.4,float(z))),Vector((0,1,0)),.8)[0]
        if hit is None:raise ValueError('Profile station misses face')
        return hit.y
    bvh=tree(original)
    stations=np.linspace(rows[0,0],rows[-1,0],145)
    old_y=np.array([anterior(bvh,z) for z in stations])
    # Smoothstep joins control points without sharp corners at the lip/chin stations.
    def interpolate(z,column):
        i=np.clip(np.searchsorted(rows[:,0],z)-1,0,len(rows)-2)
        t=np.clip((z-rows[i,0])/(rows[i+1,0]-rows[i,0]),0,1);t=t*t*(3-2*t)
        return rows[i,column]*(1-t)+rows[i+1,column]*t
    inside=np.all((original>=lo)&(original<=hi),axis=1)
    edge=np.minimum(original-lo,hi-original).min(axis=1)
    feather=np.clip(edge/region['feather'],0,1)
    width=interpolate(original[:,2],2)
    lateral=np.maximum(0,1-(original[:,0]/width)**2)**2
    lateral[np.abs(original[:,0])>=width]=0
    shift=(interpolate(original[:,2],1)-np.interp(original[:,2],stations,old_y))*lateral*inside*feather
    if np.max(np.abs(shift))>cap:raise ValueError('Profile exceeds displacement cap')
    key=layers.begin(obj)
    try:
        inv=obj.matrix_world.inverted()
        for i in np.flatnonzero(shift):
            p=original[i].copy();p[1]+=shift[i];key.data[int(i)].co=inv@Vector(p)
        profile_layer=layers.finish(obj);profile_layer.name='Lower face profile'
    except Exception:
        if obj.get('mw_pending'):layers.finish(obj,cancel=True)
        raise
    reports=[anatomy.stroke(obj,command) for command in spec['strokes']]
    after=sculpt.coordinates(obj)
    np.testing.assert_array_equal(original[~inside],after[~inside])
    for r in reports:sculpt.set_layer(obj,r['layer'],0)
    profile_layer.value=0
    np.testing.assert_allclose(sculpt.coordinates(obj),original,atol=1e-8)
    profile_layer.value=1
    for r in reports:sculpt.set_layer(obj,r['layer'],1)
    np.testing.assert_array_equal(sculpt.coordinates(source),source_before)
    info=geometry.inspect(obj)
    if not info['finite'] or info['nonmanifold_edges']:raise ValueError('Invalid refined surface')
    bvh=tree(after)
    samples={name:{'before_y':anterior(tree(original),p[2]),'after_y':anterior(bvh,p[2]),'target_y':p[1]}
             for name,p in spec['landmarks'].items()}
    # Verify intended visual effect: lips gain support, chin projection decreases.
    if not (samples['upper_lip']['after_y']<samples['upper_lip']['before_y']-.004 and
            samples['lower_lip']['after_y']<samples['lower_lip']['before_y']-.004 and
            samples['chin']['after_y']>samples['chin']['before_y']+.001):
        raise ValueError('Lip support / chin setback did not occur')
    output.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'vertices_before':len(source_before),'vertices_after':len(after),
            'protected_vertices':int((~inside).sum()),'protected_exact':True,'source_preserved':True,
            'rollback_verified':True,'nonmanifold_edges':info['nonmanifold_edges'],
            'max_displacement_mm':float(np.linalg.norm(after-original,axis=1).max()*1000),
            'profile_samples':samples,'brushes':reports,'scope':'Large lower-face profile; no nostril cavities or lip microdetail.'}
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'human-lower-face.blend').resolve()))
    for view,pos in [('head-front',(0,-4,1.56)),('head-side',(4,0,1.56))]:
        camera(position=pos,target=(0,0,1.56),scale=.48,size=(800,900))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('LOWER_FACE_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':build(*sys.argv[sys.argv.index('--')+1:])
