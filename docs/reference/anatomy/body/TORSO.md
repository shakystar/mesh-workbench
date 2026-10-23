# Registered torso controls

Stage C remains in progress. This pass establishes 29 front/back skin controls
for sternum, thorax, costal transition, abdomen, pelvic transition and back.
The actual render shows subtle volume separation; costal margins, abdominal
planes and scapular form remain insufficient. Existing armpit junction roughness
also remains. Next: costal margin and abdominal connection, within stage C.

## Relationship sources and authored dimensions

[OpenStax thoracic cage](https://openstax.org/books/anatomy-and-physiology-2e/pages/7-4-the-thoracic-cage)
supports the anterior sternum/ribs/posterior vertebrae relationship.
[OpenStax pelvic girdle](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-3-the-pelvic-girdle-and-pelvis)
supports the iliac crest and pelvis/sacrum relationship.
No source image or numerical body proportion is copied. Control coordinates,
depth changes and radii are authored modeling values, not anatomical measurements.
Skin probes named sternum/waist/pelvis do not locate underlying bone automatically.

## API and preserved inputs

`from mesh_workbench.regions import torso`

`torso.compile_controls(source, target, relief=1)` emits a sampled-surface
`curve_fit` diagram using `torso-surface-v1`. Target requires three visible front
XYZ references (`sternum`, `waist`, `pelvis`), descending Z and aligned midline,
`half_width_m` and a protected `region`. Coordinates use front -Y, up Z.
This trial uses half-width 0.13 m, radius 91 mm, feather 15 mm and an 8 mm
maximum displacement. Curve-fit accepted radius/feather ranges now extend to
150/30 mm for torso scale; polygon guards and displacement checks are unchanged.

Run `examples/human/torso/audit.py` and `planes.py` with the preserved
`runs/human/rebuilt-underside/rebuilt-underside.blend` and separate fresh output
folders. Current result: `runs/human/torso-planes/torso-planes.blend`, object
`Torso plane study`, reversible layer `MW torso planes`.

## Focused evidence

Blender 5.2.2 LTS; one process, two CPU/numerical threads. 29 controls,
10,168 changed vertices, maximum displacement 3.66272 mm, maximum nearest-surface
control residual 0.00788 mm. Minimum changed polygon area ratio 0.97627.
77,457 vertices outside the box [-.17,-.15,.96] to [.17,.15,1.42] remain exact.
This is spatial protection, not automatic anatomical limb segmentation.
Source geometry/topology, layer rollback, invalid reference order rejection,
injected late-failure object/mesh cleanup, native reopen and input SHA256 pass.
No global collision or anatomical accuracy claim. Reports and diagram are in
`runs/human/torso-planes/`. Three matched 640px, 16-sample views were inspected.

| View | Before | After |
| --- | --- | --- |
| Front | ![](../../../assets/human/torso/before-front.png) | ![](../../../assets/human/torso/after-front.png) |
| Side | ![](../../../assets/human/torso/before-side.png) | ![](../../../assets/human/torso/after-side.png) |
| Back | ![](../../../assets/human/torso/before-back.png) | ![](../../../assets/human/torso/after-back.png) |
