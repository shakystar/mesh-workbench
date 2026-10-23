"""Read back saved lower-nose geometry; no rendering or native-file writes."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt


def run(folder):
    folder=Path(folder).resolve()
    diagram=json.loads((folder/'diagram.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(folder/'lower-nose.blend'))
    source=bpy.data.objects['Surface brushed nose']; obj=bpy.data.objects['Lower nose curve study']
    p=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in obj.data.polygons])
    errors={c['name']:tree.find_nearest(Vector(c['target']))[3]*1000 for c in diagram['controls']}
    assert max(errors.values())<.2, errors
    assert [v.select for v in obj.data.vertices]==[v.select for v in source.data.vertices]
    for key in ('mw_masks','mw_selections'):
        assert obj.get(key)==source.get(key)
    assert [g.name for g in obj.vertex_groups]==[g.name for g in source.vertex_groups]
    assert all([(g.group,g.weight) for g in a.groups]==[(g.group,g.weight) for g in b.groups]
               for a,b in zip(source.data.vertices,obj.data.vertices))
    report={'target_surface_distance_mm':errors,'max_target_surface_distance_mm':max(errors.values()),
            'selection_and_vertex_groups_preserved':True,'scope':'Nearest surface residual, not anatomical accuracy or global collision detection.'}
    (folder/'readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('LOWER_NOSE_READBACK_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
