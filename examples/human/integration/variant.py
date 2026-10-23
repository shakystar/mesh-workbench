"""Generate a distinct body/face assembly and re-register existing guide rays."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import bpy,numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists());sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt
from mesh_workbench.assembly import variant,guides
from mesh_workbench.runner import camera
path,guide_path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
sources=[bpy.data.objects['Grounded character body']]+[bpy.data.objects['Grounded character attachment '+str(i)] for i in (1,2)]
source_names=[o.name for o in sources]
before=[sculpt.coordinates(o) for o in sources]
profile={'height_scale':1.04,'lateral_width':1.08,'sections':[[0,1,1,0],[.2,1,1,0],[.45,1.02,1,0],[.8,1.08,1.04,0],[.95,1.10,1.06,0],[1.1,.94,1,0],[1.35,1.12,1.10,0],[1.48,1,1,0],[1.55,1.08,1.06,-.004],[1.64,.90,.95,0],[1.76,.94,.95,0]]}
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(profile);bad['sections'][1][1]=0
try:variant.apply(sources,bad)
except ValueError as exc:assert str(exc)=='Variant parameters exceed limits'
else:raise AssertionError('Invalid scale accepted')
original=variant._apply;calls=[]
def fail_second(*args,**kwargs):
 calls.append(1)
 if len(calls)==2:raise RuntimeError('Injected eye failure')
 return original(*args,**kwargs)
with patch.object(variant,'_apply',side_effect=fail_second):
 try:variant.apply(sources,profile)
 except RuntimeError as exc:assert str(exc)=='Injected eye failure'
 else:raise AssertionError('Failure not exercised')
assert len(calls)==2 and objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,report=variant.apply(sources,profile)
for old,new,p,key in zip(sources,result,before,report['layers']):
 np.testing.assert_array_equal(p,sculpt.coordinates(old));assert sculpt.topology(old)==sculpt.topology(new)
 np.testing.assert_allclose(sculpt.coordinates(new),variant.transform(p,profile),atol=2e-7,rtol=0)
 sculpt.set_layer(new,key,0);np.testing.assert_allclose(p,sculpt.coordinates(new),atol=2e-7,rtol=0);sculpt.set_layer(new,key,1)
rows=json.loads(guide_path.read_text())['registration']
for row in rows:
 a=np.asarray(row['origin']);direction=np.asarray(row['direction'])
 row['origin']=variant.transform([a],profile)[0].tolist()
 v=variant.transform([a+direction*.01],profile)[0]-np.asarray(row['origin']);row['direction']=(v/np.linalg.norm(v)).tolist()
 lo,hi=np.asarray(row['bounds']);corners=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]);q=variant.transform(corners,profile)
 row['bounds']=[q.min(axis=0).tolist(),q.max(axis=0).tolist()]
diagram=guides.register(result[0],rows)
folder.mkdir(parents=True);(folder/'guides.json').write_text(json.dumps(diagram,indent=2));(folder/'profile.json').write_text(json.dumps(profile,indent=2))
for obj in sources:obj.hide_render=True;obj.hide_set(True)
after=[sculpt.coordinates(o) for o in result]
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'variant.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));bpy.ops.wm.open_mainfile(filepath=str(native))
for i,p in enumerate(after):np.testing.assert_array_equal(p,sculpt.coordinates(bpy.data.objects['Variant B '+str(i)]))
for view,pos,target,scale in [('body',(0,-4,.91),(0,0,.91),1.42),('face',(1,-4,1.66),(0,0,1.66),.38)]:
 camera(position=pos,target=target,scale=scale,size=(640,960) if view=='body' else (640,640))
 scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
 for label,show_original in [('before',True),('after',False)]:
  for source_name in source_names:bpy.data.objects[source_name].hide_render=not show_original
  for i in range(3):bpy.data.objects['Variant B '+str(i)].hide_render=show_original
  scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report.update(blender=bpy.app.version_string,source_unchanged=True,rollback=True,invalid_scale_rejected=True,late_failure_atomic=True,saved_readback=True,re_registered_guides=len(rows),source_sha256=digest,height_before_m=float(np.ptp(before[0][:,2])),height_after_m=float(np.ptp(after[0][:,2])))
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('VARIANT_PASS',json.dumps(report),flush=True)
