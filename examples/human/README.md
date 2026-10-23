# Human modeling entry point

Current native: `runs/human/oral-relief/oral-relief.blend`.
Current images: `docs/assets/human/mouth/after-front.png` and `after-oblique.png`.
Registered lip relief is reviewed; philtrum termination and lower fold remain
rough. The preserved input is `runs/human/supported-eyelids-collar/supported-lids.blend`.
Run `mouth/refine.py` with that input and a fresh output directory inside Blender.
The nasal input remains in `runs/human/tip-ala-refined/`.
The entrance-stage input remains in `runs/human/nasal-entrances-smooth/`.
The input control-study native remains in `runs/human/lower-nose-curves/`.
The earlier brush-stage native is preserved in `runs/human/surface-brushed-nose/`.
Earlier cavity-stage underside: `docs/assets/human/nose/underside.png`.

Human scripts live in `scripts/`, `eyes/` and `nose/`; target JSON lives in `recipes/`. Tool implementations remain
in `src/mesh_workbench/`; knowledge data in `src/mesh_workbench/knowledge/`.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/eyes/fit_lids.py -- runs/human/tip-ala-refined/tip-ala.blend runs/human/new-eyelid-study
```

Use one Blender process and numerical-library thread limits of two.

| Purpose | Scripts |
| --- | --- |
| Base and early shaping | `human_base.py`, `human_guided_brush.py`, `human_lower_face.py` |
| Mouth/nose | `human_mouth.py`, `fit_anatomy.py` |
| Eyes/ears | `human_eyes.py`, `human_ears.py` |
| Open eyes, fitted lids and rendered previews | `../eyes/build_open_eyes.py` (relative to `scripts/`) |
| Registered lid support and independent gaze | `../eyes/fit_lids.py` (relative to `scripts/`) |
| Nasal volumes, cavities and three previews | `../nose/build_nose.py` (relative to `scripts/`) |
| Surface-following brush trial | `../nose/brush_surface.py` (relative to `scripts/`) |
| Registered lower-nose controls and saved-file check | `../nose/fit_lower_nose.py`, `../nose/check_lower_nose.py` (relative to `scripts/`) |
| Connected entrance patches and saved-file check | `../nose/build_entrances.py`, `../nose/check_entrances.py` (relative to `scripts/`) |
| Tip/upper-alar refinement with entrance protection | `../nose/refine/tip_ala.py` (relative to `scripts/`) |
| Guide illustrations | `draw_anatomy_diagram.py`, `draw_mouth_diagram.py` |
| Current model images | `render_human.py` |

See [knowledge/API](../../docs/ANATOMY_KNOWLEDGE.md),
[brush controls](../../docs/ANATOMY_BRUSH.md) and
[workspace layout](../../docs/WORKSPACE_LAYOUT.md).
