"""Read back the original slotted-driver blade and preserved round shank."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import nested


def verify(source,output):
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load()
    obj=bpy.data.objects[state['outputs']['bit']['object']]
    points=[obj.matrix_world @ v.co for v in obj.data.vertices]
    tips=[p for p in points if abs(p.x-117)<1e-4]
    shank=[p for p in points if p.x<110]
    edges={}
    for face in obj.data.polygons:
        ids=list(face.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    finite=all(math.isfinite(v) for p in points for v in p)
    nonmanifold=sum(n!=2 for n in edges.values())
    thickness=max(p.z for p in tips)-min(p.z for p in tips) if tips else None
    width=max(p.y for p in tips)-min(p.y for p in tips) if tips else None
    radial_error=max(abs(math.hypot(p.y,p.z-160)-1) for p in shank) if shank else None
    report={'blender':bpy.app.version_string,'source_sha256':digest,
            'source_preserved':digest==hashlib.sha256(source.read_bytes()).hexdigest(),
            'finite':finite,'nonmanifold_edges':nonmanifold,
            'tip_vertices':len(tips),'tip_thickness_mm':thickness,'tip_width_mm':width,
            'round_shank_vertices':len(shank),'maximum_shank_radius_error_mm':radial_error,
            'extent_x':[min(p.x for p in points),max(p.x for p in points)],
            'scope':'Authored 2 mm round-shank slotted driver, 0.6 mm blade. Not a cutting drill flute or strength certification; jaw sweep is separate.'}
    report['passed']=(report['source_preserved'] and finite and nonmanifold==0 and
        len(tips)>=4 and len(shank)>=96 and abs(thickness-.6)<1e-4 and 1.8<width<=2.001 and
        radial_error<1e-4 and abs(report['extent_x'][0]-83)<1e-4 and abs(report['extent_x'][1]-117)<1e-4)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('DRIVER_BIT',json.dumps(report),flush=True)
    if not report['passed']:raise ValueError('Driver blade or preserved shank geometry failed')

if __name__=='__main__':
    verify(*map(Path,sys.argv[sys.argv.index('--')+1:]))
