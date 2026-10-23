"""Registered mouth paths on a preserved lower-face model; two bounded previews."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy,sculpt,geometry
from mesh_workbench.runner import camera


def build(source_path,output):
    output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory')
    spec=json.loads((ROOT/'examples/human-mouth-diagram.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects['Lower face refinement']
    before=sculpt.coordinates(source)
    bounds=spec['regions']['mouth']
    lo,hi=np.array(bounds['min']),np.array(bounds['max'])
    selection=geometry.selection(source,'FACE',box=[lo,hi])
    obj=geometry.edit_topology(source,selection,'subdivide','Diagram guided mouth',cuts=1)
    for p in obj.data.polygons:p.use_smooth=True
    source.hide_render=True;source.hide_set(True)
    anatomy.bind(obj,spec)
    original=sculpt.coordinates(obj)
    reports=[anatomy.path_stroke(obj,c) for c in spec['paths']]
    after=sculpt.coordinates(obj)
    protected=~np.all((original>=lo)&(original<=hi),axis=1)
    np.testing.assert_array_equal(original[protected],after[protected])
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    for r in reports:sculpt.set_layer(obj,r['layer'],0)
    np.testing.assert_allclose(original,sculpt.coordinates(obj),atol=1e-8)
    for r in reports:sculpt.set_layer(obj,r['layer'],1)
    info=geometry.inspect(obj)
    assert info['finite'] and info['nonmanifold_edges']==0
    # A bad command must fail before adding a key or changing evaluated coordinates.
    count=len(obj.data.shape_keys.key_blocks)
    try:anatomy.path_stroke(obj,{**spec['paths'][0],'distance_mm':4})
    except ValueError:pass
    else:raise AssertionError('Excess displacement accepted')
    assert len(obj.data.shape_keys.key_blocks)==count
    np.testing.assert_array_equal(after,sculpt.coordinates(obj))
    report={'blender':bpy.app.version_string,'strokes':reports,
            'protected_vertices':int(protected.sum()),'protected_exact':True,
            'source_preserved':True,'rollback_verified':True,'invalid_command_atomic':True,
            'nonmanifold_edges':info['nonmanifold_edges'],
            'max_displacement_mm':float(np.linalg.norm(after-original,axis=1).max()*1000),
            'scope':'Authored diagram registration; no anatomical ground-truth validation.'}
    output.mkdir(parents=True)
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'human-mouth.blend').resolve()))
    for view,pos in [('mouth-front',(0,-4,1.58)),('mouth-side',(4,0,1.58))]:
        camera(position=pos,target=(0,-.025,1.58),scale=.19,size=(800,800))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('MOUTH_COMPLETE',json.dumps({k:v for k,v in report.items() if k!='strokes'}),flush=True)


if __name__=='__main__':build(*sys.argv[sys.argv.index('--')+1:])
