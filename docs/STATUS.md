# Current development status

Updated 2026-10-07. Mesh Workbench is an early Python/JSON toolkit running inside Blender. The completed implementation is `a03b8fab4928116f8fc5406cfc0643023de171ed`; completion records were published in `0e1fd2d4efcea45f43f4cdf4f4f9241d1df9120d`. The precision drill assembly phase is **in progress**; its acceptance gates are not yet complete.

## Latest verified result

The [cordless drill study](studies/DRILL_STUDY.md) demonstrates feature-pinned triangle remeshing, UV/material/mask/binding transfer, direct-detail assembly migration and failure rollback. Local artifact: `runs/drill-study-09/drill.blend`; hashes and detailed results are in the [audit](audits/DRILL_AUDIT.json).

- Selected patch: 1,290 to 1,078 triangles; 106 collapses and 60 flips.
- Maximum bidirectional sampled surface error: 0.0847725 mm against a 0.09 mm limit; 2,603 pinned vertices unchanged.
- Six through-vents; 51 modeled parts checked for nonmanifold edges and overlap candidates.
- Fresh-process reopen verifies UVs, masks, bindings, rollback and subsequent assembly editing.
- Windows Blender 5.2.2 and [Linux Blender 4.0.2 CI](https://github.com/shakystar/mesh-workbench/actions/runs/37398919639): 31 integration and 3 host tests pass. Actual host CLI also passes. These are implementation checks, not tests rerun for the documentation reorganization.

## Current boundaries

Remeshing produces baked triangles with sampled distance checks; it is not automatic quad retopology. The completed baseline supports directly bound topology migration. Nested shell/detail regeneration is now implemented in the active phase and still awaits its full variant/reopen acceptance matrix. Face IDs are not stable semantic identities. Continuous collision guarantees, complete mechanical internals, manufacturing tolerances and production-ready rigs remain unverified. The drill is an exterior assembly study; functional chuck, latch and trigger geometry is under active validation.

## Next work

[Drill assembly roadmap](ROADMAP.md): freeze dimensions/interfaces, reshape connected housing/grip surfaces, implement functional part geometry, propagate nested topology changes, verify constrained motions, and deliver reopenable variant evidence. The M0 dimension brief and guides are recorded in `audits/DRILL_ASSEMBLY_BRIEF.json`. Continuous enclosure and split-shell prototypes pass sampled wall checks; nested regeneration and functional parts are under validation; see the [active implementation record](studies/DRILL_ASSEMBLY_STUDY.md). These preliminary checks do not replace the M1-M5 acceptance evidence.

Use the [documentation index](README.md) for all studies and APIs. Earlier results and then-active goals are retained in [development history](archive/DEVELOPMENT_HISTORY.md).

## Active assembly checkpoint

The version-2 nested graph, continuous housing, functional part geometry and prismatic/radial checks are implemented. Windows Blender 5.2.2 passes 35 integration tests; all 3 host tests and scoped Ruff checks pass. These are the current local checks; Linux and real CLI verification are pending.

Baseline `runs/drill-assembly-05/drill.blend` passes outline IoU 0.9998716, maximum section error 0.031172 mm and sampled junction normal mismatch 0.033664 degrees. Its trigger, latch, battery and three-jaw sweeps pass; 6 mm and 10 mm bit cases also pass. Width +2, length +5, split +1 and local root remesh variants pass their nested wall/gap gates. The remesh changes 80 selected triangles to 78 with sampled drift 0.0102743 mm and zero pinned displacement.

Fresh-process baseline reopening, stale-attribute detection, actual late-commit rollback and a further width +0.25 mm edit pass. Remaining variant reopen checks, full variant motion evidence, final renders, CLI/CI and the completion audit remain open. See the [implementation record](studies/DRILL_ASSEMBLY_STUDY.md).
