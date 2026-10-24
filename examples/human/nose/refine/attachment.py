"""Registered alar-cheek fairing on the single editable character."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import bpy,numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists());sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt,curve_fit
from mesh_workbench.assembly import nose
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
source=bpy.data.objects['Nasal connections study'];before=sculpt.coordinates(source)
dz=-.007871014066040516
registrations=[]
for side in (-1,1):
    xs=sorted([side*.0135,side*.036])
    registrations.append(dict(side=side,stations=[.016,.019,.022,.025,.028,.032],heights=[z+dz for z in [1.612,1.616,1.620,1.624]],
        region=dict(min=[xs[0],-.13,1.608+dz],max=[xs[1],-.035,1.628+dz],feather_mm=2)))
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(registrations);bad[0]['stations'][1]=bad[0]['stations'][0]
try:nose.apply_attachments(source,bad)
except ValueError:pass
else:raise AssertionError('Invalid stations accepted')
original=curve_fit.apply;calls=[]
def fail_second(*args,**kwargs):
    calls.append(1)
    if len(calls)==2:raise RuntimeError('Injected right ala failure')
    return original(*args,**kwargs)
with patch.object(curve_fit,'apply',side_effect=fail_second):
    try:nose.apply_attachments(source,registrations)
    except RuntimeError as e:assert str(e)=='Injected right ala failure'
    else:raise AssertionError('Failure not exercised')
assert len(calls)==2 and objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,diagrams,reports=nose.apply_attachments(source,registrations);after=sculpt.coordinates(result)
np.testing.assert_array_equal(before,sculpt.coordinates(source));assert sculpt.topology(source)==sculpt.topology(result)
allowed=np.zeros(len(before),bool)
for d in diagrams:allowed|=np.all((before>d['region']['min'])&(before<d['region']['max']),axis=1)
np.testing.assert_array_equal(before[~allowed],after[~allowed])
central=np.abs(before[:,0])<=.0135
np.testing.assert_array_equal(before[central],after[central])
for r in reports:sculpt.set_layer(result,r['layer'],0)
np.testing.assert_array_equal(before,sculpt.coordinates(result))
for r in reports:sculpt.set_layer(result,r['layer'],1)
# Compare actual sampled skin curvature at the authored rows.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
def roughness(points):
    tree=BVHTree.FromPolygons(points.tolist(),[list(p.vertices) for p in result.data.polygons]);values=[]
    for reg in registrations:
        for z in reg['heights']:
            ys=[tree.ray_cast(Vector((reg['side']*x,-1,z)),Vector((0,1,0)))[0].y for x in reg['stations']]
            # Changes of adjacent slopes account for unequal final station spacing.
            values.append(float(np.abs(np.diff(np.diff(ys)/np.diff(reg['stations']))).sum()))
    return values
oldrough,newrough=roughness(before),roughness(after)
assert sum(newrough)<sum(oldrough),(oldrough,newrough)
folder.mkdir(parents=True)
(folder/'registration.json').write_text(json.dumps(dict(registrations=registrations,diagrams=diagrams),indent=2))
source_mesh=source.data;bpy.data.objects.remove(source,do_unlink=True)
if source_mesh.users==0:bpy.data.meshes.remove(source_mesh)
result.name='Nasal connections study';result.hide_render=False;result.hide_set(False)
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True);bpy.ops.wm.open_mainfile(filepath=str(native))
result=bpy.data.objects['Nasal connections study'];np.testing.assert_array_equal(after,sculpt.coordinates(result))
for view,position in [('oblique',(2,-4,1.62+dz)),('profile',(4,-.075,1.62+dz))]:
    camera(position=position,target=(0,-.075,1.62+dz),scale=.085,size=(560,560))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    for state,value in [('before',0),('after',1)]:
        for r in reports:sculpt.set_layer(result,r['layer'],value)
        scene.render.filepath=str(folder/(state+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report=dict(blender=bpy.app.version_string,regions=reports,source_sha256=digest,source_preserved=True,protected_vertices=int((~allowed).sum()),
    central_nose_vertices=int(central.sum()),protected_exact=True,central_nose_exact=True,rollback=True,invalid_stations_rejected=True,
    second_side_failure_atomic=True,saved_readback=True,roughness_before=oldrough,roughness_after=newrough,native_bytes=native.stat().st_size)
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('ATTACHMENT_PASS',json.dumps(report),flush=True)
