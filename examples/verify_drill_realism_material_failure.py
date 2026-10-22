"""Native material creation failure cleanup and subsequent valid assignment."""
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mesh_workbench import materials, nested, sculpt


def verify(source, output):
    if output.exists():
        raise ValueError('Fresh report required')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    obj = bpy.data.objects[state['outputs']['housing_left']['object']]
    meshes, mats = set(bpy.data.meshes), set(bpy.data.materials)
    mesh = obj.data
    slots = {o.name: tuple(o.data.materials) for o in bpy.data.objects if o.type == 'MESH'}
    coordinates = sculpt.coordinates(obj).tobytes()
    creation_observed = []
    name = 'Injected native finish failure'

    def reject_metadata(*args, **kwargs):
        material = bpy.data.materials.get(name)
        creation_observed.append(material is not None and len(material.node_tree.links) > 5)
        raise RuntimeError('Injected material metadata creation failure')

    rejected = False
    with patch.object(materials.json, 'dumps', side_effect=reject_metadata):
        try:
            materials.finish([obj], name, 'plastic', [.3, .3, .3, 1], seed=13)
        except RuntimeError as exc:
            if str(exc) != 'Injected material metadata creation failure':
                raise
            rejected = True
    preserved = (obj.data == mesh and set(bpy.data.meshes) == meshes
                 and set(bpy.data.materials) == mats
                 and all(tuple(bpy.data.objects[key].data.materials) == value for key, value in slots.items())
                 and sculpt.coordinates(obj).tobytes() == coordinates)
    if not rejected or creation_observed != [True] or not preserved:
        raise ValueError('Material creation failure did not preserve native state')
    recovery = materials.finish([obj], 'Recovered native finish', 'plastic', [.3, .3, .3, 1], seed=13)
    recovered = (obj.data.materials[0].name == recovery['material']
                 and json.loads(obj.data.materials[0]['mw_finish'])['seed'] == 13
                 and tuple(obj.data.materials)[1:] == slots[obj.name][1:])
    result = {'blender': bpy.app.version_string, 'source_sha256': digest,
              'source_preserved': digest == hashlib.sha256(source.read_bytes()).hexdigest(),
              'material_and_shader_created_before_failure': creation_observed == [True],
              'rejected': rejected, 'native_state_preserved_after_failure': preserved,
              'valid_assignment_after_failure': recovered,
              'scope': 'Failure after shader creation, before assignment; native file remains untouched'}
    result['passed'] = result['source_preserved'] and preserved and recovered and rejected
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print('MATERIAL_CREATION_RECOVERY', result['passed'], flush=True)
    if not result['passed']:
        raise ValueError('Native material failure recovery failed')


if __name__ == '__main__':
    verify(*map(Path, sys.argv[sys.argv.index('--') + 1:]))
