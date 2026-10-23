"""Small, authored nasal trial of generic surface brushes; no anatomy claim."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import surface_brush,sculpt
from mesh_workbench.runner import camera


def run(source_path,output_path):
    folder=Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects['Nasal structure'];before=sculpt.coordinates(source)
    tree=BVHTree.FromPolygons(before.tolist(),[list(p.vertices) for p in source.data.polygons])
    landmarks={};commands=[]
    def path(prefix,xz):
        names=[]
        for i,(x,z) in enumerate(xz):
            hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
            if hit is None:raise ValueError('Nasal trial anchor misses surface')
            key=f'{prefix}_{i}';landmarks[key]=list(hit);names.append(key)
        return names
    tip=path('tip',[(-.008,1.622),(0,1.623),(.008,1.622)])
    commands.append(dict(mode='relax_volume',anchors=tip,region='nose',radius_mm=5,
                         strength=.18,iterations=3,max_displacement_mm=.6,label='Nasal volume relax'))
    for sign,label in [(-1,'left'),(1,'right')]:
        names=path(label+'_ala',[(sign*.012,1.615),(sign*.014,1.619),(sign*.011,1.623)])
        commands.append(dict(mode='ridge',anchors=names,region='nose',radius_mm=2.8,
                             distance_mm=.35,max_displacement_mm=.45,label=label+' alar ridge'))
        names=path(label+'_crease',[(sign*.019,1.615),(sign*.020,1.619),(sign*.017,1.624)])
        commands.append(dict(mode='crease',anchors=names,region='nose',radius_mm=1.8,
                             distance_mm=.22,max_displacement_mm=.3,label=label+' alar groove'))
    diagram={'units':'m','landmarks':landmarks,'regions':{'nose':{
        'min':[-.024,-.125,1.613],'max':[.024,-.065,1.631],'feather':.001}}}
    result,reports=surface_brush.apply(source,diagram,commands,'Surface brushed nose')
    after=sculpt.coordinates(result)
    region=diagram['regions']['nose']
    protected=~np.all((before>=region['min'])&(before<=region['max']),axis=1)
    np.testing.assert_array_equal(before[protected],after[protected])
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    for row in reports:sculpt.set_layer(result,row['layer'],0)
    np.testing.assert_array_equal(before,sculpt.coordinates(result))
    for row in reports:sculpt.set_layer(result,row['layer'],1)
    report={'blender':bpy.app.version_string,'source_preserved':True,'all_layer_rollback':True,
            'protected_vertices':int(protected.sum()),'brushes':reports,
            'maximum_combined_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
            'scope':'Generic brush trial on authored nasal paths; not anatomical validation.'}
    folder.mkdir(parents=True)
    for filename,value in [('verification.json',report),('diagram.json',diagram),('commands.json',commands)]:
        (folder/filename).write_text(json.dumps(value,indent=2),encoding='utf-8')
    source.hide_render=True;source.hide_set(True)
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    camera(position=(0,-4,1.65),target=(0,-.005,1.64),scale=.29,size=(800,800))
    scene.cycles.samples=16;scene.cycles.use_denoising=True
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'surface-brushed.blend'))
    print('NASAL_BRUSH_PASS',json.dumps({k:v for k,v in report.items() if k!='brushes'}),flush=True)
    for view,position,target,scale in [('front',(0,-4,1.65),(0,-.005,1.64),.29),
                                     ('detail',(1.6,-4,1.64),(0,-.075,1.616),.125)]:
        camera(position=position,target=target,scale=scale,size=(800,800))
        scene.cycles.samples=16;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    print('NASAL_BRUSH_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
