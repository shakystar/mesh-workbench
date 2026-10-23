"""Current native renders and front-projected authored control paths."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())


def run(font_path='DejaVuSans.ttf'):
    folder=ROOT/'runs/human/lower-nose-curves'
    out=ROOT/'docs/assets/human/nose'
    board=Image.new('RGB',(1920,720),'#17202b')
    d=ImageDraw.Draw(board); font=ImageFont.truetype(font_path,24)
    for i,name in enumerate(('front','profile','basal')):
        board.paste(Image.open(folder/(name+'.png')).convert('RGB'),(640*i,50))
        d.text((640*i+18,12),name.upper()+' / CURRENT CURVE STUDY',font=font,fill='white')
    d.text((18,692),'Actual saved mesh. Lower-nose control fit; nostril rim and vestibule remain unfinished.',font=ImageFont.truetype(font_path,20),fill='white')
    board.save(out/'lower-nose-current.png')
    guide=Image.new('RGB',(1000,700),'#17202b')
    guide.paste(Image.open(folder/'front.png').convert('RGB'),(0,50))
    d=ImageDraw.Draw(guide)
    d.text((15,12),'REGISTERED SURFACE CONTROLS / NOT CARTILAGE GEOMETRY',font=font,fill='white')
    diagram=json.loads((folder/'diagram.json').read_text(encoding='utf-8'))
    points={c['name']:c['target'] for c in diagram['controls']}
    colors=['#ffb347','#6ce2fa','#ff7b91','#94ee8b','#94ee8b','#94ee8b','#94ee8b','#94ee8b','#94ee8b']
    for i,(name,keys) in enumerate(diagram['curves'].items()):
        screen=[(320+points[k][0]*640/.11,50+320-(points[k][2]-1.63)*640/.11) for k in keys]
        color=colors[i%len(colors)]
        d.line(screen,fill=color,width=2)
        for x,y in screen: d.ellipse((x-3,y-3,x+3,y+3),fill=color)
        d.text((650,110+45*i),name,font=ImageFont.truetype(font_path,20),fill=color)
    guide.save(out/'lower-nose-controls.png')


if __name__=='__main__':run(*sys.argv[1:])
