# Human modeling entry point

Current native: `runs/human/lower-nose-curves/lower-nose.blend`.
Current images: `docs/assets/human/nose/lower-nose-current.png` and
`docs/assets/human/nose/lower-nose-controls.png`. This is still a rough study.
The earlier brush-stage native is preserved in `runs/human/surface-brushed-nose/`.
Earlier cavity-stage underside: `docs/assets/human/nose/underside.png`.

Human scripts live in `scripts/`, `eyes/` and `nose/`; target JSON lives in `recipes/`. Tool implementations remain
in `src/mesh_workbench/`; knowledge data in `src/mesh_workbench/knowledge/`.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/nose/fit_lower_nose.py -- runs/human/surface-brushed-nose/surface-brushed.blend runs/human/new-lower-nose-study
```

Use one Blender process and numerical-library thread limits of two.

| Purpose | Scripts |
| --- | --- |
| Base and early shaping | `human_base.py`, `human_guided_brush.py`, `human_lower_face.py` |
| Mouth/nose | `human_mouth.py`, `fit_anatomy.py` |
| Eyes/ears | `human_eyes.py`, `human_ears.py` |
| Open eyes, fitted lids and rendered previews | `../eyes/build_open_eyes.py` (relative to `scripts/`) |
| Nasal volumes, cavities and three previews | `../nose/build_nose.py` (relative to `scripts/`) |
| Surface-following brush trial | `../nose/brush_surface.py` (relative to `scripts/`) |
| Registered lower-nose controls and saved-file check | `../nose/fit_lower_nose.py`, `../nose/check_lower_nose.py` (relative to `scripts/`) |
| Guide illustrations | `draw_anatomy_diagram.py`, `draw_mouth_diagram.py` |
| Current model images | `render_human.py` |

See [knowledge/API](../../docs/ANATOMY_KNOWLEDGE.md),
[brush controls](../../docs/ANATOMY_BRUSH.md) and
[workspace layout](../../docs/WORKSPACE_LAYOUT.md).
