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
from mesh_workbench import construction, mechanical, detail, materials, sectionstock, enclosure
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
    panel_finish = material('Satin control panel', (.025,.03,.033), .15,.55)
    rubber = material('Charcoal leather', (.025,.03,.033), 0,.7)
    brass = material('Warm index accent', (.66,.31,.08), .8,.27)
    glass = material('Coated optical glass', (.025,.105,.13), .32,.09,.35)
    optical_glass = material('Clear lens coating', (.96,.985,1), 0,.025,1)
    optical_glass.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.46
    iris_material = material('Aperture blade metal', (.12,.135,.15), .7,.38)
    cavity_material = material('Optical cavity black', (.002,.003,.004), 0,.85)
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

    def casing(name, rows, mat):
        return assign(sectionstock.create(name,
            [[z,0,0,hx,hy] for z,hx,hy in rows],exponent=8,segments=192),mat)

    # Corresponding outlines keep cover corners flush with the body, with a
    # recessed gasket in the 0.25 mm joint instead of a protruding flat plate.
    body=casing('Rounded main body',[(7,59.7,17.7),(7.4,60,18),
        (68.6,60,18),(69,59.7,17.7)],rubber)
    materials.finish([body], 'Body leather grain', role='rubber', color=(.025,.03,.033,1),
                     roughness=.7, variation=.04, grain_mm=.5, bump_mm=.035, seed=19)
    upper=casing('Upper alloy cover',[(69.25,59.7,17.7),(69.65,60,18),
        (81.8,60,18),(82.5,59.7,17.7),(83,59.2,17.2)],silver)
    lower=casing('Lower alloy cover',[(2.5,59.2,17.2),(2.9,59.7,17.7),
        (3.4,60,18),(6.35,60,18),(6.75,59.7,17.7)],silver)
    casing('Upper recessed gasket',[(68.8,59.4,17.4),(69.5,59.4,17.4)],black)
    casing('Lower recessed gasket',[(6.5,59.4,17.4),(7.2,59.4,17.4)],black)
    # Taper both ends into the body; no separate projecting top plate.
    grip=assign(sectionstock.create('Tapered front grip',[
        [8,-44,-16.6,7,1.0],[10,-44,-18.5,9,3.0],
        [16,-44,-20.6,10.5,5.0],[47,-44,-20.6,10.5,5.0],
        [54,-44,-19.6,10,4.0],[59,-44,-17.8,8.8,2.2],
        [63,-44,-16.6,7,1.0]],exponent=4,segments=128),rubber)
    materials.finish([grip], 'Grip fine grain', role='rubber', color=(.025,.03,.033,1),
                     roughness=.7, variation=.03, grain_mm=.5, bump_mm=.025, seed=19)
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
    cylinder('Dark optical backing',(10,-24,40),(10,-25,40),19,cavity_material)
    ring('Inner lens seat',(10,-28,40),2,18.4,13.5,black)
    cylinder('Inner lens element',(10,-29.5,40),(10,-30.3,40),13.4,optical_glass)
    # Nine separate closed iris leaves surround an actual polygonal opening.
    blades=[]
    for i in range(9):
        a=math.tau*i/9
        b=math.tau*(i+1)/9
        outline=[(6*math.cos(a),6*math.sin(a)),
                 (19.2*math.cos(a+.22),19.2*math.sin(a+.22)),
                 (19.2*math.cos(b+.22),19.2*math.sin(b+.22)),
                 (6*math.cos(b),6*math.sin(b))]
        front=-37.7-i*.012
        vertices=[(10+x,y,40+z) for y in (front,front+.08) for x,z in outline]
        faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
        blade=assign(enclosure._mesh('Iris leaf %02d'%i,vertices,faces),iris_material)
        for f in blade.data.polygons:f.use_smooth=False
        blades.append(blade)
    # The clear element is recessed behind the filter rim. No metallic opacity
    # or coordinate mirroring: its closed profile retains outward normals.
    optic=construction.revolve('Convex front element',
        [[.01,-.65],[8,-.62],[15,-.52],[20.9,-.35],
         [20.9,0],[15,.55],[8,.92],[.01,1.05]],
        segments=128,closed=False,location=(10,-46.5,40))
    optic.rotation_euler=(math.pi/2,0,0)
    assign(optic,optical_glass)
    for i in range(16):
        a=math.tau*i/16
        mark=box('Focus scale tick %02d'%i,(.35,3 if i%4==0 else 1.5,.15),
                 (10+26.65*math.sin(a),-42.5,40+26.65*math.cos(a)),white,.05)
        mark.rotation_euler[1]=a
    box('Lens alignment marker',(1.1,2,.25),(10,-25,69),red,.1)
    # Top dials and the inset shutter button.
    for name,x,r in [('Shutter dial',-39,10),('Exposure dial',43,9)]:
        ring(name+' seated bezel',(x,2,82.9),.6,r+.6,r-.2,black,(0,0,1))
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
        for i,text in enumerate(('M','A','S','P') if x<0 else ('-2','-1','0','+1')):
            a=math.tau*i/4
            label(text,(x+5*math.sin(a)-.7,2+5*math.cos(a)-.7,86.65),1.7,white,top=True)
    ring('Shutter surround',(-40,-9,83),1.2,5.5,3.9,black,(0,0,1))
    cylinder('Shutter release',(-40,-9,83.2),(-40,-9,85),3.8,red)
    box('Hot shoe base',(18,14,1.5),(5,3,83.5),black,.5)
    for x in (-3.5,13.5):box('Hot shoe rail '+str(x),(1.4,14,2.2),(x,3,85),silver,.3)
    cylinder('Hot shoe contact',(5,3,84),(5,3,84.5),1.1,brass)
    # Front window and autofocus lamp.
    box('Viewfinder surround',(21,1.1,10),(-35,-18.1,75),black,.5)
    box('Viewfinder window',(16,.3,6),(-35,-18.7,75),glass,.12)
    cylinder('Autofocus lamp',(45,-18,61),(45,-19.2,61),2.3,glass)
    label('FRAME',(-7,-18.6,74),4,black)
    label('35 / 2',(33,-18.7,58),2.3,white)
    # Rear display and a small control cluster.
    display_stock=box('Display bezel stock',(80,1.2,52),(-10,17.9,38),black,.35)
    display_frame=mechanical.cut_box(display_stock,'Inset display bezel',(76,3,48),(-10,17.9,38),.6)
    display_stock.hide_render=True;display_stock.hide_set(True);parts.append(display_frame)
    display_glass=box('Rear display glass',(75.6,.4,47.6),(-10,18.1,38),screen,.15)
    box('Display backing',(76,.4,48),(-10,17.6,38),black,.15)
    for x in (-39,19):
        for z in (23,53):
            box('Display frame horizontal %s %s'%(x,z),(5,.2,.4),(x,18.42,z),white,.08)
            box('Display frame vertical %s %s'%(x,z),(.4,.2,4),(x+(2.4 if x<0 else -2.4),18.42,z),white,.08)
    label('1/125   F2.8   ISO 200',(22,18.45,20),2,white,rear=True)
    panel=box('Rear service panel',(24,.7,55),(43,17.85,40),panel_finish,.18)
    controls_before=set(bpy.data.objects)
    ring('Navigation seated bezel',(43,18.7,35),.45,8.8,8.35,silver,(0,1,0))
    ring('Rear navigation wheel',(43,18.8,35),1.15,8.1,3.7,black,(0,1,0))
    cylinder('Select button',(43,18.8,35),(43,20.15,35),3.35,silver)
    label('OK',(44.5,20.2,34.3),1.7,black,rear=True)
    for dx,dz in ((0,6),(0,-6),(6,0),(-6,0)):
        box('Direction mark %s %s'%(dx,dz),(1.3,.15,.4),(43+dx,20,35+dz),white,.05)
    for z,text in ((52,'MENU'),(62,'PLAY')):
        ring('Button bezel '+text,(43,18.7,z),.5,3.8,3.25,silver,(0,1,0))
        cylinder('Rear function '+text,(43,18.7,z),(43,19.8,z),3.05,black)
        label(text,(48,19, z-5),1.6,white,rear=True)
    for obj in set(bpy.data.objects)-controls_before:
        obj.location.y-=.5
    box('Rear viewfinder eyecup',(25,1.2,12),(-35,18.3,75),black,.4)
    box('Rear viewfinder glass',(17,.4,6),(-35,19.0,75),glass,.15)

    def screw(name, x, y, z, rear=True):
        direction=1 if rear else -1
        stock=cylinder(name+' stock',(x,y,z),(x,y+direction*.35,z),.85,silver)
        result=mechanical.cut_box(stock,name,(1.2,.3,.22),(x,y+direction*.35,z),.06)
        stock.hide_render=True;stock.hide_set(True)
        parts.append(result)
        return result
    for x,z in ((33,15),(53,15),(33,65),(53,65)):
        screw('Rear panel screw %s %s'%(x,z),x,18.2 if x>0 else 17.8,z)
    for x in (-60,60):
        box('Strap mounting plate '+str(x),(1.5,9,12),(x,0,64),black,.5)
        sign=1 if x>0 else -1
        cylinder('Strap stud '+str(x),(x,0,64),(x+sign*4,0,64),2.5,silver)
        ring('Strap eye '+str(x),(x+sign*4,-1,64),2,4.5,2.5,silver,(0,1,0))

    # A real bottom opening, not a hatch drawn over a solid body. Retain the
    # uncut construction objects hidden; the first native model stays untouched.
    pocket=mechanical.cut_box(body,'Body battery pocket',(32,22,18),(-33,0,15),1.2)
    body.hide_render=True;body.hide_set(True);parts.append(pocket)
    flange=box('Panel seat flange',(24.9,2,55.9),(43,16.6,40),black,.8)
    supported_body=enclosure.boolean(pocket,flange,'UNION','Body panel support')
    pocket.hide_render=True;pocket.hide_set(True)
    flange.hide_render=True;flange.hide_set(True);parts.append(supported_body)
    seated_body=mechanical.cut_box(supported_body,'Body with panel seat',(24.5,2,55.5),(43,18.2,40),.55)
    supported_body.hide_render=True;supported_body.hide_set(True);parts.append(seated_body)
    display_body=mechanical.cut_box(seated_body,'Body display recess',(80.4,2.2,52.4),(-10,18,38),.5)
    seated_body.hide_render=True;seated_body.hide_set(True);parts.append(display_body);seated_body=display_body
    panel_gasket_stock=box('Panel gasket stock',(24,.3,55),(43,17.35,40),rubber,.1)
    panel_gasket=mechanical.cut_box(panel_gasket_stock,'Panel perimeter gasket',(21.6,1,52.6),(43,17.35,40),.4)
    panel_gasket_stock.hide_render=True;panel_gasket_stock.hide_set(True);parts.append(panel_gasket)
    for i,(x,z) in enumerate(((33,15),(53,15),(33,65),(53,65))):
        bore=construction.strut('Panel fastener cutter',(x,16.8,z),(x,20,z),.65,48)
        drilled=enclosure.boolean(panel,bore,'DIFFERENCE','Drilled service panel '+str(i))
        mechanical.remove(bore)
        panel.hide_render=True;panel.hide_set(True);parts.append(drilled);panel=drilled
        ring('Panel mounting boss '+str(i),(x,17.2,z),.3,1.5,.65,black,(0,1,0))
        cylinder('Panel screw shaft '+str(i),(x,17.2,z),(x,18.25,z),.5,silver)
    # Through apertures, guide sleeves and shafts replace surface-only caps.
    button_specs=((52,3.25,'MENU'),(62,3.25,'PLAY'),(35,8.35,'Navigation'))
    for z,r,name in button_specs:
        cutter=construction.strut('Control aperture cutter',(43,16,z),(43,20,z),r,96)
        drilled=enclosure.boolean(panel,cutter,'DIFFERENCE','Panel aperture '+name)
        mechanical.remove(cutter)
        panel.hide_render=True;panel.hide_set(True);parts.append(drilled);panel=drilled
    recessed=mechanical.cut_box(seated_body,'Body control cavity',(20,3.2,44),(43,16.1,44),.5)
    seated_body.hide_render=True;seated_body.hide_set(True);parts.append(recessed);seated_body=recessed
    shafts=[]
    for z,name in ((52,'MENU'),(62,'PLAY'),(35,'Select')):
        shafts.append(cylinder(name+' button shaft',(43,14.8,z),(43,18.4,z),1.5,black))
        ring(name+' guide sleeve',(43,14.4,z),1.0,2.3,1.7,panel_finish,(0,1,0))
        cylinder(name+' retaining flange',(43,15.55,z),(43,15.8,z),2.6,black)
    ring('Navigation carrier',(43,17.6,35),.8,7.9,3.7,black,(0,1,0))
    ring('Navigation rear guide',(43,14.4,35),3.2,8.2,8.0,panel_finish,(0,1,0))
    # Discard inherited custom normals from the baked bevel/boolean chain.
    # Flat shading prevents interpolation across coplanar drilled face triangles.
    panel_normals=[(0,0,0)]*len(panel.data.loops)
    for face in panel.data.polygons:
        face.use_smooth=False
        for index in face.loop_indices:panel_normals[index]=tuple(face.normal)
    panel.data.normals_split_custom_set(panel_normals)
    bottom=mechanical.cut_box(lower,'Lower cover hatch opening',(32,22,8),(-33,0,4),.35)
    lower.hide_render=True;lower.hide_set(True);parts.append(bottom)
    old_gasket=bpy.data.objects['Lower recessed gasket']
    gasket=mechanical.cut_box(old_gasket,'Lower gasket hatch opening',(32,22,3),(-33,0,7),1.2)
    old_gasket.hide_render=True;old_gasket.hide_set(True);parts.append(gasket)
    cutter=construction.strut('Tripod bore tool',(4,0,0),(4,0,5.9),2.5,64)
    socket_cover=enclosure.boolean(bottom,cutter,'DIFFERENCE','Lower cover with tripod bore')
    mechanical.remove(cutter)
    bottom.hide_render=True;bottom.hide_set(True);parts.append(socket_cover)
    for face in socket_cover.data.polygons:
        if abs(face.normal.z)>.999:face.use_smooth=False
    # Fixed rebate and pocket liner; the door gasket lands on this frame.
    rim_stock=box('Hatch seat stock',(33.2,23.2,.55),(-33,0,4.525),black,.2)
    hatch_seat=mechanical.cut_box(rim_stock,'Hatch seat rebate',(29.8,19.8,2),(-33,0,4.525),.7)
    rim_stock.hide_render=True;rim_stock.hide_set(True);parts.append(hatch_seat)
    liner_stock=box('Pocket liner stock',(31.8,21.8,17),(-33,0,15),black,1)
    liner=mechanical.cut_box(liner_stock,'Pocket liner',(30.8,20.8,17),(-33,0,14.5),.8)
    liner_stock.hide_render=True;liner_stock.hide_set(True);parts.append(liner)
    battery=box('Removable battery',(17,15,15),(-38,0,15.5),black,1)
    box('Battery release catch',(2.5,5,2),(-26.7,0,6),red,.5)
    box('Battery card divider',(.65,19,14),(-26.8,0,15),panel_finish,.2)
    box('Card socket',(2.8,16,15),(-21.5,0,14.5),black,.4)
    box('Memory card edge',(1.2,13,1.2),(-21.5,0,6.5),brass,.2)
    for y in (-5,0,5):box('Battery contact '+str(y),(1.5,2,.3),(-38,y,22.6),brass,.1)
    door_root=bpy.data.objects.new('Battery hatch hinge',None)
    scene.collection.objects.link(door_root);door_root.location=(-49,0,3.25)
    hatch_parts=[]
    hatch_parts.append(box('Battery and card hatch',(31.4,21.4,1.4),(-33,0,3.25),silver,.18))
    door_seal_stock=box('Door seal stock',(31,21,.3),(-33,0,4.1),rubber,.1)
    door_seal=mechanical.cut_box(door_seal_stock,'Door perimeter seal',(28.8,18.8,1),(-33,0,4.1),.4)
    door_seal_stock.hide_render=True;door_seal_stock.hide_set(True);parts.append(door_seal)
    hatch_parts.append(door_seal)
    hatch_parts.append(box('Hatch latch recess',(5,8,.4),(-21,0,2.45),black,.15))
    hatch_parts.append(box('Hatch lock slider',(3.5,4,.55),(-21,-1.5,2.25),black,.2))
    hatch_parts.append(box('Hatch inner face',(27,17,.35),(-33,0,4.12),panel_finish,.12))
    for y in (-6,6):hatch_parts.append(box('Hatch inner rib '+str(y),(24,1,.7),(-33,y,4.55),black,.2))
    # Alternating fixed and moving knuckles share the parent's true pivot axis.
    cylinder('Hatch hinge pin',(-49,-9.3,3.25),(-49,9.3,3.25),.45,silver)
    for i in range(5):
        knuckle=ring('Hatch hinge knuckle '+str(i),(-49,-9+i*3.6,3.25),3.2,.95,.5,silver,(0,1,0))
        if i%2:
            hatch_parts.append(knuckle)
            hatch_parts.append(box('Hatch hinge leaf '+str(i),(2.2,2.8,.6),(-48.2,-7.4+i*3.6,3.55),silver,.2))
        else:
            box('Fixed hinge leaf '+str(i),(2.2,2.8,.6),(-49.8,-7.4+i*3.6,3.55),silver,.2)
    latch_root=bpy.data.objects.new('Hatch latch slider',None)
    scene.collection.objects.link(latch_root);latch_root.location=(-21,-1.5,2.25)
    latch_tongue=box('Latch tongue',(2.6,3,1),(-18.1,0,4.85),silver,.2)
    receiver_stock=box('Latch receiver stock',(2.3,5,2.2),(-16.7,0,5),black,.3)
    receiver=mechanical.cut_box(receiver_stock,'Latch receiver slot',(3.5,3.4,1.3),(-17.5,0,4.85),.2)
    receiver_stock.hide_render=True;receiver_stock.hide_set(True);parts.append(receiver)
    bpy.context.view_layer.update()
    for obj in (bpy.data.objects['Hatch lock slider'],latch_tongue):
        world=obj.matrix_world.copy();obj.parent=latch_root;obj.matrix_world=world
        if obj in hatch_parts:hatch_parts.remove(obj)
    world=latch_root.matrix_world.copy();latch_root.parent=door_root;latch_root.matrix_world=world
    for obj in hatch_parts:
        world=obj.matrix_world.copy();obj.parent=door_root;obj.matrix_world=world
    # Rebuild face corner normals after body recess cuts to avoid broad
    # interpolation bands across the narrow remaining outer skin.
    body_normals=[(0,0,0)]*len(seated_body.data.loops)
    for face in seated_body.data.polygons:
        face.use_smooth=False
        for index in face.loop_indices:body_normals[index]=tuple(face.normal)
    seated_body.data.normals_split_custom_set(body_normals)
    # Bottom tripod socket is separate from the hatch.
    ring('Tripod socket',(4,0,2.45),1.3,4,2.5,silver,(0,0,1))
    # Focused static geometry check only, before adding the presentation floor.
    evaluated=bpy.context.evaluated_depsgraph_get()
    errors=[]
    for obj in parts:
        mesh=obj.evaluated_get(evaluated).to_mesh()
        if not len(mesh.polygons) or any(not math.isfinite(c) for v in mesh.vertices for c in v.co):
            errors.append(obj.name)
        obj.evaluated_get(evaluated).to_mesh_clear()
    if errors:raise ValueError('Invalid camera parts: '+str(errors))
    # Check the new opening and hatch in its two explicitly shown poses.
    from mathutils.bvhtree import BVHTree
    def tree(ob):
        return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],
                                   [list(f.vertices) for f in ob.data.polygons])
    opening_clear=all(tree(ob).ray_cast(Vector((-33,0,0)),Vector((0,0,1)),10)[0] is None
                      for ob in (seated_body,socket_cover,gasket,hatch_seat,liner))
    battery_access=tree(battery).ray_cast(Vector((-38,0,0)),Vector((0,0,1)),10)[0] is not None
    hatch_closed=tree(hatch_parts[0]).ray_cast(Vector((-33,0,0)),Vector((0,0,1)),10)[0] is not None
    panel_bores=all(tree(panel).ray_cast(Vector((x,16,z)),Vector((0,1,0)),5)[0] is None
                    for x,z in ((33,15),(53,15),(33,65),(53,65)))
    control_apertures=all(tree(panel).ray_cast(Vector((43,16,z)),Vector((0,1,0)),5)[0] is None
                          for z,_,_ in button_specs)
    shafts_clear=all(not tree(shaft).overlap(tree(panel)) and
                     not tree(shaft).overlap(tree(seated_body)) for shaft in shafts)
    guides_attached=all(tree(bpy.data.objects[name]).overlap(tree(seated_body))
                        for name in ('MENU guide sleeve','PLAY guide sleeve','Select guide sleeve',
                                     'Navigation rear guide'))
    # Negative check: an oversized shaft must intersect a real aperture wall.
    probe=construction.strut('Oversized button probe',(43,17,52),(43,19,52),3.5,96)
    oversized_rejected=bool(tree(probe).overlap(tree(panel)))
    mechanical.remove(probe)
    if not all((control_apertures,shafts_clear,oversized_rejected,guides_attached)):
        raise ValueError('Button aperture/shaft clearance or negative fit check failed')
    display_clear=not tree(display_frame).overlap(tree(display_glass))
    if not display_clear:raise ValueError('Inset display glass intersects bezel')
    latch_fits=not tree(latch_tongue).overlap(tree(receiver))
    def bounds(ob,axis):
        values=[(ob.matrix_world@v.co)[axis] for v in ob.data.vertices]
        return min(values),max(values)
    seal_contact=abs(bounds(door_seal,2)[1]-bounds(hatch_seat,2)[0])<1e-4
    panel_contact=abs(bounds(panel_gasket,1)[1]-bounds(panel,1)[0])<1e-4
    latch_root.location.x-=2
    bpy.context.view_layer.update()
    latch_released=bounds(latch_tongue,0)[1]<bounds(receiver,0)[0]
    door_root.rotation_euler[1]=math.radians(105)
    bpy.context.view_layer.update()
    hatch_open=tree(hatch_parts[0]).ray_cast(Vector((-33,0,0)),Vector((0,0,1)),10)[0] is None
    door_root.rotation_euler[1]=0
    latch_root.location.x+=2
    bpy.context.view_layer.update()
    if not all((opening_clear,battery_access,hatch_closed,hatch_open,panel_bores,
                latch_fits,latch_released,seal_contact,panel_contact)):
        raise ValueError('Panel seat, latch fit, seal contact or hatch opening failed: '+
                         str((opening_clear,battery_access,hatch_closed,hatch_open,panel_bores,
                              latch_fits,latch_released,seal_contact,panel_contact)))
    output.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'mesh_parts':len(parts),'finite_geometry':not errors,
            'scope':'Camera exterior, controls and battery/card hatch; two static hatch poses, not a motion sweep.',
            'threads':2,'renders':['front','rear-controls'],
            'opening_clear':opening_clear,'battery_access':battery_access,
            'closed_hatch_covers_opening':hatch_closed,'open_hatch_clears_opening':hatch_open,
            'hatch_angle_degrees':105,'button_radial_clearance_mm':.2,
            'control_apertures_open':control_apertures,'button_shafts_clear':shafts_clear,
            'guide_supports_attached':bool(guides_attached),
            'oversized_shaft_rejected':oversized_rejected,'shaft_radial_clearance_mm':.2,
            'display_glass_bezel_clear':display_clear,
            'panel_bores_open':panel_bores,'panel_gasket_contact':panel_contact,
            'door_seal_seat_contact':seal_contact,'latch_fits_receiver':latch_fits,
            'latch_releases_before_opening':latch_released}
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
    for view,pos,target,scale in [('front',(175,-260,155),(0,-8,42),185),
                                ('rear-controls',(-125,240,155),(0,4,48),160)]:
        if view=='hatch-open':
            floor.hide_render=True
            latch_root.location.x-=2
            door_root.rotation_euler[1]=math.radians(105)
            fill=bpy.data.objects['Fill'];fill.location=(-110,70,-100)
            fill.rotation_euler=(Vector((-35,0,0))-fill.location).to_track_quat('-Z','Y').to_euler()
            light=bpy.data.objects['Key'];light.location=(-60,-100,-130)
            light.rotation_euler=(Vector((-25,0,10))-light.location).to_track_quat('-Z','Y').to_euler()
            bpy.context.view_layer.update()
        camera(position=pos,target=target,scale=scale,size=(1000,800))
        scene.cycles.samples=32;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    door_root.rotation_euler[1]=0
    if view=='hatch-open':latch_root.location.x+=2
    print('CAMERA_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':
    build(sys.argv[sys.argv.index('--')+1])
