"""Attach procedural foots on new topology snapshots, retaining the original."""
import sys,json,hashlib
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench.regions import foot,footgraft as graft
from mesh_workbench import sculpt
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh output required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
source=bpy.data.objects['Foot relief study'];before=sculpt.coordinates(source);topology=sculpt.topology(source)
stocks=[]
for side in (-1,1):
    stock,parts=foot.build('Forefoot stock '+str(side),side=side)
    for obj in [stock]+parts:
        for v in obj.data.vertices:v.co.x+=side*.103
    stocks.append(stock)
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
try:graft.replace_forefoot(source,stocks[0],-1,body_cut=-.13)
except ValueError as exc:assert str(exc)=='Expected separated forefoot cuts'
else:raise AssertionError('Invalid cuts accepted')
with patch.object(graft.np.testing,'assert_array_equal',side_effect=RuntimeError('Injected late graft failure')):
    try:graft.replace_forefoot(source,stocks[0],-1)
    except RuntimeError as exc:assert str(exc)=='Injected late graft failure'
    else:raise AssertionError('Failure not exercised')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
left,report_left=graft.replace_forefoot(source,stocks[0],-1,'Left foot graft snapshot')
result,report_right=graft.replace_forefoot(left,stocks[1],1,'Forefoots grafted study')
np.testing.assert_array_equal(before,sculpt.coordinates(source));assert topology==sculpt.topology(source)
# Original heel/ankle and upper-body points survive exactly, independent of new indices.
after=sculpt.coordinates(result);protected=before[(before[:,1]>=-.105)|(before[:,2]>=.10)]
assert set(map(tuple,protected)).issubset(set(map(tuple,after)))
assert result.data.shape_keys is None and not result.vertex_groups
from mathutils import Vector
from mathutils.bvhtree import BVHTree
tree=BVHTree.FromPolygons(after.tolist(),[list(f.vertices) for f in result.data.polygons])
for side in (-1,1):
    for u in (-.0185,.0025,.021,.037):assert tree.ray_cast(Vector((side*(.103+u),-.160,1)),Vector((0,0,-1)))[0] is None
    for u in (-.032,-.008,.012,.029,.044):assert tree.ray_cast(Vector((side*(.103+u),-.160,1)),Vector((0,0,-1)))[0] is not None
folder.mkdir(parents=True)
source.hide_render=True;left.hide_render=True
for stock in stocks:stock.hide_render=True
result.hide_render=False
source.hide_set(True);left.hide_set(True)
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'foots-grafted.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));bpy.ops.wm.open_mainfile(filepath=str(native))
np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Forefoots grafted study']))
for view,pos,target,scale in [('top',(.103,-1,1),(.103,-.08,.04),.32),('oblique',(2,-3,.5),(.103,-.06,.065),.34)]:
    camera(position=pos,target=target,scale=scale,size=(640,640))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    for label,show_source in [('before',True),('after',False)]:
        bpy.data.objects['Foot relief study'].hide_render=not show_source
        bpy.data.objects['Forefoots grafted study'].hide_render=show_source
        scene.render.filepath=str(folder/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report={'blender':bpy.app.version_string,'left':report_left,'right':report_right,'protected_above_forefoots':len(protected),'source_unchanged':True,'original_topology_preserved':True,'new_snapshot_has_no_stale_keys_or_groups':True,'invalid_cut_rejected':True,'late_failure_cleanup':True,'eight_toe_gaps_open':True,'ten_toe_hits':True,'saved_readback':True,'source_sha256':digest}
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('FOREFOOT_GRAFT_PASS',json.dumps(report),flush=True)
