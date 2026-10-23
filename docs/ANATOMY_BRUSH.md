# Registered anatomy diagram brushes

The diagram is an editable registration for the included procedural adult. It is
not a population-average chart, automatic anatomical detector or an accuracy
certificate. World coordinates use metres; brush distances use millimetres.

![Head registration diagram](assets/human-anatomy-diagram.png)

## Controls

`examples/human-anatomy-diagram.json` defines named landmarks and regional bounds.
Only the cranium region is enabled in this first pass. Face, neck and body remain
protected. Other landmarks are reference points for later regional work.

- `anchor`: named world landmark; `offset_mm`: horizontal/vertical diagram offset.
- `view`: front projects along +Y; side projects along -X. The first surface hit
  locates the brush. A miss or a hit outside the selected region fails unchanged.
- `radius_mm`: geodesic radius along mesh edges; boundary feathering limits edits.
- `mode`: `smooth` or signed `normal`; `strength`, `steps`, `distance_mm` set action.
- `max_displacement_mm`: cumulative cap for one stroke, not all strokes combined.
- `symmetry_x`: mirrors the surface footprint across world X=0; overlap uses the
  stronger influence. An asymmetric source is not automatically made symmetric.
- `protect_mask`: optional existing workbench protection mask, additionally applied.

The orange diagram circles show projected radius envelopes, not the exact
geodesic footprint. The blue region is editable; feathering applies inside it.
`crown` marks the measured source summit; `crown_guide` is the working anchor below
it. Adjust registration for a different subject before brushing.

## Reproduce

Use one factory-startup Blender process with two threads at a time. Set numerical
library thread limits to two in the calling environment.

```text
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human_base.py -- runs/human-input
blender -b --factory-startup -t 2 --python-exit-code 2 --python examples/human_guided_brush.py -- runs/human-input/human-base.blend runs/human-guided
python examples/draw_anatomy_diagram.py runs/human-guided/diagram-preview.json runs/human-guided/diagram.png
```

The last command requires Pillow. Each Blender example requires a fresh output
directory. The guided example retains the original object and its modifiers/keys,
creates a new evaluated snapshot, then adds reversible brush keys. It does not
transfer prior editable masks/layers onto that snapshot; they remain on the
preserved source. The new diagram binds to the snapshot's topology and transform.
Topology or transform changes require registration again.

## Python API and evidence

`anatomy.bind(obj, diagram)` validates and stores registration on a static baked
mesh. `anatomy.stroke(obj, command)` reprojects the anchor to its current surface
and creates a workbench layer. `sculpt.set_layer(obj, layer_name, 0)` disables it.
Unsupported active modifiers are rejected; do not bake a user's original mesh.

Blender 5.2.2 LTS: the focused test in `tests/blender_tests.py` checks real normal
and smooth deformation, protected vertices, displacement limits, rollback and
invalid/missed/out-of-region/stale commands. The included skull run preserves
64,220 protected vertex coordinates exactly and verifies source preservation and
both-layer rollback. Two strokes produce about 1.22 mm maximum total displacement.
The underlying 6 mm fused head still limits visible fine detail. This tool places
and bounds edits precisely; it does not supply anatomical ground truth.
