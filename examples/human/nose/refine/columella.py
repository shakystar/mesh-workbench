"""Central columella and philtrum junction on the single editable character."""
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
registration=dict(half_width_mm=2.8,stations=[[z+dz,a,b] for z,a,b in [(1.598,0,0),(1.601,0,1),(1.604,.1,.55),(1.607,.7,0),(1.610,1,0),(1.613,.4,0),(1.616,0,0)]])
diagram=nose.compile_columella(source,registration)
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(registration);bad['stations'][1][0]=bad['stations'][0][0]
try:nose.compile_columella(source,bad)
except ValueError:pass
else:raise AssertionError('Invalid stations accepted')
with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected junction failure')):
    try:curve_fit.apply(source,diagram,'Junction candidate')
    except RuntimeError as e:assert str(e)=='Injected junction failure'
    else:raise AssertionError('Failure not exercised')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,report=curve_fit.apply(source,diagram,'Junction candidate');after=sculpt.coordinates(result)
np.testing.assert_array_equal(before,sculpt.coordinates(source));assert sculpt.topology(source)==sculpt.topology(result)
lo,hi=np.asarray(diagram['region']['min']),np.asarray(diagram['region']['max'])
protected=np.any((before<=lo)|(before>=hi),axis=1)
np.testing.assert_array_equal(before[protected],after[protected])
sculpt.set_layer(result,report['layer'],0);np.testing.assert_array_equal(before,sculpt.coordinates(result));sculpt.set_layer(result,report['layer'],1)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
tree=BVHTree.FromPolygons(after.tolist(),[list(p.vertices) for p in result.data.polygons])
residual=max(tree.find_nearest(Vector(c['target']))[3]*1000 for c in diagram['controls'])
assert residual<.2,residual
reports=[report]
folder.mkdir(parents=True)
(folder/'registration.json').write_text(json.dumps(dict(registration=registration,diagram=diagram),indent=2))
source_mesh=source.data;bpy.data.objects.remove(source,do_unlink=True)
if source_mesh.users==0:bpy.data.meshes.remove(source_mesh)
result.name='Nasal connections study';result.hide_render=False;result.hide_set(False)
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True);bpy.ops.wm.open_mainfile(filepath=str(native))
result=bpy.data.objects['Nasal connections study'];np.testing.assert_array_equal(after,sculpt.coordinates(result))
for view,position in [('profile',(4,-.075,1.611+dz)),('basal',(0,-1.5,.05+dz))]:
    camera(position=position,target=(0,-.078,1.610+dz),scale=.065,size=(560,560))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    for state,value in [('before',0),('after',1)]:
        for r in reports:sculpt.set_layer(result,r['layer'],value)
        scene.render.filepath=str(folder/(state+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report.update(blender=bpy.app.version_string,source_sha256=digest,source_preserved=True,protected_vertices=int(protected.sum()),
    protected_exact=True,rollback=True,invalid_stations_rejected=True,late_failure_atomic=True,saved_readback=True,
    surface_residual_mm=residual,native_bytes=native.stat().st_size)
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('JUNCTION_PASS',json.dumps(report),flush=True)
