"""Reproduce rejected wrist fairing and inspect the suspect seam face."""
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import surface_brush,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Hands grafted study'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    diagram={'units':'m','landmarks':{},'regions':{}};commands=[]
    for side in (-1,1):
        for view in (-1,1):
            name='wrist '+str(side)+' '+str(view);keys=[]
            for i,offset in enumerate(np.linspace(-.017,.017,7)):
                x=side*.31+offset;z=.901
                hit=tree.ray_cast(Vector((x,view,z)),Vector((0,-view,0)))[0]
                if hit is None:raise ValueError('Wrist path misses surface')
                key=name+'_'+str(i);diagram['landmarks'][key]=list(hit);keys.append(key)
            xs=sorted((side*.27,side*.35))
            diagram['regions'][name]={'min':[xs[0],-.08,.875],'max':[xs[1],.08,.932],'feather':.005}
            commands.append({'mode':'relax_volume','label':name,'anchors':keys,'region':name,
                'view_direction':[0,-view,0],'radius_mm':20,'strength':.4,'iterations':8,'max_displacement_mm':3})
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try:surface_brush.apply(source,diagram,commands,'Rejected wrist trial')
    except ValueError as exc:
        assert str(exc)=='Surface brush exceeds displacement cap',str(exc)
        failure=str(exc)
    else:raise AssertionError('Expected unsafe wrist trial to be rejected')
    assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    polygon=source.data.polygons[122586];v=before[list(polygon.vertices)]
    lengths=np.linalg.norm(np.roll(v,-1,axis=0)-v,axis=1)
    folder.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'uniform_trial_rejection':failure,
        'no_objects_or_meshes_leaked':True,'source_geometry_unchanged':True,
        'examined_polygon':122586,'vertex_ids':list(polygon.vertices),
        'coordinates':v.tolist(),'edge_lengths_mm':(lengths*1000).tolist(),
        'edge_length_ratio':float(lengths.max()/lengths.min()),
        'source_sha256':digest,'new_native_created':False,
        'limits':'Examined face was identified in a rejected inverse-length experiment; this audit reproduces only the uniform displacement rejection.'}
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'commands.json').write_text(json.dumps(commands,indent=2))
    print('WRIST_REJECTION_AUDIT',json.dumps(report),flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
