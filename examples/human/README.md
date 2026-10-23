# Human modeling entry point

Current hand: `hands/caps/run.py` takes finger-contours native and a fresh output folder.
Recorded native: `runs/human/rounded-caps/rounded-caps.blend`.
160 cap controls; rounded ends with residual flaring.

Current hand: `hands/fingers.py` takes thumb-outline native and a fresh output folder.
Recorded native: `runs/human/finger-contours/finger-contours.blend`.
160 controls; terminal caps remain angular.

Current native: `runs/human/thumb-outline/thumb-outline.blend`.
`hands/thumb.py` takes hand-transitions native and a fresh folder; it checks
actual section continuity in addition to preservation and failure paths.
Images: `docs/assets/human/hands/thumb/`. A small silhouette notch remains.
Earlier fairing pass:


Current native: `runs/human/hand-transitions/hand-transitions.blend`.
`hands/transitions.py` takes palm-shaped native and a fresh folder. The eight
fairing paths preserve wrist/fingertip regions; medial thumb step remains.
Images: `docs/assets/human/hands/transitions/`.
Earlier palm-control pass:


Current native: `runs/human/palm-shaped/palm-shaped.blend`.
`hands/palm.py` takes the preserved wrist-ring-faired native and a fresh folder.
Current views: `docs/assets/human/hands/palm/`.
Earlier wrist-ring pass:


Current native: `runs/human/wrist-ring-faired/wrist-transitions.blend`.
`hands/attach.py` now adds intermediate wrist rings; `hands/fair_wrist.py` takes
that reconstructed native and a fresh output folder. Original boundaries remain
on the input; local fairing uses reversible layers. Images: `docs/assets/human/hands/rings/`.
Earlier stock-weld pass:


Current integrated native: `runs/human/hands-grafted-welded/hands-grafted.blend`.
`hands/attach.py` includes stock-only near-vertex welding. `hands/wrist.py` is a
rejection audit on the earlier hands-grafted native; it does not save a new model.
Current images: `docs/assets/human/hands/welded/`. Wrist band remains unresolved.
Earlier graft pass:


Current integrated native: `runs/human/hands-grafted/hands-grafted.blend`.
`hands/attach.py` takes the preserved elbow-relief native and a fresh output
folder. Both hands are grafted on a new snapshot; original body/layers remain.
Current images: `docs/assets/human/hands/grafted/`.
Earlier separate-hand pass:


Separate hand prototype: `runs/human/hand-stock-curved/hand-stock.blend`.
`hands/audit.py` and `hands/build.py` take the preserved elbow-relief native and
fresh output folders. The prototype is NOT attached; the integrated native below
remains authoritative. [Evidence](../../docs/reference/anatomy/body/HANDS.md).


Current native: `runs/human/elbow-relief/elbow-relief.blend`.
`arms/elbow.py` takes the preserved arm-relief native and a fresh output folder;
`arms/check_elbow.py` takes the result folder for focused registration failures.
Current views: `docs/assets/human/arms/elbow/`.
Earlier arm-volume pass:


Current native: `runs/human/arm-relief/arm-relief.blend`.
`arms/audit.py` reads the flank-transition native; `arms/relief.py` applies bilateral
controls to it with a fresh output folder. Current views: `docs/assets/human/arms/`.
Earlier torso pass:


Current native: `runs/human/flank-transition/flank-transition.blend`.
Run `torso/flank.py` on the preserved axillary native into a fresh folder.
`torso/check_flank.py` takes the result folder and checks lateral-origin rejection.
Current matched views: `docs/assets/human/torso/flank/`.
Earlier axillary pass:


Current native: `runs/human/axillary-junction/axillary-transitions.blend`.
Run `torso/axilla.py` on the preserved posterior-torso native into a fresh folder.
Current matched junction renders: `docs/assets/human/torso/axilla/`.
Earlier posterior-plane pass:


Current native: `runs/human/posterior-torso/posterior-torso.blend`.
Run `torso/back.py` on the preserved costal-continuous native into a fresh folder.
Current posterior images: `docs/assets/human/torso/back/`.
Earlier costal/abdominal pass:


Current native: `runs/human/costal-continuous/costal-abdomen.blend`.
Run `torso/abdomen.py` on the preserved torso-planes native into a fresh output folder.
Current images: `docs/assets/human/torso/costal-{front,side,back}.png`.
Earlier torso-plane pass:

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
