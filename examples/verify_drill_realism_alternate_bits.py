"""Actual nominal bit and 6/10 mm inspection-shank clearance and jaw motion."""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))
from mesh_workbench import nested, actuators, construction, mechanical
from drill_assembly_motion import verify_alternate_bits


def verify(source, output):
    output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    originals = {row['object']: bpy.data.objects[row['object']].matrix_world.copy()
                 for row in state['outputs'].values()}
    objects = set(bpy.data.objects)
    # The shared sweep uses this authored shank extent. Reject a different
    # recipe instead of testing an unrelated cylinder at old coordinates.
    stock = state['nodes']['bit_stock']['args']
    if stock['start'] != [83, 0, 160] or stock['end'] != [117, 0, 160]:
        raise ValueError('Alternate-bit probe requires the declared shank extent')
    sweeps = verify_alternate_bits(output)
    fixed = {key: bpy.data.objects[row['object']] for key, row in state['outputs'].items()
             if state['nodes'][key].get('visible', True)
             and key not in ('bit', 'jaw_0', 'jaw_1', 'jaw_2')}
    # Unlike the jaw sweeps, this checks the bit itself against all fixed
    # solids, including the added nose support. Intentional jaw contacts are
    # covered by the diameter-specific sweeps above.
    clearances = {}
    for diameter in (2, 6, 10):
        bit = (bpy.data.objects[state['outputs']['bit']['object']] if diameter == 2
               else construction.strut('Stationary inspection bit', stock['start'], stock['end'],
                                       radius=diameter / 2, segments=96))
        try:
            clearances[str(diameter)] = {key: actuators.pair(bit, obj, minimum=.2)
                                        for key, obj in fixed.items()}
        finally:
            if diameter != 2:
                mechanical.remove(bit)
    error = max(abs(bpy.data.objects[name].matrix_world[i][j] - matrix[i][j])
                for name, matrix in originals.items() for i in range(4) for j in range(4))
    report = {'blender': bpy.app.version_string, 'source_sha256': digest,
              'source_preserved': digest == hashlib.sha256(source.read_bytes()).hexdigest(),
              'bits': {key: {'passed': row['passed'], 'positions': len(row['samples']),
                             'rest_restored': row['rest_restored']} for key, row in sweeps.items()},
              'fixed_clearances': clearances, 'rest_matrix_error': error,
              'temporary_objects_removed': set(bpy.data.objects) == objects,
              'scope': 'Actual 2 mm driver and 6/10 mm cylindrical shanks; sampled clearance and jaw motion, not cutting efficacy'}
    report['passed'] = (report['source_preserved'] and error <= 1e-7
                        and report['temporary_objects_removed']
                        and all(row['passed'] and row['rest_restored'] for row in report['bits'].values())
                        and all(row['passed'] for rows in clearances.values() for row in rows.values()))
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ALTERNATE_BITS', report['passed'], flush=True)
    if not report['passed']:
        raise ValueError('Alternate-bit clearance or restoration failed')


if __name__ == '__main__':
    verify(*map(Path, sys.argv[sys.argv.index('--') + 1:]))
