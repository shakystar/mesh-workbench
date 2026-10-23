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
