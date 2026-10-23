"""Focused surface-frame, volume, protection and atomic-failure checks."""
import json
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import surface_brush,sculpt


def volume(obj):
    bm=bmesh.new()
    try:
        bm.from_mesh(obj.data)
        for v,p in zip(bm.verts,sculpt.coordinates(obj)):v.co=p
        return bm.calc_volume(signed=True)
    finally:bm.free()


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh=bpy.data.meshes.new('Curved rough fixture')
    bm=bmesh.new();bmesh.ops.create_uvsphere(bm,u_segments=96,v_segments=48,radius=.05)
    for v in bm.verts:
        p=v.co.copy()
        if p.y<-.02:
            v.co*=1+.012*np.sin(p.x*1300)*np.cos(p.z*1300)
    bm.to_mesh(mesh);bm.free();mesh.update()
    source=bpy.data.objects.new('Fixture',mesh);bpy.context.collection.objects.link(source)
    before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in mesh.polygons])
    landmarks={}
    for name,x in [('left',-.024),('middle',0),('right',.024)]:
        landmarks[name]=list(tree.ray_cast(Vector((x,-1,0)),Vector((0,1,0)))[0])
    diagram={'units':'m','landmarks':landmarks,'regions':{'front':{
        'min':[-.04,-.06,-.02],'max':[.04,-.02,.02],'feather':.002}}}
    common={'anchors':['left','middle','right'],'region':'front','radius_mm':10,
            'distance_mm':.5,'max_displacement_mm':1}
    outputs=[];reports=[]
    for mode in ('ridge','crease','relax_volume'):
        command=dict(common,mode=mode,label=mode,strength=.35,iterations=4)
        obj,rows=surface_brush.apply(source,diagram,[command],mode)
        outputs.append(obj);reports.extend(rows)
        after=sculpt.coordinates(obj);delta=after-before
        changed=np.linalg.norm(delta,axis=1)>1e-8
        np.testing.assert_array_equal(before[before[:,1]>0],after[before[:,1]>0])
        if mode!='relax_volume':
            radial=np.einsum('ij,ij->i',delta[changed],before[changed])
            assert np.all(radial>0) if mode=='ridge' else np.all(radial<0)
            assert np.max(np.abs(delta[changed,0]))>.00005, 'Fixed-axis deformation'
        else:
            assert abs(volume(obj)-volume(source))*1e9<.1
            neighbors=[[] for _ in before]
            for e in mesh.edges:
                a,b=e.vertices;neighbors[a].append(b);neighbors[b].append(a)
            area=np.flatnonzero((abs(before[:,0])<.02)&(abs(before[:,2])<.004)&(before[:,1]<0))
            def roughness(points):
                return float(np.mean([np.linalg.norm(points[i]-points[neighbors[i]].mean(axis=0))**2 for i in area]))
            ratio=roughness(after)/roughness(before)
            assert ratio<.9, ratio
            rows[0]['roughness_ratio']=ratio
        sculpt.set_layer(obj,rows[0]['layer'],0)
        np.testing.assert_array_equal(before,sculpt.coordinates(obj))
        sculpt.set_layer(obj,rows[0]['layer'],1)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    failures=0
    invalid=[dict(common,mode='ridge',max_displacement_mm=.01),
             dict(common,mode='ridge',view_direction=[0,0,0])]
    for commands in ([invalid[0]],[invalid[1]],[dict(common,mode='ridge'),invalid[1]]):
        objects=set(bpy.data.objects);meshes=set(bpy.data.meshes)
        try:surface_brush.apply(source,diagram,commands,'Invalid batch')
        except ValueError:failures+=1
        else:raise AssertionError('Invalid request accepted')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    opened=source.copy();opened.data=mesh.copy();bpy.context.collection.objects.link(opened)
    bm=bmesh.new();bm.from_mesh(opened.data)
    rear=max(bm.faces,key=lambda f:f.calc_center_median().y)
    bmesh.ops.delete(bm,geom=[rear],context='FACES_ONLY');bm.to_mesh(opened.data);bm.free()
    try:surface_brush.apply(opened,diagram,[dict(common,mode='relax_volume')],'Open invalid')
    except ValueError as exc:
        assert 'closed mesh' in str(exc);failures+=1
    else:raise AssertionError('Open volume accepted')
    report={'blender':bpy.app.version_string,'brushes':reports,'failure_cases':failures,
            'source_preserved':True,'hidden_sheet_preserved':True,'layer_rollback':True}
    folder=ROOT/'runs/human/surface-brush-check';folder.mkdir(parents=True,exist_ok=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('SURFACE_BRUSH_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run()
