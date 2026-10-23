"""Build and inspect separate hand stock without replacing the source character."""
import sys,json,hashlib
from pathlib import Path
from unittest.mock import patch
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench.regions import hand
from mesh_workbench import sculpt
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path))
source=bpy.data.objects['Elbow relief study'];before=sculpt.coordinates(source)
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
try:hand.build(scale=0)
except ValueError:pass
else:raise AssertionError('Invalid scale accepted')
with patch.object(hand.models,'combine',side_effect=RuntimeError('Injected fusion failure')):
    try:hand.build()
    except RuntimeError as exc:assert str(exc)=='Injected fusion failure'
    else:raise AssertionError('Failure not exercised')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
result,parts=hand.build();result.data.materials.append(source.data.materials[0])
import numpy as np
np.testing.assert_array_equal(before,sculpt.coordinates(source))
bm=bmesh.new();bm.from_mesh(result.data)
assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
bm.verts.ensure_lookup_table();seen=set();stack=[bm.verts[0]]
while stack:
    v=stack.pop()
    if v in seen:continue
    seen.add(v);stack.extend(e.other_vert(v) for e in v.link_edges)
assert len(seen)==len(bm.verts);bm.free()
p=sculpt.coordinates(result);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in result.data.polygons])
for x in (-.017,0,.017):assert tree.ray_cast(Vector((x,-1,.79)),Vector((0,1,0)))[0] is None
for x in (-.027,-.009,.009,.027):assert tree.ray_cast(Vector((x,-1,.79)),Vector((0,1,0)))[0] is not None
folder.mkdir(parents=True)
for obj in bpy.data.objects:
    if obj.type=='MESH' and obj!=result:obj.hide_render=True
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'hand-stock.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
bpy.ops.wm.open_mainfile(filepath=str(native))
np.testing.assert_array_equal(p,sculpt.coordinates(bpy.data.objects['Hand stock']))
for view,pos in [('front',(0,-4,.825)),('oblique',(2,-4,.825))]:
    camera(position=pos,target=(0,0,.825),scale=.22,size=(640,640))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report={'blender':bpy.app.version_string,'vertices':len(p),'one_connected_closed_oriented_surface':True,'three_finger_gaps_at_z_079':True,'four_finger_hits_at_z_079':True,'source_geometry_unchanged':True,'source_file_sha256':digest,'invalid_scale_rejected':True,'late_failure_atomic':True,'saved_readback':True,'attached_to_character':False}
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('HAND_STOCK_PASS',json.dumps(report),flush=True)
