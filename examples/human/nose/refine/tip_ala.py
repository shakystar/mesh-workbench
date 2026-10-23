"""Round the authored tip and upper alae, preserving every entrance-patch vertex."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import curve_fit,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    path,folder=Path(source_path).resolve(),Path(output_path).resolve()
    if folder.exists(): raise ValueError('Use a fresh output folder')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source=bpy.data.objects['Nasal entrance study']; before=sculpt.coordinates(source)
    old={tuple(p) for p in sculpt.coordinates(bpy.data.objects['Lower nose curve study'])}
    entrance=np.asarray([tuple(p) not in old for p in before])
    assert entrance.any()
    lower=float(before[entrance,2].max())+.0002
    if lower>1.615: raise ValueError('Entrance protection overlaps planned tip controls')
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    controls=[]; curves={}
    def line(name,probes):
        keys=[]
        for i,(x,z,dx,dy,dz) in enumerate(probes):
            hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
            if hit is None: raise ValueError('Control misses visible skin')
            key=name+'_'+str(i);p=np.asarray(hit)
            controls.append({'name':key,'source':p.tolist(),'target':(p+[dx,dy,dz]).tolist()})
            keys.append(key)
        curves[name]=keys
    line('tip_shoulders',[(-.0055,1.619,-.0003,-.0014,-.0002),
                         (0,1.619,0,.0005,-.0005),(.0055,1.619,.0003,-.0014,-.0002)])
    line('upper_tip',[(x,1.625,0,.0006,0) for x in (-.004,0,.004)])
    line('bridge_guard',[(x,1.634,0,0,0) for x in (-.006,0,.006)])
    for s,side in [(-1,'left'),(1,'right')]:
        line(side+'_alar_volume',[(s*.014,1.620,s*.0006,-.0012,0),
                                 (s*.016,1.617,s*.0003,-.0006,0)])
        line(side+'_attachment',[(s*.020,1.619,0,.0003,0),(s*.022,1.625,0,0,0)])
    diagram={'units':'m','label':'tip and alar volumes','radius_mm':10,'max_displacement_mm':3,
             'region':{'min':[-.028,-.14,lower],'max':[.028,-.045,1.64],'feather_mm':1},
             'controls':controls,'curves':curves,
             'intent':'Authored outer-volume study, not inferred cartilage geometry or population proportions.'}
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    try: curve_fit.apply(source,{**diagram,'label':''})
    except ValueError: pass
    else: raise AssertionError('Invalid label accepted')
    assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    result,report=curve_fit.apply(source,diagram,'Tip and alar study')
    after=sculpt.coordinates(result)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    np.testing.assert_array_equal(before[entrance],after[entrance])
    assert sculpt.topology(source)==sculpt.topology(result)
    sculpt.set_layer(result,report['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    sculpt.set_layer(result,report['layer'],1)
    actual=BVHTree.FromPolygons(after.tolist(),[list(p.vertices) for p in result.data.polygons])
    residuals={c['name']:actual.find_nearest(Vector(c['target']))[3]*1000 for c in controls}
    assert max(residuals.values())<.2,residuals
    report.update(blender=bpy.app.version_string,source_preserved=True,topology_preserved=True,
                  entrance_vertices_preserved=int(entrance.sum()),entrance_max_movement_mm=0,
                  entrance_protection_z=lower,layer_rollback=True,invalid_label_rejected=True,
                  source_sha256=digest,target_surface_distance_mm=residuals)
    folder.mkdir(parents=True)
    for filename,value in [('diagram.json',diagram),('verification.json',report)]:
        (folder/filename).write_text(json.dumps(value,indent=2),encoding='utf-8')
    source.hide_render=True;source.hide_set(True);result.hide_render=False;result.hide_set(False)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    camera(position=(0,-4,1.63),target=(0,-.075,1.63),scale=.11,size=(640,640))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    native=folder/'tip-ala.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    # Read back the saved native before rendering, without another Blender process.
    bpy.ops.wm.open_mainfile(filepath=str(native))
    saved=sculpt.coordinates(bpy.data.objects['Tip and alar study'])
    np.testing.assert_array_equal(saved,after)
    print('TIP_ALA_SAVED_READBACK_PASS',json.dumps({k:v for k,v in report.items() if k!='target_surface_distance_mm'}),flush=True)
    for name,position,target,scale in [
        ('front',(0,-4,1.63),(0,-.075,1.63),.11),
        ('profile',(4,-.075,1.63),(0,-.075,1.63),.11),
        ('basal',(0,-1.5,.05),(0,-.078,1.613),.105)]:
        camera(position=position,target=target,scale=scale,size=(640,640))
        scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report['saved_native_readback']=True;report['source_file_unchanged']=True
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('TIP_ALA_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
