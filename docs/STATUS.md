# Current development status

Updated 2026-10-07. The editable drill assembly M0-M5 is complete. Runtime implementation: `ba465916831c1d4889c6f09c027803e732ab1ebc`. Final evidence is in the [study](studies/DRILL_ASSEMBLY_STUDY.md) and [completion audit](audits/DRILL_ASSEMBLY_AUDIT.json).

## Latest verified result

- Continuous hollow housing/grip, functional three-jaw geometry, fastening receivers, trigger guides and captured battery rails/latch.
- 70 dependency nodes, 38 declared IDs/frames and 35 visible mesh objects; persisted native millimetre units.
- Width +2 mm, length +5 mm, split +1 mm and local remesh all regenerate affected descendants while preserving independent parts.
- Five native files and five fresh-process follow-up edits pass geometry, frame and interface checks. Forty motion sweeps pass and restore rest transforms.
- Baseline outline IoU 0.99987161, maximum section error 0.031172 mm; local remesh sampled drift 0.0102743 mm with zero pinned movement.
- Stale attributes, unknown IDs, injected build/transfer/validation/commit failures, collisions and travel limits are tested. Actual CLI success and rejection preserve source files.
- Windows Blender 5.2.2 LTS and [Linux Blender 4.0.2](https://github.com/shakystar/mesh-workbench/actions/runs/37568855075): 37 integration tests each; 3 host tests pass.

Native baseline: `runs/drill-assembly-r4/baseline/drill.blend`. Variant and follow-up locations, hashes, reproduction and eleven previews are recorded in the study/audit. The previous `runs/drill-study-09/drill.blend` remains unchanged.

## Boundaries and next work

The [roadmap](ROADMAP.md) retains the completed acceptance contract. M6-M10 surface refinement is now active; see the [new brief](audits/DRILL_SURFACE_BRIEF.json). The earlier assembly completion does not certify the new surface candidate.

The model is an original authored assembly, not a manufacturer replica. Collision/distance checks are sampled; no continuous collision, strength or manufacturing claim is made. Local remeshing bakes triangles; general quad retopology and seam-aware projected patch reconstruction are unsupported. This remains an early Blender Python/JSON toolkit.

Use the [documentation index](README.md) for APIs and earlier studies; historical checkpoints remain in [development history](archive/DEVELOPMENT_HISTORY.md).

## Active surface refinement checkpoint

The [M6-M10 surface study](studies/DRILL_SURFACE_STUDY.md) now includes section-shaped housing, fluted/tapered parts, projected ribs/grooves, variable edge offsets and bounded patch reconstruction. Windows Blender 5.2.2 passes 44 integration tests. The actual 519-to-487-triangle master patch improves lower-tail quality and edge-length spread, preserves unedited polygons, and regenerates the nested model within wall/gap limits. Final CLI, Linux, fresh-process edits and visual delivery remain required.
