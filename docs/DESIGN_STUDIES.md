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
