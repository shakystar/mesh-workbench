"""Side-projected external-ear guides; no canal or detached cartilage geometry."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt


def compile_relief(obj,target,*,rim_mm=1.4,inner_mm=1,concha_mm=1.6):
    """Compile sampled-surface ear controls; authored relief, not cartilage inference."""
    rim,inner,concha=[sculpt.number(v,0,2.5,'ear relief') for v in (rim_mm,inner_mm,concha_mm)]
    guide=compile_ear(obj,target,tolerance_mm=.1)
    sign=-1 if target['side']=='negative_x' else 1
    half=guide['registration']['half_width_m'];p=guide['landmarks']
    points=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(points.tolist(),[list(f.vertices) for f in obj.data.polygons])
    # Add concavities between the named ridges. Locations and depth are authored.
    from .anatomy_fit import knowledge
    for name,feature in knowledge('auricle-v1')['relief_features'].items():
        a,b=feature['between']
        midpoint=(np.array(p[a])+p[b])/2
        hit=tree.ray_cast(Vector((sign*(abs(points[:,0]).max()+1),midpoint[1],midpoint[2])),Vector((-sign,0,0)))[0]
        if hit is None:raise ValueError('Ear concavity misses surface')
        p[name]=list(hit)
    controls=[]
    for name,point in p.items():
        if name.startswith('helix'):amount=rim
        elif name.startswith('anti'):amount=inner
        elif name.startswith('concha'):amount=-concha
        elif name.startswith('tragus'):amount=inner
        elif name.startswith('lobule'):amount=rim*.25
        else:amount=-concha*.4
        q=list(point);q[0]+=sign*amount/1000
        controls.append({'name':name,'source':point,'target':q})
    region=next(iter(guide['regions'].values()))
    return {'units':'m','label':target['side']+' auricle relief','surface_interpolation':True,
            'radius_mm':half*1000*.65,'max_displacement_mm':3,
            'region':{'min':region['min'],'max':region['max'],'feather_mm':region['feather']*1000},
            'controls':controls,'registration':guide['registration'],
            'limits':'Static lateral relief; no open canal, free rolled rim or cartilage thickness.'}


def apply_relief(source,targets,name='Auricle relief study',**options):
    """Apply one or two disjoint ears atomically; retain both reversible layers."""
    import bpy
    from . import curve_fit
    if not isinstance(targets,list) or not 1<=len(targets)<=2:
        raise ValueError('Expected one or two ear targets')
    if name in bpy.data.objects:raise ValueError('Output already exists')
    diagrams=[compile_relief(source,t,**options) for t in targets]
    if len(diagrams)==2:
        a,b=[d['region'] for d in diagrams]
        if np.all(np.maximum(a['min'],b['min'])<np.minimum(a['max'],b['max'])):
            raise ValueError('Ear edit regions overlap')
    made=[];reports=[];current=source
    try:
        for i,diagram in enumerate(diagrams):
            current,report=curve_fit.apply(current,diagram,name if i==len(diagrams)-1 else name+' intermediate')
            made.append(current);reports.append(report)
        for obj in made[:-1]:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        return current,diagrams,reports
    except Exception:
        for obj in reversed(made):
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise


def compile_surface_paths(obj,targets):
    """Compile continuous cubic ear paths for surface_brush on a refined snapshot.

    Named knowledge anchors determine the paths; amplitudes remain authored.
    Each path is projected to visible skin. No mesh edits occur during compilation.
    """
    if not isinstance(targets,list) or not 1<=len(targets)<=2:
        raise ValueError('Expected one or two ear targets')
    guides=[compile_ear(obj,t,tolerance_mm=.1) for t in targets]
    if len(guides)==2:
        a,b=[next(iter(g['regions'].values())) for g in guides]
        if np.all(np.maximum(a['min'],b['min'])<np.minimum(a['max'],b['max'])):
            raise ValueError('Ear edit regions overlap')
    points=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(points.tolist(),[list(f.vertices) for f in obj.data.polygons])
    diagram={'units':'m','landmarks':{},'regions':{},'registrations':[]};commands=[]
    settings=[(3.5,1.2),(2.6,1.0),(2.2,.5),(4.5,-1.5),(3.5,.35),(2.5,.7)]
    for guide in guides:
        side=guide['registration']['side'];sign=-1 if side=='negative_x' else 1
        diagram['regions'].update(guide['regions']);diagram['registrations'].append(guide['registration'])
        for row,(radius,depth) in zip(guide['paths'],settings):
            p=np.asarray([guide['landmarks'][a] for a in row['anchors']])
            padded=np.vstack([2*p[0]-p[1],p,2*p[-1]-p[-2]])
            samples=[]
            for i in range(len(p)-1):
                a,b,c,d=padded[i:i+4]
                for t in np.linspace(0,1,8,endpoint=False):
                    samples.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            samples.append(p[-1]);keys=[]
            for i,sample in enumerate(samples):
                hit=tree.ray_cast(Vector((sign*(abs(points[:,0]).max()+1),sample[1],sample[2])),Vector((-sign,0,0)))[0]
                if hit is None:raise ValueError('Cubic ear path misses surface')
                key=row['label']+'_'+str(i);diagram['landmarks'][key]=list(hit);keys.append(key)
            commands.append({'label':row['label'],'mode':'ridge' if depth>0 else 'crease',
                'anchors':keys,'region':row['region'],'view_direction':[-sign,0,0],
                'radius_mm':radius,'distance_mm':abs(depth),'max_displacement_mm':abs(depth)+.1})
        # Fair the ridge/skin collar after the six shaping paths. All coordinates
        # are reprojected by the brush; the source and opposite side stay protected.
        helix=commands[-6]
        commands.append({'label':side+' ridge collar','mode':'relax_volume',
            'anchors':helix['anchors'],'region':helix['region'],'view_direction':[-sign,0,0],
            'radius_mm':6,'strength':.35,'iterations':6,'max_displacement_mm':1})
    return diagram,commands


def compile_ear(obj,target,*,relief=1,tolerance_mm=5):
    from .anatomy_fit import knowledge
    sculpt.editable(obj)
    if target.get('units')!='m':raise ValueError('Target units must be metres')
    side=target.get('side')
    if side not in ('negative_x','positive_x'):raise ValueError('Specify ear diagram side')
    sign=-1 if side=='negative_x' else 1
    midline=sculpt.number(target.get('midline_x',0),-100,100,'midline X')
    relief=sculpt.number(relief,.5,1.5,'relief')
    tolerance=sculpt.number(tolerance_mm,.01,10,'target tolerance')
    kb=knowledge('auricle-v1');points={}
    for name in kb['required_target_landmarks']:
        p=np.asarray(target.get('landmarks',{}).get(name),dtype=float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ ear reference required: '+name)
        if sign*(p[0]-midline)<=0:raise ValueError('Ear reference is on the wrong side')
        points[name]=p
    a,b=points['anterior'],points['posterior'];half=(b[1]-a[1])/2
    center=(a+b)/2
    upper=points['superior'][2]-center[2];lower=center[2]-points['inferior'][2]
    if not .004<=half<=.03 or not .008<=upper<=.05 or not .008<=lower<=.05:
        raise ValueError('Unsupported ear width/height or inverted references')
    if abs(a[2]-b[2])>half*.1:raise ValueError('Align anterior/posterior reference heights')
    if any(abs(points[n][1]-center[1])>half*.25 for n in ('superior','inferior')):
        raise ValueError('Upper/lower references must align near ear center')
    original=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(original.tolist(),[list(p.vertices) for p in obj.data.polygons])
    ray_x=float(original[:,0].max()+1 if sign>0 else original[:,0].min()-1)
    def project(y,z):
        hit=tree.ray_cast(Vector((ray_x,float(y),float(z))),Vector((-sign,0,0)))[0]
        if hit is None or sign*(hit.x-midline)<=0:raise ValueError('Ear guide misses the selected side surface')
        return np.asarray(hit)
    residuals={}
    for name,p in points.items():
        residuals[name]=float(np.linalg.norm(project(p[1],p[2])-p)*1000)
        if residuals[name]>tolerance:raise ValueError('Ear reference off visible surface: '+name)
    landmarks={name:project(center[1]+u*half,center[2]+v*(upper if v>=0 else lower)).tolist()
               for name,(u,v) in kb['landmarks_uv'].items()}
    xyz=np.array(list(landmarks.values()));margin=half*.2
    lo=xyz.min(axis=0)-[half*.5,margin,margin];hi=xyz.max(axis=0)+[half*.5,margin,margin]
    if (sign<0 and hi[0]>=midline) or (sign>0 and lo[0]<=midline):raise ValueError('Ear bounds cross midline')
    region='ear_'+side;view='side_'+side;paths=[]
    for row in kb['paths']:
        cmd={k:v for k,v in row.items() if not k.endswith('_half_width_ratio')}
        cmd.update(region=region,view=view,label=side+' '+cmd['label'])
        for name in ('radius','distance','max_displacement'):
            cmd[name+'_mm']=row[name+'_half_width_ratio']*half*1000*(relief if name!='radius' else 1)
        if cmd['radius_mm']>30 or cmd['max_displacement_mm']>5:raise ValueError('Scaled ear brush exceeds limits')
        for n,m in zip(cmd['anchors'][:-1],cmd['anchors'][1:]):
            p,q=np.array(landmarks[n]),np.array(landmarks[m])
            count=max(2,int(np.ceil(np.linalg.norm((q-p)[[1,2]])/.0005))+1)
            for t in np.linspace(0,1,count):
                r=p+(q-p)*t;hit=project(r[1],r[2])
                if np.any(hit<lo) or np.any(hit>hi):raise ValueError('Ear path leaves depth envelope')
        paths.append(cmd)
    return {'units':'m','landmarks':landmarks,'regions':{region:{'min':lo.tolist(),'max':hi.tolist(),
            'feather':min(half*.08,float(np.min(hi-lo))*.2)}},'paths':paths,
            'registration':{'knowledge_id':kb['id'],'schema_version':kb['schema_version'],'target':target,
                'side':side,'view':view,'half_width_m':float(half),'upper_span_m':float(upper),
                'lower_span_m':float(lower),'target_residual_mm':residuals,'relief':relief,
                'topology':sculpt.topology(obj),'matrix':[list(r) for r in obj.matrix_world],
                'limits':'Side-surface relief only; no ear canal, free rim or cartilage thickness.'}}
