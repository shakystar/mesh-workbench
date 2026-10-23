# Proportional anatomy knowledge and registration

The first reusable module is the neutral oral region. It contains six semantic
feature groups, their qualitative relationships, 20 normalized controls and seven
brush paths. It is no longer tied to one model's absolute coordinates.

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
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/fit_anatomy.py -- runs/human-lower-face-final/human-lower-face.blend "Lower face refinement" examples/human-mouth-target.json runs/human-mouth-fit-visible
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
| Nose, eye sockets, ears | No reusable knowledge modules yet |
| Skull, neck, torso, limbs, hands and feet | No reusable knowledge modules yet |
| Automatic landmark detection | Not implemented |
| Pose/expression, age or body-type models | Not implemented |
| Anatomical accuracy across human subjects | Not validated |

Next module: nose base and alar region, linked to the existing nose-base and
philtrum references. Whole-body variation requires additional regional modules
and independently registered models; the current two fixtures do not establish it.
