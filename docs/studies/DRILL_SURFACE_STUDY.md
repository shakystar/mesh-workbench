# Drill surface refinement - active study

Status: **in progress**. [M6-M10](../ROADMAP.md) remains the completion contract. [Frozen brief](../audits/DRILL_SURFACE_BRIEF.json), [target specification](../../examples/drill-surface-target.json), and [six-view/detail guides](../assets/drill-surface-target.svg) precede candidate evaluation. The M0-M5 assembly remains preserved.

## Current native evidence

- `runs/drill-surface-02/drill.blend`: section-controlled housing and grip; original four motion sweeps pass. The first lowered front-roof candidate was rejected by unchanged wall gates; revision 2 restores bore clearance.
- `runs/drill-surface-03/drill.blend`: tapered/fluted chuck and torque ring. Independent dense side outline IoU 0.99988655; sampled section-coordinate error 0.029785 mm; section-join normal mismatch 0.037339 degrees. The section reference includes a separately built unwarped rounded envelope and independent scalar evaluation of the frozen width controls.
- `runs/drill-surface-04/drill.blend`: broader rubber patches with real ribs/perimeter, three subtractive trigger grooves and two battery-fixed side shrouds. All four sweeps pass, checking 36/36/210/105 opposing pairs per pose.
- `runs/drill-surface-05/drill.blend`: additional torque index ticks, variable top/bottom/vertical shroud bevel offsets and declared cover frames. Wall/gap checks pass; final motion and visual evidence still required.
- `runs/drill-surface-patch-03/drill.blend`: actual master grip patch rebuilt and dependent shells/inserts/ribbons regenerated. 519 to 487 selected triangles; 81 splits, 97 collapses, 91 flips and 292 projected relaxation steps. Selected p10 quality 0.272266 to 0.413375; edge-length coefficient of variation 0.505640 to 0.381802. Sampled drift 0.056453 mm <= 0.09; 15,617 pinned vertices unchanged. All 17,018 untouched polygons are retained.

The first patch candidate exceeded shape error; the second exposed inner-shell overlaps outside the selected patch because whole-source triangulation changed offset normals. `rebuild_patch` now retains original unselected polygons and their exact corner UVs. Legacy `remesh` retains its original default behavior; polygon preservation is optional there.

## Tool additions

- `sectionshape`: bounded independent rear/front/crown width fields, fixed interface neighborhoods and monotone width checks.
- `detail.profiled_ring`: genuine radial flutes, axial taper/chamfers and index tick geometry, fixed inner clearance profile.
- `detail.variable_bevel` / `edge_box`: per-edge offsets, source preservation, stale-mask rejection and failure cleanup. Proven global affine UV/mask fields transfer exactly; other fields retain native Blender interpolation. Arbitrary chart reconstruction is not implied.
- `surfacedetail.paths`: projected raised ribs, closed borders and subtractive grooves. Explicit chart correspondence; missing support, wrong-facing rays and UV/material discontinuities reject the operation.
- `remesh.rebuild_patch`: chart-constrained edge operations and projected relaxation; requires improved selected p10 triangle quality and edge-length variation. Boundary/seam pins, sampled drift and correspondence remain enforced.

Windows Blender 5.2.2 LTS passes 44 integration tests. The latest Linux CI, actual CLI, final saved-file follow-up edit, six-view before/after and detailed completion audit remain pending. No M6-M10 completion claim is made by this checkpoint.
