# Proportional anatomy knowledge and registration

Reusable modules cover the neutral oral region, front-visible nasal base and
periorbital surface and external-ear relief.
The oral module contains six semantic feature groups, 20 normalized controls and
seven brush paths. The nasal module adds five groups, 19 controls and six paths.
The periorbital module adds six groups, 19 controls and five paths per eye.
The auricle module adds five groups, 19 controls and six paths per ear.
Each stores source references separately from authored modeling proportions.

## Knowledge versus authored proportions

[`oral-neutral-v1.json`](../src/mesh_workbench/knowledge/oral-neutral-v1.json)
records feature definitions, source IDs, relations and normalized controls.
Terminology follows the NIH/NHGRI
[oral anatomy reference](https://elementsofmorphology.nih.gov/anatomy-oral.shtml):
lip corners join the upper and lower margins, the philtrum belongs to the upper
lip, and the mentolabial sulcus bounds the central lower lip region.
Only short, independently worded descriptions and citations are stored; no
reference images are redistributed.

All numerical proportions, brush sizes and deformation strengths are authored
modeling choices. They are not measured population averages or clinical limits.
The feature graph describes relationships; it is not a muscle or tissue simulator.

## Fit a different model

Supply four world-space landmarks in metres: `corner_left`, `corner_right`,
`nose_base`, and `chin_fold`. Left/right mean negative/positive diagram X,
not anatomical left/right. The model faces -Y with Z up and a neutral mouth.
Reference depth must agree with the visible surface within 5 mm by default.

1. Mouth corners establish center and half-width.
2. Nose-base and chin-fold heights independently scale controls above/below the
   mouth. The guide therefore accommodates different widths and vertical ratios.
3. Every control and sampled path is projected onto the target surface.
4. Brush radius and relief scale with mouth half-width. `bow_width` (0.7–1.3)
   adjusts the paired bow controls; `relief` (0.5–1.5) scales brush displacement.
5. A new snapshot receives a fresh binding and seven reversible layers.

The parameter ranges are implementation bounds, not anatomical normality ranges.
Existing source geometry, layers, selections and masks are untouched. Prior masks
are not transferred to the new snapshot; it has newly computed regional bounds.
Failed application removes the new object and mesh. Registration provenance,
target residuals, topology and transform are stored with the result.

```python
from mesh_workbench import anatomy_fit, anatomy

# Read-only preparation; does not bind or alter the object.
diagram = anatomy_fit.compile_diagram(obj, target, bow_width=1.1)

# Complete application to a new evaluated snapshot; input remains intact.
result, diagram, reports = anatomy_fit.apply(
    obj, target, "Registered oral study", bow_width=1.1, relief=0.9
)
```

Included procedural model example (one Blender process, two threads; numerical
library thread limits must also be two):

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/fit_anatomy.py -- runs/human-lower-face-final/human-lower-face.blend "Lower face refinement" examples/human/human-mouth-target.json runs/human-mouth-fit-visible
```

The example hides the preserved input after success to avoid overlapping surfaces.
It writes the fitted native file, compiled diagram and brush reports, without a
render. Use a fresh output directory.

## Verified scope and remaining work

Blender 5.2.2 LTS: `tests/anatomy_fit_test.py` applies the knowledge to two curved
surface fixtures, with mouth widths 42/58 mm and different upper/lower spans.
Both verify actual displacement, bounds, preserved input, unchanged protected
vertices and complete layer rollback. Eight invalid registrations fail without
leaving partial scene objects. The current procedural human also accepts the
measured target file and saves the fitted result. No new visual-quality claim is
made from this geometry-only pass.

| Area | Current coverage |
| --- | --- |
| Oral region | Semantic definitions, proportional guide, manual landmark fitting |
| Nasal base and alae | Semantic definitions, proportional guide, shared oral reference |
| Periorbital surface | Eyelid/crease/brow guides, per-eye canthal-axis fitting |
| External ear surface | Lateral projection, proportional guides, paired reversible application |
| Orbital cavities, eyeballs, ear canals, upper nasal bridge | No reusable knowledge modules yet |
| Skull, neck, torso, limbs, hands and feet | No reusable knowledge modules yet |
| Automatic landmark detection | Not implemented |
| Pose/expression, age or body-type models | Not implemented |
| Anatomical accuracy across human subjects | Not validated |

Whole-body variation requires additional regional modules and independently
registered models; the current fixtures do not establish it.

## Nasal base and alar module

`anatomy_fit.knowledge("nasal-base-v1")` loads
[`nasal-base-v1.json`](../src/mesh_workbench/knowledge/nasal-base-v1.json).
Definitions of the ala, columella and tip reference the
[NIH/NHGRI nasal anatomy page](https://elementsofmorphology.nih.gov/anatomy-nose.shtml).
The alar attachment and central junction are explicitly labeled authored modeling
conventions. In particular, the shared legacy key `nose_base` means the central
nose/upper-lip junction here, not the complete anatomical nasal-base line.

Set `knowledge_id` to `nasal-base-v1` in the target JSON. Required references:
`ala_left`, `ala_right`, `nose_base`, `nose_tip`, `philtrum_top`.
Alar width sets the horizontal scale; base-to-tip height sets the upper scale.
The philtrum reference lies below the base. Targets must be front-visible,
upright and close to the mesh surface; tilted/asymmetric reference frames beyond
the documented horizontal tolerance are rejected instead of silently corrected.

An optional `linked_oral_target` checks the shared nose-base coordinate within
0.1 mm and ensures the philtrum reference is between mouth and nose base. This
checks reference consistency, not anatomical correctness. The included human
target uses this link. Nasal edit bounds stop at the base height, keeping all
lower mouth/philtrum coordinates unchanged, including existing oral deformations.

Six paths add paired alar volume/attachment relief, columella support and a tip
transition. They project from the front. Hidden underside structures, open
nostril cavities, internal septum and cartilage are not modeled. `relief` remains
available; `bow_width` is oral-only and non-default values are rejected for nose.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/fit_anatomy.py -- runs/human-mouth-fit-visible/fitted.blend "Fitted oral guide" examples/human/human-nasal-target.json runs/human-nasal-fit
```

Focused checks: `tests/nasal_fit_test.py`, Blender 5.2.2 LTS. Two curved fixtures
use alar widths 28/44 mm and heights 18/26 mm. Checks cover deformation caps,
protected regions, existing mouth-layer preservation, rollback, eight atomic
failure cases and old oral-default compilation. The procedural human application
also checks source preservation, protected coordinates and full rollback before
saving. No new renders or anatomical-accuracy claims accompany this tool pass.

## Periorbital surface module

[`periorbital-v1.json`](../src/mesh_workbench/knowledge/periorbital-v1.json) stores
upper/lower eyelid, canthal registration, upper crease, lower transition and brow
groups. Terms for lid, crease and brow reference the
[NIH/NHGRI periorbital anatomy page](https://elementsofmorphology.nih.gov/anatomy-periorbital.shtml).
The canthal guide and lower transition are authored modeling conventions.
All numerical ratios remain artist-defined, with no demographic meaning.

Each target selects `knowledge_id: periorbital-v1`, supplies `side: negative_x`
or `positive_x` (diagram sides, not anatomical left/right), and four visible
surface references: `medial_canthus`, `lateral_canthus`, `upper_lid`, `lower_lid`.
`midline_x` defaults to zero. The canthal axis runs medial to lateral and follows
the measured tilt. Upper/lower lid references set independent perpendicular
heights. This differs from the horizontal-only oral/nasal reference frame.

Implementation bounds: eye half-width 5–30 mm, upper/lower heights 1–20 mm and
absolute vertical canthal-axis component at most 0.35. These are supported tool
ranges, not normal anatomy ranges. Wrong-side references, inverted lid heights,
off-surface points, bounds crossing the facial midline and excessive tilt fail.
`bow_width` is not applicable. Five surface paths mark the upper/lower lid,
upper crease, lower transition and brow support. They do not create an eye
opening, eyeball, tear duct or an orbital cavity.

### Both eyes in one reversible result

```python
result, diagrams, reports = anatomy_fit.apply_many(
    source, [negative_x_target, positive_x_target], "Both eye guides"
)
```

All target diagrams are compiled before editing. Their axis-aligned edit bounds
must be disjoint. Each path stays a separate reversible layer on the same output;
the first eye is not baked away when applying the second. Any failure, including
one after the first region has changed, removes the entire new object and mesh.
The source stays intact. `mw_anatomy_fits` retains all registration metadata.
Only the last diagram remains the active `anatomy` brush binding; explicitly bind
another returned diagram before extending that region. The existing single-region
`apply` API still returns one diagram and uses the same transaction mechanism.

Included example measures reference depths on the existing procedural human,
subdivides only selected eye-region faces into a preserved baseline, then applies
both guides. Existing nose/mouth deformation remains in the new baseline;
previous source objects and keys remain available.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/human_eyes.py -- runs/human-nasal-fit/fitted.blend runs/human-eye-fit
```

Use a fresh output directory, one Blender process and numerical-library thread
limits of two. The example saves native geometry and reports without rendering.

Focused check: `tests/orbital_fit_test.py`, Blender 5.2.2 LTS. Two bilateral
fixtures use 24/34 mm eye widths, distinct lid heights, and 0/0.12 rad canthal
tilts. It verifies both-eye geometry changes, protected coordinates, earlier
lower-face layers, all-layer rollback, eight invalid batches, an injected failure
after five successful paths, and compatibility of the original oral `apply` API.
The current human example additionally verifies closed manifold geometry and
source/baseline preservation. These checks do not establish anatomical accuracy
or rendered realism.

## External ear and side projection

[`auricle-v1.json`](../src/mesh_workbench/knowledge/auricle-v1.json) records helix,
antihelix, concha, lobule and tragus groups, referencing the
[NIH/NHGRI external-ear anatomy page](https://elementsofmorphology.nih.gov/anatomy-ear.shtml).
Descriptions are independently worded; no reference images or measured ratios
are copied. All numerical proportions remain authored defaults.

Set `knowledge_id: auricle-v1` and `side: negative_x` or `positive_x`. Four
manually identified visible points are required: `anterior`, `posterior`,
`superior`, `inferior`. The model faces -Y, with Z up. Anterior/posterior span
sets Y width; upper/lower references set independent heights. `midline_x`
defaults to zero. This module requires approximately level anterior/posterior
references and does not automatically correct rotated ears.

The path tool now supports `side_negative_x` and `side_positive_x` projection.
Both use Y/Z controls, cast toward the selected side and change only X. Positive
brush displacement is outward; negative is inward. Each affected vertex must be
visible from that same side, protecting the opposite ear and hidden nearby sheets.
The existing front path behavior is unchanged.

Supported implementation ranges: half-width 4–30 mm, upper/lower heights 8–50 mm,
front/back height difference at most 10% of half-width, and upper/lower horizontal
offset at most 25% of half-width. These are tool limits, not normality criteria.
The default target-to-visible-surface tolerance remains 5 mm. Wrong-side,
inverted, missing, nonfinite and off-surface references fail without retaining
partial results. The existing `relief` multiplier applies; `bow_width` does not.

Six paths provide helix relief, antihelix stem/branch, a shallow conchal recess,
lobule and tragus support. They do not create a free-standing rolled rim, cartilage
thickness or an auditory canal. This does not complete anatomical ear modeling.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human/human_ears.py -- runs/human-eye-fit/fitted-eyes.blend runs/human-ear-fit
```

The example reuses the paired-region local subdivision workflow, preserves the
current face source and applies both ears in one reversible result. Only selected
ear patch faces are subdivided. Native geometry and reports are saved without a
render; source/baseline objects remain available and are hidden after success.

Focused Blender 5.2.2 LTS check: `tests/ear_fit_test.py` uses 18/26 mm widths and
44/56 mm heights on two pairs of curved sheets with occluded backing surfaces.
It checks side directions, unchanged Y/Z, opposite/hidden surface protection,
source preservation, caps and rollback, six invalid batches, and the existing
front-path effect/failure check. The human example verifies protection, rollback
and manifold edges. No anatomical accuracy or new rendered-quality claim is made.
