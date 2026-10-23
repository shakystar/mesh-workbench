"""Draw the registered guide exported by human_guided_brush.py (requires Pillow)."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont


def draw(source,target):
    data=json.loads(Path(source).read_text())
    img=Image.new('RGB',(1100,700),'#f4f5f7');d=ImageDraw.Draw(img)
    font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=14)
    d.text((32,20),'REGISTERED HEAD DIAGRAM',font=ImageFont.load_default(size=25),fill='#182536')
    d.text((32,58),'Artist-defined landmarks, not universal anatomy | geometry units: metres',font=font,fill='#3d4e62')
    for index,(view,axis,extent) in enumerate([('FRONT',0,.15),('SIDE',1,.15)]):
        left=45+index*550;top=125;w=460;h=480;zmin=1.50;zmax=1.79
        def project(horizontal,z):return (left+(horizontal+extent)/(2*extent)*w,top+(zmax-z)/(zmax-zmin)*h)
        d.text((left,94),view,font=font,fill='#182536')
        d.rectangle((left,top,left+w,top+h),fill='white',outline='#bac3ce')
        boundary=project(0,data['regions']['cranium']['min'][2])[1]
        d.rectangle((left,top,left+w,boundary),fill='#d9ecff')
        d.line((left,boundary,left+w,boundary),fill='#3275ac',width=2)
        points=data['outline'];a=[];b=[]
        for step in range(150):
            z=zmin+(zmax-zmin)*step/149
            row=[p[axis] for p in points if abs(p[2]-z)<.003]
            if row:a.append(project(min(row),z));b.append(project(max(row),z))
        if a:d.line(a+list(reversed(b))+[a[0]],fill='#526070',width=2)
        d.line((project(0,zmin),project(0,zmax)),fill='#b7bfc8',width=1)
        for name in ('crown','brow','ear_right','chin'):
            p=data['landmarks'][name];x,y=project(p[axis],p[2])
            d.line((x-4,y,x+4,y),fill='#1e5f9e',width=2);d.line((x,y-4,x,y+4),fill='#1e5f9e',width=2)
            d.text((x+7,y+5),name,font=small,fill='#1e5f9e')
        hit=data['hits'][index];x,y=project(hit[axis],hit[2]);r=data['strokes'][index]['radius_mm']/1000
        rx=r*w/(2*extent);ry=r*h/(zmax-zmin)
        d.ellipse((x-rx,y-ry,x+rx,y+ry),outline='#cb6d22',width=2)
        d.ellipse((x-3,y-3,x+3,y+3),fill='#cb6d22')
        d.text((left+8,top+8),'CRANIUM: editable + feathered boundary',font=small,fill='#25618d')
        d.text((left+8,boundary+8),'FACE / NECK: protected',font=small,fill='#526070')
    d.text((32,640),'Orange: projected radius envelope. Actual brush footprint follows mesh geodesic distance.',font=small,fill='#3d4e62')
    d.text((32,665),'Two reversible strokes | per-stroke displacement cap: 3 mm | protected vertices unchanged',font=small,fill='#3d4e62')
    img.save(target)


if __name__=='__main__':draw(*sys.argv[1:])
