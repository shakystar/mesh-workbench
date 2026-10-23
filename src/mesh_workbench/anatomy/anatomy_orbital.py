"""Front-visible periorbital registration using a canthal axis for each eye."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import sculpt


def compile_orbital(obj,target,*,relief=1,tolerance_mm=5):
    from .anatomy_fit import knowledge
    sculpt.editable(obj)
    if target.get('units')!='m':raise ValueError('Target units must be metres')
    side=target.get('side')
    if side not in ('negative_x','positive_x'):raise ValueError('Specify diagram side negative_x or positive_x')
    sign=-1 if side=='negative_x' else 1
    midline=sculpt.number(target.get('midline_x',0),-100,100,'midline X')
    relief=sculpt.number(relief,.5,1.5,'relief multiplier')
    tolerance=sculpt.number(tolerance_mm,.01,10,'target tolerance')
    kb=knowledge('periorbital-v1');points={}
    for name in kb['required_target_landmarks']:
        p=np.asarray(target.get('landmarks',{}).get(name),dtype=float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ reference required: '+name)
        points[name]=p
    medial,lateral=points['medial_canthus'],points['lateral_canthus']
    if not 0<sign*(medial[0]-midline)<sign*(lateral[0]-midline):
        raise ValueError('Canthi must be ordered from midline to lateral on the named side')
    axis=(lateral-medial)[[0,2]];half=np.linalg.norm(axis)/2
    if not .005<=half<=.03:raise ValueError('Supported eye half-width is 5..30 mm')
    axis/=2*half
    if abs(axis[1])>.35:raise ValueError('Canthal tilt exceeds this front-guide range')
    up=np.array([-axis[1],axis[0]])
    if up[1]<0:up=-up
    center=(medial+lateral)/2;uvcenter=center[[0,2]]
    upper=np.dot((points['upper_lid']-center)[[0,2]],up)
    lower=-np.dot((points['lower_lid']-center)[[0,2]],up)
    if not .001<=upper<=.02 or not .001<=lower<=.02:
        raise ValueError('Upper/lower lid references must bracket the canthal axis')
    for name in ('upper_lid','lower_lid'):
        if abs(np.dot((points[name]-center)[[0,2]],axis))>half*.15:
            raise ValueError('Lid midpoint must align near the canthal-axis center')
    original=sculpt.coordinates(obj)
    tree=BVHTree.FromPolygons(original.tolist(),[list(p.vertices) for p in obj.data.polygons])
    ray_y=float(original[:,1].min()-1)
    def project(xz):
        hit=tree.ray_cast(Vector((float(xz[0]),ray_y,float(xz[1]))),Vector((0,1,0)))[0]
        if hit is None:raise ValueError('Periorbital guide misses visible surface')
        return np.asarray(hit)
    residuals={}
    for name,p in points.items():
        residuals[name]=float(np.linalg.norm(project(p[[0,2]])-p)*1000)
        if residuals[name]>tolerance:raise ValueError('Reference off visible surface: '+name)
    landmarks={name:project(uvcenter+axis*u*half+up*v*(upper if v>=0 else lower)).tolist()
               for name,(u,v) in kb['landmarks_uv'].items()}
    for name in kb['required_target_landmarks']:
        landmarks[name]=project(points[name][[0,2]]).tolist()
    xyz=np.array(list(landmarks.values()));margin=half*.18
    lo=xyz.min(axis=0)-[margin,half*.5,margin]
    hi=xyz.max(axis=0)+[margin,half*.5,margin]
    if (side=='negative_x' and hi[0]>=midline) or (side=='positive_x' and lo[0]<=midline):
        raise ValueError('Eye edit bounds cross the facial midline')
    region='eye_'+side;paths=[]
    for row in kb['paths']:
        command={k:v for k,v in row.items() if not k.endswith('_half_width_ratio')}
        command['region']=region;command['label']=side+' '+command['label']
        for name in ('radius','distance','max_displacement'):
            command[name+'_mm']=row[name+'_half_width_ratio']*half*1000*(relief if name!='radius' else 1)
        if command['radius_mm']>30 or command['max_displacement_mm']>5:
            raise ValueError('Scaled eye brush exceeds supported limits')
        for a,b in zip(command['anchors'][:-1],command['anchors'][1:]):
            p,q=np.array(landmarks[a])[[0,2]],np.array(landmarks[b])[[0,2]]
            count=max(2,int(np.ceil(np.linalg.norm(q-p)/.0005))+1)
            for t in np.linspace(0,1,count):
                hit=project(p+(q-p)*t)
                if np.any(hit<lo) or np.any(hit>hi):raise ValueError('Eye path leaves registered depth envelope')
        paths.append(command)
    return {'units':'m','landmarks':landmarks,'regions':{region:{'min':lo.tolist(),'max':hi.tolist(),
                'feather':min(half*.06,float(np.min(hi-lo))*.2)}},'paths':paths,
        'registration':{'knowledge_id':kb['id'],'schema_version':kb['schema_version'],'target':target,
            'half_width_m':float(half),'upper_span_m':float(upper),'lower_span_m':float(lower),
            'canthal_axis_xz':axis.tolist(),'side':side,'relief':relief,'target_residual_mm':residuals,
            'topology':sculpt.topology(obj),'matrix':[list(r) for r in obj.matrix_world],
            'limits':'Surface guides only; no eyeball, open lid aperture or orbital cavity.'}}
