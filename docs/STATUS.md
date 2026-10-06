# Current development status

Updated 2026-10-06. Mesh Workbench is an early Python/JSON toolkit running inside Blender. The completed implementation is `a03b8fab4928116f8fc5406cfc0643023de171ed`; completion records were published in `0e1fd2d4efcea45f43f4cdf4f4f9241d1df9120d`. The next modeling phase is **planned, not implemented**.

## Latest verified result

The [cordless drill study](studies/DRILL_STUDY.md) demonstrates feature-pinned triangle remeshing, UV/material/mask/binding transfer, direct-detail assembly migration and failure rollback. Local artifact: `runs/drill-study-09/drill.blend`; hashes and detailed results are in the [audit](audits/DRILL_AUDIT.json).

- Selected patch: 1,290 to 1,078 triangles; 106 collapses and 60 flips.
- Maximum bidirectional sampled surface error: 0.0847725 mm against a 0.09 mm limit; 2,603 pinned vertices unchanged.
- Six through-vents; 51 modeled parts checked for nonmanifold edges and overlap candidates.
- Fresh-process reopen verifies UVs, masks, bindings, rollback and subsequent assembly editing.
- Windows Blender 5.2.2 and [Linux Blender 4.0.2 CI](https://github.com/shakystar/mesh-workbench/actions/runs/37398919639): 31 integration and 3 host tests pass. Actual host CLI also passes. These are implementation checks, not tests rerun for the documentation reorganization.

## Current boundaries

Remeshing produces baked triangles with sampled distance checks; it is not automatic quad retopology. Topology migration supports directly bound details, not shell/nested dependency propagation. Face IDs are not stable semantic identities. Continuous collision guarantees, complete mechanical internals, manufacturing tolerances and production-ready rigs remain unverified. The drill is an exterior assembly study; functional chuck, latch and trigger mechanisms remain planned work.

## Next work

[Drill assembly roadmap](ROADMAP.md): freeze dimensions/interfaces, reshape connected housing/grip surfaces, implement functional part geometry, propagate nested topology changes, verify constrained motions, and deliver reopenable variant evidence. No modeling implementation is started by this documentation-only planning update.

Use the [documentation index](README.md) for all studies and APIs. Earlier results and then-active goals are retained in [development history](archive/DEVELOPMENT_HISTORY.md).
