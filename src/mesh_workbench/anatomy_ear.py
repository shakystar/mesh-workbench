"""Side-projected external-ear guides; no canal or detached cartilage geometry."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt


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
