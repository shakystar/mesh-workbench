# Next milestones: editable drill assembly

Status: **in progress**. An implementation goal is active. The frozen brief is recorded in `audits/DRILL_ASSEMBLY_BRIEF.json`; all M0-M5 acceptance evidence is still required before completion.

## Objective and baseline

Evolve the current exterior drill into a dimensioned, editable assembly: changes to its housing and grip regenerate dependent shells, cutouts, fittings and surface details, while declared clearances and motions remain valid. Preserve the [completed drill](studies/DRILL_STUDY.md) as the comparison baseline (`runs/drill-study-09/drill.blend`, hash in the [audit](audits/DRILL_AUDIT.json)).

The model remains an original authored design. Planned engineering values below are prototype acceptance targets, not manufacturer specifications or validated production tolerances. Freeze them in M0 before implementation; record any later change and its reason before evaluating a new candidate.

## Milestone sequence

| ID | Modeling deliverable | Reusable tool work | Exit evidence | Dependency |
| --- | --- | --- | --- | --- |
| M0 | Dimension brief, side/front/top guides, exploded part map, interface/contact list | Versioned assembly specification with stable part IDs and coordinate frames | Every moving or connected part names its parent, mating frame, clearance and allowed travel; authored reference and threshold hashes recorded | None |
| M1 | Continuous head-to-grip transition, finger relief, trigger opening, left/right housing and rubber insert regions | Guide-controlled transitions; geometric region selectors independent of raw polygon indices | Same-camera baseline comparison; smooth intended junctions; zero unintended open/nonmanifold edges; section and silhouette measurements meet frozen targets | M0 |
| M2 | Hollow chuck with three jaws, torque ring, housing fastening features, battery rails/latch and trigger guide | Axis/radial part arrays, bore/cut recipes, mating-frame and clearance inspection | Native separate solids; jaw axes converge on bit axis; rail and trigger sections match brief; moving bodies have declared opposing surfaces and stops | M1 |
| M3 | Regenerating master -> housing shells -> vents/bosses -> grip inserts/patterns assembly | Persisted nested graph; semantic region re-resolution; topology/UV/mask/binding migration at each changed stage; staged atomic commit | Three geometry variants and a remesh trial rebuild all affected descendants; unrelated parts stay unchanged; ambiguous mappings and injected mid/late failures restore the entire previous assembly | M2 |
| M4 | Trigger press/release, battery insertion/removal, three-jaw opening/closing | Prismatic/radial constraints, limits and contact classification; sampled interference probes with explicit sample spacing | All declared motion ranges checked; intentional contacts separately reported; planted collision and over-travel failures detected; exact rest transforms restored | M3 |
| M5 | Final assembly, separated views, sections, topology/clearance overlays and three editable variants | Fresh-process validation recipe and machine-readable completion audit | Each saved file reopens, accepts a new dimension edit, regenerates descendants and repeats gates; Windows/Linux tests and real CLI pass | M4 |

Implementation order is M0 -> M1 -> M2 -> M3 -> M4 -> M5. Build tools from the actual part/model failures at each stage; do not defer geometric validation until the final render.

## Proposed numerical gates to freeze in M0

| Item | Proposed gate | Measurement |
| --- | --- | --- |
| Model units | Millimetres, fixed world/part frames | Bounds, transforms and saved specification |
| Housing | Nominal 2.0 mm; sampled wall >= 1.6 mm | Opposite inner/outer surface probes, including near vents, openings and transitions; missed/ambiguous probes fail instead of disappearing |
| Housing split | Nominal 0.8 mm total; sampled gap 0.5-1.1 mm | Paired boundary samples, separately from fastener/contact interfaces |
| Constrained remesh | Maximum sampled drift <= 0.09 mm; fixed boundaries <= 1e-5 mm | Bidirectional vertex/edge/centroid probes and saved fixed-vertex pairs |
| Smooth housing junction | Position mismatch <= 0.05 mm; sampled normal mismatch <= 5 degrees | Paired junction samples; explicit sharp seams excluded by specification |
| Interface alignment | Frame position <= 0.05 mm; axis angle <= 0.5 degrees | World-space mating frames |
| Non-contact moving interfaces | Sampled clearance >= 0.2 mm | Opposing-surface distances and triangle intersections at every sampled pose |
| Trigger | 0-3 mm translation | Endpoints and <= 0.25 mm pose increments |
| Battery | 0-40 mm slide; final pose fully disengaged | Endpoints and <= 1 mm increments; rail/latch conditions checked separately |
| Chuck | Three jaws accommodate 2-10 mm bit diameters | Symmetric axis/radial positions; diameter increments <= 0.5 mm; intended bit contact reported explicitly |
| Attribute transfer | Mask weight error <= 1e-5; UV error <= 1e-4 on an independent known field | Analytic fixtures plus preservation of actual seams/material boundaries; missing/ambiguous mapping rejects the operation |
| Recovery | Original graph, coordinates, attributes, object/mesh sets and visibility unchanged on failure | Inject failures during child build, attribute transfer, validation and commit; compare snapshots |

These are sampled geometric gates, not continuous collision or strength proofs. If M0 exposes an infeasible travel or interface, revise the authored design and brief before evaluating it; do not relax a threshold solely to make a failing model pass.

## Required variant and failure matrix

- Grip width +2 mm: regenerate grip insert, housing transition and tactile pattern; retain independent chuck and battery geometry where inputs are unchanged.
- Grip length +5 mm: regenerate affected interfaces and connected parts; preserve declared assembly frames and allowable travel.
- Housing split displacement +1 mm: re-resolve both shell regions, regenerate walls and nearby cutouts, and verify the resulting gap and wall measurements.
- Local master remesh: migrate nested shell/detail correspondence with explicit normal, distance, chart and region checks; no nearest-surface jump to the opposite wall.
- Reject unknown part IDs, dependency cycles, empty/ambiguous semantic regions, stale topology, wrong-side transfer, thin walls, excessive travel and unintended collision.
- Include disconnected nearby surfaces and UV/material boundaries in fixtures. Zero nonmanifold edges alone does not satisfy surface quality, thickness or assembly checks.

## Planned artifacts

Names below are deliverables to create during implementation, not existing links:

- `examples/drill-assembly-target.json`: frozen dimensions, reference provenance, part IDs, interfaces and acceptance gates.
- `examples/drill_assembly.py`: reproducible construction, variants, nested regeneration and motion inspection.
- `examples/verify_drill_assembly.py`: fresh-process migration, follow-up edit, motion and rollback audit.
- `examples/drill-assembly.json`: public host-CLI exercise including one successful nested edit and a separately recorded rejected edit.
- `runs/drill-assembly-*/{baseline,grip-width,grip-length,split-shift}/drill.blend`: preserved source and native variants, with renders and per-variant measurements; a remesh trial is recorded separately.
- `docs/studies/DRILL_ASSEMBLY_STUDY.md`, `docs/audits/DRILL_ASSEMBLY_AUDIT.json`, `docs/assets/drill-assembly-*.png`: public before/after evidence and completion matrix.

Extend the existing assembly, shell, attachment and motion APIs where possible. Decide new module boundaries after M0 identifies the missing operations; the tool/API names are not frozen in this plan.

## Completion boundary

All six milestones, all four change scenarios, all required failure classes and the fresh-process checks must have recorded evidence before completion. A render, a passing mesh-validity test or the ability to move a separated part is insufficient. Internal motor/gearing simulation, electrical design, material strength, injection-mold tooling and production certification are outside this phase; functional mechanical geometry and the specified assembly motions are inside it.
