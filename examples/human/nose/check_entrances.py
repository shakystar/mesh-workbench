"""Read back the final entrance snapshot and its preserved source."""
import json
import sys
from pathlib import Path
import bpy
import bmesh


def run(folder):
    folder=Path(folder).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(folder/'nasal-entrances.blend'))
    result=bpy.data.objects['Nasal entrance study']; source=bpy.data.objects['Lower nose curve study']
    assert source.hide_render and not result.hide_render
    assert not result.data.shape_keys and not result.vertex_groups
    assert all(not v.groups and not v.select for v in result.data.vertices)
    assert all(not e.select for e in result.data.edges)
    assert all(not p.select for p in result.data.polygons)
    assert source.data.shape_keys and 'MW lower nose curves' in source.data.shape_keys.key_blocks
    bm=bmesh.new()
    try:
        bm.from_mesh(result.data)
        assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
        report={'saved_native_readback':True,'source_layers_present':True,
                'topology_bound_selection_not_transferred':True,'nonmanifold_edges':0,
                'vertices':len(bm.verts),'faces':len(bm.faces),'blender':bpy.app.version_string}
    finally: bm.free()
    (folder/'readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ENTRANCE_READBACK_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
