"""Apply two KB eye regions on a preserved local subdivision; no render."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy_fit,geometry,sculpt


def run(source_path,output_path,*,source_name='Fitted nasal guide',target_file='human-eye-targets.json',
        prefix='Eye',filename='fitted-eyes.blend',
        scope='Surface eye guides; no eyeballs, openings or orbital cavities. No visual quality validation.'):
    folder=Path(output_path)
    if folder.exists():raise ValueError('Use a fresh output directory')
    targets=json.loads((ROOT/'examples'/target_file).read_text())['targets']
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects[source_name];source_before=sculpt.coordinates(source)
    guides=[anatomy_fit.compile_diagram(source,t) for t in targets]
    chosen=set()
    for guide in guides:
        region=next(iter(guide['regions'].values()))
        chosen.update(geometry.selection(source,'FACE',box=[region['min'],region['max']])['indices'])
    selection=geometry.selection(source,'FACE',indices=sorted(chosen))
    baseline=geometry.edit_topology(source,selection,'subdivide',prefix+' patch baseline',cuts=2)
    for p in baseline.data.polygons:p.use_smooth=True
    before=sculpt.coordinates(baseline)
    result,diagrams,reports=anatomy_fit.apply_many(baseline,targets,'Fitted '+prefix.lower()+' guides')
    after=sculpt.coordinates(result);editable=np.zeros(len(before),dtype=bool)
    for diagram in diagrams:
        region=next(iter(diagram['regions'].values()))
        editable|=np.all((before>=region['min'])&(before<=region['max']),axis=1)
    np.testing.assert_array_equal(before[~editable],after[~editable])
    np.testing.assert_array_equal(source_before,sculpt.coordinates(source))
    np.testing.assert_array_equal(before,sculpt.coordinates(baseline))
    for r in reports:sculpt.set_layer(result,r['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),atol=1e-8)
    for r in reports:sculpt.set_layer(result,r['layer'],1)
    info=geometry.inspect(result)
    if not info['finite'] or info['nonmanifold_edges']:raise ValueError('Invalid fitted regional surface')
    for obj in (source,baseline):obj.hide_render=True;obj.hide_set(True)
    report={'blender':bpy.app.version_string,'protected_vertices':int((~editable).sum()),
            'source_preserved':True,'baseline_preserved':True,'rollback':True,'nonmanifold_edges':0,
            'paths':len(reports),'maximum_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'scope':scope}
    folder.mkdir(parents=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    (folder/'diagrams.json').write_text(json.dumps(diagrams,indent=2))
    (folder/'brush-report.json').write_text(json.dumps(reports,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str((folder/filename).resolve()))
    print('HUMAN_'+prefix.upper()+'_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
