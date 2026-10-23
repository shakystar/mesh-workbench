"""Round stepped chin transitions and fit registered projection/width controls."""
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
from mesh_workbench import anatomy_fit,curve_fit,surface_brush,sculpt
from mesh_workbench.runner import camera

def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists():raise ValueError('Fresh output folder required')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Oral transition study'];before=sculpt.coordinates(source)
    def tree(obj):
        return BVHTree.FromPolygons(sculpt.coordinates(obj).tolist(),[list(p.vertices) for p in obj.data.polygons])
    def project(bvh,x,z):
        hit=bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
        if hit is None:raise ValueError('Chin path misses skin')
        return list(hit)
    bvh=tree(source)
    landmarks={str(i):project(bvh,x,1.536) for i,x in enumerate([-.022,-.011,0,.011,.022])}
    region={'min':[-.052,-.13,1.516],'max':[.052,-.02,1.558],'feather':.003}
    brush_diagram={'units':'m','landmarks':landmarks,'regions':{'chin':region}}
    command={'mode':'relax_volume','label':'chin surface fairing','anchors':list(landmarks),
             'region':'chin','radius_mm':20,'strength':.5,'iterations':12,'max_displacement_mm':3}
    smooth,brushes=surface_brush.apply(source,brush_diagram,[command],'Faired chin source')
    smooth_before=sculpt.coordinates(smooth)
    target={'center':project(tree(smooth),0,1.546),'half_width_m':.028,
            'upper_protection_z':1.558,'lower_protection_z':1.516}
    diagram=anatomy_fit.compile_chin_contour(smooth,target)
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    bad={**target,'center':[0,-.2,1.546]}
    for invalid in (bad,{**target,'upper_protection_z':1.54}):
        try:anatomy_fit.compile_chin_contour(smooth,invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid registration accepted')
    try:anatomy_fit.compile_chin_contour(smooth,target,narrowing_mm=5)
    except ValueError:pass
    else:raise AssertionError('Invalid narrowing accepted')
    with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected chin failure')):
        try:curve_fit.apply(smooth,diagram,'Chin contour study')
        except RuntimeError as exc:assert str(exc)=='Injected chin failure'
        else:raise AssertionError('Late failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,fit=curve_fit.apply(smooth,diagram,'Chin contour study');after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    np.testing.assert_array_equal(smooth_before,sculpt.coordinates(smooth))
    assert sculpt.topology(source)==sculpt.topology(result)
    protected=before[:,2]>=1.558
    np.testing.assert_array_equal(before[protected],after[protected])
    for row in [*brushes,fit]:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    for row in [*brushes,fit]:sculpt.set_layer(result,row['layer'],1)
    actual=tree(result)
    residuals={c['name']:actual.find_nearest(Vector(c['target']))[3]*1000 for c in diagram['controls']}
    assert max(residuals.values())<.2,residuals
    central_before=project(tree(smooth),0,1.546)[1]
    central_after=project(actual,0,1.546)[1]
    assert central_after-central_before>.0012
    report={'blender':bpy.app.version_string,'source_preserved':True,'intermediate_preserved':True,
            'topology_preserved':True,'upper_face_vertices_preserved':int(protected.sum()),
            'combined_rollback':True,'invalid_cases':3,'late_failure_atomic':True,
            'max_displacement_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'central_setback_mm':(central_after-central_before)*1000,
            'target_surface_distance_mm':residuals,'brushes':brushes,'fit':fit,'source_sha256':digest}
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'fairing.json').write_text(json.dumps({'diagram':brush_diagram,'commands':[command]},indent=2))
    for obj in (source,smooth):obj.hide_render=True;obj.hide_set(True)
    result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    native=folder/'chin-contour.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.wm.open_mainfile(filepath=str(native))
    np.testing.assert_array_equal(after,sculpt.coordinates(bpy.data.objects['Chin contour study']))
    print('CHIN_READBACK_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(0,-4,1.57)),('profile',(4,-.03,1.57))]:
        camera(position=pos,target=(0,-.03,1.57),scale=.18,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report.update(saved_native_readback=True,source_file_unchanged=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    print('CHIN_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
