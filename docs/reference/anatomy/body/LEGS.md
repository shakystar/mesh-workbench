# Lower-limb registration and next controls

## Current source audit - 2026-10-24

Stage E starts from `runs/human/rounded-caps/rounded-caps.blend`, object
`Rounded fingertip study`. `examples/human/legs/audit.py` loads this saved
character without editing geometry. Twelve manually specified interior axes
produce 48 outward skin exits with normal and distance guards. The lower-thigh
midline ray is open; geometry and input SHA256 are unchanged. Blender 5.2.2 LTS,
one process/two threads. Output: `runs/human/lower-limb-audit/audit.json` and two
actual renders. No new native file or repeated arm/hand tests were needed.

Right-side distances from authored axis to visible skin, in millimetres:

| Section | Front | Back | Outer | Inner |
| --- | ---: | ---: | ---: | ---: |
| Thigh | 90.64 | 90.67 | 79.65 | 79.75 |
| Lower thigh | 73.43 | 73.15 | 63.54 | 63.42 |
| Knee | 56.42 | 47.26 | 46.54 | 47.19 |
| Calf | 66.12 | 59.25 | 54.36 | 54.40 |
| Shin | 38.70 | 38.40 | 34.59 | 34.51 |
| Ankle | 35.82 | 33.73 | 36.82 | 32.04 |

These are skin distances, not bone dimensions. The source axes come from
`examples/human/scripts/human_base.py`; they are not automatically detected.
Views show cylindrical thigh mass, button-like knee relief, broad calf volumes
and an undivided foot/toe block. No realistic lower limb claim.

## Source relationships and bounded sequence

[OpenStax lower-limb bones](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-4-bones-of-the-lower-limb)
places the patella in front of the distal femur, the tibia medially and fibula
laterally. The tibial tuberosity and anterior border provide anterior shin
landmarks; the distal tibia/fibula form medial/lateral ankle prominences.
These relationships guide registration; authored skin depths remain separate.
No reference artwork is copied.

1. Thigh-to-knee: register proximal thigh, knee and proximal shin axes; separate
   knee central relief from medial/lateral transition and flatten the spherical
   knee appearance with bounded reversible controls. Protect pelvis above the
   region, calf/feet below it, the other limb and upper body.
2. Shin/calf: anterior crest versus posterior mass, without carving exposed bones.
3. Ankle/foot: ankle prominence ordering, heel/arch/forefoot, explicit toe divisions.
4. Review stage-E silhouette and connections from saved native views, then F/G.

Each implementation must verify registration rejection, atomic bilateral failure,
original/protected geometry, layer rollback, target surface and saved readback.
No whole-project regression or compatibility expansion is authorized.

| Front | Oblique |
| --- | --- |
| ![](../../../assets/human/legs/audit/front.png) | ![](../../../assets/human/legs/audit/oblique.png) |

## Registered thigh-knee controls - 2026-10-24

`regions.leg.compile_controls(source, target)` accepts side and descending
manual proximal/knee/shin axes plus a protection box. Eight radial directions
at seven stations register visible skin through outward interior-exit checks.
`knowledge/body/leg-surface-v1.json` separates sourced anatomical relationships
from authored skin offsets. `leg.apply_pair` compiles both sides before editing,
rejects overlapping boxes, and removes partial snapshots on second-side failure.
Two reversible layers preserve the original. Fixed standing frame only.

Blender 5.2.2 LTS: 112 controls, max move 3.05306 mm, surface residual .00851 mm,
minimum changed polygon area ratio .94344. 144,789 outside-region vertices exact.
Original/topology/rollback/invalid axes/second-leg cleanup/saved readback/input
hash pass. Mid-thigh gap remains open. Actual front rays at the knee measure
2.99758 and 3.00252 mm less protrusion. Pelvis above Z=.79 m and calf/feet below
Z=.43 m are protected by the registered boxes.

Matched front/oblique views show modest lower-thigh contour and knee projection
changes. The spherical knee outline still reads clearly; this does not establish
an anatomical patella or finished leg. Next: local kneecap border/transition,
then shin/calf. Stage E remains active.

Native: `runs/human/thigh-knee/knee-relief.blend`, object `Thigh knee study`.
Example: `examples/human/legs/relief.py` takes rounded-caps native and a fresh
output folder. One Blender process/two threads, exited.

| View | Before | After |
| --- | --- | --- |
| Front | ![](../../../assets/human/legs/knee/before-front.png) | ![](../../../assets/human/legs/knee/after-front.png) |
| Oblique | ![](../../../assets/human/legs/knee/before-oblique.png) | ![](../../../assets/human/legs/knee/after-oblique.png) |
