# Human modeling entry point

Current torso native: `runs/human/torso-planes/torso-planes.blend`.
`torso/planes.py` takes the preserved rebuilt-underside native and a fresh output
folder; `torso/audit.py` records the matched before views.
[Current torso evidence](../../docs/reference/anatomy/body/TORSO.md).

Earlier neck stage:

Current native: `runs/human/rebuilt-underside/rebuilt-underside.blend`.
Current images: `docs/assets/human/neck/rebuilt-front.png` and `rebuilt-profile.png`.
The local under-chin fold is repaired. Run `neck/rebuild_underside.py` from
`runs/human/neck-submental/neck-transitions.blend` into a fresh folder.
The source and old topology remain preserved. Prior neck trial: `neck/transitions.py` from
`runs/human/continuous-ears-faired/continuous-ears.blend` into a fresh folder.
Prior ear stage:
Ear ridge continuity is reviewed; thickness remains shallow. Neck transition is next.
Run `ears/continuous.py` from the preserved `runs/human/chin-contour/chin-contour.blend`
input with a fresh output folder. It refines only ears on a new snapshot and
applies 14 reversible curve/fairing layers. `ears/relief.py` retains the earlier
point-control trial. Prior face stage:
Run `mouth/chin.py` with `runs/human/oral-transitions/oral-transitions.blend`
and a fresh output directory. The static face-tool pass is reviewed; ears/neck
are next. Prior oral transition stage:
Local philtrum/lower-fold fairing is reviewed; broad chin/jaw contours remain
rough. Run `mouth/transitions.py` with `runs/human/oral-relief/oral-relief.blend`
and a fresh output directory inside Blender. The prior lip-relief stage is
reproduced by `mouth/refine.py` from the supported-eyelids-collar input.
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
