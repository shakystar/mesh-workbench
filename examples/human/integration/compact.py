"""Write one editable visible scene; preserve keys and verify saved readback.

Does not delete input files. Filesystem cleanup is a separate explicit action.
"""
import hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists());sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt
source,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if output.exists():raise ValueError('Fresh output required')
digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
old_meshes=len(bpy.data.meshes)
keep=[o for o in bpy.context.scene.objects if not o.hide_render]
meshes=[o for o in keep if o.type=='MESH']
def snapshot(obj):
    return dict(coords=sculpt.coordinates(obj),topology=sculpt.topology(obj),
                keys={k.name:(k.value,np.array([v.co[:] for v in k.data])) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {},
                groups=[g.name for g in obj.vertex_groups])
expected={o.name:snapshot(o) for o in meshes}
keep_names={o.name for o in keep}
for obj in list(bpy.data.objects):
    if obj.name not in keep_names:bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output))
for name,data in expected.items():
    actual=snapshot(bpy.data.objects[name]);np.testing.assert_array_equal(actual['coords'],data['coords'])
    assert actual['topology']==data['topology'] and actual['groups']==data['groups'] and actual['keys'].keys()==data['keys'].keys()
    for key,(value,points) in data['keys'].items():
        assert actual['keys'][key][0]==value;np.testing.assert_array_equal(actual['keys'][key][1],points)
assert set(bpy.data.objects.keys())==keep_names
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
report=dict(blender=bpy.app.version_string,source_sha256=digest,source_bytes=source.stat().st_size,output_bytes=output.stat().st_size,
            original_mesh_datablocks=old_meshes,retained_mesh_datablocks=len(bpy.data.meshes),objects=sorted(keep_names),
            mesh_keys={name:list(data['keys']) for name,data in expected.items()},geometry_topology_keys_groups_readback=True,source_unchanged=True,
            limits='Hidden historical topology snapshots are excluded. Existing current-topology keys remain editable.')
(output.parent/'compact-verification.json').write_text(json.dumps(report,indent=2));print('COMPACT_PASS',json.dumps(report),flush=True)
