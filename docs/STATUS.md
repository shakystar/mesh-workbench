# Development status

Version 0.1.0, initial open-source extraction. Implementation includes coordinate sculpting, multi-model assembly, explicit polygon editing and surface patterns. It is an API/CLI package; no finished interactive UI is claimed.

Validation is recorded after executing Blender integration tests and procedural examples. Generated files are kept in ignored `runs/`; only asset-free preview images are published. Model assets from the originating project are not part of this repository.

Remaining limitations: orthographic maps, fixed topology for morph blending, approximate edge-path distances, no general retopology, no full pattern collision solver, no arbitrary-surface UV optimizer, and no animation rigging. OBJ and native Blender imports have direct regression coverage; additional import formats use Blender's standard operators and require format-specific fixtures for broader coverage.

## Executed local verification (2026-10-05)

- Blender 5.2.2 LTS on Windows: 7 integration tests passed, process exit 0. Coverage includes numerical displacements and layer restoration, polygon edits/manifold extrusion, join/boolean/voxel fusion/morph blending, projection and real mesh patterns, masks/stale data, disconnected-sheet protection, symmetry, OBJ and native Blender import, saved-file reopen.
- Python 3.12: 3 CLI rejection tests passed.
- Assembly and polygon-edit recipes ran through the host CLI, each with Blender exit 0 and a complete audit. Both actual rendered previews were inspected.
- Wheel packaging succeeded. Public files scanned for project-specific character names, local user paths and credential patterns; none found.
- Linux CI (Ubuntu 24.04, distribution Blender 4.0.2) passed the same 7 Blender tests and 3 host CLI tests. Initial missing NumPy dependency was corrected. Evidence: https://github.com/shakystar/mesh-workbench/actions/runs/37277671758 .
- The wheel was installed into an isolated directory and its CLI entry point executed successfully.
- Public repository: https://github.com/shakystar/mesh-workbench (GPL-3.0-or-later).

## Active design iteration (2026-10-05)

Two original designs now exercise the tool in actual modeling: a field robot and work lantern. Both were rendered, visually evaluated, revised and reopened for coordinate/mesh verification. See [design journal](DESIGN_STUDIES.md) for before/after findings, reproducible commands, measured geometry and unresolved defects.

Added dimensioned rounded boxes, profile revolutions and two-anchor struts in the Python API. Local Blender 5.2.2 LTS: 8 integration tests and 3 host tests passed. Evaluated final visible mesh parts had no nonmanifold edges; this is not a collision/rig/production validation. New work has not yet been independently verified on Linux.

Goal continues: try additional design families, use captured surface data for local refinement, and extract tools from demonstrated failures.

## Organic modeling iteration (2026-10-05)

- Added an original ray sculpture and actual render-coordinate-driven symmetric Grab. Final body: 14,850 vertices, 5,966 modified. Independent reopen test verifies saved arrays, disable/restore, 4,994 unchanged central vertices and mirror displacement error below 2.82e-7.
- First narrow geodesic result was visually rejected for abrupt wing curvature; revised influence covers the wing thickness. Material boundaries and tail-root proportions were also revised. Separate tail junction and simple anatomy remain unresolved.
- Added elliptical section sweep with transported frames and editable triangle cap domains. Reused it to replace the lantern's overlapping handle rods with a continuous rounded tube.
- Nine Blender integration tests passed locally after the final sweep changes. Previous product-study CI passed on Linux: https://github.com/shakystar/mesh-workbench/actions/runs/37279692223 .
- Actual previews and reproduction commands: [design journal](DESIGN_STUDIES.md). Goal remains active; persistent model edits and tool reuse are demonstrated, not expert-level organic modeling.

## Organic junction correction (2026-10-05)

- Found a defect missed by previous manifold checks: 328 nonadjacent overlap candidates in the old ray body. Width-dependent end camber corrected the source; exact union then worked. Empty Boolean UNION results are now explicitly rejected and cleaned up.
- Added local reversible two-pass fairing, component counts and overlap-candidate diagnostics. Rejected three overly strong edits and verified complete rollback. The accepted weak union fairing had negligible visual benefit.
- Compared a continuous-section alternative and selected it from actual close-up renders. Final ray: one component, 18,946 vertices, 18,944 faces, zero boundary/nonmanifold edges and zero nonadjacent overlap candidates. Saved-file verification passes; the diagnostic is not a complete self-intersection proof.
- Ten Blender integration tests passed; saved join/rejection and continuous-ray verification also passed in fresh processes. Prior commit Linux CI passed: https://github.com/shakystar/mesh-workbench/actions/runs/37281114724 .
- Preferred example: `organic_study.py -- NEW_OUTPUT --continuous`. Journal retains the rejected alternatives and remaining work. Goal stays active.

## Conforming surface motifs (2026-10-05)

- Modeled and compared 48-spot and 32-spot relief designs; selected the sparse layout from whole/detail renders.
- Added `relief.dots`: per-vertex projection, closed raised motifs, individual radii, conservative inter-motif spacing and sampled top-clearance rejection. Target geometry is preserved exactly.
- First attempt had six edge-midpoint penetrations missed by face-center-only checks. Corrected clearance and verified all 9,248 sparse probes positive after saved-file reopen. Target file hash and vertex arrays remain unchanged.
- Eleven Blender integration tests passed locally. Prior junction changes passed Linux CI: https://github.com/shakystar/mesh-workbench/actions/runs/37283321666 .
- Reproduction, actual previews and limitations are in the design journal. Python API additions still need recipe integration; goal continues.
