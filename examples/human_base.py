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
        [.79,0,.015,.055,.055],[.84,0,.015,.115,.08],
        [.94,0,.02,.15,.105],[1.02,0,.005,.14,.09],
        [1.11,0,0,.115,.075],[1.22,0,.004,.15,.10],
        [1.32,0,0,.178,.105],[1.40,0,.005,.19,.085],
        [1.44,0,.01,.16,.07],[1.48,0,.012,.08,.052],
        [1.52,0,.008,.047,.045],[1.57,0,0,.048,.045]])
    stock('Source head',[
        [1.52,0,-.02,.032,.035],[1.55,0,-.016,.053,.057],
        [1.61,0,-.003,.074,.082],[1.68,0,.003,.078,.085],
        [1.72,0,.006,.065,.07],[1.746,0,.006,.035,.04],
        [1.755,0,.006,.004,.005]])
    for sign,side in ((-1,'Left'),(1,'Right')):
        stock(side+' source leg',[
            [.075,sign*.103,.018,.033,.04],[.14,sign*.103,.015,.034,.04],
            [.26,sign*.104,.026,.052,.059],[.36,sign*.103,.018,.061,.065],
            [.46,sign*.102,-.012,.048,.05],[.52,sign*.102,-.017,.05,.052],
            [.64,sign*.098,.005,.068,.075],[.78,sign*.092,.008,.085,.092],
            [.91,sign*.087,.014,.083,.09],[.98,sign*.085,.015,.06,.065]])
        stock(side+' source foot',[
            [.008,sign*.103,-.055,.043,.112],[.027,sign*.103,-.055,.05,.13],
            [.06,sign*.103,-.047,.048,.125],[.095,sign*.103,0,.036,.067],
            [.125,sign*.103,.015,.029,.038]])
        stock(side+' source arm',[
            [.895,sign*.31,0,.026,.028],[.96,sign*.299,.003,.033,.035],
            [1.06,sign*.28,.006,.041,.044],[1.14,sign*.26,.012,.036,.038],
            [1.22,sign*.24,.01,.046,.05],[1.32,sign*.216,.006,.054,.058],
            [1.405,sign*.19,.004,.063,.062],[1.445,sign*.178,.005,.04,.045]])
        stock(side+' source hand',[
            [.755,sign*.337,-.005,.016,.015],[.79,sign*.332,-.006,.032,.022],
            [.845,sign*.322,-.004,.037,.025],[.885,sign*.314,0,.029,.026],
            [.915,sign*.307,0,.026,.027]])
        stock(side+' source thumb',[
            [.802,sign*.284,-.015,.012,.013],[.837,sign*.281,-.016,.016,.018],
            [.866,sign*.296,-.008,.02,.019]])

    body=models.combine(sources,'Human base surface',voxel=.006)
    for source in sources:source.hide_render=True;source.hide_set(True)
    body.data.materials.clear();body.data.materials.append(clay)
    for face in body.data.polygons:face.material_index=0;face.use_smooth=True
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
    report={'blender':bpy.app.version_string,'height_m':height,'source_parts':len(sources),
            'vertices':len(coords),'connected_components':components,'closed_edges':closed,
            'leg_gap_open':leg_gap,'voxel_m':.006,'threads':2,
            'scope':'Adult neutral proportion blockout; no detailed face, fingers, anatomy or rig.'}
    ev.to_mesh_clear()
    output.mkdir(parents=True)
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
    floor=bpy.context.object;floor.name='Studio floor'
    floor.data.materials.append(material('Studio floor material',(.06,.075,.085),.8))
    scene.world=bpy.data.worlds.new('Human study studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.18,.2,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    for name,pos,power,size in [('Key',(-2,-3,3.5),450,2.5),('Fill',(2,-1,2),170,2),('Rim',(1,2,3),350,2)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,0,.95))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera(position=(0,-4,.9),target=(0,0,.9),scale=1.3,size=(650,1000))
    scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str((output/'human-base.blend').resolve()))
    for view,pos in [('front',(0,-4,.9)),('side',(4,0,.9))]:
        camera(position=pos,target=(0,0,.9),scale=1.3,size=(650,1000))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((output/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('HUMAN_BASE_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':build(sys.argv[sys.argv.index('--')+1])
