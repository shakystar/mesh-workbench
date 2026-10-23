"""Apply KB guide: INPUT.blend OBJECT TARGET.json OUTPUT_DIR (no render)."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy_fit,sculpt


def run(source,name,target,folder):
    folder=Path(folder)
    if folder.exists():raise ValueError('Use a fresh output directory')
    settings=json.loads(Path(target).read_text())
    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    source_obj=bpy.data.objects[name]
    original=sculpt.coordinates(source_obj)
    result_name='Fitted nasal guide' if settings.get('knowledge_id')=='nasal-base-v1' else 'Fitted oral guide'
    obj,diagram,reports=anatomy_fit.apply(source_obj,settings,result_name)
    after=sculpt.coordinates(obj)
    region=next(iter(diagram['regions'].values()))
    protected=~np.all((original>=region['min'])&(original<=region['max']),axis=1)
    np.testing.assert_array_equal(original[protected],after[protected])
    np.testing.assert_array_equal(original,sculpt.coordinates(source_obj))
    for r in reports:sculpt.set_layer(obj,r['layer'],0)
    np.testing.assert_allclose(original,sculpt.coordinates(obj),atol=1e-8)
    for r in reports:sculpt.set_layer(obj,r['layer'],1)
    verification={'blender':bpy.app.version_string,'knowledge_id':diagram['registration']['knowledge_id'],
        'protected_vertices':int(protected.sum()),'source_preserved':True,'rollback':True,
        'maximum_mm':float(np.linalg.norm(after-original,axis=1).max()*1000)}
    # Display the result without coplanar overlap; source geometry and keys survive.
    source_obj.hide_render=True;source_obj.hide_set(True)
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'brush-report.json').write_text(json.dumps(reports,indent=2))
    (folder/'verification.json').write_text(json.dumps(verification,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str((folder/'fitted.blend').resolve()))
    print('ANATOMY_FIT_COMPLETE',obj.name,json.dumps(verification),flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
