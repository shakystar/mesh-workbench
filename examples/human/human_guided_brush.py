"""Apply the registered anatomy diagram to an included human_base.py result.

blender -b --factory-startup -t 2 --python examples/human/human_guided_brush.py -- INPUT.blend OUTPUT_DIR
"""
import json,sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy,sculpt
from mesh_workbench.runner import camera


def build(source_path,output):
    source_path=Path(source_path);output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory')
    spec=json.loads((ROOT/'examples/human/human-anatomy-diagram.json').read_text(encoding='utf-8-sig'))
    bpy.ops.wm.open_mainfile(filepath=str(source_path.resolve()))
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    source=bpy.data.objects['Human base surface']
    original=sculpt.coordinates(source)
    obj=source.copy();obj.data=source.data.copy();obj.name='Anatomy guided cranium'
    scene.collection.objects.link(obj)
    # Bake only a NEW evaluated snapshot. Source keys and smoothing remain intact.
    sculpt.bake(obj)
    source.hide_render=True;source.hide_set(True)
    anatomy.bind(obj,spec)
    reports=[anatomy.stroke(obj,command) for command in spec['strokes']]
    after=sculpt.coordinates(obj)
    protected=original[:,2]<spec['regions']['cranium']['min'][2]
    np.testing.assert_array_equal(original[protected],after[protected])
    for report in reports:sculpt.set_layer(obj,report['layer'],0)
    np.testing.assert_allclose(sculpt.coordinates(obj),original,atol=1e-8)
    for report in reports:sculpt.set_layer(obj,report['layer'],1)
    np.testing.assert_array_equal(sculpt.coordinates(source),original)
    if not np.isfinite(after).all():raise ValueError('Nonfinite brush result')
    output.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'strokes':reports,
            'protected_vertices':int(protected.sum()),'protected_exact':True,
            'source_preserved':True,'rollback_verified':True,
            'total_max_displacement_mm':float(np.linalg.norm(after-original,axis=1).max()*1000),
            'scope':'Artist-registered skull diagram; coordinate precision is not anatomical validation.'}
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    # Diagram outline and guides use the SAME world frame as brush projection.
    diagram={**spec,'hits':[r['hit_world'] for r in reports],
             'outline':original[original[:,2]>1.50].tolist()}
    (output/'diagram-preview.json').write_text(json.dumps(diagram))
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'human-guided.blend').resolve()))
    for view,pos in [('head-front',(0,-4,1.56)),('head-side',(4,0,1.56))]:
        camera(position=pos,target=(0,0,1.56),scale=.48,size=(800,900))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('ANATOMY_GUIDED_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    build(*args)
