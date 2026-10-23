# Current development status

Workspace organization: all folders outside `.git` and the approved `.venv`
exception have at most ten direct files. 4,938 files were grouped by topic/type;
source imports, example resources and documentation links were updated.
Layout violations: zero. Import/CLI/wheel checks passed; no new renders.
[Locations and move maps](WORKSPACE_LAYOUT.md).

## Neck guide / unresolved underside projection - 2026-10-24

Added `mesh_workbench.regions.neck.compile_paths` and sourced
`neck-transition-v1`. Five authored submental/lower-neck/clavicle skin paths
compile with visible-surface registration and a facial protection height.

Blender 5.2.2 LTS: source/topology, 88,934 protected vertices, 29,478 unchanged
face/ear vertices, all-layer rollback, two invalid inputs, late failure cleanup,
saved-coordinate readback and input hash pass. Maximum movement 1.61868 mm.
One process at a time, two CPU/numerical threads; all exited.

Visual gate OPEN: both front-projected and inferior-oblique submental relaxation
leave a thin lower-chin projection in the saved-model profile. The first pass
had matched before/after renders; the changed projection used two new result
views and hash-matched source views. A read-only visible-object audit rules out
overlapping preserved heads. Next: directly inspect/reshape the local underside,
not another repetition of the same smoothing. Stage B/full goal unfinished.
Current trial native: `runs/human/neck-submental/neck-transitions.blend`.
[Sources, API, actual views and unresolved gate](reference/anatomy/NECK_TRANSITIONS.md).

## Continuous auricle paths and local refinement - 2026-10-24

`anatomy_ear.compile_surface_paths` converts the existing knowledge anchors to
projected cubic paths. The example refines only ear face selections on a new
snapshot, then applies six shaping paths and one ridge-collar fairing per ear.
Point-bulge fitting is superseded for the current character, with old inputs
and trial outputs preserved.

Blender 5.2.2 LTS: 83,081 -> 91,375 vertices, every original vertex retained;
82,201 protected vertices unchanged. Source/refined-input preservation, 14-layer
rollback, overlapping-ear rejection, injected second-ear failure cleanup,
zero nonmanifold edges, saved readback and input hash pass. Maximum combined
displacement 1.49981 mm. One process at a time, two CPU/numerical threads; exited.

Two initial continuous-path views exposed sharp attachments, prompting collar
fairing. The two final matched 640px/16-sample views show continuous ridges rather
than isolated bulges. Ridge continuity is reviewed; shallow thickness and stylized
attachment remain limits. Stage B is unfinished; next is neck/chin/shoulder
transition and the under-chin band. Full goal active.
Current native: `runs/human/continuous-ears-faired/continuous-ears.blend`.
[API, topology policy, actual comparison and limits](reference/anatomy/AURICLE_RELIEF.md#continuous-path-pass).

## Stage B auricle relief trial / visual gate open - 2026-10-24

Added `anatomy_ear.compile_relief` and atomic `apply_relief` for one/two ears.
The existing auricle knowledge now includes sourced scapha/triangular-fossa
relationships, separate from authored midpoint controls. Each ear has 21
surface-fitted controls and its own reversible layer.

Blender 5.2.2 LTS: 498 changed vertices per ear, 1.83345 mm maximum movement;
82,041 protected vertices unchanged. Source/topology, paired rollback, two
invalid registrations, injected second-ear failure cleanup, saved-coordinate
readback and input hash pass. Maximum surface residual 0.03510 mm. Four matched
640px/16-sample renders inspected, one process/two CPU/numerical threads; exited.

Visual gate remains OPEN: deeper relief is visible, but the rim/inner ridges are
scalloped around controls, especially in the left oblique view. Next is continuous
ridge shaping and local mesh resolution, not neck work yet. Stage B and the full
goal remain unfinished. Current trial native:
`runs/human/auricle-relief/auricle-relief.blend`.
[Actual views, API, sources and unresolved visual issue](reference/anatomy/AURICLE_RELIEF.md).

## Chin contour / static face-stage handoff - 2026-10-24

Added sourced `chin-contour-v1` and `anatomy_fit.compile_chin_contour` with nine
visible-surface controls. The example first fairs the stepped lower chin, then
fits projection/width controls while retaining both reversible layers.

Blender 5.2.2 LTS: source/intermediate/topology preservation, 19,355 unchanged
upper-face vertices, combined rollback, three invalid inputs, late-failure
cleanup, saved-coordinate readback and input hash pass. Maximum combined movement
1.53701 mm; central setback 1.49971 mm; maximum surface residual 0.00684 mm.
Two matched input and two saved-output 640px/16-sample views inspected. One
Blender process at a time, two CPU/numerical threads; processes exited.

The lower-chin profile is smoother; frontal change is small. A shallow band
remains at the neck attachment. Stage A's bounded static face-tool criteria have
evidence; this is not a finished realistic head or anatomical validation.
Next: stage B ears/neck, including the under-chin attachment. Full goal active.
Current native: `runs/human/chin-contour/chin-contour.blend`.
[Knowledge, API, views and face-stage evidence](reference/anatomy/CHIN_CONTOUR.md).

## Protected oral transition fairing - 2026-10-24

`anatomy_fit.compile_oral_transitions` derives two bounded fairing paths from
the registered philtrum and lower-fold landmarks. The lip band and nose are
excluded. Existing geodesic volume-preserving relaxation is reused;
`surface_brush` now rejects changed polygon reversal or collapse before a layer
is written. No anatomical dimensions are inferred.

Blender 5.2.2 LTS: 63 philtrum and 200 lower-fold vertices changed; maximum
combined movement 0.86820 mm. 81,755 out-of-region vertices and all 988 lip-band
vertices are unchanged. Source, topology, layer rollback, invalid second-stroke
cleanup, injected layer-finish failure, saved-coordinate readback and input hash
pass. Minimum polygon area ratios are 0.59834/0.79306; stored volume differences
are 0.000037/0.001172 mm3. One Blender process, two threads, exited.

Two matched 640px/16-sample saved-model views were compared with the previous
oral-relief images. The lower-fold transition is slightly softer; this is a
limited local change. The broad angular chin still needs silhouette work.
Next: chin projection and jaw/cheek transition, preserving the finished local
oral controls. Stage A and the full goal remain incomplete.
Current native: `runs/human/oral-transitions/oral-transitions.blend`.
[API and actual views](reference/anatomy/ORAL_RELIEF.md#protected-transition-fairing).

## Oral relief and sampled-surface fitting - 2026-10-24

`anatomy_fit.compile_oral_relief` compiles 20 registered controls from the existing
oral knowledge module. Upper/lower lip projection, seam recession, philtral
pillars and the lower fold have independent authored displacement parameters.
`curve_fit` optionally solves against barycentric mesh samples: the initial
0.25589 mm target error is reduced to 0.02252 mm without relaxing checks.

Blender 5.2.2 LTS: 617 changed vertices, 1.40372 mm maximum displacement;
source/topology, 81,668 region-protected vertices, nose/eye protection, rollback,
four invalid inputs, injected late failure cleanup, native coordinate readback
and unchanged input file pass. Four matched 640px/16-sample before/after renders
were inspected. One process, two CPU/numerical threads; Blender exited.
The lip volumes are more distinct; philtrum termination and the coarse lower
fold remain visually unfinished. Next is their transition into surrounding skin
and chin. Face stage A and the full goal remain open.
Current native: `runs/human/oral-relief/oral-relief.blend`.
[Source relationships, API, images and limits](reference/anatomy/ORAL_RELIEF.md).

## Eyelid skin transition reviewed - 2026-10-24

The goal remains active. The static eyelid-connection/gaze substep now has
front/oblique review evidence after tapering displacement through its skin collar.
The source geometry is not smoothed: registered margin/return displacements are
pinned and only the surrounding displacement field is diffused. Sliver-related
vertices keep the original fit; polygon reversal/collapse rejection is unchanged.
Left/right collars contain 418/423 vertices with 43/35 sliver guards.

Blender 5.2.2 LTS: prior margin-clearance range, nose/source/topology preservation,
rollback, two registration failures, late failure cleanup and saved-coordinate
readback pass. Two 640px/16-sample renders were inspected and the pinched corner
transition is improved. One process, two CPU/numerical threads; Blender exited.
Current native: `runs/human/supported-eyelids-collar/supported-lids.blend`.
Next: lips/philtrum/chin structural review and lip-boundary/volume work.
Face stage A and the overall goal are incomplete; tear anatomy and dynamic lids
are not claimed. [Updated evidence](reference/anatomy/EYELID_SUPPORT.md).

## Active anatomy-tool goal / eyelid support - 2026-10-24

The user-authorized [goal contract](reference/anatomy/DEVELOPMENT_GOAL.md) is
active: face -> ears/neck -> torso -> arms/hands -> legs/feet -> integration ->
second face/body configuration. Clothing/hair, arbitrary-mesh automation and
production rigs are excluded from this goal. No new compatibility/full-suite work.

[First implementation and actual renders](reference/anatomy/EYELID_SUPPORT.md):
`eyelid_fit.fit` registers existing lid margins to explicit spherical supports
with a reversible layer. Orbital orientation and gaze are separated in the
example. `eyelid_fit.knowledge()` exposes sourced relationships, authored-model
assumptions and limits; it is not an `anatomy_fit` normalized-path module.

Blender 5.2.2 LTS: 113 margin samples per eye, stored radial clearance
0.110-0.292 mm, maximum movement 1.63795 mm; 81,761 unaffected vertices and
11,786 nose-region vertices preserved. Source head/globes, topology, rollback,
two invalid registrations, injected late failure and saved-coordinate readback
pass. Knowledge-resource loading and source-key references pass. One Blender
at a time, two CPU/numerical threads, two 640px/16-sample views; all processes exited.

Visual gate remains OPEN: forward gaze is corrected, but medial lid-corner
pinching remains. Next action is local corner/skin-transition correction, then
oral/philtrum/chin work. Do not call the eye stage or overall goal complete.
Current native: `runs/human/supported-eyelids/supported-lids.blend`.

## Tip and upper-alar volume refinement - 2026-10-24

[Current renders and comparison](reference/anatomy/TIP_ALA.md).
Seventeen registered controls soften the central tip projection and add modest
paired tip/upper-alar volume. The exact 1,372 vertices added or moved by entrance
construction are protected; the entire deformation starts above that patch.
A new `MW tip and alar volumes` layer preserves topology and the original object.
`curve_fit` now accepts an optional validated layer label; its default is unchanged.

Blender 5.2.2 LTS: maximum displacement 1.44309 mm, 2,782 changed vertices,
78,004 region-protected vertices, zero entrance-patch displacement. Source,
topology, layer rollback, invalid-label rejection and saved-native coordinate
readback pass. Three 640px/16-sample views were rendered with two CPU/numerical
threads and one Blender process, which exited. All three views were inspected.
The change is modest; protected lower alae
and regular aperture shapes remain limits. This is not anatomical validation.
Native: `runs/human/tip-ala-refined/tip-ala.blend`; diagram/report beside it.

## Connected nasal entrances - 2026-10-24

[Current renders, comparison and API](reference/anatomy/NASAL_ENTRANCES.md).
`nasal_entrance.build` replaces both registered ellipsoid cutouts with connected
skin-following shoulder/rim/interior patches on a new topology snapshot.
The exterior-tangent transition and local collar fairing address the visible
craters/seam wrinkles found in intermediate renders. Aperture/interior rings
remain fixed during fairing. Each side uses a 70-vertex boundary and 630 new faces.
This is authored surface construction with a short blind interior, not a nasal
airway, tissue-thickness model or anatomically validated human library.

Blender 5.2.2 LTS: source preserved, 77,985 out-of-region vertices unchanged,
invalid registration rejected, injected second-patch failure leaves no output.
Both central depths read 5.80 mm; no nonmanifold/inconsistently oriented edges.
Final native readback confirms source layers and explicit exclusion of stale
topology-bound selections from the output. Front/profile/basal-oblique renders
were inspected; final visible collar wrinkles were removed. Global geometric
self-intersection and airway correctness are not established.

Native: `runs/human/nasal-entrances-smooth/nasal-entrances.blend`.
Registration, geometry/readback reports and cleanup record are beside it.
One Blender process at a time, two CPU/numerical threads, 640px/16 samples;
all processes exited. Three rejected intermediate native files were deleted
after final readback; their images/reports and the original input remain.
Thumbnail-cache warnings did not prevent native save or successful readback.

## Registered lower-nose controls - 2026-10-24

[Current mesh, controls and limits](reference/anatomy/LOWER_NOSE_CURVES.md).
`curve_fit.apply` fits compact 3D control displacements on a copied mesh with
a reversible layer. The 25-control nasal study adjusts tip/columella/ala/sill
connections. It preserves the source, topology, existing keys, selections and
vertex groups. This is authored surface registration, not cartilage geometry
or a population anatomy model. Nostril rim and vestibule construction remain.

Blender 5.2.2 LTS: maximum movement 2.02465 mm; 74,508 out-of-region vertices
unchanged; rollback, two invalid inputs and injected late failure pass.
Minimum changed polygon area ratio 0.85332, no reversed polygon area vectors.
Saved-file readback: maximum target-to-surface distance 0.01389 mm.
These checks do not guarantee absence of self-intersections.
Front/profile/basal-oblique renders inspected; one Blender process at a time,
two CPU/numerical threads, 640px/16 samples. All processes exited.
Native: `runs/human/lower-nose-curves/lower-nose.blend`; diagram and reports beside it.
The input SHA256 was unchanged. A thumbnail-cache write warning did not prevent
native save, successful readback or the three render outputs.

## Nose anatomy audit - 2026-10-24

[Source-based structural review and current three-view board](reference/anatomy/NOSE_AUDIT.md)
separates anatomical relationships from authored displacement functions.
The current model lacks registered lower-nose support/surface relationships;
brush mechanics are not anatomical validation. Next bounded target is the
tip-columella-alar-base connection, before further detail strokes.
No geometry changed. Blender 5.2.2 LTS rendered front/profile/basal-oblique
views with one process, two threads, 560px and 16 samples. An occluded basal
view was corrected once; both processes exited. Source SHA256 was unchanged.
No person-specific shape accuracy or measured anatomy template is established.

## Surface-following brush engine - 2026-10-24

`surface_brush.apply` introduces named-path ridge/crease strokes along per-vertex
surface normals, edge-graph geodesic footprints, visible-sheet/mask traversal
barriers and closed-volume-constrained relaxation. Each stroke is a reversible
layer on one new snapshot; a later failure removes the complete batch. The
legacy axis-projected brush remains available and unchanged.

Blender 5.2.2 LTS focused checks pass: opposite ridge/crease motion and nonzero
lateral motion on a curved fixture; hidden surface/source preservation;
layer rollback; four failure cases, including an injected-by-command second
stroke failure and open-mesh rejection. The rough curved fixture's measured
Laplacian roughness ratio is 0.0642 after relaxation, with enclosed-volume
change -0.0000154 mm3. This is a synthetic geometry check, not anatomy evidence.
Evidence: `runs/human/surface-brush-check/verification.json`.

The current nasal trial applies five strokes within a small protected region.
82,382 outside vertices and the source remain unchanged; all layers roll back.
Maximum combined displacement is 0.3494 mm. The relaxation step changes signed
volume by -0.0001230 mm3; ridge/groove steps intentionally change volume.
Native: `runs/human/surface-brushed-nose/surface-brushed.blend`.
Diagram, commands and verification are stored beside it. The two current
800px/16-sample renders show the saved model's front and nasal oblique detail.
One Blender process and two CPU/numerical threads were used; Blender exited.
This establishes brush behavior on authored paths, not a correct anatomical
diagram, tissue model or finished realistic nose. No new anatomy dataset was added.

## Nasal tip, alae and nostril cavities - 2026-10-24

`nasal_structure.build` adds controlled tip/alar/central-column volumes on a
locally subdivided snapshot. `Nasal volumes` is a reversible shape-key layer
supported by `sculpt.set_layer`. Angled oval cavities and 0.35 mm rim bevels
are made on a separate final snapshot. The original open-eye head, its history
and both globe meshes are preserved. The nasal base/philtrum transition is
protected by a smooth lower cutoff; old selections stay on the source topology.

Blender 5.2.2 LTS checks pass: 74,504 protected vertices remain byte-exact;
the source and eyes are unchanged; the volume layer restores its baseline;
two invalid registrations and an injected second-cavity failure leave no new
objects or meshes. The final head has zero nonmanifold edges, both cavities
measure 7.000 mm along their axes and maximum volume movement is 10.771 mm.
Native: `runs/human/nasal-structure-final/nasal-structure.blend`.
Evidence: `runs/human/nasal-structure-final/verification.json`.
Example: `examples/human/nose/build_nose.py`.

Front, oblique and underside previews use 800px, 16 samples, one Blender
process and two CPU/numerical threads. Initial forward-facing, oversized
openings were lowered and directed toward the underside; their circular shape
was replaced with paired angled ovals. These are authored static volumes and
blind cavities, not an internal airway, cartilage model or anatomical validation.
Ear, mouth and chin detail remains rough. The native and explicit render saves
succeed despite the existing OS thumbnail-cache write restriction.
All three final views were inspected and Blender exited. Two intermediate
native files were removed (104,606,729 bytes); source/final models and preview
evidence remain. Public previews match the final render hashes. The folder
limit check reports zero violations outside `.git` and `.venv`.

## Open eyes and fitted lids - 2026-10-24

`eye_socket.build` creates a new head snapshot with paired eye openings,
connected upper/lower lids, inner lid returns, closed sockets and separate globes.
Width, independent opening heights, tilt, yaw and globe radius are explicit
controls. A fitted boundary plane replaces the old relief inside the patch.
The source ear-stage model and its existing layers remain untouched; old
selections are not transferred to changed topology.

Blender 5.2.2 LTS: both eyes replace 1,348 local faces each. The head has zero
nonmanifold edges; 72,450 protected vertices and all source coordinates remain
unchanged. Invalid globe size, overlapping regions and a missing second-eye
surface fail without leaving meshes or objects, including a late batch failure.
Evidence: `runs/human/open-eyes-finished/verification.json`.
Native: `runs/human/open-eyes-finished/open-eyes.blend`.
Entry point: `examples/human/eyes/build_open_eyes.py`.

The saved model supplies the current front/three-quarter previews. Rendering
uses one Blender process, two threads, 24 samples and 900px views. The earlier
iterations exposed an uneven transition and inward pupil placement; the fitted
transition and globe orientation were corrected. A quadratic boundary fit was
replaced with an affine fit after its interior bulging appeared in the preview.
The seam band receives bounded smoothing (2 mm cap), with the aperture rim fixed.
Ears, nose and chin remain
rough. Tear ducts, corneal optics, animation and anatomical validation are not
implemented. Blender's OS thumbnail-cache write failed under the sandbox;
the native file and explicit render files were saved successfully.
Final front/three-quarter inspection confirms visible openings and globes with
the radial seam artifacts removed. Blender exited. Four intermediate native
files generated during this pass were removed (182,327,324 bytes); the source,
final native, iteration images and verification records remain. The ten-file
folder check reports zero violations outside `.git` and `.venv`.

## Human proportion base — 2026-10-23

Earlier ear-stage front/three-quarter renders were published as
`docs/assets/human/human-current-front.png` and `human-current-three-quarter.png`.
Visual inspection shows shallow eye/ear relief, no eye openings and persistent
chin irregularities. Previous tool-pass reports were not visual-quality evidence.
The saved ear-stage model was rendered with one Blender process, two CPU threads,
24 samples and two 900px views; Blender exited.

Workspace cleanup: 17 human example/config files moved to `examples/human/`;
2,282 anonymous test runs moved to `runs/_archive/tests/` without deletion.
References and script roots were updated; syntax/JSON/resource-path checks passed.
New anonymous tests use that subfolder. Named historical model runs remain.
[Current entry points](WORKSPACE_LAYOUT.md).

Auricle knowledge: `auricle-v1.json` adds five semantic groups, 19 controls and
six paths per ear. `anatomy.path_stroke` supports explicit positive/negative-X
side views in addition to front projection. Same-view visibility protects opposite
and occluded surfaces. Four manual references scale each ear's width and heights.

Blender 5.2.2 LTS: `tests/ear_fit_test.py` passes two paired proportion fixtures
(18/26 mm widths, 44/56 mm heights), outward direction, unchanged Y/Z, caps,
source preservation and rollback. All 9,882 hidden vertices per fixture remain
unchanged; protected counts are 12,068 / 11,988. Maximum movement: 0.479 / 0.702 mm.
Six invalid batches and the existing front-path effect/failure check pass.
Evidence: `runs/human/ear-fit/verification.json`. The current human application locally
subdivides ear patches and preserves existing facial edits:
`runs/human/human-ear-fit/fitted-ears.blend`. No new renders; canals, cartilage thickness,
free-standing helix rims and anatomical accuracy remain outside this pass.
The human result preserves 75,230 protected vertices and source/baseline geometry,
passes all-layer rollback and has zero nonmanifold edges. Maximum movement is
0.700 mm. One Blender process and two CPU threads were used; Blender exited.

Periorbital knowledge: `periorbital-v1.json` adds six semantic groups, 19 controls
and five paths per eye. Four references determine the canthal axis and independent
lid heights. `apply_many` applies disjoint regions to one new snapshot while
retaining all reversible layers and registration metadata. Failed batches remove
the entire output, including failure after earlier paths succeeded.

Blender 5.2.2 LTS: `tests/orbital_fit_test.py` passes two bilateral fixtures
(24/34 mm eye widths, 0/0.12 rad tilt), caps, source/lower-face preservation,
protection, complete rollback, eight invalid batches and an injected second-eye
failure after five successful paths. The original single oral API also passes.
Protected counts: 12,471 / 11,723; maximum movements: 0.510 / 0.871 mm.
Evidence: `runs/human/orbital-fit/verification.json`. Current native example:
`runs/human/human-eye-fit/fitted-eyes.blend`. It locally subdivides eye patches and
preserves previous nasal/oral objects and layers. It preserves 72,618 protected
vertices and the source/baseline, passes all-layer rollback, and reports zero
nonmanifold edges with at most 0.8775 mm displacement. One Blender process and
two CPU threads were used; Blender exited. No new renders; eye openings,
eyeballs, orbital cavities and anatomical accuracy remain outside this pass.

Nasal knowledge: packaged `nasal-base-v1.json` adds five semantic groups,
19 normalized controls and six front-surface paths. Five manual target points
set alar width, base/tip height and philtrum reference. Optional linked oral
targets check the common nose-base coordinate and vertical ordering. Nasal
protection stops at base height, preserving existing oral deformations.

Blender 5.2.2 LTS: `tests/nasal_fit_test.py` passes two curved fixtures with
28/44 mm alar widths and 18/26 mm heights. Protected counts: 6,578 / 6,176;
unchanged below-base counts: 4,141 / 3,333. Source layers, rollback, caps,
eight atomic failure cases and oral-default compilation pass. Maximum movement:
0.698 / 1.093 mm. Evidence: `runs/human/nasal-fit/verification.json`.
The current procedural human uses measured targets with the oral link;
native output: `runs/human/human-nasal-fit/fitted.blend`. It preserves 72,204 protected
vertices and its source, passes rollback, and moves at most 0.567 mm.
One Blender process and two CPU threads were used; Blender exited. No new renders; nostril
cavities, underside anatomy and anatomical accuracy remain outside this pass.

Reusable oral knowledge: `anatomy_fit` loads packaged `oral-neutral-v1.json`,
separating sourced semantic relationships from authored numerical proportions.
Four measured targets determine width and independent upper/lower spans;
20 controls and seven brush paths project onto the visible target surface.
New snapshots retain registration provenance and reversible layers; failed
applications remove their partial outputs. [Scope/API](ANATOMY_KNOWLEDGE.md).

Blender 5.2.2 LTS: two curved proportion fixtures (42/58 mm mouth widths) pass
actual deformation, source preservation, protection and rollback. Protected
counts: 5,651 / 5,531; maximum combined movement: 1.250 / 1.822 mm.
Eight invalid targets fail atomically. Evidence: `runs/human/anatomy-fit/verification.json`.
The current human target initially failed the depth tolerance at the corners;
surface readback corrected those coordinates without relaxing the tolerance.
Native application: `runs/human/human-mouth-fit-visible/fitted.blend`.
No new renders; full-body variation and anatomical accuracy remain unvalidated.
Runs used one Blender process and two CPU threads; Blender exited.

Mouth diagram paths: `anatomy.path_stroke` projects named front-view polylines
onto the visible mesh with regional protection and reversible layers.
`examples/human/recipes/human-mouth-diagram.json` drives seven paths for lip contours,
lip separation, philtrum ridges/groove and the lip/chin fold. The corresponding
diagram uses the same coordinates. Native: `runs/human/human-mouth/human-mouth.blend`.
Only the mouth patch is subdivided into a new object; earlier sources remain.

Blender 5.2.2 LTS focused path test passes forward displacement, rear-surface
protection, bounds, rollback, six atomic failure cases and stale registration.
The example preserves 71,482 protected vertices exactly, preserves its source,
passes complete layer rollback and has zero nonmanifold edges. Maximum combined
movement is 1.314 mm. Front/side mouth previews were inspected: lip separation
and the upper lip bow are visible; lip corners remain coarse and the existing
chin surface irregularities remain. This is authored registration, not validated
anatomical accuracy. One Blender process, two CPU threads; Blender exited.

Lower-face profile revision: `examples/human/scripts/human_lower_face.py` takes the guided
cranium native file, subdivides only lower-face topology into a new object, and
applies an authored sagittal profile from `examples/human/recipes/human-lower-face.json`.
Nose base, philtrum, upper/lower lip and chin anchors define forward support and
chin setback. The profile is a reversible shape key followed by a bounded
registered smoothing brush. The source and its cranium brush layers remain intact.
Native result: `runs/human/human-lower-face-final/human-lower-face.blend`.

Focused checks verify unchanged protected coordinates, full layer rollback,
source preservation, manifold edges, and actual anterior lip support/chin setback
by surface ray samples. Nostril cavities and detailed lip anatomy remain outside
this pass. Blender 5.2.2 LTS: 65,004 protected vertices stayed unchanged;
source preservation and full rollback passed, with zero nonmanifold edges.
Upper/lower lip centerline samples moved forward 9.48/9.31 mm; the chin
sample moved back 3.23 mm. Maximum total displacement was 13.59 mm.
Final front/side previews were inspected. Lip definition and shallow chin
surface irregularities remain unfinished. Blender exited; runs used one
process with two CPU threads. Previous revisions follow.

Registered anatomy brushing: `anatomy.bind` and `anatomy.stroke` project named
landmarks from front/side diagrams to the current mesh surface. Regional bounds,
feathering, optional protection masks, geodesic radius, X mirroring and per-stroke
displacement caps constrain smooth/normal edits. Each stroke is a reversible
workbench layer. The template is authored for this procedural subject, not an
anatomical standard. [Controls and reproduction](ANATOMY_BRUSH.md).

First application: two cranium strokes on a new evaluated snapshot of the head.
Native result: `runs/human/human-guided-cranium/human-guided.blend`. The prior object,
keys and smoothing are preserved. Maximum total movement is 1.2243 mm; 64,220
protected vertices remain coordinate-identical. Source preservation and complete
brush rollback pass. The focused `tests/blender_tests.py` anatomy test passes
normal/smooth effects, limits, protection, rollback and invalid/stale commands.
Blender 5.2.2 LTS; front/side close-ups and the registration diagram were inspected.
No anatomy ground-truth or fine-detail claim is made. Blender exited; runs used
one process and two CPU threads at a time. Previous head revision follows.

Head/neck plane revision: cranium and jaw sections replace the egg-shaped head.
Nose bridge/tip, muzzle/chin and ear masses join the existing surface.
Orbital recesses, broad cheek relief, brow relief, shallow mouth indication and anterior neck ridges
are a separate reversible shape key. The neck shifts under the posterior jaw.
Native result: `runs/human/human-head-refined/human-base.blend`; previous native models
are preserved. Only front and side head close-ups are rendered.

Focused checks cover connected closed geometry, head height, nose projection
and ear silhouette. Eyes/eyelids, detailed lips, ear folds, hair and facial
animation topology are not implemented. Blender 5.2.2 LTS passed the checks.
Both close-ups were inspected; an initial render exposed spherical cheek/muzzle
bulges and excessive nose projection, which were reduced before the final pair.
Facial contours remain coarse at 6 mm fusion resolution, particularly the mouth
region and skull outline. One process and two CPU threads were used at a time;
Blender exited. Earlier revisions follow.

Silhouette and joint-landmark revision: rounded shoulder stations replace the
flat arm caps. Torso profiles distinguish ribcage, lumbar curve and pelvis;
thigh/calf profiles taper into narrower ankles. Separate kneecap and staggered
ankle masses fuse into the surface. Clavicle and shin relief is a reversible shape
key, followed by the existing smoothing modifier. Native result:
`runs/human/human-landmarks/human-base.blend`; the initial native model is preserved.

Focused checks retain connected/closed geometry, height and the leg gap, and add
upper-arm gap rays and kneecap projection checks. This remains a static anatomy
blockout; facial features, fingers and a deformation rig are outside this pass.
Blender 5.2.2 LTS passed the checks: one closed connected surface with 65,256
vertices and preserved 1.7455 m height. Front/side images were visually inspected;
the square shoulder caps are removed, and knee/ankle landmarks and torso curves
are visible. Joint masses remain simplified and do not establish anatomical
accuracy. One process, two CPU threads and two renders were used. Blender exited.
Initial revision details follow.

`examples/human/scripts/human_base.py` starts the human-modeling stage with an original adult
neutral-stance blockout. Separate section sources define the head, torso/pelvis,
arms, legs, mitten hands, thumb masses and feet. A 6 mm voxel fusion creates a
new continuous surface; source objects are retained hidden and smoothing remains
a reversible modifier. Native result: `runs/human/human-base/human-base.blend`.

The focused check measures height, finite geometry, a single connected component,
two-face edge incidence and the leg gap. This is a proportion study, not detailed
anatomy, finger topology or a deformation-ready rig. Blender 5.2.2 LTS verified
12 source parts fused into one closed surface (66,158 vertices), 1.7455 m height
and an open leg gap. Front and side renders were visually inspected. Shoulder
contours, pelvis and knees remain simplified; hands are masses without fingers.
One Blender process and two CPU threads produced two 650x1000, 24-sample views.
Blender exited. The camera is retained at its last revision below.

## Compact camera exterior — 2026-10-23

Contour and fitting revision: the grip now uses 57 eased sections and rounder
cross-sections instead of seven linear stations. Both viewfinders have body
recesses, open rims, recessed coated glass and dark backing wells. The side strap
mounts and studs are smaller; rounded-wire eyes replace the thick flat washers.
Native result: `runs/camera/compact-camera-contours/camera.blend`.

Focused checks cover grip/body intersection, open finder apertures, glass/rim
clearance and open strap eyes. The viewfinder is a visual assembly, not a
validated optical path; strap strength is not simulated. Blender 5.2.2 LTS
passed the checks. Front and rear renders were visually inspected: the finder
glass sits behind its rim, the strap eye is thinner and the grip transitions
are smoother. The grip remains a distinct attached part. Blender exited after
one generation and two renders, using one process and two CPU threads.
Previous revisions follow.

Exterior integration revision addresses the four user-marked areas. A tapered
section grip replaces the rounded block and projecting top plate. The control
panel, gasket and body seat extend down to align with the screen; lower fasteners
move with the panel. Its finish is closer to the body. The display now has a
cut-through bezel, recessed glass, a backing and an actual body recess; exposed
display-corner screws are removed. Native result:
`runs/camera/compact-camera-integration/camera.blend`.

Focused checks cover display glass/bezel non-intersection and the affected panel
bores, gasket contact and button supports. Front and rear views cover the changed
exterior. Blender 5.2.2 LTS passed these checks. Both views were inspected;
a broad shading band introduced by the body recess was corrected with explicit
face corner normals and the rear view was rendered again. The final rear image
shows an even body surface below the extended panel and around the inset display.
The front image predates this final body-normal correction but shows the current
grip geometry. Blender exited; one process and two CPU threads were used at a
time. This remains a static visual model, not a manufacturing validation.
Previous revisions follow.

Button seating revision: MENU, PLAY and navigation controls now use real panel
apertures. Separate button shafts run through guide sleeves into a body cavity;
retaining flanges and a navigation carrier complete the static assembly.
The guide sleeves and rear navigation guide attach to the cavity floor.
Shaft/sleeve radial clearance is 0.2 mm. Native result:
`runs/camera/compact-camera-buttons/camera.blend`.

Blender 5.2.2 LTS checks aperture rays, shaft clearance from panel/body and guide
attachment. An oversized shaft must intersect the panel as a negative fit check.
Explicit per-face corner normals remove the triangular panel shading seen in
the first render; the corrected rear image was visually inspected. The internal
guide depth was finalized in the saved native file and checked without rendering.
Blender exited. Runs used one process and two CPU threads at a time.
Only the rear view is rendered; the hatch preview remains from the previous
revision. Button travel, switches and spring forces are not simulated. Earlier
revisions follow.

Visual finishing revision: the service panel is reduced from 1.2 to 0.7 mm,
with a satin finish and flat shading on its planar drilled faces. Buttons move
with the lowered panel; screw heads, display surround and eyecup protrude less.
The hatch opening has a tighter corner radius and flat underside shading.
A recessed, smaller battery exposes more of the pocket wall; a divider separates
the card area. The door has an inner face insert and a smaller edge bevel.
The underside view now looks toward the inner door and hinge connection.

Native result: `runs/camera/compact-camera-finish-final/camera.blend`. Focused checks
cover the existing panel bores, gasket contacts, latch release and two hatch
poses; they do not establish continuous collision-free travel. Blender 5.2.2 LTS
produced both images and the completion report; both images were inspected and
Blender exited. The hatch view shows the inner ribs, seal, hinge and pocket
divider. The rear panel's strong reflection is reduced, but faint edge shading
variation remains. One process and two CPU threads were used; an initial render
was stopped to correct button seating and the underside viewing angle. The shell
reported a nonzero status with redirected Blender warnings; the log contains
both saved images and CAMERA_COMPLETE, with no Python traceback. Previous
revisions follow.

Assembly revision: the rear service panel now seats in a supported body recess
with a perimeter gasket, four screw bores, mounting bosses and separate shafts.
The battery/card pocket has a liner and a rebate contacting the door's perimeter
seal. Alternating fixed/moving hinge knuckles share the door pivot and pin axis.
A separate latch tongue fits a receiver slot and retracts 2 mm before opening.
The native model remains closed with the latch engaged; the hatch, slider and
individual components remain separately editable.

Focused Blender 5.2.2 LTS checks pass panel bore rays, gasket/panel and seal/seat
contact bounds, latch surface non-overlap and release clearance, battery access,
and closed/open hatch coverage. These are static geometry checks, not a continuous
motion or manufacturing validation. Native result:
`runs/camera/compact-camera-assembly/camera.blend`. Only rear-controls and open-hatch
views are rendered with one Blender process and two CPU threads. Earlier native
models are preserved. Both renders were visually inspected and Blender exited.
Updated previews: [rear panel](assets/camera/compact-camera-controls.png) and
[open hatch](assets/camera/compact-camera-hatch.png). Previous revisions follow.

Controls and access revision: seated button bezels and separate caps, menu/play/OK
labels, dial mode markings, a rear service panel with slotted screws, lower-profile
viewfinder windows and strap mounting feet/studs replace the first-pass controls.
A cut-through lower cover and gasket expose a real body pocket containing a
separate battery and card edge/socket. The hatch has ribs, a gasket, hinge barrels
and a lock slider; a tripod socket has a blind bore. The saved native model is
closed; the named `Battery hatch hinge` object provides the demonstrated 105-degree
open pose. This is not a continuous interference or mechanical-function guarantee.

The focused Blender 5.2.2 LTS check passes the opening rays through body/cover/
gasket, access to the battery, and hatch coverage in the closed/open poses. Mesh
parts have finite geometry. Native result: `runs/camera/compact-camera-controls/camera.blend`.
Only front, rear-controls and open-hatch views are rendered, with one Blender
process and two CPU threads. Previous native inputs are preserved. Lens optics
and unrelated tool/OS tests are not rerun. Earlier revision details follow.

All three views were inspected and Blender exited. The rear controls show the
separate bezels, labels and panel screws; the underside image shows the opened
door, exposed battery, release catch and card socket. Public previews:
[controls](assets/camera/compact-camera-controls.png),
[open hatch](assets/camera/compact-camera-hatch.png). Only the two static door poses
were verified; no collision-free travel or manufacturing claim is made.

Refinement: the body and alloy covers now share sampled superellipse outlines.
The two 0.25 mm joints use recessed gaskets instead of protruding rectangular
seam plates. The lens has a nonmetallic clear front element recessed inside the
filter rim, a separate inner element, nine closed iris leaves and a dark cavity.
The original `runs/camera/compact-camera/camera.blend` is preserved; the new native file
is `runs/camera/compact-camera-refined/camera.blend`.

The focused Blender 5.2.2 LTS check passes matching cover outlines, a clear
4 mm-radius ray bundle through the iris and blade coverage at 10 mm radius.
All 100 mesh parts contain finite geometry. Front and lens-detail renders were
visually inspected: the protruding corner seams are removed, and the aperture
opening and inner glass are visible through the clear front element. Blender
has exited. Only those two views were rendered; rear controls are unchanged. No core tools,
OS matrix or full regression were added. The following describes the first pass.

`examples/camera/scripts/compact_camera.py` creates an original 120 mm-wide fixed-lens camera
using existing rounded-box, annular, profiled-ring and lathed-surface tools.
The exterior includes a textured body/grip, satin metal covers, concentric lens
rings, convex coated glass, two knurled top dials, shutter, hot shoe, viewfinder,
rear display and controls. It uses Blender's bundled font; no reference assets
or host fonts are required. No new core modeling operation was added.

Scope: static exterior only. The optics, internal mechanisms and articulation
are not simulated. Blender 5.2.2 LTS checked 88 mesh parts for finite, nonempty
geometry. The one native model is `runs/camera/compact-camera/camera.blend`.
Both front/rear 1000x800, 32-sample views were rendered and visually inspected.
The exterior pass is complete; the glass is stylized and shallow cover seams
remain visible. No OS/version matrix or
full regression is part of this work. Runs are limited to one Blender process,
two threads and two logical CPUs. The script rejects an existing output directory.
Blender has exited. Public previews are
[front](assets/camera/compact-camera-front.png) and [rear](assets/camera/compact-camera-rear.png).

The user's longer-term target is human-body design. After this camera, the next
appropriate scope is a simplified static full-body figure; hands/face and joint
deformation are separate later steps, not additional requirements for this model.

## Two-flute drill bit — 2026-10-23

The current example replaces the 2 mm slotted driver with a 6 mm two-flute drill
bit: 22 mm straight shank, 38 mm fluted portion, 32 mm helix pitch and a 1.8 mm
tapered point. Flutes start beyond the jaw tips. All three jaw openings now match
the 6 mm shank. Metal roughness is 0.22 on the lands and 0.38 inside the flutes.
The body remains unchanged from the previous scoped result below.

Blender 5.2.2 LTS: closed finite mesh, two recessed channels per inspected section,
shank radius error below 0.00001 mm, all three jaw contact radii 3 mm, and no
triangle overlaps with the chuck body, cage or nose support. Three invalid-input
cases reject while preserving the scene. An initial channel counter included
float32 jitter on circular lands; its 0.0001 mm prominence threshold fixes that
measurement issue without rebuilding or altering the mesh.

Native result: `runs/drill/drill-twist-bit/drill.blend`. The public JSON recipe is the
recipe used for this build. Verification is limited to the bit and stationary
chuck interface; no OS matrix, full regression or motion sweep was run. The
faceted point is a visual approximation, not a manufacturing cutter definition.
The single 1000px/32-sample [detail image](assets/drill/base/drill-twist-bit-detail.png) was
inspected. Both helical channels and the pointed end are visible. Blender exited;
the run used at most one process, two threads and two logical CPUs. The old
overall preview below depicts the earlier slotted bit; the detail image is current.

## Scoped resumption — 2026-10-23

The active goal is limited to remaining visible drill defects and integration into
the example generator/recipe. The historical runtime matrices and broad acceptance
tasks below are superseded by the user's narrower scope; they must not be resumed.
Candidate 48 rear-screw and beauty images were inspected. The example generator and
JSON recipe now integrate its connected/tapered grip, rounded trigger grooves and
housing sections, with roof-cage compression halved around the fixed rear screw
land. Only the master cage differs from the candidate-48 recipe. The public JSON is
byte-identical to the recipe used by the local build.

Blender 5.2.2 LTS build passes: shell walls 1.994–2.591 mm, split gap 0.800 mm.
Reopened cage disable/re-enable and all 270 pinned vertices have zero measured
error; original native inputs are preserved. Runs use one Blender process limited
to two threads and two logical CPUs. Focused images use 800px/32 samples; they are
local visual checks, not completion of the old seven-defect acceptance matrix.

The scoped correction/integration is complete. Rear-screw clay and overall beauty
images were inspected: the localized roof swell is reduced; the unchanged grip
and trigger details retain their earlier inspected geometry. A faint roof highlight
transition remains, so this is not a claim of perfect reflection continuity.
Native result: `runs/drill/drill-realism-final-local/drill.blend`; preview:
`runs/drill/drill-realism-final-local/overall-review/beauty-hero.png`. Both Blender jobs
have exited. No further renders, runtime matrices or full regressions were run.
Public copies of the existing renders are included at
[`assets/drill-realism-hero.png`](assets/drill/realism/drill-realism-hero.png) and
[`assets/drill-realism-rear-screw.png`](assets/drill/realism/drill-realism-rear-screw.png).

The previous parallel jobs were stopped. User-approved cleanup removed 69 obsolete
Blend files and the local Linux Blender distribution/archive, freeing 4.34 GiB.
Historical logs remain, but paths to those deleted native artifacts are no longer
reopenable. The original, candidates 40/42/45/48 and latest edit results were retained.

## Historical broad-scope snapshot (superseded)

Updated 2026-10-23. **Drill surface refinement M6-M10 complete; realism M11-M15 resumed, incomplete.** [Study and 28 native previews](studies/DRILL_SURFACE_STUDY.md) | [Completion audit](audits/recipes/part-01/DRILL_SURFACE_AUDIT.json) | [Next development contract](DRILL_REALISM_PLAN.md) | [Realism progress](studies/DRILL_REALISM_STUDY.md)

## Next development phase

The current public generator and self-contained recipe reproduce candidate 40 exactly (`runs/drill/drill-realism-integrated-40-recipe-01/verification.json`). Frozen five-view silhouette, part and landmark gates pass: front/rear IoU 0.97648, hero 0.97449. Native build, cage restoration/pins, four seam grids, three seats, bit/nose checks, all four sampled motion channels, and independent width +0.25 / length +1 edits with reopened vents/seats/materials/eight markings pass. Original inputs remain preserved.

Candidate 42 integrates connected side/rear grip patches and retains the original side chart as an explicit construction dependency for the ribs. Generation, fixed rear coverage rays, connectivity, rib support, all four motion channels and frozen silhouette/part/landmark checks pass. Both independent edits pass after reopening, including grip support and all 51 finished parts/eight markings. All twelve native rejection cases preserve state; successful recovery and reopened finish/marking checks pass. High-resolution clay/stripe inspection still finds fastener curvature, trigger-groove highlights and rear-grip edge quality unresolved. This experimental wrap has not replaced the public recipe.

Core snapshot 05: Windows Blender 5.2.2 LTS and Linux Blender 4.0.2 each pass 62 tests. New insert rim-profile support passes 63 tests each on Windows and Linux against unchanged snapshot 06. This includes three-axis insert projection and explicit removal/reporting of stale CSG binding metadata. Candidate-40 native evidence predates those final core changes; current recipe CLI replay on both runtimes remains required. After an initial WSL startup timeout, candidate 42 Linux recipe replay and reopened grip/finish/seat checks pass (`runs/other/linux-runtime-01/recipes/part-02/recipes-05.json`); this is native runner evidence, not host CLI evidence.

Candidate 44 replaces projected flat groove cutters with rounded cutters at unchanged 0.25 mm depth and 0.8 mm width. All 35 depth/land rays pass and the 2000px clay detail shows smoother groove highlights. Candidate 45 adds tapered rear-grip rim heights; build and unchanged coverage/connectivity/rib-support gates pass. Its clay grip/rear views were inspected and show reduced rear-edge protrusion; all four motion channels pass, with unchanged rest transforms. Finish/marking readback, frozen-view and alternate-bit checks pass. Candidate 46 reduces width differences around fixed screw lands; all pin/release/frame/cage definitions remain unchanged. Build and all frozen-view measurements pass; stripe inspection still finds local fastener disturbance. Candidate 47 reduces adjacent width correction further but is rejected by the blind-seat wall gauge; diagnosis found three neck samples above the 2.6 mm maximum (peak 2.602125 mm), not a screw-floor failure. Candidate 48 restores the previously passing Z145 row while retaining the zero corrections at Z165/Z180. It passes build, 1.980-2.591 mm wall / 0.800 mm gap checks and all frozen-view gates (hero IoU 0.972035). Stripe/clay hero views show reduced front-fastener disturbance; front screw detail and beauty hero are also inspected. Material creation-failure preservation/recovery passes. Rear detail review, chuck/battery beauty details, independent reopened edits and geometry/interface checks are running. Public recipe remains candidate 40.

M11-M15 remain active and incomplete. Commercial-photo calibration is unavailable; the frozen authored evaluation basis is retained. Remaining acceptance includes grip wrap, neck/fastener reflection continuity, trigger groove quality, high-resolution/noise-comparison images, latest-asset editing/recovery, alternate bit cases and complete runtime replay. Historical candidate-26 cross-platform and candidate-20 recovery evidence is retained in the study; it does not certify the current candidate. No final visual acceptance, publication or deployment is claimed.

## Verified result

Historical candidate-26 measurement: 1.970-2.594 mm shell walls and 0.800 mm split gap. Candidate 26 passes cage disabling/re-enabling and 270 pinned-vertex checks with zero measured error. This proves selected implementation checks, not final drill realism or complete editing/motion acceptance.

- Section-shaped housing/grip, tapered/fluted chuck and torque ring, geometric index ticks, projected rubber ribs/perimeters, trigger grooves and beveled battery side covers.
- 73 dependency nodes, 40 declared part frames, 37 visible mesh solids; native millimetre units.
- Actual 519-to-487-triangle grip reconstruction: p10 quality 0.272266 to 0.413375, sampled drift 0.056453 mm, zero pinned movement, 17,018 untouched polygons retained.
- Final and reopened +0.25 mm width model pass geometry, frame, UV/mask/binding, wall/gap and physical interface checks. Ten bounded motion sweeps pass and restore rest transforms.
- Actual CLI success, native reopening and out-of-range rejection pass. Twenty-seven detail measurements pass. Windows Blender 5.2.2 LTS and Linux Blender 4.0.2 each pass 46 integration tests; 3 host tests pass.
- Runtime implementation: `f227142c6b0a902c16233834fc5382f41db5468c`. [Linux runtime CI](https://github.com/shakystar/mesh-workbench/actions/runs/37576165857).

Native candidate: `runs/drill/drill-surface-06/drill.blend`. Follow-up: `runs/drill/drill-surface-06/reopen/followup.blend`. CLI: `runs/drill/drill-surface-cli-08/result.blend`. Recipes and public previews are tracked; generated native files remain local in ignored `runs/`.

## Limits

The authored design is not a manufacturer replica. Visible fixed-land curvature, shell-split light leaks and faceted groove highlights remain. Collision/error measurements are sampled; no continuous collision, strength or manufacturing claim is made. Patch rebuilding preserves unselected polygons but does not generate a general quad cage or cross arbitrary UV/material seams. Later parameter changes regenerate the procedural root, not arbitrary manual edits.

The preceding [M0-M5 assembly study](studies/DRILL_ASSEMBLY_STUDY.md), [audit](audits/recipes/part-01/DRILL_ASSEMBLY_AUDIT.json) and original native models remain preserved. Earlier model and tool studies are indexed in [documentation](README.md); historical development records remain in [archive](archive/DEVELOPMENT_HISTORY.md).

## Open-source access and discovery

Original project code/documentation now use MIT. The public repository includes contribution instructions, an agent quickstart, llms.txt and a descriptive CLI manifest. A GitHub Pages workflow publishes static HTML, raw Markdown and a sitemap; see [discovery operations](DISCOVERY.md). Search indexing and external agent adoption are separate from deployment and have not been claimed.

Search Console update (2026-10-07): URL-prefix ownership verified; homepage and agent-guide indexing requests accepted. Sitemap submission accepted, but its report still says Could not fetch despite a successful Google live fetch. Indexing and sitemap processing success remain unconfirmed; see [registration evidence](audits/recipes/part-02/SEARCH_DISCOVERY.json).
