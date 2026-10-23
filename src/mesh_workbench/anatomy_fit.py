"""Fit an authored proportional oral guide to manually identified surface landmarks.

No landmark detection or demographic inference. Compilation never mutates a mesh.
"""
import json
from importlib.resources import files
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt


def apply(obj, target, name, **options):
    """Create a new evaluated snapshot and apply all paths atomically.

    The input object's geometry, layers, visibility and registration stay intact.
    Failure removes the new object; no partially applied output is retained.
    """
    from . import anatomy
    if name in bpy.data.objects:raise ValueError('Output object exists')
    if obj.type!='MESH' or obj.animation_data or obj.get('mw_pending'):
        raise ValueError('Expected idle static mesh')
    if obj.data.shape_keys and obj.data.shape_keys.animation_data:
        raise ValueError('Animated shape keys unsupported')
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(graph),depsgraph=graph)
    output=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(output);output.matrix_world=obj.matrix_world.copy()
    try:
        diagram=compile_diagram(output,target,**options)
        anatomy.bind(output,diagram)
        reports=[anatomy.path_stroke(output,command) for command in diagram['paths']]
        output['mw_anatomy_fit']=json.dumps(diagram['registration'])
        return output,diagram,reports
    except Exception:
        bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise


def knowledge():
    return json.loads(files('mesh_workbench').joinpath('knowledge/oral-neutral-v1.json').read_text())


def compile_diagram(obj, target, *, bow_width=1.0, relief=1.0, tolerance_mm=5):
    """Return a bindable diagram and scaled paths; fail without changing state.

    Target units are metres, front faces -Y, Z is up. Left/right mean diagram
    negative/positive X. Four targets must lie near this object's visible surface.
    """
    sculpt.editable(obj)
    if target.get('units')!='m':raise ValueError('Target units must be metres')
    bow_width=sculpt.number(bow_width,.7,1.3,'bow width multiplier')
    relief=sculpt.number(relief,.5,1.5,'relief multiplier')
    tolerance=sculpt.number(tolerance_mm,.01,10,'target tolerance')/1000
    kb=knowledge()
    points={}
    for name in kb['required_target_landmarks']:
        if name not in target.get('landmarks',{}):raise ValueError('Missing target landmark: '+name)
        p=np.asarray(target['landmarks'][name],dtype=float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ target required')
        points[name]=p
    left,right=points['corner_left'],points['corner_right']
    half=(right[0]-left[0])/2
    if not .005<=half<=.06:raise ValueError('Supported mouth half-width is 5..60 mm')
    if abs(right[2]-left[2])>half*.05:raise ValueError('Align mouth corners horizontally before fitting')
    center=(left+right)/2
    upper=points['nose_base'][2]-center[2]
    lower=center[2]-points['chin_fold'][2]
    if not .003<=upper<=.08 or not .003<=lower<=.08:
        raise ValueError('Nose base must be above and chin fold below mouth')
    if any(abs(points[n][0]-center[0])>half*.15 for n in ('nose_base','chin_fold')):
        raise ValueError('Central target landmarks must align with the mouth center')
    original=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(original.tolist(),[list(f.vertices) for f in obj.data.polygons])
    ray_y=float(original[:,1].min()-1)
    def project(x,z):
        hit=tree.ray_cast(Vector((float(x),ray_y,float(z))),Vector((0,1,0)))[0]
        if hit is None:raise ValueError('Registered diagram misses target surface')
        return np.asarray(hit)
    residuals={}
    for name,p in points.items():
        residuals[name]=float(np.linalg.norm(project(p[0],p[2])-p)*1000)
        if residuals[name]>tolerance*1000:raise ValueError('Target landmark is off visible surface: '+name)
    landmarks={}
    for name,(u,v) in kb['landmarks_uv'].items():
        if name in ('bow_left','bow_right'):u*=bow_width
        landmarks[name]=project(center[0]+u*half,center[2]+v*(upper if v>=0 else lower)).tolist()
    # Preserve the measured corner heights instead of flattening accepted small offsets.
    for name in ('corner_left','corner_right'):
        landmarks[name]=project(points[name][0],points[name][2]).tolist()
    xyz=np.array(list(landmarks.values()))
    margin=half*.20
    lo=xyz.min(axis=0)-[margin,half*.5,margin]
    hi=xyz.max(axis=0)+[margin,half*.5,margin]
    feather=min(half*.08,float(np.min(hi-lo))*.2)
    paths=[]
    for row in kb['paths']:
        command={k:v for k,v in row.items() if not k.endswith('_half_width_ratio')}
        for name in ('radius','distance','max_displacement'):
            command[name+'_mm']=row[name+'_half_width_ratio']*half*1000*(relief if name!='radius' else 1)
        if command['radius_mm']>30 or command['max_displacement_mm']>5:
            raise ValueError('Scaled brush exceeds supported limits')
        # Validate complete centerlines now, before binding or applying any path.
        for a,b in zip(command['anchors'][:-1],command['anchors'][1:]):
            p,q=np.array(landmarks[a]),np.array(landmarks[b])
            n=max(2,int(np.ceil(np.linalg.norm((q-p)[[0,2]])/.0005))+1)
            for t in np.linspace(0,1,n):
                r=p+(q-p)*t;hit=project(r[0],r[2])
                if np.any(hit<lo) or np.any(hit>hi):raise ValueError('Path leaves registered depth envelope')
        paths.append(command)
    return {'units':'m','landmarks':landmarks,
            'regions':{'mouth':{'min':lo.tolist(),'max':hi.tolist(),'feather':feather}},
            'paths':paths,'registration':{'knowledge_id':kb['id'],'schema_version':kb['schema_version'],
                'target':target,'half_width_m':float(half),'upper_span_m':float(upper),'lower_span_m':float(lower),
                'bow_width':bow_width,'relief':relief,'target_residual_mm':residuals,
                'topology':sculpt.topology(obj),'matrix':[list(r) for r in obj.matrix_world],
                'limits':'Manual front-view registration; authored ratios, not anatomical validation.'}}
