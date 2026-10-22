"""Fresh-process native verification of the asset-free realism fixture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import assembly, attachments, nested, sculpt


def verify(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Use a fresh verification directory")
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    state=nested.load()
    obj=bpy.data.objects['Form sample']
    after=sculpt.coordinates(obj)
    assert abs(after[:,0].mean()-0.15)<1e-6
    layer=json.loads(obj['mw_layers'])[-1]['name']
    sculpt.set_layer(obj,layer,0)
    assert abs(sculpt.coordinates(obj)[:,0].mean())<1e-7
    sculpt.set_layer(obj,layer,1)
    np.testing.assert_array_equal(sculpt.coordinates(obj),after)
    finish=json.loads(obj.data.materials[0]['mw_finish'])
    assert finish['seed']==19 and abs(finish['mm_per_unit']-1)<1e-6
    seat=bpy.data.objects[state['outputs']['seat']['object']]
    assert abs(json.loads(seat['mw_recess_seat'])['floor_minimum']-1.75)<1e-4
    assert all(json.loads(mat['mw_finish'])['seed']==3 for mat in seat.data.materials)
    mark=bpy.data.objects[state['outputs']['mark']['object']]
    metadata=json.loads(mark['mw_surface_paths'])
    assert metadata['source_revision']==attachments.revision(bpy.data.objects[metadata['source']])
    assert json.loads(mark['mw_marking'])['text']=='12'
    first=nested.update({'depth':0.3})
    assert first['updated']==['seat']
    saved=nested.load()
    objects=set(bpy.data.objects)
    materials=set(bpy.data.materials)
    checkpoint=nested._checkpoint
    def fail(phase):
        if phase=='after_commit':
            raise RuntimeError('Injected reopened commit failure')
    nested._checkpoint=fail
    rejected=False
    try:
        nested.update({'depth':0.2})
    except assembly.Rejected:
        rejected=True
    finally:
        nested._checkpoint=checkpoint
    assert rejected and nested.load()==saved
    assert set(bpy.data.objects)==objects and set(bpy.data.materials)==materials
    assert nested.update({'depth':0.2})['updated']==['seat']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    output.mkdir(parents=True)
    report={'passed':True,'blender':bpy.app.version_string,'source_sha256':before,'source_preserved':True,'cage_disable_restore':True,'finish_scale_seed_slots':True,'marking_binding_current':True,'seat_floor_mm':1.75,'selective_update':['seat'],'late_failure_rollback':True,'post_failure_update':True}
    (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'followup.blend'))
    print('REALISM_TOOLS_VERIFIED',json.dumps(report),flush=True)


if __name__=='__main__':
    arguments=sys.argv[sys.argv.index('--')+1:]
    verify(*arguments)
