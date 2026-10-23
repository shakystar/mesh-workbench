"""Register and display integrated surface guides on the saved character."""
import hashlib,json,sys,copy
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sculpt
from mesh_workbench.assembly import guides
from mesh_workbench.runner import camera
path,folder=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
if folder.exists():raise ValueError('Fresh folder required')
digest=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path))
body=bpy.data.objects['Grounded character body'];before=sculpt.coordinates(body)
placement=json.loads((path.parent/'assembly.json').read_text())
dz=placement['placement']['translation_m'][2];rows=[]
def add(name,region,x,z,view=-1):
    z+=dz
    rows.append({'name':name,'region':region,'origin':[x,view,z],'direction':[0,-view,0],
        'bounds':[[x-.002,-.23,z-.002],[x+.002,.16,z+.002]],
        'evidence':placement['region_evidence'][next(k for k in placement['region_evidence'] if region==k or region.startswith(k+'_'))]})
for name,z in [('nose_bridge',1.646),('nose_tip',1.624),('upper_lip',1.589),('chin',1.548)]:add(name,'face',0,z)
for name,z in [('neck_front',1.51),('neck_base',1.47)]:add(name,'ear_neck',0,z)
for name,z in [('sternum',1.31),('costal_midline',1.20),('abdomen',1.10),('pelvic_front',.96)]:add(name,'torso',0,z)
for side,label in [(-1,'L'),(1,'R')]:
    add(label+'_ear_surface','ear_neck_'+label,side*.085,1.628)
    add(label+'_hallux_tip','legs_feet_toes_'+label,side*.071,.028)
    for name,x,z in [('upper_lid',.027,1.655),('cheek',.045,1.611)]:add(label+'_'+name,'face_'+label,side*x,z)
    for name,x,z in [('upper_arm',.222,1.30),('elbow',.26,1.14),('wrist',.306,.92)]:add(label+'_'+name,'arms_'+label,side*x,z)
    for name,x,z in [('palm',.32,.85),('finger_base',.332,.82)]:add(label+'_'+name,'hands_'+label,side*x,z)
    for name,x,z in [('thigh',.096,.62),('knee',.101,.505),('shin',.104,.23),('ankle',.103,.13)]:add(label+'_'+name,'legs_feet_'+label,side*x,z)
    for name,x,z in [('scapular_surface',.08,1.31),('lumbar_surface',.06,1.10)]:add(label+'_'+name,'torso_back_'+label,side*x,z,1)
# Resolve evidence by explicit family rather than underscore parsing.
objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
bad=copy.deepcopy(rows);bad[-1]['origin'][0]=3
try:guides.register(body,bad)
except ValueError as exc:assert 'Guide misses' in str(exc)
else:raise AssertionError('Missing late ray accepted')
assert objects==set(bpy.data.objects) and meshes==set(bpy.data.meshes)
diagram=guides.register(body,rows)
np.testing.assert_array_equal(before,sculpt.coordinates(body))
tree=BVHTree.FromPolygons(before.tolist(),[list(f.vertices) for f in body.data.polygons])
residual=max(tree.find_nearest(Vector(p))[3] for p in diagram['landmarks'].values())
assert residual<.00001
folder.mkdir(parents=True);(folder/'guides.json').write_text(json.dumps(diagram,indent=2))
collection=bpy.data.collections.new('Integrated surface guides');bpy.context.scene.collection.children.link(collection)
colors=[(.95,.22,.08),(.1,.65,1),(.25,.85,.3),(1,.7,.05),(.8,.2,.85),(.05,.8,.8)]
materials=[]
for i,color in enumerate(colors):
    mat=bpy.data.materials.new('Guide color '+str(i));mat.diffuse_color=(*color,1);mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.6;materials.append(mat)
for group,names in diagram['paths'].items():
    i=list(placement['region_evidence']).index(next(k for k in placement['region_evidence'] if group==k or group.startswith(k+'_')))
    for name in names:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.006,location=diagram['landmarks'][name])
        obj=bpy.context.object;obj.name='Guide '+name;obj.data.materials.append(materials[i%len(materials)])
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj);obj['region']=group;obj['surface_anchor']=diagram['landmarks'][name]
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
native=folder/'guided.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));bpy.ops.wm.open_mainfile(filepath=str(native))
np.testing.assert_array_equal(before,sculpt.coordinates(bpy.data.objects['Grounded character body']))
for name,p in diagram['landmarks'].items():np.testing.assert_allclose(list(bpy.data.objects['Guide '+name].location),p,atol=1e-7,rtol=0)
for view,pos in [('front',(0,-4,.88)),('back',(0,4,.88))]:
    camera(position=pos,target=(0,0,.88),scale=1.38,size=(640,960))
    scene=bpy.context.scene;scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
report={'blender':bpy.app.version_string,'landmarks':len(rows),'regions':len(diagram['regions']),
    'surface_residual_mm':residual*1000,'source_unchanged':True,'late_miss_no_mutation':True,
    'saved_body_and_guides_readback':True,'source_sha256':digest}
(folder/'verification.json').write_text(json.dumps(report,indent=2));print('GUIDES_PASS',json.dumps(report),flush=True)
