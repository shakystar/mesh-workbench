"""Local procedural five-digit hand stock; attachment remains explicit."""
import json
from importlib.resources import files
import bpy
from .. import sectionstock,models,sculpt

def build(name='Hand stock',scale=1,side=1):
    scale=sculpt.number(scale,.7,1.4,'hand scale')
    if side not in (-1,1):raise ValueError('Hand side must be -1 or 1')
    if name in bpy.data.objects:raise ValueError('Output exists')
    kb=json.loads(files('mesh_workbench').joinpath('knowledge/hand-structure-v1.json').read_text())
    objects,meshes=set(bpy.data.objects),set(bpy.data.meshes)
    parts=[]
    def stock(label,rows):
        rows=[[z*scale,x*side*scale,y*scale,rx*scale,ry*scale] for z,x,y,rx,ry in rows]
        dense=[]
        for i in range(len(rows)-1):
            p0,p1,p2,p3=rows[max(0,i-1)],rows[i],rows[i+1],rows[min(len(rows)-1,i+2)]
            for step in range(5):
                t=step/5;values=[p1[0]+(p2[0]-p1[0])*t]
                for j in range(1,5):
                    value=.5*(2*p1[j]+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t*t*t)
                    values.append(max(.001*scale,value) if j>=3 else value)
                dense.append(values)
        dense.append(rows[-1])
        obj=sectionstock.create(name+' '+label,dense,exponent=2,segments=32);parts.append(obj)
        return obj
    try:
        stock('palm',[[.815,0,0,.032,.013],[.835,0,-.001,.036,.017],
            [.865,-.002,0,.031,.019],[.89,0,.001,.025,.020],[.91,0,.002,.026,.022]])
        for i,(x,length,radius) in enumerate(zip(kb['finger_centers'],kb['finger_lengths'],kb['finger_radii'])):
            tip=.825-length;rows=[]
            for t,r in ((0,.18),(.07,.8),(.22,.94),(.34,1.04),(.50,.94),(.64,1.08),(.82,1),(1,1.08)):
                z=tip+length*t;rows.append([z,x+x*.10*(1-t),-.002-.004*(1-t),radius*r,radius*.84*r])
            stock('digit '+str(i+2),rows)
        stock('thumb',[[.785,-.059,-.012,.0015,.002],[.791,-.059,-.012,.007,.0065],
            [.809,-.052,-.012,.009,.008],[.824,-.044,-.009,.010,.009],
            [.846,-.027,-.005,.015,.014],[.864,-.019,0,.016,.016]])
        result=models.combine(parts,name,voxel=.001*scale)
        result['mw_hand_structure']=json.dumps(kb);result['mw_attachment']='Closed proximal cap; not grafted to body'
        for obj in parts:obj.hide_render=True;obj.hide_set(True)
        return result,parts
    except Exception:
        for obj in set(bpy.data.objects)-objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in set(bpy.data.meshes)-meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise


def compile_palm(source,side,center_x):
    """Authored palm cupping/web arch on this upright hand frame; metres."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sculpt.editable(source)
    if side not in (-1,1):raise ValueError('Hand side must be -1 or 1')
    center_x=sculpt.number(center_x,-2,2,'palm center')
    if center_x*side<=0:raise ValueError('Palm center must match side')
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[]
    for view in (-1,1):
        for iz,z in enumerate((.820,.835,.850,.865)):
            for ix,u in enumerate((-.024,-.012,0,.012,.024)):
                x=center_x+side*(u+.2*(.85-z))
                hit=tree.ray_cast(Vector((x,view,z)),Vector((0,-view,0)))[0]
                if hit is None:raise ValueError('Palm reference misses visible skin')
                a=np.asarray(hit);b=a.copy()
                arch=(0,-2,-1,2,5)[ix]/1000
                b[2]+=arch*(1,.5,.12,0)[iz]
                # Palm hollow between lateral pads; dorsal surface stays shallow.
                depth=((.5,.1,-1.3,.2,.6)[ix] if view==-1 else -.3)*(0.5,1,1,.25)[iz]/1000
                b[1]+=view*depth
                controls.append({'name':f'palm_{view}_{iz}_{ix}','source':a.tolist(),'target':b.tolist()})
    xs=sorted((center_x-side*.045,center_x+side*.045))
    return {'units':'m','label':'palm '+str(side),'surface_interpolation':True,
        'radius_mm':24,'max_displacement_mm':8,'controls':controls,
        'region':{'min':[xs[0],-.07,.800],'max':[xs[1],.07,.878],'feather_mm':6},
        'registration':{'side':side,'center_x':center_x},
        'limits':'Authored skin hollow and web arch; not measured joint or muscle positions.'}


def apply_palms(source,centers,name='Palm shaped study',profile='palm'):
    from .. import curve_fit
    if name in bpy.data.objects:raise ValueError('Output exists')
    if len(centers)!=2:raise ValueError('Two palm centers required')
    if profile not in ('palm','thumb','fingers'):raise ValueError('Unknown hand profile')
    compiler={'palm':compile_palm,'thumb':compile_thumb_outline,'fingers':compile_fingers}[profile]
    diagrams=[compiler(source,side,center) for side,center in zip((-1,1),centers)]
    a,b=[d['region'] for d in diagrams]
    if a['max'][0]>=b['min'][0]:raise ValueError('Palm regions overlap')
    created=[];reports=[];current=source
    def remove(obj):
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    try:
        for i,diagram in enumerate(diagrams):
            current,report=curve_fit.apply(current,diagram,name if i else name+' temporary')
            created.append(current);reports.append(report)
        remove(created.pop(0));current['mw_source']=source.name
        return current,diagrams,reports
    except Exception:
        for obj in reversed(created):remove(obj)
        raise


def compile_transitions(source,centers):
    """Registered palm/thumb fairing paths, keeping wrist and fingertip zones out."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sculpt.editable(source)
    if len(centers)!=2:raise ValueError('Two palm centers required')
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    diagram={'units':'m','landmarks':{},'regions':{}};commands=[]
    for side,center in zip((-1,1),centers):
        center=sculpt.number(center,-2,2,'hand center')
        if center*side<=0:raise ValueError('Palm center must match side')
        for view in (-1,1):
            for part,rows,radius in [('thumb',((-.035,.85),(-.029,.858),(-.024,.867),(-.018,.875)),12),
                                     ('palm',((-.020,.835),(-.010,.835),(0,.835),(.010,.837),(.022,.840)),18)]:
                name=f'{part} transition {side} {view}';keys=[]
                for i,(u,z) in enumerate(rows):
                    x=center+side*(u+.2*(.85-z))
                    hit=tree.ray_cast(Vector((x,view,z)),Vector((0,-view,0)))[0]
                    if hit is None:raise ValueError('Transition path misses surface')
                    key=name+' '+str(i);diagram['landmarks'][key]=list(hit);keys.append(key)
                xs=sorted((center-side*.065,center+side*.045))
                diagram['regions'][name]={'min':[xs[0],-.07,.812],'max':[xs[1],.07,.883],'feather':.003}
                commands.append({'mode':'relax_volume','label':name,'region':name,'anchors':keys,
                    'view_direction':[0,-view,0],'radius_mm':radius,'strength':.5,'iterations':10,'max_displacement_mm':3})
    return diagram,commands


def compile_thumb_outline(source,side,center_x):
    """Fit endpoint-preserving cubic medial skin sections, not bone landmarks."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sculpt.editable(source)
    if side not in (-1,1):raise ValueError('Hand side must be -1 or 1')
    center_x=sculpt.number(center_x,-2,2,'palm center')
    if center_x*side<=0:raise ValueError('Palm center must match side')
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[];sections=[];t=np.linspace(0,1,9);basis=np.column_stack((t*(1-t),t*t*(1-t)))
    for j,y in enumerate((-.012,0,.012)):
        points=[]
        for z in np.linspace(.850,.890,9):
            direction=Vector((-side,0,0));hit,normal,_,distance=tree.ray_cast(Vector((center_x,y,z)),direction)
            if hit is None or normal.dot(direction)<=0 or not .008<distance<.08:
                raise ValueError('Thumb origin must exit the hand from inside')
            points.append(np.asarray(hit))
        a=np.asarray(points);chord=a[0,0]*(1-t)+a[-1,0]*t
        coefficients=np.linalg.lstsq(basis,a[:,0]-chord,rcond=None)[0]
        x=chord+basis@coefficients
        if np.max(np.abs(x-a[:,0]))>.003:raise ValueError('Thumb fit exceeds 3 mm local limit')
        for i,point in enumerate(a):
            target=point.copy();target[0]=x[i]
            controls.append({'name':f'thumb_{side}_{j}_{i}','source':point.tolist(),'target':target.tolist()})
        sections.append({'y':y,'source':a.tolist(),'fitted_x':x.tolist()})
    xs=sorted((center_x-side*.07,center_x+side*.02))
    return {'units':'m','label':'thumb outline '+str(side),'surface_interpolation':True,
        'radius_mm':18,'max_displacement_mm':3,'controls':controls,
        'region':{'min':[xs[0],-.05,.840],'max':[xs[1],.05,.900],'feather_mm':6},
        'registration':{'side':side,'center_x':center_x},'sections':sections,
        'limits':'Upright skin continuity fit; endpoints fixed at control samples, not anatomical inference.'}


def compile_fingers(source,side,center_x):
    """Register four skin sections per digit and two joint relief stations."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sculpt.editable(source)
    if side not in (-1,1):raise ValueError('Hand side must be -1 or 1')
    center_x=sculpt.number(center_x,-2,2,'palm center')
    if center_x*side<=0:raise ValueError('Palm center must match side')
    kb=json.loads(files('mesh_workbench').joinpath('knowledge/hand-structure-v1.json').read_text())
    p=sculpt.coordinates(source);tree=BVHTree.FromPolygons(p.tolist(),[list(f.vertices) for f in source.data.polygons])
    controls=[]
    for digit,(u,length,radius) in enumerate(zip(kb['finger_centers'],kb['finger_lengths'],kb['finger_radii'])):
        # Distal section expansion blends into unchanged shaft. Joint marks are
        # authored skin relief, never a claim that underlying bones were detected.
        for station,(t,relief) in enumerate(((.04,.00035),(.08,.00045),(.15,.0002),(.23,0),(.34,.00035),(.64,.0004))):
            z=.825-length+length*t
            x=center_x+side*(u*(1+.1*(1-t))+.2*(.85-z))
            y=-.002-.004*(1-t)
            for axis,sign in ((0,-1),(0,1),(1,-1),(1,1)):
                # Joint relief only on palmar/dorsal faces; keep lateral gaps.
                if station>=4 and axis==0:continue
                direction=Vector((sign if axis==0 else 0,sign if axis==1 else 0,0))
                hit,normal,_,distance=tree.ray_cast(Vector((x,y,z)),direction)
                if hit is None or normal.dot(direction)<=0 or not .001<distance<radius*1.6:
                    raise ValueError('Finger reference must exit its local skin envelope')
                a=np.asarray(hit);b=a.copy()
                delta=relief if station<4 else (relief if sign==1 else -relief*.5)
                b[axis]+=sign*delta
                controls.append({'name':f'finger_{digit}_{station}_{axis}_{sign}','source':a.tolist(),'target':b.tolist()})
    xs=sorted((center_x-side*.05,center_x+side*.06))
    return {'units':'m','label':'finger contours '+str(side),'surface_interpolation':True,
        'radius_mm':4,'max_displacement_mm':1.5,'controls':controls,
        'region':{'min':[xs[0],-.035,.738],'max':[xs[1],.035,.813],'feather_mm':2},
        'registration':{'side':side,'center_x':center_x},
        'limits':'Fixed upright procedural hand only; authored distal and joint skin relief, no bone detection or nails.'}
