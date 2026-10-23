# Mesh Workbench - Blender modeling tools for AI agents

Coordinate-driven modeling tools that operate **inside Blender**. Inspect render pixels and mesh data, edit vertices and polygons, combine models, and place patterns on surfaces through reproducible JSON recipes or a Python API. No simulated mouse input or external generation service.

Early **0.1.0** implementation. Built for iterative work by people and coding agents, with explicit failure checks and source-preserving operations.

[Documentation website](https://shakystar.github.io/mesh-workbench/) | [Agent quickstart](docs/AGENT_QUICKSTART.md) | [Documentation index](docs/README.md) | [Current status](docs/STATUS.md) | [Milestones](docs/ROADMAP.md)

## Modeled designs

Actual Blender renders created with this toolkit.

**Current human model, actually rendered:** registered oral volume controls with
sampled-surface fitting, preserved eyelid support, forward gaze and nasal work.
Lip volume is more distinct and local philtrum/lower-fold transitions are
softened with protected lips. Chin projection and the stepped lower surface are
refined. Ear ridges now use continuous curves on a locally refined mesh;
ear thickness is shallow. Neck paths protect the face, and a locally rebuilt
underside patch removes the folded under-chin projection.
Torso front/back and costal/abdominal controls now separate the main volumes; stage C remains
in progress. This is not anatomical validation.
[Torso control evidence and actual comparisons](docs/reference/anatomy/body/TORSO.md).
[Files and folders](docs/WORKSPACE_LAYOUT.md).

[Nose structural audit: actual three-view comparison and sourced relationship map](docs/reference/anatomy/NOSE_AUDIT.md).

![Current eyelid front and oblique views](docs/assets/human/eyes/supported-current.png)

![Current face and chin profile](docs/assets/human/chin/profile.png)

[Chin controls and static face-stage evidence](docs/reference/anatomy/CHIN_CONTOUR.md).

[Current ear curves and remaining limits](docs/reference/anatomy/AURICLE_RELIEF.md#continuous-path-pass).

[Current neck model and bounded underside repair](docs/reference/anatomy/NECK_TRANSITIONS.md#bounded-patch-reconstruction).

![Current neck profile](docs/assets/human/neck/rebuilt-profile.png)

![Current continuous ear ridges](docs/assets/human/ears/continuous-left.png)

[Oral control implementation and actual before/after](docs/reference/anatomy/ORAL_RELIEF.md).

[Active anatomy-tool goal](docs/reference/anatomy/DEVELOPMENT_GOAL.md) |
[Eyelid implementation, comparison and limits](docs/reference/anatomy/EYELID_SUPPORT.md).

[Human scripts and current native location](examples/human/README.md).
[Earlier cavity-stage underside](docs/assets/human/nose/underside.png).

Latest: an adult human proportion blockout in a neutral stance, with preserved
section sources and a separate fused surface. This is an initial silhouette and
proportion study, without detailed anatomy, individual fingers or a rig. The
current pass adds diagram-guided mouth paths: lip contours, separation, philtrum
and the lip/chin fold, with protected regions and reversible edits.
[Generator](examples/human/scripts/human_base.py) · [Scope and checks](docs/STATUS.md)

[Registered anatomy brushes](docs/ANATOMY_BRUSH.md) now use named landmarks,
regional protection, geodesic radius and reversible displacement-limited layers.
Point brushes cover the cranium; path brushes follow the mouth diagram.
The guides are authored for this model.
[Registration diagram](docs/assets/human/human-anatomy-diagram.png).

[Proportional anatomy knowledge](docs/ANATOMY_KNOWLEDGE.md) separates oral, nasal
and periorbital/ear feature relationships from authored ratios. Manual landmarks fit
regional guides to different widths, heights and supported eye tilts. Both eye
regions can share one reversible result; failed batches leave no partial output.
Ear guides use side projection with opposite/hidden-surface protection.
Whole-body knowledge and automatic landmark detection remain unimplemented.

Latest mouth pass: [brush diagram](docs/assets/human/human-mouth-diagram.png).

| Mouth front | Mouth side |
| --- | --- |
| ![Mouth front](docs/assets/human/human-mouth-front.png) | ![Mouth side](docs/assets/human/human-mouth-side.png) |

Earlier lower-face profile:

| Head planes front | Head planes side |
| --- | --- |
| ![Head planes front](docs/assets/human/human-head-front.png) | ![Head planes side](docs/assets/human/human-head-side.png) |

Earlier full-body silhouette and joint-landmark pass:

| Human base front | Human base side |
| --- | --- |
| ![Human base front](docs/assets/human/human-base-front.png) | ![Human base side](docs/assets/human/human-base-side.png) |

Previous: an original fixed-lens compact camera with a satin metal top, textured
grip, concentric lens barrel, clear front element, nine-leaf aperture, top dials
and rear controls. Matching cover outlines replace the earlier protruding seams.
Seated buttons, marked dials and panel screws define the controls. The bottom
battery/card hatch has an actual opening, liner, gasket seat and retracting latch.
The rear panel seats in a body recess with a perimeter gasket and through-holes
for separate screws. Fixed and moving hinge knuckles share one pin axis.
The grip tapers into the body without a projecting cap; the rear panel aligns
with a recessed display and narrow bezel.
[Generator](examples/camera/scripts/compact_camera.py) · [Scope and checks](docs/STATUS.md)

| Refined front | Lens and aperture |
| --- | --- |
| ![Compact camera front](docs/assets/camera/compact-camera-front.png) | ![Lens and aperture](docs/assets/camera/compact-camera-lens.png) |

| Rear controls | Open battery/card hatch |
| --- | --- |
| ![Rear controls](docs/assets/camera/compact-camera-controls.png) | ![Battery/card hatch](docs/assets/camera/compact-camera-hatch.png) |

Previous: a 6 mm two-flute drill bit with a round shank, helical chip channels and
a tapered cutting point. Three chuck jaws contact the shank; the flute interiors
use a rougher metal finish than the lands. This is an original visual model.

![Two-flute drill bit and chuck](docs/assets/drill/base/drill-twist-bit-detail.png)

Previous housing refinement: connected rubber grip with tapered edges, rounded trigger
grooves and reduced housing distortion around the rear screw. The
[self-contained recipe](examples/drill/realism/recipes/part-02/drill-realism.json) and
[generator](examples/drill/realism/scripts/part-01/drill_realism.py) are included. The preview below is an
800px, 32-sample local check; a faint roof highlight transition remains.

![Refined drill realism example](docs/assets/drill/realism/drill-realism-hero.png)

[Rear screw detail](docs/assets/drill/realism/drill-realism-rear-screw.png) ·
[Current scope and verification](docs/STATUS.md)

| Field robot | Work lantern |
| --- | --- |
| ![Field robot](docs/assets/general/images/part-01/field-robot.png) | ![Work lantern](docs/assets/lantern/lantern-final.png) |
| Ray sculpture | Field speaker |
| ![Ray sculpture](docs/assets/sculpture/images/part-02/ray-relief-sparse.png) | ![Field speaker](docs/assets/general/images/part-01/precision-after-hero.png) |
| Asymmetric mouse | Mouse shell separation |
| ![Asymmetric mouse](docs/assets/mouse/images/part-01/mouse-final-hero.png) | ![Separated mouse shells](docs/assets/mouse/images/part-01/mouse-exploded-hero.png) |
| Folding headphones | Folded configuration |
| ![Headphones](docs/assets/headphones/images/part-01/headphone-standard-open.png) | ![Folded headphones](docs/assets/headphones/images/part-01/headphone-standard-folded.png) |
| Refined cordless drill | Chuck and torque detail |
| ![Drill](docs/assets/drill/surface/images/part-01/drill-surface-after-hero.png) | ![Chuck](docs/assets/drill/surface/images/part-01/drill-surface-after-chuck-detail.png) |

See the [four-design portfolio and completion audit](docs/studies/PORTFOLIO.md) for model details and reproduction commands, and the [design journal](docs/studies/DESIGN_STUDIES.md) for revisions and evaluation. The [field speaker recipe](examples/speaker/recipes/field-speaker.json) runs directly through the CLI.

Latest: [drill surface refinement](docs/studies/DRILL_SURFACE_STUDY.md): section-shaped housing, fluted parts, surface ribs/grooves, variable bevel, measured local patch rebuilding and 28 before/after previews. Windows/Linux: 46 integration tests each.

Previous: [editable drill assembly](docs/studies/DRILL_ASSEMBLY_STUDY.md): continuous housing, nested regeneration, constrained jaws/trigger/battery, ten verified native files and Windows/Linux regression evidence.

Previous: [local remeshing and cordless drill](docs/studies/DRILL_STUDY.md): feature-pinned edge operations, UV/mask/binding transfer, atomic assembly migration and saved-file follow-up editing.

Previous: [folding headphones](docs/studies/HEADPHONE_STUDY.md): measured surface repair, explicit subdivision correspondence, section-preserving paths and constrained group hinges across three sizes.

Previous: [regenerating mouse assembly](docs/studies/ASSEMBLY_STUDY.md): persisted dependencies, selective updates, atomic rollback and sampled motion checks, demonstrated on three native variants.

Previous: [asymmetric mouse and measured shell study](docs/studies/MOUSE_STUDY.md), including guide lofts, independent local edits, real wall thickness, panel gaps and deformation-following details. Earlier: [reference-driven speaker refinement](docs/studies/PRECISION_STUDY.md).

## Use with a coding agent

Start with the [agent quickstart](docs/AGENT_QUICKSTART.md), [llms.txt](llms.txt), and [tool manifest](tool-manifest.json). The manifest describes this local CLI; it is not an MCP server or an automatic agent installation protocol. Forks, commercial use, bug reports and pull requests are welcome under MIT. See [Contributing](CONTRIBUTING.md).

## Features

- Orthographic render-to-surface maps: world position, geometric normal, depth, object/face IDs, geometry/camera revision checks.
- Coordinate Grab, Pinch, Smooth and signed normal strokes; path interpolation, pressure, edge-distance neighborhoods, masks, X symmetry and independent layers.
- Multiple models: selected `.blend` append; OBJ/STL/PLY/glTF import; transforms; copies; mesh joining; exact booleans; voxel fusion; indexed-topology morph blending.
- Vertex/edge/face selection by indices or world bounds; vertex growth; precise displacement; subdivision, extrusion, inset, bevel, weld, deletion and triangulation.
- Surface projection and conforming; raised seam curves; repeated real mesh motifs; cylindrical UVs and a procedural woven material.
- Dimensioned boxes, revolved profiles, anchored struts, transported section sweeps, local fairing and conforming relief dots through Python and JSON recipes.
- Reference silhouette metrics, named vertex regions, reversible section profiles, cubic handles, bound mesh seams and candidate comparison/restore.
- Asymmetric guide lofts, source-preserving shell partitions, section cuts, wall/gap gauges and native violation markers.
- Persisted assembly recipes, selective regeneration, measured acceptance, atomic failure recovery and discrete rigid-motion interference checks.
- Curvature maps and reflection diagnostics, pinned quadratic surface fitting, explicit triangle-refinement correspondence, measured section paths and absolute group hinges.
- Local triangle remeshing with fixed feature charts, sampled shape-error gates, UV/mask/material/binding correspondence and direct-detail assembly migration.
- Bounded section controls, profiled fluted parts, per-edge bevel offsets and chart-checked projected grooves/borders.
- Quality-gated local patch rebuilding with preserved unselected polygons and reopened dependency regeneration.
- Simple materials, mesh diagnostics/export, multi-view capture, saved-file checkpoints and structured failure audits.

Topology edits and combinations create new objects. Deformation layers can be disabled independently. Existing inputs and files are preserved.

## Quick start

Install Blender separately and make `blender` available on PATH, or set `BLENDER_BIN` to its executable.

```sh
python -m pip install -e .
mesh-workbench run examples/general/recipes/assembly.json --output runs/other/assembly
mesh-workbench inspect runs/other/assembly/review --pixel 192 192
```

Pixel inspection on the host requires `python -m pip install -e ".[analysis]"`. Official Blender builds include NumPy. Distribution packages may require it separately (Ubuntu: `python3-numpy`). No PyPI `bpy` package is required.

From a checkout without installation:

```sh
PYTHONPATH=src python -m mesh_workbench run examples/general/recipes/polygon-edit.json --output runs/other/polygon-edit
```

PowerShell equivalent: `$env:PYTHONPATH='src'`. Alternatively use the installed `mesh-workbench` command. Output paths must be new; each run produces `result.blend`, `recipe.json`, `audit.json` and requested captures. Logs are stored beside the run directory.

## Recipes and API

See [operation reference](docs/reference/OPERATIONS.md), [design and limits](docs/reference/DESIGN.md), [validation status](docs/STATUS.md), and the asset-free [examples](examples).

```python
# Inside Blender Python, with this package on sys.path
from mesh_workbench import geometry, models

base = models.primitive('cube', 'Base')
top = geometry.selection(base, 'FACE', box=[[-2, -2, .99], [2, 2, 1.01]])
tower = geometry.edit_topology(base, top, 'extrude', 'Tower', delta=[0, 0, .5])
```

This is an API/CLI toolkit, not a finished interactive sculpting application. The current surface camera is orthographic. Pattern anchor spacing does **not** guarantee collision-free geometry. Blending requires matching vertex correspondence. Topology-changing results require fresh selections/maps/masks. No automatic retopology or animation rigging is claimed.

## Tests

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python tests/blender_tests.py
python -m unittest discover -s tests -p "test_*.py"
```

## License

MIT for the original project code, documentation and procedural examples; see [LICENSE](LICENSE) and [dependency licensing](THIRD_PARTY_NOTICES.md). No third-party character models, contest references, textures or proprietary assets are bundled. Included examples are generated procedurally by this repository. Blender is a separate dependency; this is an independent project, not an official Blender product.
