"""Lower nose on the preserved integrated character; bounded checks and views."""
import copy, hashlib, json, sys
from pathlib import Path
from unittest.mock import patch
import bpy, numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists());sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt,curve_fit
from mesh_workbench.assembly import nose
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path))
source=bpy.data.objects['Grounded character body'];before=sculpt.coordinates(source)
dz=json.loads((path.parent/'assembly.json').read_text())['placement']['translation_m'][2]
rays=[]
def row(name,group,x,z,offset):
    rays.append(dict(name=name,group=group,origin=[x,-1,z+dz],direction=[0,1,0],offset=offset))
for i,x in enumerate([-.005,0,.005]):
    row('tip_'+str(i),'tip',x,1.619,[0,-.85,-.3])
    row('upper_'+str(i),'tip',x,1.627,[0,.25,0])
    row('bridge_'+str(i),'tip',x,1.636,[0,0,0])
for s in [-1,1]:
    for i,(x,z,offset) in enumerate([(.014,1.619,[s*.4,-.75,0]),(.016,1.615,[s*.6,-.5,-.1]),(.013,1.608,[s*.3,-.55,-.2]),(.007,1.604,[0,-.3,0]),(.022,1.618,[0,0,0])]):
        row('ala_'+str(s)+'_'+str(i),'ala',s*x,z,offset)
for i,(z,off) in enumerate([(1.600,[0,0,0]),(1.604,[0,-.35,0]),(1.608,[0,-.7,-.2]),(1.612,[0,-.8,-.2])]):row('columella_'+str(i),'columella',0,z,off)
registration=dict(rays=rays,radius_mm=10,region=dict(min=[-.029,-.15,1.595+dz],max=[.029,-.04,1.642+dz],feather_mm=2))
# Basal rays register the outer entrance margins rather than cavity centres.
normal=np.array([0,-.30,-.954]);normal/=np.linalg.norm(normal)
h=np.array([1.,0,0]);v=np.cross(normal,h)
for side in (-1,1):
    angle=np.radians(side*18);u=h*np.cos(angle)+v*np.sin(angle);w=np.cross(normal,u)
    center=np.array([side*.00663,-.0862,1.6068+dz])
    for i,t in enumerate(np.linspace(0,2*np.pi,8,endpoint=False)):
        radial=u*.0035*np.cos(t)+w*.0057*np.sin(t)
        origin=center+radial+normal*.035
        offset=normal*.65+radial/np.linalg.norm(radial)*.25
        rays.append(dict(name='rim_'+str(side)+'_'+str(i),group='ala',origin=origin.tolist(),direction=(-normal).tolist(),offset=offset.tolist()))
amounts=dict(tip_mm=1.4,ala_mm=1.4,columella_mm=1.0)
diagram=nose.compile_controls(source,registration,**amounts)
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(registration);bad['rays'][-1]['direction']=[0,0,0]
try:nose.apply(source,bad)
except ValueError:pass
else:raise AssertionError('Invalid ray accepted')
with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected nasal failure')):
    try:nose.apply(source,registration,**amounts)
    except RuntimeError as e:assert str(e)=='Injected nasal failure'
    else:raise AssertionError('Failure not reached')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,report=nose.apply(source,registration,**amounts);after=sculpt.coordinates(result)
np.testing.assert_array_equal(before,sculpt.coordinates(source))
assert sculpt.topology(source)==sculpt.topology(result)
lo,hi=np.asarray(registration['region']['min']),np.asarray(registration['region']['max'])
protected=np.any((before<=lo)|(before>=hi),axis=1)
np.testing.assert_array_equal(before[protected],after[protected])
sculpt.set_layer(result,report['layer'],0);np.testing.assert_array_equal(before,sculpt.coordinates(result));sculpt.set_layer(result,report['layer'],1)
folder.mkdir(parents=True)
(folder/'registration.json').write_text(json.dumps(dict(registration=registration,diagram=diagram),indent=2))
source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'nose.blend'));bpy.ops.wm.open_mainfile(filepath=str(folder/'nose.blend'))
np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Nasal connections study']))
for view,position,target in [('front',(0,-4,1.62+dz),(0,-.075,1.62+dz)),('profile',(4,-.075,1.62+dz),(0,-.075,1.62+dz)),('basal',(0,-1.5,.05+dz),(0,-.078,1.613+dz))]:
    camera(position=position,target=target,scale=.085,size=(560,560))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    for state,old in [('before',True),('after',False)]:
        bpy.data.objects['Grounded character body'].hide_render=not old;bpy.data.objects['Nasal connections study'].hide_render=old
        scene.render.filepath=str(folder/(state+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report.update(blender=bpy.app.version_string,source_preserved=True,protected_exact=True,rollback=True,invalid_ray_rejected=True,late_failure_atomic=True,saved_readback=True,source_sha256=digest)
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('NASAL_PASS',json.dumps(report),flush=True)
