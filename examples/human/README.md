# Human modeling entry point

Current native: `runs/human-ear-fit/fitted-ears.blend`.
Current images: `docs/assets/human-current-front.png` and
`docs/assets/human-current-three-quarter.png`. This is still a rough study.

All human example scripts and target JSON live here. Tool implementations remain
in `src/mesh_workbench/`; knowledge data in `src/mesh_workbench/knowledge/`.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/render_human.py -- runs/human-ear-fit/fitted-ears.blend runs/human-current-preview
```

Use one Blender process and numerical-library thread limits of two.

| Purpose | Scripts |
| --- | --- |
| Base and early shaping | `human_base.py`, `human_guided_brush.py`, `human_lower_face.py` |
| Mouth/nose | `human_mouth.py`, `fit_anatomy.py` |
| Eyes/ears | `human_eyes.py`, `human_ears.py` |
| Guide illustrations | `draw_anatomy_diagram.py`, `draw_mouth_diagram.py` |
| Current model images | `render_human.py` |

See [knowledge/API](../../docs/ANATOMY_KNOWLEDGE.md),
[brush controls](../../docs/ANATOMY_BRUSH.md) and
[workspace layout](../../docs/WORKSPACE_LAYOUT.md).
