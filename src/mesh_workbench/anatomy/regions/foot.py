"""Local procedural five-toe forefoot stock; attachment remains explicit."""
import json
from importlib.resources import files
import bpy
from .. import sectionstock,models,sculpt

def build(name='Forefoot stock',scale=1,side=1):
    scale=sculpt.number(scale,.7,1.4,'forefoot scale')
    if side not in (-1,1):raise ValueError('Foot side must be -1 or 1')
    if name in bpy.data.objects:raise ValueError('Output exists')
    kb=json.loads(files('mesh_workbench').joinpath('knowledge/body/toe-structure-v1.json').read_text())
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
        for v in obj.data.vertices:v.co=(v.co.x,-v.co.z,v.co.y)
        obj.data.update()
        return obj
    try:
        stock('forefoot',[[.105,0,.036,.043,.025],[.125,.002,.033,.049,.024],
            [.14,.003,.029,.049,.014],[.147,.003,.026,.043,.007]])
        import math
        for i,(x,length,radius) in enumerate(zip(kb['centers'],kb['lengths'],kb['radii'])):
            rows=[]
            for j in range(21):
                t=j/20;s=.134+length*t
                r=1 if t<=.75 else math.sqrt(max(.005,1-((t-.75)/.25)**2))
                z=.028 if i==0 else .025
                rows.append([s,x,z,radius*r,radius*.85*r])
            stock('toe '+str(i+1),rows)
        result=models.combine(parts,name,voxel=.001*scale)
        result['mw_toe_structure']=json.dumps(kb);result['mw_attachment']='Closed forefoot cap; not grafted to character'
        for obj in parts:obj.hide_render=True;obj.hide_set(True)
        return result,parts
    except Exception:
        for obj in set(bpy.data.objects)-objects:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in set(bpy.data.meshes)-meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
