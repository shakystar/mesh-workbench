# Current development status

## Human proportion base — 2026-10-23

Registered anatomy brushing: `anatomy.bind` and `anatomy.stroke` project named
landmarks from front/side diagrams to the current mesh surface. Regional bounds,
feathering, optional protection masks, geodesic radius, X mirroring and per-stroke
displacement caps constrain smooth/normal edits. Each stroke is a reversible
workbench layer. The template is authored for this procedural subject, not an
anatomical standard. [Controls and reproduction](ANATOMY_BRUSH.md).

First application: two cranium strokes on a new evaluated snapshot of the head.
Native result: `runs/human-guided-cranium/human-guided.blend`. The prior object,
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
Native result: `runs/human-head-refined/human-base.blend`; previous native models
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
`runs/human-landmarks/human-base.blend`; the initial native model is preserved.

Focused checks retain connected/closed geometry, height and the leg gap, and add
upper-arm gap rays and kneecap projection checks. This remains a static anatomy
blockout; facial features, fingers and a deformation rig are outside this pass.
Blender 5.2.2 LTS passed the checks: one closed connected surface with 65,256
vertices and preserved 1.7455 m height. Front/side images were visually inspected;
the square shoulder caps are removed, and knee/ankle landmarks and torso curves
are visible. Joint masses remain simplified and do not establish anatomical
accuracy. One process, two CPU threads and two renders were used. Blender exited.
Initial revision details follow.

`examples/human_base.py` starts the human-modeling stage with an original adult
neutral-stance blockout. Separate section sources define the head, torso/pelvis,
arms, legs, mitten hands, thumb masses and feet. A 6 mm voxel fusion creates a
new continuous surface; source objects are retained hidden and smoothing remains
a reversible modifier. Native result: `runs/human-base/human-base.blend`.

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
Native result: `runs/compact-camera-contours/camera.blend`.

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
`runs/compact-camera-integration/camera.blend`.

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
`runs/compact-camera-buttons/camera.blend`.

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

Native result: `runs/compact-camera-finish-final/camera.blend`. Focused checks
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
`runs/compact-camera-assembly/camera.blend`. Only rear-controls and open-hatch
views are rendered with one Blender process and two CPU threads. Earlier native
models are preserved. Both renders were visually inspected and Blender exited.
Updated previews: [rear panel](assets/compact-camera-controls.png) and
[open hatch](assets/compact-camera-hatch.png). Previous revisions follow.

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
parts have finite geometry. Native result: `runs/compact-camera-controls/camera.blend`.
Only front, rear-controls and open-hatch views are rendered, with one Blender
process and two CPU threads. Previous native inputs are preserved. Lens optics
and unrelated tool/OS tests are not rerun. Earlier revision details follow.

All three views were inspected and Blender exited. The rear controls show the
separate bezels, labels and panel screws; the underside image shows the opened
door, exposed battery, release catch and card socket. Public previews:
[controls](assets/compact-camera-controls.png),
[open hatch](assets/compact-camera-hatch.png). Only the two static door poses
were verified; no collision-free travel or manufacturing claim is made.

Refinement: the body and alloy covers now share sampled superellipse outlines.
The two 0.25 mm joints use recessed gaskets instead of protruding rectangular
seam plates. The lens has a nonmetallic clear front element recessed inside the
filter rim, a separate inner element, nine closed iris leaves and a dark cavity.
The original `runs/compact-camera/camera.blend` is preserved; the new native file
is `runs/compact-camera-refined/camera.blend`.

The focused Blender 5.2.2 LTS check passes matching cover outlines, a clear
4 mm-radius ray bundle through the iris and blade coverage at 10 mm radius.
All 100 mesh parts contain finite geometry. Front and lens-detail renders were
visually inspected: the protruding corner seams are removed, and the aperture
opening and inner glass are visible through the clear front element. Blender
has exited. Only those two views were rendered; rear controls are unchanged. No core tools,
OS matrix or full regression were added. The following describes the first pass.

`examples/compact_camera.py` creates an original 120 mm-wide fixed-lens camera
using existing rounded-box, annular, profiled-ring and lathed-surface tools.
The exterior includes a textured body/grip, satin metal covers, concentric lens
rings, convex coated glass, two knurled top dials, shutter, hot shoe, viewfinder,
rear display and controls. It uses Blender's bundled font; no reference assets
or host fonts are required. No new core modeling operation was added.

Scope: static exterior only. The optics, internal mechanisms and articulation
are not simulated. Blender 5.2.2 LTS checked 88 mesh parts for finite, nonempty
geometry. The one native model is `runs/compact-camera/camera.blend`.
Both front/rear 1000x800, 32-sample views were rendered and visually inspected.
The exterior pass is complete; the glass is stylized and shallow cover seams
remain visible. No OS/version matrix or
full regression is part of this work. Runs are limited to one Blender process,
two threads and two logical CPUs. The script rejects an existing output directory.
Blender has exited. Public previews are
[front](assets/compact-camera-front.png) and [rear](assets/compact-camera-rear.png).

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

Native result: `runs/drill-twist-bit/drill.blend`. The public JSON recipe is the
recipe used for this build. Verification is limited to the bit and stationary
chuck interface; no OS matrix, full regression or motion sweep was run. The
faceted point is a visual approximation, not a manufacturing cutter definition.
The single 1000px/32-sample [detail image](assets/drill-twist-bit-detail.png) was
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
Native result: `runs/drill-realism-final-local/drill.blend`; preview:
`runs/drill-realism-final-local/overall-review/beauty-hero.png`. Both Blender jobs
have exited. No further renders, runtime matrices or full regressions were run.
Public copies of the existing renders are included at
[`assets/drill-realism-hero.png`](assets/drill-realism-hero.png) and
[`assets/drill-realism-rear-screw.png`](assets/drill-realism-rear-screw.png).

The previous parallel jobs were stopped. User-approved cleanup removed 69 obsolete
Blend files and the local Linux Blender distribution/archive, freeing 4.34 GiB.
Historical logs remain, but paths to those deleted native artifacts are no longer
reopenable. The original, candidates 40/42/45/48 and latest edit results were retained.

## Historical broad-scope snapshot (superseded)

Updated 2026-10-23. **Drill surface refinement M6-M10 complete; realism M11-M15 resumed, incomplete.** [Study and 28 native previews](studies/DRILL_SURFACE_STUDY.md) | [Completion audit](audits/DRILL_SURFACE_AUDIT.json) | [Next development contract](DRILL_REALISM_PLAN.md) | [Realism progress](studies/DRILL_REALISM_STUDY.md)

## Next development phase

The current public generator and self-contained recipe reproduce candidate 40 exactly (`runs/drill-realism-integrated-40-recipe-01/verification.json`). Frozen five-view silhouette, part and landmark gates pass: front/rear IoU 0.97648, hero 0.97449. Native build, cage restoration/pins, four seam grids, three seats, bit/nose checks, all four sampled motion channels, and independent width +0.25 / length +1 edits with reopened vents/seats/materials/eight markings pass. Original inputs remain preserved.

Candidate 42 integrates connected side/rear grip patches and retains the original side chart as an explicit construction dependency for the ribs. Generation, fixed rear coverage rays, connectivity, rib support, all four motion channels and frozen silhouette/part/landmark checks pass. Both independent edits pass after reopening, including grip support and all 51 finished parts/eight markings. All twelve native rejection cases preserve state; successful recovery and reopened finish/marking checks pass. High-resolution clay/stripe inspection still finds fastener curvature, trigger-groove highlights and rear-grip edge quality unresolved. This experimental wrap has not replaced the public recipe.

Core snapshot 05: Windows Blender 5.2.2 LTS and Linux Blender 4.0.2 each pass 62 tests. New insert rim-profile support passes 63 tests each on Windows and Linux against unchanged snapshot 06. This includes three-axis insert projection and explicit removal/reporting of stale CSG binding metadata. Candidate-40 native evidence predates those final core changes; current recipe CLI replay on both runtimes remains required. After an initial WSL startup timeout, candidate 42 Linux recipe replay and reopened grip/finish/seat checks pass (`runs/linux-runtime-01/recipes-05.json`); this is native runner evidence, not host CLI evidence.

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

Native candidate: `runs/drill-surface-06/drill.blend`. Follow-up: `runs/drill-surface-06/reopen/followup.blend`. CLI: `runs/drill-surface-cli-08/result.blend`. Recipes and public previews are tracked; generated native files remain local in ignored `runs/`.

## Limits

The authored design is not a manufacturer replica. Visible fixed-land curvature, shell-split light leaks and faceted groove highlights remain. Collision/error measurements are sampled; no continuous collision, strength or manufacturing claim is made. Patch rebuilding preserves unselected polygons but does not generate a general quad cage or cross arbitrary UV/material seams. Later parameter changes regenerate the procedural root, not arbitrary manual edits.

The preceding [M0-M5 assembly study](studies/DRILL_ASSEMBLY_STUDY.md), [audit](audits/DRILL_ASSEMBLY_AUDIT.json) and original native models remain preserved. Earlier model and tool studies are indexed in [documentation](README.md); historical development records remain in [archive](archive/DEVELOPMENT_HISTORY.md).

## Open-source access and discovery

Original project code/documentation now use MIT. The public repository includes contribution instructions, an agent quickstart, llms.txt and a descriptive CLI manifest. A GitHub Pages workflow publishes static HTML, raw Markdown and a sitemap; see [discovery operations](DISCOVERY.md). Search indexing and external agent adoption are separate from deployment and have not been claimed.

Search Console update (2026-10-07): URL-prefix ownership verified; homepage and agent-guide indexing requests accepted. Sitemap submission accepted, but its report still says Could not fetch despite a successful Google live fetch. Indexing and sitemap processing success remain unconfirmed; see [registration evidence](audits/SEARCH_DISCOVERY.json).
