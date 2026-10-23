"""Actual source/result eye comparison and current oblique view."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())


def run(font_path='DejaVuSans.ttf'):
    out=ROOT/'docs/assets/human/eyes';out.mkdir(exist_ok=True)
    folder=ROOT/'runs/human/supported-eyelids'
    font=ImageFont.truetype(font_path,24)
    for filename,panels in [
        ('supported-current.png',[('CURRENT / FRONT',folder/'front.png'),('CURRENT / OBLIQUE',folder/'oblique.png')]),
        ('supported-comparison.png',[('BEFORE / ORBIT-ALIGNED GAZE',ROOT/'runs/human/tip-ala-refined/front.png'),
                                     ('AFTER / LID FIT + FORWARD GAZE',folder/'front.png')])]:
        board=Image.new('RGB',(1280,700),'#17202b');d=ImageDraw.Draw(board)
        for i,(label,path) in enumerate(panels):
            board.paste(Image.open(path).convert('RGB'),(640*i,50))
            d.text((640*i+16,12),label,font=font,fill='white')
        board.save(out/filename)


if __name__=='__main__':run(*sys.argv[1:])
