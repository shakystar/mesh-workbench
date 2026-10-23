"""Restore unrelated scene visibility from preserved input and verify readback."""
import sys,json
from pathlib import Path
import bpy
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt
import numpy as np
source,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
bpy.ops.wm.open_mainfile(filepath=str(source))
visibility={o.name:o.hide_render for o in bpy.data.objects if o.name!='Elbow relief study'}
native=folder/'hands-grafted.blend';bpy.ops.wm.open_mainfile(filepath=str(native))
before=sculpt.coordinates(bpy.data.objects['Hands grafted study']);changed=[]
for name,value in visibility.items():
    obj=bpy.data.objects.get(name)
    if obj and obj.hide_render!=value:obj.hide_render=value;changed.append(name)
bpy.ops.wm.save_as_mainfile(filepath=str(native))
bpy.ops.wm.open_mainfile(filepath=str(native))
for name,value in visibility.items():
    if name in bpy.data.objects:assert bpy.data.objects[name].hide_render==value
np.testing.assert_array_equal(before,sculpt.coordinates(bpy.data.objects['Hands grafted study']))
(folder/'visibility-check.json').write_text(json.dumps({'restored_objects':changed,'unrelated_visibility_preserved':True,'geometry_unchanged':True},indent=2))
print('VISIBILITY_READBACK_PASS',changed,flush=True)
