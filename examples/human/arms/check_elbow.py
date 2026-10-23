"""Check elbow invalid registrations without repeating renders."""
import json,sys
from pathlib import Path
import bpy
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench.regions import arm
from mesh_workbench import sculpt
folder=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(folder/'elbow-relief.blend'))
source=bpy.data.objects['Arm relief study'];before=sculpt.coordinates(source)
targets=[d['registration'] for d in json.loads((folder/'diagram.json').read_text())]
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
for field,value,message in [('elbow',targets[1]['wrist'],'Descending finite arm axes required'),('profile','invalid','Unknown arm profile')]:
    bad=[dict(t) for t in targets];bad[1][field]=value
    try:arm.apply_pair(source,bad,'Invalid elbow registration probe')
    except ValueError as exc:assert str(exc)==message
    else:raise AssertionError('Invalid target accepted')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
np.testing.assert_array_equal(before,sculpt.coordinates(source))
(folder/'registration-check.json').write_text(json.dumps({'invalid_order_rejected':True,'unknown_profile_rejected':True,'no_mutation':True,'blender':bpy.app.version_string},indent=2))
print('ELBOW_REGISTRATION_CHECK_PASS',flush=True)
