"""Compose actual entrance-study renders without retouching."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())


def run(font_path='DejaVuSans.ttf'):
    folder=ROOT/'runs/human/nasal-entrances-smooth'
    out=ROOT/'docs/assets/human/nose'
    font=ImageFont.truetype(font_path,24)
    board=Image.new('RGB',(1920,720),'#17202b'); d=ImageDraw.Draw(board)
    for i,name in enumerate(('front','profile','basal')):
        board.paste(Image.open(folder/(name+'.png')).convert('RGB'),(640*i,50))
        d.text((640*i+18,12),name.upper()+' / CURRENT ENTRANCE STUDY',font=font,fill='white')
    d.text((18,692),'Actual saved mesh. Connected rim and short blind interior; not a complete nasal airway.',font=ImageFont.truetype(font_path,20),fill='white')
    board.save(out/'entrances-current.png')
    comparison=Image.new('RGB',(1280,700),'#17202b'); d=ImageDraw.Draw(comparison)
    for i,(label,path) in enumerate([
        ('BEFORE / ELLIPSOID CUTOUT',ROOT/'runs/human/lower-nose-curves/basal.png'),
        ('AFTER / CONNECTED RIM + INTERIOR',folder/'basal.png')]):
        comparison.paste(Image.open(path).convert('RGB'),(640*i,50))
        d.text((640*i+18,12),label,font=font,fill='white')
    comparison.save(out/'entrances-comparison.png')


if __name__=='__main__':run(*sys.argv[1:])
