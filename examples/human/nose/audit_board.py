"""Compose unretouched audit renders and an original relationship diagram."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
RUN = ROOT/'runs/human/nose-anatomy-audit'
OUT = ROOT/'docs/assets/human/nose'


def build(font_path='DejaVuSans.ttf'):
    def f(size): return ImageFont.truetype(font_path, size)
    board = Image.new('RGB', (1680, 720), '#17202b')
    d = ImageDraw.Draw(board)
    d.text((24, 15), 'CURRENT MODEL / STRUCTURAL AUDIT / NO GEOMETRY CHANGES', font=f(28), fill='white')
    for i, (name, path, note) in enumerate([
        ('FRONT', RUN/'front.png', '1  Openings read as isolated cutouts'),
        ('PROFILE', RUN/'profile.png', '2  Tip-to-columella transition is bulky'),
        ('BASAL OBLIQUE', RUN/'basal-corrected/basal.png', '3  Inspect rim / sill / central-column continuity'),
    ]):
        board.paste(Image.open(path).convert('RGB'), (i*560, 65))
        d.text((i*560+18, 635), name, font=f(24), fill='#70d4db')
        d.text((i*560+18, 674), note, font=f(18), fill='white')
    board.save(OUT/'anatomy-audit.png')
    diagram = Image.new('RGB', (1400, 850), '#17202b')
    d = ImageDraw.Draw(diagram)
    d.text((35, 25), 'NOSE: SUPPORT -> SOFT TISSUE -> VISIBLE SURFACE', font=f(30), fill='white')
    d.text((35, 76), 'Original relationship map. Not measured anatomy or a shape template.', font=f(21), fill='#afbdcb')
    rows = [
        ('Nasal bones + septum\n+ lateral cartilages', 'Skin / muscle / fat\nvary by region and person', 'Root / bridge / dorsum\nSurface does not copy the framework'),
        ('Paired alar cartilages\nMedial + lateral crura', 'Soft-tissue envelope\nincluding tip tissue', 'Columella / tip / outer nostril wall\nConnected structures, not separate bumps'),
        ('Registered surface curves\nCurrent tool: missing', 'Rim / sill / attachment\nCurrent tool: ellipse cuts', 'Next: coherent lower-nose surface\nThen local brushing'),
    ]
    for r, row in enumerate(rows):
        y = 140+r*190
        for c, text in enumerate(row):
            x = 30+c*465
            d.rounded_rectangle((x,y,x+420,y+135), radius=12, fill='#25384a', outline='#70d4db', width=2)
            d.multiline_text((x+15,y+35), text, font=f(19), fill='white', spacing=12)
            if c < 2:
                d.line((x+425,y+67,x+457,y+67), fill='#70d4db', width=3)
                d.polygon([(x+457,y+67),(x+449,y+61),(x+449,y+73)], fill='#70d4db')
    d.text((35, 730), 'Sources: NIH Elements of Morphology; Anderson et al. (2008), J Anat 213:210-216.', font=f(20), fill='#afbdcb')
    d.text((35, 772), 'Rows 1-2: source-based relationships. Row 3: proposed tool workflow, not an anatomical finding.', font=f(20), fill='#afbdcb')
    diagram.save(OUT/'structure-map.png')


if __name__ == '__main__':
    import sys
    build(*sys.argv[1:])
