"""Procedural adult proportion study; neutral stance, no rig or fine anatomy.

blender -b --factory-startup -t 2 --python examples/human_base.py -- runs/human-base
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import sectionstock, models
from mesh_workbench.runner import camera


def build(output):
    output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    scene.render.threads_mode='FIXED';scene.render.threads=2
    sources=[]

    def material(name,color,roughness):
        m=bpy.data.materials.new(name);m.use_nodes=True
        bsdf=m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value=(*color,1)
        bsdf.inputs['Roughness'].default_value=roughness
        return m

    clay=material('Neutral sculpting clay',(.38,.43,.46),.65)

    def stock(name,rows):
        # Cubic interpolation through anatomical landmarks gives continuous
        # slopes; source sections remain independently editable in the blend.
        dense=[]
        for i in range(len(rows)-1):
            p0=rows[max(0,i-1)];p1=rows[i];p2=rows[i+1];p3=rows[min(len(rows)-1,i+2)]
            for step in range(5):
                t=step/5
                values=[p1[0]+(p2[0]-p1[0])*t]
                for k in range(1,5):
                    v=.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t*t+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t*t*t)
                    values.append(max(.003,v) if k>=3 else v)
                dense.append(values)
        dense.append(rows[-1])
        ob=sectionstock.create(name,dense,exponent=2,segments=64)
        ob.data.materials.append(clay);sources.append(ob)
        return ob

    stock('Source torso pelvis neck',[
        [.79,0,.018,.055,.055],[.85,0,.024,.114,.084],
        [.92,0,.026,.142,.106],[.98,0,.014,.145,.099],
        [1.04,0,-.003,.133,.085],[1.11,0,-.012,.123,.077],
        [1.18,0,-.006,.141,.09],[1.27,0,-.008,.164,.109],
        [1.35,0,-.003,.175,.10],[1.40,0,.005,.178,.081],
        [1.435,0,.012,.149,.065],[1.465,0,.015,.106,.052],
        [1.49,0,.014,.059,.042],[1.53,0,.018,.043,.038],
        [1.575,0,.018,.045,.041]])
    stock('Source cranium jaw',[
        [1.525,0,-.018,.028,.035],[1.54,0,-.013,.043,.063],
        [1.565,0,.005,.061,.069],[1.60,0,.009,.07,.081],
        [1.645,0,.014,.077,.091],[1.69,0,.017,.077,.09],
        [1.725,0,.017,.062,.074],[1.748,0,.017,.032,.039],
        [1.757,0,.017,.004,.005]])
    stock('Source nose bridge and tip',[
        [1.599,0,-.079,.009,.012],[1.61,0,-.079,.016,.018],
        [1.625,0,-.087,.013,.019],[1.643,0,-.077,.01,.014],
        [1.663,0,-.071,.011,.012],[1.675,0,-.065,.008,.008]])
    for sign,side in ((-1,'Left'),(1,'Right')):
        stock(side+' source leg',[
            [.075,sign*.103,.018,.031,.039],[.13,sign*.103,.018,.03,.034],
            [.19,sign*.104,.021,.035,.039],[.29,sign*.105,.027,.052,.059],
            [.37,sign*.104,.018,.055,.06],[.44,sign*.102,-.002,.044,.048],
            [.49,sign*.101,-.016,.047,.049],[.535,sign*.10,-.014,.049,.05],
            [.62,sign*.096,0,.064,.074],[.76,sign*.092,.012,.08,.091],
            [.88,sign*.087,.02,.083,.096],[.96,sign*.083,.02,.068,.078],
            [1.00,sign*.082,.018,.042,.047]])
        stock(side+' source foot',[
            [.008,sign*.103,-.055,.043,.112],[.027,sign*.103,-.055,.05,.13],
            [.06,sign*.103,-.047,.048,.125],[.095,sign*.103,0,.036,.067],
            [.125,sign*.103,.015,.029,.038]])
        stock(side+' source arm',[
            [.895,sign*.31,0,.026,.028],[.96,sign*.299,.003,.033,.035],
            [1.06,sign*.28,.006,.041,.044],[1.14,sign*.26,.012,.036,.038],
            [1.22,sign*.24,.013,.043,.047],[1.30,sign*.222,.008,.05,.054],
            [1.365,sign*.205,.005,.059,.063],[1.405,sign*.186,.006,.052,.054],
            [1.434,sign*.165,.01,.035,.036],[1.45,sign*.147,.012,.012,.016]])
        stock(side+' source hand',[
            [.755,sign*.337,-.005,.016,.015],[.79,sign*.332,-.006,.032,.022],
            [.845,sign*.322,-.004,.037,.025],[.885,sign*.314,0,.029,.026],
            [.915,sign*.307,0,.026,.027]])
        stock(side+' source thumb',[
            [.802,sign*.284,-.015,.012,.013],[.837,sign*.281,-.016,.016,.018],
            [.866,sign*.296,-.008,.02,.019]])

    def landmark(name,center,radii):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=center)
        ob=bpy.context.object;ob.name=name;ob.scale=radii
        ob.data.materials.append(clay);sources.append(ob)

    for sign,side in ((-1,'Left'),(1,'Right')):
        landmark(side+' kneecap',(sign*.101,-.057,.505),(.029,.016,.034))
        landmark(side+' outer ankle',(sign*.132,.012,.121),(.012,.019,.018))
        landmark(side+' inner ankle',(sign*.077,.009,.14),(.011,.017,.017))

    for sign,side in ((-1,'Left'),(1,'Right')):
        landmark(side+' ear mass',(sign*.077,.012,1.628),(.016,.021,.035))
    landmark('Muzzle plane',(0,-.063,1.579),(.027,.008,.014))
    landmark('Chin plane',(0,-.063,1.543),(.028,.019,.017))

    body=models.combine(sources,'Human base surface',voxel=.006)
    for source in sources:source.hide_render=True;source.hide_set(True)
    body.data.materials.clear();body.data.materials.append(clay)
    for face in body.data.polygons:face.material_index=0;face.use_smooth=True
    body.shape_key_add(name='Basis')
    landmarks=body.shape_key_add(name='Clavicle and shin landmarks')
    for vertex in landmarks.data:
        x,y,z=vertex.co
        # Broad, shallow relief follows front-facing skin, not detached rods.
        front=max(0,min(1,(-y-.012)/.025))
        clavicle=.005*math.exp(-((abs(x)-.09)/.065)**4-((z-(1.449-.14*abs(x)))/.015)**2)
        shin=.0035*math.exp(-((abs(x)-.103)/.018)**2-((z-.33)/.12)**4)
        vertex.co.y-=front*(clavicle+shin)
    landmarks.value=1
    facial=body.shape_key_add(name='Face planes and neck tendons')
    for vertex in facial.data:
        x,y,z=vertex.co
        front=max(0,min(1,(-y-.02)/.025))
        orbit=.010*math.exp(-((abs(x)-.031)/.019)**2-((z-1.645)/.013)**2)
        brow=.004*math.exp(-((abs(x)-.03)/.023)**2-((z-1.665)/.012)**2)
        mouth=.003*math.exp(-(x/.023)**4-((z-1.578)/.004)**2)
        cheek=.004*math.exp(-((abs(x)-.045)/.027)**2-((z-1.614)/.026)**2)
        vertex.co.y+=front*(orbit-brow+mouth-cheek)
        # Shallow anterior neck ridges from jaw toward the collarbone.
        ridge_x=.018+.34*(z-1.475)
        tendon=.003*math.exp(-((abs(x)-ridge_x)/.011)**2-((z-1.52)/.05)**4)
        vertex.co.y-=front*tendon
        if abs(x)>.072:
            concha=.004*math.exp(-((y-.003)/.011)**2-((z-1.63)/.02)**2)
            vertex.co.x-=math.copysign(concha,x)
    facial.value=1
    smooth=body.modifiers.new('Reversible surface smoothing','SMOOTH')
    smooth.factor=.65;smooth.iterations=5
    # Inspect generated geometry, not just successful operator return codes.
    dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);mesh=ev.to_mesh()
    coords=[body.matrix_world@v.co for v in mesh.vertices]
    if not coords or any(not math.isfinite(c) for v in coords for c in v):
        raise ValueError('Nonfinite or empty human surface')
    adjacency=[[] for _ in coords];uses={}
    for face in mesh.polygons:
        vs=list(face.vertices)
        for a,b in zip(vs,vs[1:]+vs[:1]):
            key=tuple(sorted((a,b)));uses[key]=uses.get(key,0)+1
            adjacency[a].append(b);adjacency[b].append(a)
    visited=set();components=0
    for start in range(len(coords)):
        if start in visited:continue
        components+=1;stack=[start];visited.add(start)
        while stack:
            for neighbor in adjacency[stack.pop()]:
                if neighbor not in visited:visited.add(neighbor);stack.append(neighbor)
    height=max(v.z for v in coords)-min(v.z for v in coords)
    closed=all(count==2 for count in uses.values())
    if components!=1 or not closed or not 1.70<height<1.78:
        raise ValueError('Disconnected, open or incorrectly scaled human base')
    # A narrow ray at the lower thigh must pass through the leg gap.
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromPolygons(coords,[list(f.vertices) for f in mesh.polygons])
    leg_gap=tree.ray_cast(Vector((0,-.4,.65)),Vector((0,1,0)),.8)[0] is None
    if not leg_gap:raise ValueError('Legs fused across intended gap')
    arm_gaps=all(tree.ray_cast(Vector((sign*.197,-.4,1.19)),Vector((0,1,0)),.8)[0] is None
                 for sign in (-1,1))
    knees=[]
    for sign in (-1,1):
        hit=tree.ray_cast(Vector((sign*.101,-.4,.505)),Vector((0,1,0)),.8)[0]
        knees.append(hit is not None and hit.y<-.066)
    if not arm_gaps or not all(knees):raise ValueError('Armpit clearance or kneecap relief lost')
    nose=tree.ray_cast(Vector((0,-.4,1.625)),Vector((0,1,0)),.8)[0]
    brow=tree.ray_cast(Vector((0,-.4,1.68)),Vector((0,1,0)),.8)[0]
    nose_projection=nose is not None and brow is not None and nose.y<brow.y-.02
    ear_width=max(abs(v.x) for v in coords if 1.61<v.z<1.65)
    if not nose_projection or ear_width<.083:
        raise ValueError('Nose projection or ear silhouette lost during fusion')
    report={'blender':bpy.app.version_string,'height_m':height,'source_parts':len(sources),
            'vertices':len(coords),'connected_components':components,'closed_edges':closed,
            'leg_gap_open':leg_gap,'arm_gaps_open':arm_gaps,'kneecap_relief_present':all(knees),
            'reversible_landmarks':True,'nose_projection_present':nose_projection,
            'ear_half_width_m':ear_width,'renders':['head-front','head-side'],'voxel_m':.006,'threads':2,
            'scope':'Adult head and neck plane study; no detailed eyes, lips, ear folds, fingers or rig.'}
    ev.to_mesh_clear()
    output.mkdir(parents=True)
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
    floor=bpy.context.object;floor.name='Studio floor'
    floor.data.materials.append(material('Studio floor material',(.06,.075,.085),.8))
    scene.world=bpy.data.worlds.new('Human study studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.18,.2,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    for name,pos,power,size in [('Key',(-2,-3,3.5),450,2.5),('Fill',(2,-1,2),85,2),('Rim',(1,2,3),350,2)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,0,.95))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera(position=(0,-4,1.56),target=(0,0,1.56),scale=.48,size=(800,900))
    scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'human-base.blend').resolve()))
    for view,pos in [('head-front',(0,-4,1.56)),('head-side',(4,0,1.56))]:
        camera(position=pos,target=(0,0,1.56),scale=.48,size=(800,900))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('HUMAN_BASE_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':build(sys.argv[sys.argv.index('--')+1])
