"""Measure declared seam visibility rays against intended native supports."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import assembly,nested

def verify(source, output, spec_path=None):
    if output.exists():
        raise ValueError('Use a fresh report path')
    spec_path = spec_path or ROOT/'examples/drill-realism-upper-seam-rays.json'
    spec = json.loads(spec_path.read_text())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state = nested.load()
    reports = {}
    for name,roi in spec['rois'].items():
        blockers = roi.get('blockers') or [roi['blocker']]
        trees = [assembly._tree(bpy.data.objects[state['outputs'][key]['object']])
                 for key in blockers]
        misses = [i for i,ray in enumerate(roi['rays'])
                  if not any(tree.ray_cast(Vector(ray['origin']),Vector(ray['direction']))[0] is not None
                             for tree in trees)]
        reports[name] = {'rays':len(roi['rays']), 'blockers':blockers,
                         'misses':misses,'passed':len(roi['rays'])>=100 and not misses}
        if 'blocker' in roi:
            reports[name]['blocker'] = roi['blocker']
    report = {'blender':bpy.app.version_string,'scope':spec['scope'],
              'rays_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),
              'source_sha256':digest,'rois':reports,
              'source_preserved':digest==hashlib.sha256(source.read_bytes()).hexdigest()}
    report['passed'] = report['source_preserved'] and all(r['passed'] for r in reports.values())
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('UPPER_SEAM_CHECK',json.dumps(report),flush=True)
    if not report['passed']:
        raise ValueError('Declared seam visibility rays failed')

if __name__ == '__main__':
    verify(*map(Path,sys.argv[sys.argv.index('--')+1:]))
