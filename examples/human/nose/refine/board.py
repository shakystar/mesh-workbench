"""Actual before/after views of the tip/alar refinement."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())


def run(font_path='DejaVuSans.ttf'):
    folder=ROOT/'runs/human/tip-ala-refined';out=ROOT/'docs/assets/human/nose'
    font=ImageFont.truetype(font_path,24)
    board=Image.new('RGB',(1920,720),'#17202b');d=ImageDraw.Draw(board)
    for i,view in enumerate(('front','profile','basal')):
        board.paste(Image.open(folder/(view+'.png')).convert('RGB'),(640*i,50))
        d.text((640*i+16,12),view.upper()+' / TIP AND ALAR VOLUMES',font=font,fill='white')
    d.text((16,690),'Current saved model. Entrance patch vertices unchanged; authored outer-surface study.',font=ImageFont.truetype(font_path,21),fill='white')
    board.save(out/'tip-ala-current.png')
    compare=Image.new('RGB',(1280,700),'#17202b');d=ImageDraw.Draw(compare)
    for i,(label,path) in enumerate([
        ('BEFORE',ROOT/'runs/human/nasal-entrances-smooth/front.png'),
        ('AFTER / 17 REGISTERED CONTROLS',folder/'front.png')]):
        compare.paste(Image.open(path).convert('RGB'),(640*i,50))
        d.text((640*i+16,12),label,font=font,fill='white')
    compare.save(out/'tip-ala-comparison.png')


if __name__=='__main__':run(*sys.argv[1:])
