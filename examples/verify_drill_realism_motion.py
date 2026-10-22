"""Fresh-process motion evidence for the current native realism candidate."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'src'))
from drill_assembly_motion import verify as sweep
from mesh_workbench import nested

def verify(source,output,channels):
    if not channels or len(set(channels))!=len(channels) or any(c not in ('trigger','latch','battery','jaw_diameter') for c in channels):
        raise ValueError('Explicit unique supported motion channels required')
    output.mkdir(parents=True,exist_ok=False)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    original={row['object']:bpy.data.objects[row['object']].matrix_world.copy() for row in state['outputs'].values()}
    results={}
    for channel in channels:
        report=sweep(output,only=channel)[channel]
        error=max(abs(bpy.data.objects[name].matrix_world[i][j]-matrix[i][j]) for name,matrix in original.items() for i in range(4) for j in range(4))
        results[channel]={'passed':report['passed'],'samples':len(report['samples']),'rest_matrix_error':error,'evidence':channel+'.json'}
    report={'blender':bpy.app.version_string,'source_sha256':digest,'source_preserved':digest==hashlib.sha256(source.read_bytes()).hexdigest(),'channels':results}
    report['passed']=report['source_preserved'] and all(r['passed'] and r['rest_matrix_error']<=1e-7 for r in results.values())
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:
        raise ValueError('Native motion verification failed')
if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    verify(Path(args[0]),Path(args[1]),args[2:])
