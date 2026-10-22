"""Focused readback of the two-flute bit and its stationary chuck contact."""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mesh_workbench import drillbit, nested


def verify(source, output):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    def obj(key):
        return bpy.data.objects[state['outputs'][key]['object']]
    def tree(ob):
        return BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices],
                                   [list(f.vertices) for f in ob.data.polygons])
    bit = obj('bit')
    points = [bit.matrix_world @ v.co for v in bit.data.vertices]
    edges = Counter(tuple(sorted((a,b))) for f in bit.data.polygons
                    for a,b in zip(list(f.vertices), list(f.vertices)[1:]+list(f.vertices)[:1]))
    shank = [p for p in points if 83 <= p.x <= 105 and math.hypot(p.y,p.z-160) > .1]
    shank_error = max(abs(math.hypot(p.y,p.z-160)-3) for p in shank)
    # Find the two channel minima independently of the stored metadata.
    # Ignore float32 radius jitter on the cylindrical lands (under 0.00001 mm).
    sections=[]
    for x in (115,131):
        station=min(points,key=lambda p:abs(p.x-x)).x
        ring=sorted([p for p in points if abs(p.x-station)<1e-4],
                    key=lambda p:math.atan2(p.z-160,p.y))
        radii=[math.hypot(p.y,p.z-160) for p in ring]
        minima=[i for i,r in enumerate(radii)
                if r<radii[i-1]-1e-4 and r<radii[(i+1)%len(radii)]-1e-4]
        sections.append(dict(x=station,minima=len(minima),minimum=min(radii),maximum=max(radii)))
    contacts=[]
    for i in range(3):
        angle=math.tau*i/3
        direction=Vector((0,math.cos(angle),math.sin(angle)))
        hit,normal,face,distance=tree(obj('jaw_'+str(i))).ray_cast(Vector((94,0,160)),direction,8)
        contacts.append(None if hit is None else distance)
    bit_tree=tree(bit)
    overlaps={key:len(bit_tree.overlap(tree(obj(key))))
              for key in ('chuck_body','jaw_cage','chuck_nose_support')}
    objects_before=set(bpy.data.objects)
    meshes_before=set(bpy.data.meshes)
    rejected=0
    for args in ({'radius':-1},{'pitch':0},{'segments':33}):
        try: drillbit.create('Rejected bit',**args)
        except ValueError: rejected+=1
    roughness=[m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value
               for m in bit.data.materials]
    report=dict(blender=bpy.app.version_string,nonmanifold_edges=sum(v!=2 for v in edges.values()),
        finite=all(math.isfinite(c) for p in points for c in p),shank_radius_error_mm=shank_error,
        sections=sections,jaw_contact_radius_mm=contacts,static_obstruction_overlaps=overlaps,
        material_roughness=roughness,rejected_invalid_dimensions=rejected,
        failure_preserved_scene=objects_before==set(bpy.data.objects) and meshes_before==set(bpy.data.meshes),
        source_preserved=digest==hashlib.sha256(source.read_bytes()).hexdigest(),
        scope='Bit geometry, stationary 6 mm jaw contact and nose clearance only; no motion or manufacturing certification.')
    report['passed']=(report['nonmanifold_edges']==0 and report['finite'] and shank_error<1e-4
        and all(s['minima']==2 and .9<s['minimum']<1.2 and abs(s['maximum']-3)<1e-4 for s in sections)
        and all(d is not None and abs(d-3)<1e-4 for d in contacts)
        and not any(overlaps.values()) and len(roughness)==2 and roughness[0]<roughness[1]
        and rejected==3 and report['failure_preserved_scene'] and report['source_preserved'])
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('TWIST_BIT_CHECK',json.dumps(report),flush=True)
    if not report['passed']:raise ValueError('Twist bit verification failed')


if __name__=='__main__':
    verify(*map(Path,sys.argv[sys.argv.index('--')+1:]))
