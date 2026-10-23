"""Check lateral registration rejection without rendering or geometry mutation."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench.regions import torso
from mesh_workbench import sculpt
import numpy as np
folder=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(folder/'flank-transition.blend'))
source=bpy.data.objects['Axillary transition study'];before=sculpt.coordinates(source)
diagram=json.loads((folder/'diagram.json').read_text())
kb=torso.knowledge();kb['flank_controls'][0]['w']=10
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
with patch.object(torso,'knowledge',return_value=kb):
    try:torso.compile_controls(source,diagram['registration'],profile='flank')
    except ValueError as exc:assert str(exc)=='Flank reference must exit the torso from inside'
    else:raise AssertionError('Outside origin accepted')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
np.testing.assert_array_equal(before,sculpt.coordinates(source))
(folder/'registration-check.json').write_text(json.dumps({'outside_origin_rejected':True,'source_unchanged':True,'no_objects_or_meshes_created':True,'blender':bpy.app.version_string},indent=2))
print('FLANK_REGISTRATION_FAILURE_PASS',flush=True)
