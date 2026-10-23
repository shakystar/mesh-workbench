"""Authored lower-nose control curves on the preserved current head."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import curve_fit, sculpt
from mesh_workbench.runner import camera


def run(source_path, output_path):
    path, folder = Path(source_path).resolve(), Path(output_path).resolve()
    if folder.exists(): raise ValueError('Use a fresh output folder')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source = bpy.data.objects['Surface brushed nose']
    before = sculpt.coordinates(source)
    tree = BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    controls, curves = [], {}
    def curve(name, probes):
        names = []
        for i,(x,z,dx,dy,dz) in enumerate(probes):
            hit = tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
            if hit is None: raise ValueError('Control misses face')
            name_i = name+'_'+str(i)
            a = np.asarray(hit)
            controls.append({'name':name_i,'source':a.tolist(),'target':(a+np.array([dx,dy,dz])).tolist()})
            names.append(name_i)
        curves[name] = names
    # These displacements are an artistic study, never population proportions.
    curve('tip_support', [(x,1.617,0,-.0015,-.0012) for x in (-.005,0,.005)])
    curve('supratip_transition', [(x,1.629,0,.0006,0) for x in (-.006,0,.006)])
    curve('columella', [(0,1.604,0,-.0004,0),(0,1.608,0,-.0006,-.0006),(0,1.612,0,-.0012,-.001)])
    for s,label in [(-1,'left'),(1,'right')]:
        curve(label+'_alar_crest',[(s*.012,1.613,s*.0005,.0005,.0007),
                                  (s*.015,1.616,s*.0005,.0005,0),
                                  (s*.016,1.620,0,.0003,0)])
        curve(label+'_attachment',[(s*.021,1.608,0,0,0),(s*.023,1.616,0,0,0),
                                   (s*.019,1.624,0,0,0)])
        # Lower entrance margin: register actual surface rather than cavity centre.
        curve(label+'_sill',[(s*.0065,1.602,0,.0008,0),(s*.011,1.605,s*.0003,.001,.0001)])
    diagram = {'units':'m','radius_mm':13,'max_displacement_mm':4,
               'region':{'min':[-.029,-.14,1.596],'max':[.029,-.045,1.642],'feather_mm':3},
               'controls':controls,'curves':curves,
               'reference':'docs/reference/anatomy/NOSE_AUDIT.md',
               'interpretation':'Named surface controls informed by structural relationships; no internal cartilage reconstruction.'}
    objects, meshes = set(bpy.data.objects), set(bpy.data.meshes)
    bad = copy.deepcopy(diagram); bad['controls'][0]['source'][1]-=.02
    too_far = copy.deepcopy(diagram); too_far['max_displacement_mm']=.1
    for invalid in (bad,too_far):
        try: curve_fit.apply(source,invalid)
        except ValueError: pass
        else: raise AssertionError('Invalid control request accepted')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    with patch.object(curve_fit.layers,'finish',side_effect=RuntimeError('Injected layer failure')):
        try: curve_fit.apply(source,diagram)
        except RuntimeError as exc: assert str(exc)=='Injected layer failure'
        else: raise AssertionError('Failure not exercised')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report = curve_fit.apply(source,diagram,'Lower nose curve study')
    after = sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    lo,hi = np.asarray(diagram['region']['min']),np.asarray(diagram['region']['max'])
    protected = np.any((before<=lo)|(before>=hi),axis=1)
    np.testing.assert_array_equal(before[protected],after[protected])
    assert sculpt.topology(source)==sculpt.topology(result)
    sculpt.set_layer(result,report['layer'],0)
    np.testing.assert_allclose(before,sculpt.coordinates(result),rtol=0,atol=2e-7)
    sculpt.set_layer(result,report['layer'],1)
    report.update(source_preserved=True,topology_preserved=True,layer_rollback=True,
                  invalid_requests=2,late_failure_atomic=True,blender=bpy.app.version_string,
                  source_sha256=digest,protected_vertices=int(protected.sum()))
    folder.mkdir(parents=True)
    for filename,value in [('diagram.json',diagram),('verification.json',report)]:
        (folder/filename).write_text(json.dumps(value,indent=2),encoding='utf-8')
    source.hide_render=True; source.hide_set(True)
    result.hide_render=False; result.hide_set(False)
    scene=bpy.context.scene; scene.render.threads_mode='FIXED'; scene.render.threads=2
    camera(position=(0,-4,1.63),target=(0,-.075,1.63),scale=.11,size=(640,640))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'lower-nose.blend'))
    print('LOWER_NOSE_CURVES_PASS',json.dumps(report),flush=True)
    for name,position,target,scale in [
        ('front',(0,-4,1.63),(0,-.075,1.63),.11),
        ('profile',(4,-.075,1.63),(0,-.075,1.63),.11),
        ('basal',(0,-1.5,.05),(0,-.078,1.613),.105)]:
        camera(position=position,target=target,scale=scale,size=(640,640))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    print('LOWER_NOSE_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__': run(*sys.argv[sys.argv.index('--')+1:])
