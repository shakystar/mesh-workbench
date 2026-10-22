"""Original fixed-lens camera exterior, using existing workbench primitives.

blender -b --factory-startup -t 2 --python examples/compact_camera.py -- runs/compact-camera
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mesh_workbench import construction, mechanical, detail, sculpt, materials
from mesh_workbench.runner import camera


def build(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a fresh output directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .001
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    parts = []

    def material(name, color, metal=0, rough=.4, transmission=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*color, 1)
        bsdf.inputs['Metallic'].default_value = metal
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Transmission Weight'].default_value = transmission
        return mat

    silver = material('Satin aluminium', (.46,.49,.51), .85,.3)
    black = material('Black anodised metal', (.018,.022,.026), .7,.28)
    rubber = material('Charcoal leather', (.025,.03,.033), 0,.7)
    brass = material('Warm index accent', (.66,.31,.08), .8,.27)
    glass = material('Coated optical glass', (.025,.105,.13), .32,.09,.35)
    screen = material('Display glass', (.018,.035,.04), .3,.18)
    white = material('Off-white engraving', (.77,.79,.74), .1,.5)
    red = material('Shutter accent', (.5,.055,.025), .4,.32)

    def assign(obj, mat):
        obj.data.materials.append(mat)
        parts.append(obj)
        return obj

    def box(name, dims, pos, mat, radius=1):
        return assign(mechanical.box(name, dims, pos, min(radius,min(dims)*.45)), mat)

    def cylinder(name, start, end, radius, mat):
        return assign(construction.strut(name, start, end, radius, 96), mat)

    def ring(name, start, length, outer, inner, mat, axis=(0,-1,0)):
        return assign(mechanical.annulus(name, outer, inner, start, length, axis, 128), mat)

    def label(text, pos, size, mat, rear=False, top=False):
        data = bpy.data.curves.new('Engraving '+text, 'FONT')
        data.body=text
        data.size=size
        data.extrude=.015
        data.space_character=1.1
        obj=bpy.data.objects.new(data.name,data)
        scene.collection.objects.link(obj)
        obj.location=pos
        obj.rotation_euler=(0,0,0) if top else ((math.pi/2,0,math.pi) if rear else (math.pi/2,0,0))
        obj.data.materials.append(mat)

    body=box('Rounded main body',(120,36,72),(0,0,39),rubber,7)
    materials.finish([body], 'Body leather grain', role='rubber', color=(.025,.03,.033,1),
                     roughness=.7, variation=.04, grain_mm=.5, bump_mm=.035, seed=19)
    box('Upper alloy cover',(120.4,36.4,14),(0,0,76),silver,3)
    box('Lower alloy cover',(119,35.8,5),(0,0,5),silver,1.8)
    box('Top cover seam',(119.5,36.1,.65),(0,0,68.8),black,.2)
    box('Sculpted front grip',(22,17,51),(-44,-19,35),rubber,7)
    box('Grip upper accent',(19,12,2),(-44,-22,61),black,.7)
    # Lens axis: -Y. Ring bores and the glass share the same centre.
    ring('Mount flange',(10,-18,40),4,30,23,silver)
    ring('Brass mount index',(10,-22,40),1.2,28.8,23,brass)
    ring('Rear lens barrel',(10,-23,40),6,27.8,22,black)
    focus=detail.profiled_ring('Knurled focus ring', [10,-28,40],
        [[0,27,22,0],[.5,27.2,22,1],[11.5,27.2,22,1],[12,26.8,22,0]],
        flutes=96,depth=.45,segments=768,axis=(0,-1,0))
    assign(focus,black)
    ring('Lens scale band',(10,-40,40),5.5,26.6,22,black)
    ring('Front silver bevel',(10,-45.5,40),.8,26.1,21.8,silver)
    ring('Front filter rim',(10,-46.3,40),2,25.8,21.4,black)
    ring('Optical well',(10,-38,40),8,22,18.5,black)
    cylinder('Dark aperture backing',(10,-43,40),(10,-44,40),19,black)
    # Convex coated front element; central closure uses a tiny positive radius.
    optic=construction.revolve('Convex front element',
        [[.01,0],[8,-.05],[15,-.35],[20.9,-.95],[20.9,-1.6],[15,-2.25],[8,-2.6],[.01,-2.7]],
        segments=128,closed=False,location=(10,-46,40))
    optic.rotation_euler=(math.pi/2,0,0)
    # Positive local Z points toward -Y; position the bulge toward the viewer.
    for v in optic.data.vertices:v.co.z *= -1
    assign(optic,glass)
    for i in range(16):
        a=math.tau*i/16
        mark=box('Focus scale tick %02d'%i,(.35,3 if i%4==0 else 1.5,.15),
                 (10+26.65*math.sin(a),-42.5,40+26.65*math.cos(a)),white,.05)
        mark.rotation_euler[1]=a
    box('Lens alignment marker',(1.1,2,.25),(10,-25,69),red,.1)
    # Top dials and the inset shutter button.
    for name,x,r in [('Shutter dial',-39,10),('Exposure dial',43,9)]:
        knob=detail.profiled_ring(name,[x,2,82],
            [[0,r,.5,0],[.5,r,.5,1],[4,r,.5,1],[4.5,r-.4,.5,0]],
            flutes=48,depth=.3,segments=384,axis=(0,0,1))
        assign(knob,silver)
        cylinder(name+' top',(x,2,85.8),(x,2,86.5),r-.8,black)
        for i in range(12):
            a=math.tau*i/12
            mark=box(name+' index '+str(i),(.35,1.3,.12),
                     (x+(r-2)*math.sin(a),2+(r-2)*math.cos(a),86.6),white,.04)
            mark.rotation_euler[2]=-a
    ring('Shutter surround',(-40,-9,83),1.2,5.5,3.9,black,(0,0,1))
    cylinder('Shutter release',(-40,-9,83.2),(-40,-9,85),3.8,red)
    box('Hot shoe base',(18,14,1.5),(5,3,83.5),black,.5)
    for x in (-3.5,13.5):box('Hot shoe rail '+str(x),(1.4,14,2.2),(x,3,85),silver,.3)
    cylinder('Hot shoe contact',(5,3,84),(5,3,84.5),1.1,brass)
    # Front window and autofocus lamp.
    box('Viewfinder surround',(21,2,10),(-35,-18.8,75),black,1.2)
    box('Viewfinder window',(16,1,6),(-35,-20,75),glass,.7)
    cylinder('Autofocus lamp',(45,-18,61),(45,-19.2,61),2.3,glass)
    label('FRAME',(-7,-18.6,74),4,black)
    label('35 / 2',(33,-18.7,58),2.3,white)
    # Rear display and a small control cluster.
    box('Rear display surround',(81,3.5,52),(-10,19,38),black,2.3)
    box('Rear display glass',(74,1,45),(-10,21,38),screen,1.5)
    for x in (-39,19):
        for z in (23,53):
            box('Display frame horizontal %s %s'%(x,z),(5,.2,.4),(x,21.6,z),white,.08)
            box('Display frame vertical %s %s'%(x,z),(.4,.2,4),(x+(2.4 if x<0 else -2.4),21.6,z),white,.08)
    label('1/125   F2.8   ISO 200',(22,21.7,20),2,white,rear=True)
    ring('Rear navigation wheel',(44,18.5,36),2.3,8.5,3.6,black,(0,1,0))
    cylinder('Select button',(44,18,36),(44,21,36),3.4,silver)
    for z in (54,65):cylinder('Rear function '+str(z),(44,18,z),(44,20,z),3,black)
    box('Rear viewfinder eyecup',(25,4,12),(-35,19,75),black,2)
    box('Rear viewfinder glass',(17,1,6),(-35,21.3,75),glass,.8)
    for x in (-61,61):
        ring('Strap eye '+str(x),(x,-1,65),3,4.5,2.5,silver,(1 if x>0 else -1,0,0))
    # Focused static geometry check only, before adding the presentation floor.
    evaluated=bpy.context.evaluated_depsgraph_get()
    errors=[]
    for obj in parts:
        mesh=obj.evaluated_get(evaluated).to_mesh()
        if not len(mesh.polygons) or any(not math.isfinite(c) for v in mesh.vertices for c in v.co):
            errors.append(obj.name)
        obj.evaluated_get(evaluated).to_mesh_clear()
    if errors:raise ValueError('Invalid camera parts: '+str(errors))
    output.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'mesh_parts':len(parts),'finite_geometry':not errors,
            'scope':'Original fixed-lens camera exterior; no optical simulation, internals or articulation.',
            'threads':2,'renders':['front','rear']}
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    floor=box('Presentation floor',(1000,1000,2),(0,0,.5),material('Backdrop',(.055,.065,.07),0,.75),.5)
    scene.world=bpy.data.worlds.new('Camera studio')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.18,.2,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    for name,pos,power,size in [('Key',(-120,-160,260),1800000,180),('Fill',(180,-80,170),1000000,140),('Rim',(30,150,220),2200000,120)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,0,40))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera(position=(175,-260,155),target=(0,-8,42),scale=185,size=(1000,800))
    scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.view_settings.view_transform='AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'camera.blend').resolve()))
    for view,pos in [('front',(175,-260,155)),('rear',(-170,260,150))]:
        camera(position=pos,target=(0,-8 if view=='front' else 4,42),scale=185,size=(1000,800))
        scene.cycles.samples=32;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('CAMERA_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':
    build(sys.argv[sys.argv.index('--')+1])
