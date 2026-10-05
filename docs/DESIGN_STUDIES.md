# Design iteration journal

## 2026-10-05: two original product studies

These are static design studies, not mechanically validated products or rigged characters. No outside model, image texture or character reference is used.

Reproduce with a fresh output directory:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/design_studies.py -- runs/design-studies
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/review_studies.py -- runs/design-studies
```

Each study saves a native editable `model.blend`, front/rear renders and a report. The review reopens each file, checks evaluated meshes, measures a recessed slot and captures paired render/pixel world-coordinate maps. Repeat reviews require removing nothing: use a fresh design run instead. Scripts refuse existing capture folders.

### Field robot

![Field robot](field-robot.png)

- First render exposed faceted shell corners, visibly empty knee collars and flat dark rectangles standing in for vents.
- Revision increases bevel resolution, weights surface normals, fills the knee with an axle/bolt, cuts 14 actual recesses into the shell and adds a rear service panel with connectors.
- Evaluated result: 71 visible mesh parts, 24,249 vertices. No boundary/nonmanifold edges on those individual evaluated parts. Sampled recess depth: 0.1300001 world units. This is not an assembly collision or load-bearing test.
- Pixel (88,148) in the 320px front map hits the left lens at approximately (-0.50048,-1.50500,1.96492), normal (0,-1,0). Map revisions are stored with each query.
- Visual limits: box-like body, short generic piston legs, weak front lettering contrast, exaggerated bright edge gasket and weak vent contrast in the key light. Parts intersect intentionally at attachment sites; no joint kinematic clearance has been proven. Tread pieces are separate geometry, not yet a continuous molded sole.

### Work lantern

![Work lantern](work-lantern.png)

- First render exposed an unbroken lower housing and a visually uniform diffuser.
- Revision adds real circumferential seams and repeated vertical grip ribs, preserving the switch and protective cage.
- Evaluated result: 65 visible mesh parts, 9,320 vertices. No boundary/nonmanifold edges on those individual evaluated parts.
- Visual limits: handle bends are simple overlapping cylinders, top cap shading is soft, lower marking placement remains cramped and the diffuser does not model optical internals. Repeated ribs improve detail but do not alone establish design quality.

### Tools extracted from the exercise

`mesh_workbench.construction` provides:

- `rounded_box(name, dimensions, location, radius, segments=8)`: full dimensions in world units, retained bevel/normal modifiers, scale remains identity.
- `revolve(name, profile, segments=64, closed=False, location=...)`: radius/Z profiles. Open profiles receive planar caps; closed profiles create hollow rings. Positive radii only; simple profiles required. No self-intersection solver.
- `strut(name, start, end, radius, segments=32)`: cylinder endpoints fixed to world-space anchors.

These functions create fresh named objects and reject invalid dimensions, duplicate names, repeated adjacent profile points and coincident anchors. They are Python API functions; JSON recipe dispatch has not yet been added.

Validation: Blender 5.2.2 LTS, eight integration tests and three host CLI tests passed. New coverage checks dimension preservation, anchor placement, ring manifold/positive volume and no object leakage after invalid inputs. Both saved designs passed separate evaluated-mesh review. Front/rear and robot side renders were visually inspected.

## Next evaluation cycle

- Add an organic subject to expose limitations not covered by product assemblies.
- Exercise local shape edits from captured coordinates and record before/after geometry, not just parameter regeneration.
- Replace overlapping handle construction with a reusable swept section tool, then evaluate joins and shading.
- Improve the robot's silhouette and assembly logic; establish comparable detail/side/wire views before judging quality gains.

The broader iterative modeling goal remains active. Passing these checks does not establish expert-level modeling or completion of that goal.

## 2026-10-05: organic ray and tool reuse

![Original wing pose](organic-ray-before.png)
![Coordinate-sculpted wing pose](organic-ray.png)

Third design family: a stylized ray sculpture on a display stand. Body sections define the planform; the tail uses a tapering curved sweep. This is an original decorative design, not a measured anatomical reconstruction.

### Evidence-led changes

1. Captured the body into a 384 x 384 render/world-position/normal map. Pixel (305,202) corresponds to approximately (1.95078,0.11070,1.19494), on the right wing.
2. First trial used a narrow geodesic Grab. The actual before/after render exposed abrupt wing curvature; 1,474 vertices moved, but visual quality was insufficient.
3. Changed to a broader spherical influence for this thin wing so both sides of its thickness move together. This is a deliberate modeling choice, not a replacement for geodesic selection when nearby disconnected surfaces need protection.
4. Fixed the underside material assignment to use section domains rather than a global height threshold, and reduced the tail-root thickness. A small nose color irregularity and the separate tail junction remain visible.
5. Final reversible symmetric Grab moved 5,966 of 14,850 body vertices. Maximum displacement was 0.3042824 world units. A fresh process reopened the saved file, matched the recorded edited arrays, disabled the layer to match the recorded base, and restored the edited state.
6. Central 4,994 vertices remain exactly unchanged. Mirrored displacement error was at most 2.82e-7. Old surface maps were rejected after deformation. Final body is finite with no boundary/nonmanifold edges. These checks do not prove absence of self-intersections.

Reproduce (fresh output):

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/organic_study.py -- runs/organic
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/verify_organic.py -- runs/organic
```

Artifacts include `ray.blend`, before/after/side renders, paired coordinate captures, `deformation.npz`, `report.json` and independent `reopen-verification.json`.

### Reusable sweep tool

`mesh_workbench.sweep.sweep(name, centers, radii, segments=32, reference=(1,0,0))` creates a capped open-path mesh from elliptical sections. A transported frame avoids choosing a new orientation independently at each section. Geometry is in world coordinates. The initial reference must not be parallel to the first tangent; radius pairs must be positive; repeated centers and nearly reversing paths are rejected before creating an object. Triangulated end caps expose editable face domains.

This tool does not interpolate/smooth the supplied path, support closed paths or solve self-intersection. Tight bends need adequate samples and sufficiently small section radii. It is currently a Python API, not a JSON operation.

### Reused on the earlier lantern

![Continuous handle detail](lantern-handle.png)

The earlier handle had overlapping straight rods. The same sweep tool now creates a continuous tube through two rounded corners, with a separate shorter grip. Native Blender geometry and the close-up render were checked. The handle mesh has no nonmanifold edges. The mechanical hinge and manufacturing clearance remain unvalidated.

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python examples/refine_lantern.py -- runs/design-studies/work-lantern/model.blend runs/lantern-refined
```

Validation: nine Blender integration tests passed on Blender 5.2.2 LTS after the final cap change. The new test measures every section center and minimum/maximum radius, verifies frame orthogonality, manifoldness and positive signed volume, and checks failure cases leave the scene unchanged. The prior product-study commit also passed Linux CI: https://github.com/shakystar/mesh-workbench/actions/runs/37279692223 .

### Evaluation and remaining work

The organic study now proves a render-to-coordinate-to-local-edit cycle on an actual design, including persistent reversible state. It remains visually simple: the body is broad and flat, face detail is minimal, and the tail is a separate overlapping part. No expert likeness, rig or production-ready topology is claimed. The previous journal's organic-study and continuous-handle tasks have progressed; next work should address continuous organic junctions, reusable local detail patterns and comparable geometric/visual review before expanding the design count further.
