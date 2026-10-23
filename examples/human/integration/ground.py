"""Place the complete current body and both eyes on the studio floor."""
import hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import assembly,sculpt
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh output folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
body=bpy.data.objects['Forefoots grafted study']
eyes=[bpy.data.objects['Open-eye head globe '+str(i)+' forward gaze'] for i in (1,2)]
sources=[body,*eyes];before=[sculpt.coordinates(o) for o in sources]
floor=bpy.data.objects['Studio floor'];fp=sculpt.coordinates(floor)
assert np.ptp(fp[:,2])<1e-7
objects,meshes,collections=set(bpy.data.objects),set(bpy.data.meshes),set(bpy.data.collections)
try:assembly.ground(body,[body])
except ValueError as exc:assert str(exc)=='Duplicate assembly member'
else:raise AssertionError('Duplicate accepted')
original=assembly._duplicate;calls=[]
def fail_second(*args,**kwargs):
    calls.append(1)
    if len(calls)==2:raise RuntimeError('Injected attachment failure')
    return original(*args,**kwargs)
with patch.object(assembly,'_duplicate',side_effect=fail_second):
    try:assembly.ground(body,eyes)
    except RuntimeError as exc:assert str(exc)=='Injected attachment failure'
    else:raise AssertionError('Failure not exercised')
assert len(calls)==2
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes) and collections==set(bpy.data.collections)
result,report=assembly.ground(body,eyes,float(fp[0,2]))
for obj,p in zip(sources,before):np.testing.assert_array_equal(p,sculpt.coordinates(obj))
np.testing.assert_array_equal(fp,sculpt.coordinates(floor))
after=[sculpt.coordinates(o) for o in result];grounded=after[0]
contacts=[]
for side in (-1,1):
    foot=grounded[(grounded[:,0]*side>.035)&(grounded[:,2]<.18)]
    gap=float(foot[:,2].min()-fp[0,2]);assert abs(gap)<.0002,gap
    contacts.append(gap*1000)
for source in sources:source.hide_render=True;source.hide_set(True)
folder.mkdir(parents=True)
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
camera(position=(0,-4,.88),target=(0,0,.88),scale=1.95,size=(640,960))
native=folder/'integrated.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));bpy.ops.wm.open_mainfile(filepath=str(native))
for name,points in zip(report['members'],after):np.testing.assert_array_equal(points,sculpt.coordinates(bpy.data.objects[name]))
# Assembly map identifies provenance and translation; it does not infer landmarks.
diagram={'units':'m','up_axis':'Z','front_axis':'-Y','placement':report,
 'region_evidence':{'face':'docs/reference/anatomy/CHIN_CONTOUR.md','ear_neck':'docs/reference/anatomy/NECK_TRANSITIONS.md','torso':'docs/reference/anatomy/body/TORSO.md','arms':'docs/reference/anatomy/body/ARMS.md','hands':'docs/reference/anatomy/body/HANDS.md','legs_feet':'docs/reference/anatomy/body/LEGS.md'},
 'bounds_min':grounded.min(axis=0).tolist(),'bounds_max':grounded.max(axis=0).tolist()}
(folder/'assembly.json').write_text(json.dumps(diagram,indent=2))
for view,pos in [('front',(0,-4,.88)),('back',(0,4,.88))]:
    camera(position=pos,target=(0,0,.88),scale=1.95,size=(640,960))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report.update(blender=bpy.app.version_string,source_unchanged=True,floor_unchanged=True,
    member_relative_positions_preserved=True,duplicate_rejected=True,late_failure_atomic=True,
    bilateral_sole_gap_mm=contacts,saved_readback=True,source_sha256=digest)
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('ASSEMBLY_PASS',json.dumps(report),flush=True)
