"""Fit authored proportional regional guides to manually identified landmarks.

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
    output,diagrams,reports=apply_many(obj,[target],name,**options)
    return output,diagrams[0],reports


def apply_many(obj, targets, name, **options):
    """Apply disjoint regions to one snapshot; all regions remain reversible.

    Returns (object, diagrams, reports). All registrations are retained; the last
    diagram is the active brush binding. Rebind another diagram before extending it.
    """
    from . import anatomy
    if not isinstance(targets,list) or not 1<=len(targets)<=8:
        raise ValueError('Expected 1..8 regional targets')
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
        diagrams=[compile_diagram(output,target,**options) for target in targets]
        bounds=[next(iter(d['regions'].values())) for d in diagrams]
        for i,a in enumerate(bounds):
            for b in bounds[:i]:
                if np.all(np.maximum(a['min'],b['min'])<np.minimum(a['max'],b['max'])):
                    raise ValueError('Regional edit bounds overlap; apply separately with explicit review')
        reports=[]
        for diagram in diagrams:
            anatomy.bind(output,diagram)
            reports.extend(anatomy.path_stroke(output,command) for command in diagram['paths'])
        output['mw_anatomy_fit']=json.dumps(diagrams[-1]['registration'])
        output['mw_anatomy_fits']=json.dumps([d['registration'] for d in diagrams])
        return output,diagrams,reports
    except Exception:
        bpy.data.objects.remove(output,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise


def knowledge(module_id='oral-neutral-v1'):
    if module_id not in ('oral-neutral-v1','nasal-base-v1','periorbital-v1','auricle-v1'):
        raise ValueError('Unknown anatomy knowledge module')
    return json.loads(files('mesh_workbench').joinpath('knowledge/'+module_id+'.json').read_text())


def compile_diagram(obj, target, *, bow_width=1.0, relief=1.0, tolerance_mm=5):
    """Return a bindable diagram and scaled paths; fail without changing state.

    Target units are metres, front faces -Y, Z is up. Left/right mean diagram
    negative/positive X. Required targets must lie near the visible surface.
    """
    if target.get('knowledge_id')=='auricle-v1':
        from .anatomy_ear import compile_ear
        if bow_width!=1:raise ValueError('bow_width applies only to the oral module')
        return compile_ear(obj,target,relief=relief,tolerance_mm=tolerance_mm)
    if target.get('knowledge_id')=='periorbital-v1':
        from .anatomy_orbital import compile_orbital
        if bow_width!=1:raise ValueError('bow_width applies only to the oral module')
        return compile_orbital(obj,target,relief=relief,tolerance_mm=tolerance_mm)
    sculpt.editable(obj)
    if target.get('units')!='m':raise ValueError('Target units must be metres')
    bow_width=sculpt.number(bow_width,.7,1.3,'bow width multiplier')
    relief=sculpt.number(relief,.5,1.5,'relief multiplier')
    tolerance=sculpt.number(tolerance_mm,.01,10,'target tolerance')/1000
    kb=knowledge(target.get('knowledge_id','oral-neutral-v1'))
    nasal=kb['id']=='nasal-base-v1'
    if nasal and bow_width!=1:raise ValueError('bow_width applies only to the oral module')
    points={}
    for name in kb['required_target_landmarks']:
        if name not in target.get('landmarks',{}):raise ValueError('Missing target landmark: '+name)
        p=np.asarray(target['landmarks'][name],dtype=float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ target required')
        points[name]=p
    left_name,right_name=('ala_left','ala_right') if nasal else ('corner_left','corner_right')
    left,right=points[left_name],points[right_name]
    half=(right[0]-left[0])/2
    if not .005<=half<=.06:raise ValueError('Supported regional half-width is 5..60 mm')
    if abs(right[2]-left[2])>half*.05:raise ValueError('Align lateral landmarks horizontally before fitting')
    center=points['nose_base'].copy() if nasal else (left+right)/2
    upper_name,lower_name=('nose_tip','philtrum_top') if nasal else ('nose_base','chin_fold')
    upper=points[upper_name][2]-center[2]
    lower=center[2]-points[lower_name][2]
    if not .003<=upper<=.08 or not .003<=lower<=.08:
        raise ValueError('Upper and lower references must bracket the regional center')
    if any(abs(points[n][0]-center[0])>half*.15 for n in (upper_name,lower_name)):
        raise ValueError('Central target landmarks must align with the regional center')
    link=None
    if nasal:
        if abs((left[0]+right[0])/2-center[0])>half*.15:
            raise ValueError('Nose base must align with the alar midpoint')
        if not all(center[2]<=p[2]<=points['nose_tip'][2] for p in (left,right)):
            raise ValueError('Alar references must lie between nose base and tip heights')
        link=target.get('linked_oral_target')
        if link is not None:
            if link.get('units')!='m':raise ValueError('Linked oral target units must be metres')
            linked=link.get('landmarks',{})
            for key in ('nose_base','corner_left','corner_right'):
                p=np.asarray(linked.get(key),dtype=float)
                if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Invalid linked oral reference')
            if np.linalg.norm(np.asarray(linked['nose_base'])-center)>.0001:
                raise ValueError('Shared nose-base references disagree by more than 0.1 mm')
            mouth_z=(linked['corner_left'][2]+linked['corner_right'][2])/2
            if not mouth_z<points['philtrum_top'][2]<center[2]:
                raise ValueError('Philtrum reference must lie between mouth and nose base')
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
    for name in (left_name,right_name):
        landmarks[name]=project(points[name][0],points[name][2]).tolist()
    xyz=np.array(list(landmarks.values()))
    margin=half*.20
    lo=xyz.min(axis=0)-[margin,half*.5,margin]
    hi=xyz.max(axis=0)+[margin,half*.5,margin]
    if nasal:lo[2]=center[2]  # Upper lip and existing oral edits stay protected.
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
    region_name='nasal_base' if nasal else 'mouth'
    return {'units':'m','landmarks':landmarks,
            'regions':{region_name:{'min':lo.tolist(),'max':hi.tolist(),'feather':feather}},
            'paths':paths,'registration':{'knowledge_id':kb['id'],'schema_version':kb['schema_version'],
                'target':target,'half_width_m':float(half),'upper_span_m':float(upper),'lower_span_m':float(lower),
                'bow_width':bow_width,'relief':relief,'target_residual_mm':residuals,
                'shared_oral_reference_checked':link is not None,
                'topology':sculpt.topology(obj),'matrix':[list(r) for r in obj.matrix_world],
                'limits':'Manual front-view registration; authored ratios, not anatomical validation.'}}
