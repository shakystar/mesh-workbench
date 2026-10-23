"""Reuse unchanged oral and bilateral calf APIs on the distinct variant."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists());sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy_fit,curve_fit,sculpt
from mesh_workbench.assembly import variant,guides
from mesh_workbench.regions import leg
from mesh_workbench.runner import camera
path,placement_path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh output folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
source=bpy.data.objects['Variant B 0'];before=sculpt.coordinates(source)
eyes=[bpy.data.objects['Variant B '+str(i)] for i in (1,2)];eye_before=[sculpt.coordinates(o) for o in eyes]
profile=json.loads((path.parent/'profile.json').read_text());dz=json.loads(placement_path.read_text())['placement']['translation_m'][2]
def mapped(points):
    p=np.asarray(points,float).copy();p[:,2]+=dz;return variant.transform(p,profile)
tree=BVHTree.FromPolygons(before.tolist(),[list(f.vertices) for f in source.data.polygons])
def project(x,z):
    nominal=mapped([[x,0,z]])[0]
    hit=tree.ray_cast(Vector((nominal[0],-1,nominal[2])),Vector((0,1,0)))[0]
    if hit is None:raise ValueError('Variant oral ray misses')
    return list(hit)
oral={'units':'m','knowledge_id':'oral-neutral-v1','landmarks':{
 'corner_left':project(-.021,1.579),'corner_right':project(.021,1.579),
 'nose_base':project(0,1.603),'chin_fold':project(0,1.562)}}
diagram=anatomy_fit.compile_oral_relief(source,oral,upper_mm=.6,lower_mm=.9)
targets=[]
for side in (-1,1):
    refs=mapped([[side*.102,-.002,.44],[side*.105,.027,.29],[side*.103,.018,.13]])
    xs=sorted((side*.002,side*.20))
    corners=mapped([[x,y,z] for x in xs for y in (-.13,.14) for z in (.135,.438)])
    targets.append({'side':side,'profile':'calf','knee':refs[0].tolist(),'calf':refs[1].tolist(),'ankle':refs[2].tolist(),
        'region':{'min':corners.min(axis=0).tolist(),'max':corners.max(axis=0).tolist(),'feather_mm':4}})
def remove(obj):
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
def apply_reuse():
    face=None
    try:
        face,oral_report=curve_fit.apply(source,diagram,'Variant oral temporary')
        result,calf_diagrams,calf_reports=leg.apply_pair(face,targets,'Variant reused study')
        remove(face);face=None;result['mw_source']=source.name
        return result,[diagram,*calf_diagrams],[oral_report,*calf_reports]
    except Exception:
        if face is not None:remove(face)
        raise
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(oral);bad['landmarks']['corner_left'][1]-=.02
try:anatomy_fit.compile_oral_relief(source,bad)
except ValueError:pass
else:raise AssertionError('Off-surface oral target accepted')
bad=copy.deepcopy(targets[0]);bad['calf']=bad['ankle']
try:leg.compile_controls(source,bad)
except ValueError as exc:assert str(exc)=='Descending finite leg axes required'
else:raise AssertionError('Invalid calf axes accepted')
original=curve_fit.apply;calls=[]
def fail_third(*args,**kwargs):
    calls.append(1)
    if len(calls)==3:raise RuntimeError('Injected final calf failure')
    return original(*args,**kwargs)
with patch.object(curve_fit,'apply',side_effect=fail_third):
    try:apply_reuse()
    except RuntimeError as exc:assert str(exc)=='Injected final calf failure'
    else:raise AssertionError('Failure not exercised')
assert len(calls)==3 and objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,diagrams,reports=apply_reuse();after=sculpt.coordinates(result)
np.testing.assert_array_equal(before,sculpt.coordinates(source));assert sculpt.topology(source)==sculpt.topology(result)
allowed=np.zeros(len(before),bool)
for d in diagrams:allowed|=np.all((before>=d['region']['min'])&(before<=d['region']['max']),axis=1)
np.testing.assert_array_equal(before[~allowed],after[~allowed])
for r in reports:sculpt.set_layer(result,r['layer'],0)
np.testing.assert_array_equal(before,sculpt.coordinates(result))
for r in reports:sculpt.set_layer(result,r['layer'],1)
for obj,p in zip(eyes,eye_before):np.testing.assert_array_equal(p,sculpt.coordinates(obj))
actual=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
residual=max(actual.find_nearest(Vector(c['target']))[3]*1000 for d in diagrams for c in d['controls']);assert residual<.2,residual
old_guides=json.loads((path.parent/'guides.json').read_text());registered=guides.register(result,old_guides['registration'])
source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
folder.mkdir(parents=True);(folder/'registration.json').write_text(json.dumps({'oral':oral,'calves':targets,'diagrams':diagrams},indent=2));(folder/'guides.json').write_text(json.dumps(registered,indent=2))
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'reused.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));bpy.ops.wm.open_mainfile(filepath=str(native))
np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Variant reused study']))
for i,p in enumerate(eye_before,1):np.testing.assert_array_equal(p,sculpt.coordinates(bpy.data.objects['Variant B '+str(i)]))
face_z=mapped([[0,0,1.582]])[0,2];calf_z=mapped([[0,0,.29]])[0,2]
for view,pos,target,scale in [('face',(1,-4,face_z),(0,-.065,face_z),.13),('calf',(0,4,calf_z),(0,0,calf_z),.43)]:
    camera(position=pos,target=target,scale=scale,size=(640,640))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    for label,show_original in [('before',True),('after',False)]:
        bpy.data.objects['Variant B 0'].hide_render=not show_original;bpy.data.objects['Variant reused study'].hide_render=show_original
        scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report={'blender':bpy.app.version_string,'source_unchanged':True,'topology_preserved':True,'protected_vertices':int((~allowed).sum()),
    'new_layers_rollback':True,'eyes_preserved':True,'invalid_oral_and_calf_rejected':True,'final_calf_failure_atomic':True,
    'surface_residual_mm':residual,'controls':sum(len(d['controls']) for d in diagrams),'regions':reports,
    'saved_readback':True,'source_sha256':digest,'guides_re_registered':len(registered['landmarks']),
    'limits':'Same-topology variant with manual registration; oral/calf reuse does not establish every module on arbitrary meshes.'}
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('REUSE_PASS',json.dumps(report),flush=True)
