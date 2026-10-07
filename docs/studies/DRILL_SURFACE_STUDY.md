# Drill surface refinement

M6-M10 complete, 2026-10-07. [Completion audit](../audits/DRILL_SURFACE_AUDIT.json) | [Visual observations](../audits/DRILL_SURFACE_VISUAL.json) | [Frozen specification](../../examples/drill-surface-target.json) | [Target guide](../assets/drill-surface-target.svg)

This original procedural drill improves the housing sections, grip and separate mechanical surfaces. It is not a manufacturer replica. The earlier [assembly study](DRILL_ASSEMBLY_STUDY.md) and its native files remain preserved.

## Before and after

Both columns use the same frozen camera, light setup, 1000 x 1000 output and 12-sample Cycles render. Images are actual Blender output, with no generative editing. Before: `runs/drill-assembly-r4/baseline/drill.blend`. After: `runs/drill-surface-06/drill.blend`.

| View | Previous assembly | Surface refinement |
| --- | --- | --- |
| Hero | ![Before Hero](../assets/drill-surface-before-hero.png) | ![After Hero](../assets/drill-surface-after-hero.png) |
| Left | ![Before Left](../assets/drill-surface-before-left.png) | ![After Left](../assets/drill-surface-after-left.png) |
| Right | ![Before Right](../assets/drill-surface-before-right.png) | ![After Right](../assets/drill-surface-after-right.png) |
| Front | ![Before Front](../assets/drill-surface-before-front.png) | ![After Front](../assets/drill-surface-after-front.png) |
| Rear | ![Before Rear](../assets/drill-surface-before-rear.png) | ![After Rear](../assets/drill-surface-after-rear.png) |
| Top | ![Before Top](../assets/drill-surface-before-top.png) | ![After Top](../assets/drill-surface-after-top.png) |
| Bottom | ![Before Bottom](../assets/drill-surface-before-bottom.png) | ![After Bottom](../assets/drill-surface-after-bottom.png) |
| Chuck and torque ring | ![Before Chuck and torque ring](../assets/drill-surface-before-chuck-detail.png) | ![After Chuck and torque ring](../assets/drill-surface-after-chuck-detail.png) |
| Rubber perimeter and ribs | ![Before Rubber perimeter and ribs](../assets/drill-surface-before-grip-detail.png) | ![After Rubber perimeter and ribs](../assets/drill-surface-after-grip-detail.png) |
| Trigger grooves | ![Before Trigger grooves](../assets/drill-surface-before-trigger-detail.png) | ![After Trigger grooves](../assets/drill-surface-after-trigger-detail.png) |
| Battery shrouds | ![Before Battery shrouds](../assets/drill-surface-before-battery-detail.png) | ![After Battery shrouds](../assets/drill-surface-after-battery-detail.png) |
| Reflection bands | ![Before Reflection bands](../assets/drill-surface-before-stripes-hero.png) | ![After Reflection bands](../assets/drill-surface-after-stripes-hero.png) |
| Curvature, fixed 0.15 scale | ![Before Curvature, fixed 0.15 scale](../assets/drill-surface-before-curvature-hero.png) | ![After Curvature, fixed 0.15 scale](../assets/drill-surface-after-curvature-hero.png) |

The head now has a sloped roof and crown, with independently controlled rear/front grip width. The chuck has tapered ends and 24 real flutes; the torque ring has 18 flutes and 12 geometric index ticks. Broader rubber patches carry nine raised ribs and a perimeter on each side. Three grooves are cut into the trigger. Battery-fixed side covers have different upper/lower bevel offsets.

Visual limits remain visible: local curvature variation around fixed fastener lands, bright interruptions through the intentional shell split, faceted trigger-groove highlights, and simple battery/rear-cover forms. Sharp vent boundaries are deliberately discontinuous. This is not a Class-A surface or photoreal product-finish claim. Curvature colors are descriptive, not a score that certifies fairness.

## Measured evidence

| Measurement | Final native result | Gate / interpretation |
| --- | --- | --- |
| Dependency graph | 73 nodes, 40 declared part frames, 37 visible mesh solids | Saved and reopened |
| Side outline IoU | 0.99988655 | >= 0.985 against authored guide |
| Section coordinate error | 0.029785 mm maximum | <= 0.15 mm, sampled rays |
| Section-join normal step | 0.037339 degrees maximum | <= 5 degrees |
| Housing walls | 1.944138-2.310632 mm | 1.6-2.6 mm, opposite-skin probes |
| Split gap | 0.799999 mm | 0.5-1.1 mm |
| Actual detail checks | 27 pass | Radius, flute/tick count and depth, groove depth, raised height, cover offsets |
| Native units | Metric, scale 0.001 | One mesh unit = one millimetre |
| Visible solids | 37 pass | Finite coordinates, closed edges, no detected overlap candidates |

Section references use an independently constructed unwarped rounded envelope plus separate scalar evaluation of the frozen width field. The six orthographic render comparisons are visual checks; the numerical IoU is a side-outline measurement. These values measure authored constraints, not similarity to a photographed commercial drill.

The chuck flutes measure 0.7 mm, torque flutes 0.8 mm, trigger grooves 0.25 mm, and raised rib maximum 0.4 mm. Torque tick peak is **0.190211 mm** at the sampled profile row; 0.2 mm is the kernel amplitude bound. Cover bevel offsets are 0.6 mm upper and 0.2 mm lower.

## Local patch reconstruction

| Original master patch | Rebuilt master patch |
| --- | --- |
| ![Original topology](../assets/drill-surface-topology-before.png) | ![Rebuilt topology](../assets/drill-surface-topology-after.png) |

The actual left grip master patch changes from 519 to 487 triangles. It uses 81 splits, 97 collapses, 91 flips and 292 projected relaxation steps. Lower-tail p10 triangle quality improves from 0.272266 to 0.413375; mean quality from 0.475654 to 0.701769; edge-length coefficient of variation falls from 0.505640 to 0.381802. Sampled bidirectional drift is 0.056453 mm against a 0.09 mm bound. All 15,617 pinned vertices have zero movement, and 17,018 untouched polygons retain their original topology/corner UVs.

The nested operation regenerates shells, rubber inserts, ribs and borders, while transferring the tested UV/mask/binding data. The output is mixed polygons and triangles, not a general quad retopology cage. A subsequent parameter change regenerates the procedural root; arbitrary manual root edits are not promised to survive that regeneration. Previous objects and native files remain available.

## Motion, editing and regression

The final native model and a fresh-process width +0.25 mm edit both pass geometry, frames, units, wall/gap, physical rail/latch interface and four motion sweeps. Trigger: 13 poses x 36 pairs; latch: 9 x 36; battery: 41 x 210; jaws: 17 x 105. Battery covers travel with the battery. Separate 6 mm and 10 mm bit cases also pass. Ten sweeps restore rest transforms. Sampling steps remain 0.25 mm trigger/latch, 1 mm battery travel and 0.5 mm jaw diameter. These are discrete interference/distance checks, not continuous collision, strength or manufacturing certification.

Reopening checks analytic/source-corresponding UVs and masks, current projected bindings, unknown parameter rejection and injected late-commit rollback. Actual CLI execution initializes, edits width, reconstructs the root patch and saves a model; its saved geometry and units pass independent inspection. An out-of-range width exits nonzero without producing a result or changing the input hash.

Windows Blender 5.2.2 LTS and [Linux Blender 4.0.2](https://github.com/shakystar/mesh-workbench/actions/runs/37576165857) each pass **46 integration tests**, with 3 host tests. Tested runtime commit: `f227142c6b0a902c16233834fc5382f41db5468c`. Regression includes wrong/missing projection, UV/material seam rejection, stale attributes, bevel cleanup, patch quality rejection, unselected polygon/corner preservation, semantic seed ties and role-shading coordinate preservation.

## Reproduce

Install Blender separately. From a checkout, set `PYTHONPATH=src` and put Blender on PATH or set `BLENDER_BIN`. No external assets or generation service are required.

```sh
python -m mesh_workbench run examples/drill-surface.json --output runs/drill-surface-cli-08
# Expected nonzero exit; this recipe loads the preceding output.
python -m mesh_workbench run examples/drill-surface-rejected.json --output runs/drill-surface-cli-rejected-08
```

The CLI recipe is self-contained. It includes a +0.25 mm width edit before the patch operation, so its native result is not byte-identical to the gallery baseline. Output/log paths must not already exist; use a fresh path, and update the rejection recipe source when changing the success path.

Inside factory-startup background Blender, the included helpers can inspect any corresponding saved surface model:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/verify_drill_surface.py -- runs/drill-surface-cli-08/result.blend runs/surface-check
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/verify_drill_surface_details.py -- runs/drill-surface-cli-08/result.blend runs/surface-details
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/verify_drill_surface_reopen.py -- runs/drill-surface-cli-08/result.blend runs/surface-reopen --rollback
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/drill_surface_review.py -- runs/drill-surface-cli-08/result.blend runs/surface-review hero left right front rear top bottom stripes-hero curvature-hero chuck-detail grip-detail trigger-detail battery-detail
```

`drill_surface.py` builds/reconfigures the authored candidate when the preserved prior baseline is available. `drill_surface_patch.py` reconstructs its master grip patch. `export_drill_surface_recipe.py` regenerates the public recipe from the target specification. `audit_drill_surface.py --help` lists the required local evidence/log inputs; it fails if a required geometry, motion, render hash, source-preservation or regression gate is missing. Generated `.blend` files remain in ignored `runs/`; the public repository contains their recipes, measured audit and native preview images.

Verified local files:

- `runs/drill-surface-06/drill.blend`: gallery candidate with rebuilt master patch.
- `runs/drill-surface-06/reopen/followup.blend`: reopened width +0.25 mm result.
- `runs/drill-surface-cli-08/result.blend`: actual CLI-generated editable result.
- `runs/drill-surface-patch-03/drill.blend`: preserved reconstruction checkpoint.

Exact hashes are in the completion audit. Native evidence paths are local artifacts, not downloadable GitHub assets.

## Tools and rejected attempts

`sectionshape` adds bounded rear/front/crown controls and fixed interface neighborhoods. `detail.profiled_ring` builds real axial/radial details. `detail.variable_bevel` and `edge_box` use per-edge offsets and source-preserving failure recovery. `surfacedetail.paths` builds projected raised ribbons, closed borders or subtractive grooves. `remesh.rebuild_patch` enforces selected-patch quality, boundary and drift gates. Semantic queries can select a uniquely nearest connected component using an explicit seed. See the [API reference](../reference/OPERATIONS.md#surface-refinement).

The first lowered front-roof design failed the unchanged maximum wall thickness; the front roof was revised before reevaluation. An initial patch exceeded the drift bound. Whole-source triangulation then exposed hollow-shell overlaps outside the patch; preserving untouched polygons fixed that behavior. A reopened width edit exposed an unrelated normal-filter island; explicit component seeds resolved the intended region while retaining ambiguity, seam and missing-projection rejection. Revision history is retained in the frozen specification; thresholds were not lowered.
