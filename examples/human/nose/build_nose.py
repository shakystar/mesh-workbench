"""Build nasal volumes/cavities on the included open-eye head and render it."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import nasal_structure,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    folder=Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects['Open-eye head'];before=sculpt.coordinates(source)
    globes={o:sculpt.coordinates(o) for o in bpy.data.objects if o.name.startswith('Open-eye head globe')}
    objects=set(bpy.data.objects);meshes=set(bpy.data.meshes)
    for invalid in ({'width_mm':26,'nostril_width_mm':9},{'base_z':2.5}):
        try:nasal_structure.build(source,invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid nasal request accepted')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    original_subtract=nasal_structure._subtract
    calls=0
    def fail_second(head,cutter):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('Injected second-nostril failure')
        return original_subtract(head,cutter)
    with patch.object(nasal_structure,'_subtract',fail_second):
        try:nasal_structure.build(source)
        except RuntimeError as exc:assert str(exc)=='Injected second-nostril failure'
        else:raise AssertionError('Late failure not exercised')
    assert calls==2
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    head,stage,report=nasal_structure.build(source)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    for globe,points in globes.items():np.testing.assert_array_equal(points,sculpt.coordinates(globe))
    basis=np.asarray([p.co[:] for p in stage.data.shape_keys.key_blocks['Basis'].data])
    sculpt.set_layer(stage,'Nasal volumes',0)
    np.testing.assert_array_equal(basis,sculpt.coordinates(stage))
    sculpt.set_layer(stage,'Nasal volumes',1)
    after=sculpt.coordinates(head)
    protected=(np.abs(before[:,0])>.03)|(before[:,2]<1.599)|(before[:,2]>1.642)|(before[:,1]>-.04)
    retained={tuple(p) for p in after}
    assert all(tuple(p) in retained for p in before[protected])
    assert np.isfinite(after).all()
    report.update(blender=bpy.app.version_string,source_preserved=True,eyes_preserved=True,
                  protected_vertices=int(protected.sum()),volume_layer_rollback=True,
                  invalid_requests=2,late_failure_atomic=True,
                  limits='Authored static surface and blind cavities; no internal airway, rig or anatomical validation.')
    for obj in (source,stage):obj.hide_render=True;obj.hide_set(True)
    folder.mkdir(parents=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    camera(position=(0,-4,1.65),target=(0,-.005,1.64),scale=.29,size=(800,800))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'nasal-structure.blend'))
    print('NASAL_STRUCTURE_PASS',json.dumps(report),flush=True)
    views=[('front',(0,-4,1.65),(0,-.005,1.64),.29),
           ('three-quarter',(2.5,-4,1.65),(0,-.005,1.64),.29),
           ('underside',(0,-1.5,.05),(0,-.078,1.613),.105)]
    for name,position,target,scale in views:
        camera(position=position,target=target,scale=scale,size=(800,800))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    print('NASAL_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
