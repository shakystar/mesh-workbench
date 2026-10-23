"""Draw the exact front-view controls consumed by human_mouth.py (Pillow)."""
import json
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont


def draw(source,target):
    spec=json.loads(Path(source).read_text())
    img=Image.new('RGB',(1100,720),'#f4f5f7');d=ImageDraw.Draw(img)
    small=ImageFont.load_default(size=15);font=ImageFont.load_default(size=19)
    d.text((30,22),'MOUTH: REGISTERED FRONT DIAGRAM',fill='#182536',font=ImageFont.load_default(size=27))
    d.text((30,65),'Artist-authored controls | metres in JSON | not an anatomical standard',fill='#526070',font=font)
    def point(p):return (330+p[0]*8500,125+(1.608-p[2])*8500)
    region=spec['regions']['mouth'];lo=region['min'];hi=region['max']
    a=point([lo[0],0,hi[2]]);b=point([hi[0],0,lo[2]])
    d.rectangle((*a,*b),fill='#e4edf3',outline='#63819a',width=2)
    f=region['feather']*8500
    d.rectangle((a[0]+f,a[1]+f,b[0]-f,b[1]-f),fill='white',outline='#b1c5d4')
    d.line((330,120,330,595),fill='#c4ccd4')
    for z in (1.60,1.59,1.58,1.57,1.56):
        y=point([0,0,z])[1]
        d.text((17,y-8),str(z),font=small,fill='#526070')
    for i,path in enumerate(spec['paths']):
        color='#a03939' if path['distance_mm']<0 else '#186f72'
        points=[point(spec['landmarks'][name]) for name in path['anchors']]
        d.line(points,fill=color,width=3)
        for x,y in points:d.ellipse((x-3,y-3,x+3,y+3),fill=color)
        y=130+i*59
        d.text((650,y),path['label'],font=font,fill=color)
        d.text((650,y+25),f"Radius {path['radius_mm']} mm; depth {path['distance_mm']:+} mm",font=small,fill='#526070')
    d.text((65,600),'Dots: named anchors. Lines: brush centerlines.',font=font,fill='#182536')
    d.text((65,632),'Outer band: feathered protection boundary. Outside: unchanged.',font=font,fill='#526070')
    d.text((65,665),'Each path projects onto the visible mesh and creates a reversible layer.',font=font,fill='#526070')
    img.save(target)


if __name__=='__main__':draw(*sys.argv[1:])
