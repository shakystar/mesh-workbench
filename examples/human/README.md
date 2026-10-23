# Human modeling entry point

Current native: `runs/human/nasal-structure-final/nasal-structure.blend`.
Current images: `docs/assets/human/human-current-front.png` and
`docs/assets/human/human-current-three-quarter.png`. This is still a rough study.
Nose underside: `docs/assets/human/nose/underside.png`.

Human scripts live in `scripts/`, `eyes/` and `nose/`; target JSON lives in `recipes/`. Tool implementations remain
in `src/mesh_workbench/`; knowledge data in `src/mesh_workbench/knowledge/`.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/nose/build_nose.py -- runs/human/open-eyes-finished/open-eyes.blend runs/human/new-nose-study
```

Use one Blender process and numerical-library thread limits of two.

| Purpose | Scripts |
| --- | --- |
| Base and early shaping | `human_base.py`, `human_guided_brush.py`, `human_lower_face.py` |
| Mouth/nose | `human_mouth.py`, `fit_anatomy.py` |
| Eyes/ears | `human_eyes.py`, `human_ears.py` |
| Open eyes, fitted lids and rendered previews | `../eyes/build_open_eyes.py` (relative to `scripts/`) |
| Nasal volumes, cavities and three previews | `../nose/build_nose.py` (relative to `scripts/`) |
| Guide illustrations | `draw_anatomy_diagram.py`, `draw_mouth_diagram.py` |
| Current model images | `render_human.py` |

See [knowledge/API](../../docs/ANATOMY_KNOWLEDGE.md),
[brush controls](../../docs/ANATOMY_BRUSH.md) and
[workspace layout](../../docs/WORKSPACE_LAYOUT.md).
