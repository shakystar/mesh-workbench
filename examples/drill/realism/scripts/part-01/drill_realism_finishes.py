"""Seeded millimetre-scale finishes for the original procedural drill."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import copy

RUBBER_PARTS = {'grip_left', 'grip_right', 'texture_left', 'texture_right'}


def apply_finishes(nodes):
    for key,node in nodes.items():
        if 'material' not in node:
            continue
        style=copy.deepcopy(node['material'])
        if key in RUBBER_PARTS:
            style.update(name='Original elastomer grip',roughness=.72)
            finish={'role':'rubber','grain_mm':.35,'bump_mm':.025,'variation':.055,'seed':17}
        elif style.get('metallic',0)>.5:
            style.update(name='Original machined metal',roughness=.26)
            finish={'role':'metal','grain_mm':.06,'bump_mm':.002,'variation':.035,'seed':29}
        else:
            dark=max(style['color'])<.2
            style.update(name='Original dark polymer' if dark else 'Original colored polymer',
                         roughness=.48 if dark else .38)
            finish={'role':'plastic','grain_mm':.18,'bump_mm':.008,'variation':.04,'seed':43 if dark else 7}
        style['finish']=finish
        node['material']=style
