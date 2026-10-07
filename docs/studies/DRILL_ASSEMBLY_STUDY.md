# Editable drill assembly - implementation record

Status: **in progress**. The [roadmap](../ROADMAP.md) remains the completion contract. No M1-M5 completion claim is made by this record.

The authored [dimension brief](../../examples/drill-assembly-target.json) is frozen at revision 3; its [audit](../audits/DRILL_ASSEMBLY_BRIEF.json) records the construction additions and unchanged acceptance gates. The previous exterior drill is preserved at `runs/drill-study-09/drill.blend`.

## Implemented work under validation

- A continuous guide-built enclosure, closed offset skin and left/right partitions. Exact Boolean cuts retain named deform groups, corner UV data and material roles. Explicit tessellation resolves collinear Boolean edge subdivisions.
- Geometry-based semantic regions with connected-component checks. Projected rubber inserts have explicit source correspondence and reject unsupported holes, wrong sides and UV/material discontinuities.
- Nested version-2 recipe graph: geometry or frame dependencies, selective regeneration, stable logical part IDs and source-preserving physical revisions. Staged build/transfer/validation/commit failures restore the previous graph, objects, meshes and visibility.
- Dimensioned chuck, three radial jaws, trigger/stop/guide, captured battery rails and latch. Revision 3 adds opposed housing receivers, clearance bores, slotted screws and a captive latch sleeve.
- Absolute prismatic/radial channels, battery/latch interlock, travel limits and explicit intentional-contact records. Discrete interference probes combine triangle overlaps, conservative bounding-box distances, ray-parity containment and a float64 solid-angle fallback for ambiguous rays.

## Preliminary evidence

`runs/drill-assembly-04/drill.blend` was generated, reopened and rendered in hero, side and exploded views. Its sampled walls measure 1.9980-2.1456 mm with no missing probes; the split gap is 0.800003 mm. After correcting concave-surface containment and float32 ray advancement, all four declared motion sweeps pass in `runs/drill-assembly-04/motion-winding/`. These are revision-2 geometry results, not acceptance of the added revision-3 hardware.

Revision-3 geometry is saved at `runs/drill-assembly-05/drill.blend`; its construction, wall and split checks pass. Three dimension variants and a root-remesh trial are being evaluated. New-process follow-up edits, the 6/10 mm bit cases, final geometry/visual evidence, real CLI runs and Linux CI remain required.

Windows Blender 5.2.2 passed 34 integration tests at the first assembly checkpoint. Later containment precision changes and added hardware still require the final regression run. Test startup uses factory settings and does not install global add-ons.

## Reproduce the work in progress

```sh
blender --background --factory-startup --python-exit-code 2 --python examples/drill_assembly.py -- runs/drill-assembly-new
blender --background --factory-startup --python-exit-code 2 --python examples/drill_assembly_variants.py -- runs/drill-assembly-new/drill.blend runs/drill-width-new grip-width
blender --background --factory-startup --python-exit-code 2 --python examples/drill_assembly_motion.py -- runs/drill-assembly-new/drill.blend runs/drill-motion-new
blender --background --factory-startup --python-exit-code 2 --python examples/drill_assembly_render.py -- runs/drill-assembly-new/drill.blend runs/drill-assembly-new/review
```

All output directories must be new, except the render directory. The motion script writes per-channel evidence; inspect each `passed` result. A render or successful process exit alone does not certify the assembly.
