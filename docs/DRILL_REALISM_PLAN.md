# Drill realism development contract

## Current authorized scope — 2026-10-23

The user superseded the broad acceptance schedule below. Finish only the visible
fastener-surface, rear-grip edge and trigger-groove defects, integrate the result
into the example generator and recipe, and update the status. Reuse existing tools.
Check only changed geometry and necessary visual views. Do not run OS/version
matrices, full regression suites, noise comparisons or repeated candidate batches.
Run at most one Blender process with two CPU threads; preserve original inputs.
The older milestones below are historical context, not authorization for extra work.
No publication or deployment is authorized.

Fixed 2026-10-09; development started, updated 2026-10-10. **M11-M15 are active and incomplete.** Experimental tool implementation and evidence are tracked in the [progress record](studies/DRILL_REALISM_STUDY.md). Preserve the M6-M10 candidate and its [completed contract](archive/DRILL_SURFACE_ROADMAP.md).

## Scope

Create a more credible original cordless drill through reference-informed proportions, coherent housing surfaces, resolved part interfaces and differentiated materials. The reference family is selected in M11; this plan does not pretend that selection or calibration has occurred. Use one configuration throughout. Reference images, traced data and private assets stay in ignored `runs/`; public recipes and preview images contain only our original procedural design. Record source URLs, usage conditions and hashes in the local reference manifest.

Preserve `runs/drill/drill-surface-06/drill.blend` and generate new candidates. No manufacturer-replica, general retopology, full internal motor, manufacturing certification, arbitrary manual-edit replay or new interactive application is included. This planning update does not implement tools or authorize publication/deployment.

## Required tools

Interfaces below define the target contract. Experimental implementations now exist; the progress record distinguishes tested fixtures from unfinished drill integration. Every new operation requires Python API, JSON dispatch, an asset-free fixture, failure tests and API documentation.

| ID / planned operation | Existing implementation reused | Required development and result | Rejection contract |
| --- | --- | --- | --- |
| T1 `reference_register`, `reference_compare` | `reference.py` analytic masks and comparison | Annotated photo registration with explicit perspective/orthographic camera, scale evidence, landmarks and visibility masks; frozen camera, overlays and per-view residual report. No automatic reconstruction. | Reject degenerate/underdetermined calibration, empty masks, nonfinite coordinates and metric claims without scale. Report exclusions. |
| T2 `form_cage` | Layers, regions, `sectionshape.py` | New `form.py`: bounded trivariate cubic Bezier lattice, 4 x 4 x 4 control offsets in a local frame, weighted region and pinned interfaces; reversible layer with displacement and sampled Jacobian report. | Reject stale selections, unsupported transforms, nonfinite offsets and sampled inverted cells. Preserve source and previous layers on failure. |
| T3 `seam_lip`, `recess_seat` | `shells.py`, `surfacedetail.py`, booleans, variable bevel | Single continuous declared seam chart, ordered path, depth/overlap/clearance and corner radius; create new lip/recess objects and wall/gap/visibility report. | Reject ambiguous projection, chart crossing, excessive curvature/offset intersection, thin walls and opposing-part interference. Preserve both inputs. |
| T4 Replayable detail nodes | `nested.py`, semantic regions, transaction rollback | Persist T2/T3 controls, dependency versions and part-local detail placement; selective regeneration with fresh masks/bindings. | Reject missing/ambiguous roles and unsupported correspondence; late-failure rollback restores objects, attributes and graph. Never silently discard details. |
| T5 `material_finish`, `surface_marking` | `materials.py`, surface anchors | Principled plastic/rubber/metal node groups, seeded procedural roughness/bump in mm, UV/local-frame anchors; original numerals/symbols from bundled procedural stroke glyphs. Preserve unrelated material slots. | Reject invalid scale, missing UV/frame, bad anchors and naming conflicts; preserve shared meshes and prior materials. No automatic arbitrary UV unwrap or host-font dependency. |
| T6 Visual audit manifest | Existing drill review, curvature, reflection and capture tools | Versioned cameras/lights/exposure, model/reference hashes, named defect ROIs; paired clay/stripe/beauty/detail captures and audit. | Reject mismatched comparison settings, missing evidence and unresolved mandatory defects. Scores do not replace image inspection. |

Use existing profiled rings, sweeps, variable bevel, booleans, jaws, actuators and sampled motion checks for chuck/screws/vents/switches/battery details. Do not build duplicate general-purpose tools for those tasks.

## Milestones

Order: M11 -> M12 -> M13 -> M14 -> M15. T6 starts in M11; T4 integration is required before accepting new geometry. Tool fixtures can progress independently of reference collection; final housing acceptance cannot precede M11.

### M11 — Reference, original target and baseline (T1, T6)

- Acquire side/front/rear/three-quarter views of one consistent drill/battery configuration and at least one reliable overall dimension. Record observed versus inferred surfaces. Missing evidence blocks only the dependent acceptance; state the exact missing view/dimension.
- Annotate at least 12 usable landmarks overall. Each calibrated perspective view needs at least six visible points spanning the body, at least two held out from fitting, and documented camera constraints. Underdetermined views remain visual-only.
- Freeze original housing/grip/chuck/battery proportions, interfaces and role definitions. Separate measurements of the source drill from deliberate authored deviations. Source-photo scores and authored-target scores must never be conflated.
- Capture the existing model; register mandatory defects with ROIs: box-like housing, neck/fastener pinching, exposed chuck interior, simplified grip/battery, seam light leaks and faceted trigger grooves.
- Gate: held-out landmark reprojection RMS <= 1% of the visible drill bounding-box diagonal for scored views. Freeze cameras, masks, dimensions, tolerances and source hashes before candidate generation. Do not compensate for a wrong camera by deforming the model.

### M12 — Main proportions and housing continuity (T2, T4)

- Reshape head, rear cover, neck, grip and battery envelope using section controls and the cage. Set chuck/body/grip/battery proportions before fine detail; correct neck transitions and fixed-fastener pinching.
- Compare side/front/rear/three-quarter clay views. Against the frozen authored target, require silhouette IoU >= 0.97 per scored view, per-part IoU >= 0.94 for housing/chuck/grip/battery, landmark RMS <= 1% and p95 contour distance <= 1.5% of the drill bounding-box diagonal. Record every denominator and excluded region. Report commercial-photo comparison separately with authored deviations.
- Retain 1.6-2.6 mm shell walls and nominal 0.8 mm split gap (allowed 0.5-1.1 mm). Mating-frame targets may change only through the documented M11 design, not silently during evaluation.
- Pin displacement <= 0.00001 mm; disabling the layer restores source coordinates within 0.00001 mm; no sampled inverted cells. Reopen and test head width +0.25 mm and grip length +1 mm separately; details remain attached and unrelated nodes remain unchanged.

### M13 — Part structure and assembly seams (T3, T4)

- Resolve chuck nose/recess, three jaws and a consistent authored drill-bit or driver-bit form. Add torque pointer/marking seats, recessed screw seats and vent interior baffles.
- Refine trigger seating, direction switch, grip wrapping/boundaries, battery receiver/shroud, release button and battery case split. Add internal seam overlaps without closing functional vents, jaw openings or the battery exit path.
- Gate: declared solids have finite coordinates and closed boundaries; sampled overlap diagnostics, wall/gap and interface gates pass. Freeze at least 100 visibility rays per seam ROI and block all with intended interior geometry; report functional-opening exclusions. Inspect front/rear/top and backlit seam close-ups.
- Run trigger/latch/battery/jaw sweeps at existing sampling density or finer; retain existing travel ranges unless revised in M11. Test 2/6/10 mm bit cases and restore rest transforms. Reject excessive lip depth and ambiguous seam projection without mutating inputs.

### M14 — Surface finish, materials and markings (T5, T6)

- Correct residual neck/fastener pinching and faceted groove highlights with geometry/bevel edits. Review intentional sharp edges separately.
- Add distinct plastic, elastomer and metal finishes with actual-scale microtexture; original torque numerals, direction symbols and battery indicators. Baseline excludes dirt/wear and copied branding.
- Gate: inspect fixed-camera clay, reflection-band and material images; close every mandatory defect from M11-M13. List residual limitations by ROI; a global curvature average cannot certify completion.
- Capture at least 2000 x 2000 hero plus six orthographic views and six 1000 x 1000 details: chuck, vent/screw, neck/trigger, grip, seam/rear, battery. Start with 128 Cycles samples; compare representative crops at 256 and increase if noise obscures assessed defects. Preserve non-denoised clay/stripe evidence.
- Reopen and verify material slots, seeds, texture scale and marking anchors. Invalid scale/anchor or material creation failure leaves previous materials intact.

### M15 — Editing, recovery and final verification (T1-T6)

- Deliver a self-contained procedural JSON recipe, native model, fixed-view comparisons, machine-readable audit and defect register. Generated files use fresh ignored `runs/drill-realism-*` paths.
- Fresh-process checks cover baseline load, head width +0.25 mm, grip length +1 mm, battery removal/return and all supported bit cases. Verify source hashes, dependency changes, UV/masks, bindings, markings and materials.
- Exercise invalid camera data, stale region, cage foldover, seam rejection, missing role, invalid material, out-of-range parameter and injected late transaction failure. Require structured reasons, intact source/state and nonzero CLI failure exits.
- Run `tests/blender_tests.py` in factory-startup background Blender with autoexec disabled, host tests and affected example recipes. Record actual versions/counts. Previous Windows Blender 5.2.2 LTS / Linux Blender 4.0.2 evidence (46 integration tests each, three host tests) does not verify this phase.
- Completion requires numerical gates, actual native-render inspection, reopened editing/recovery and Windows/Linux runtime evidence. A missing runtime remains an incomplete gate. Local completion, commit, remote CI, publication and deployment remain separate states.

## Gate governance

These are acceptance targets, not observed measurements. If M11 shows that a reference cannot support a measurement, document a narrower claim and replacement criterion before candidate creation. Do not loosen gates after a candidate fails. Interference, geometric error and foldover checks remain sampled; this phase makes no continuous-collision, manufacturing or photorealism certification claim.

### M11 authored evaluation freeze, 2026-10-22

Commercial gallery images lack independent camera/3D-point calibration and exact battery identification. Their published 172 mm head length remains proportional context; 261 mm battery-dependent height is excluded. No commercial-photo reprojection accuracy or manufacturer replica is claimed. For original-design measurements, the replacement is prescribed orthographic cameras verified against native Blender projection, independently authored silhouette/width drawings and ray-defined structural landmarks. This narrower claim is fixed before the first candidate; numerical M12 thresholds are unchanged.

`examples/drill/realism/recipes/part-01/drill-realism-target.json` now specifies the measurement rules. External silhouettes fill enclosed background holes identically in guide/candidate images, while preserving every background region connected to the image boundary. This does not waive the M13 opening/leak gates. Housing/grip split at world Z=108 mm for measurement only. Per-part scores use isolated amodal geometry; visible landmark scores use only the frozen guide visibility list, and missing candidate ray intersections fail. No pixel ROI is excluded from silhouette scoring.

The initial freeze is `runs/drill/drill-realism-frozen-guides-01/recipes/freeze.json`: 24 ray-defined landmarks, 17/17/11/12/11 visible in left/right/front/rear/hero views, respectively; all target/section/generator/baseline-spec hashes recorded. The preceding hand-placed center/axis landmarks remain design annotations and are not substitutes for these scored surface intersections. The freeze establishes an original-design evaluation basis, not full M11 commercial-reference calibration or M12 acceptance. The remaining exact commercial configuration limitation stays explicit.
