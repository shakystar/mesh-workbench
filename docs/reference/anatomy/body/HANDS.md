# Five-digit hand stock, not yet grafted

The actual source hand is a mitten-like block with a thumb bulge. The read-only
`examples/human/hands/audit.py` records wrist/palm sections and front/back views.
At Z=0.90 m front/back thickness is about 54.35 mm; at Z=0.845 m it is 49.10 mm.
No distinct fingers exist in that source. Local relief cannot establish their
separation, so topology construction precedes further palm brushing.

## Reusable construction

`from mesh_workbench.regions import hand`

`hand.build(name, scale=1, side=1)` returns a separate closed hand and preserved
construction stocks. Palm, thumb and four finger stocks use cubic section
interpolation and local 1 mm voxel fusion (scaled with the hand). The source
character is never modified. Late fusion failure removes every created object
and orphan mesh. Scale is bounded to 0.7..1.4; only the default scale/side was
validated on this pass. This is not cross-character reuse evidence.

`hand-structure-v1` separates authored widths, lengths and skin stations from
[OpenStax hand bone relationships](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-2-bones-of-the-upper-limb):
five metacarpal rays, two thumb phalanges and three for each other digit.
No artwork, measured proportions, internal bones or automatic joint recognition.

`examples/human/hands/build.py` takes the preserved elbow-relief native and a
fresh output folder. Current separate prototype:
`runs/human/hand-stock-curved/hand-stock.blend`, object `Hand stock`.
The authoritative integrated character is still
`runs/human/elbow-relief/elbow-relief.blend`.

## Evidence and next action

Blender 5.2.2 LTS: 39,378 vertices, one connected closed consistently oriented
surface, three empty finger-gap rays and four occupied digit rays at Z=0.79 m.
These are section-specific gap checks, not a global collision guarantee.
Invalid scale rejection, injected fusion failure cleanup, original geometry,
input SHA and saved-native coordinate readback pass. Two actual result views
inspected, one process/two threads, exited. Reports are alongside the prototype.
An initial test-index error was corrected; a cubic-section revision softened
some linear edges. The palm remains slab-like, fingertips are blunt and the
finger web edge is too straight. No nails, detailed creases, tendons or rig.

Next: improve palm/web shape and establish an explicit wrist-boundary graft on
a new body snapshot. Current hand has a closed proximal cap and is NOT attached.
Wrist-boundary preservation and bilateral integration have not been achieved.
Stage D and the full goal remain active.

Source character hand:

![](../../../assets/human/hands/source-front.png)

Separate procedural stock:

![](../../../assets/human/hands/stock-front.png)
![](../../../assets/human/hands/stock-oblique.png)

## Bilateral wrist graft

`regions.graft.replace_hand(source, stock, side, name)` creates a new topology
snapshot. It removes bounded distal-hand faces, requires one simple boundary
per mesh, orders the loops, and joins them with an arc-length zipper of triangles.
Existing retained vertices are copied exactly. Inputs, layers and topology-bound
selections remain on the original; none are falsely transferred to new topology.
This is a restricted upright hand graft (world X side threshold .24 m), not an
arbitrary mesh replacement API. Opposing sides are applied as explicit snapshots;
the example does not promise a single atomic transaction across both grafts.

`examples/human/hands/attach.py` takes the preserved elbow native and a fresh
output folder. Current integrated native:
`runs/human/hands-grafted/hands-grafted.blend`, object `Hands grafted study`.
Both generated hands are offset/sheared to the existing wrist axes. Original
body, hand stocks and the intermediate left-hand snapshot remain preserved.

Blender 5.2.2 LTS: each seam connects 34 body boundary vertices to 184 stock
boundary vertices using 218 triangles. Left operation retains 90,148 vertices;
right retains 122,533 of its input, including the new left hand. All retained
positions are exact; 59,731 original vertices above Z=.912 survive exactly.
Closed/oriented edge checks, noncollapsed seam triangles, invalid-cut rejection,
injected late-failure cleanup, original topology/geometry, new snapshot free of
stale shape keys/groups, native readback and input hash pass. No global seam
intersection test or generalized graft claim.

Front/oblique integrated views were inspected. A cuff-like wrist band, flat
palm/web and blunt fingertips remain; next is local seam/palm shaping while
preserving finger gaps. Stage D remains incomplete.
An initial example hid unrelated meshes. The script now changes only original,
intermediate and generated stock visibility. `check_visibility.py` restored the
second eye and studio floor from the original and verified final readback with
unchanged graft coordinates. Hand closeups precede that unrelated visibility
restoration. One process/two threads throughout, exited.

![](../../../assets/human/hands/grafted/front.png)
![](../../../assets/human/hands/grafted/oblique.png)

## Wrist fairing rejection and stock vertex weld

The wrist band is not fixed. Uniform surface relaxation exceeded its unchanged
3 mm cap. An experimental inverse-length neighbor weighting with reduced
strength then failed polygon orientation at face 122586; it was not retained
in the library. That face had edges 21.10135, 0.0008643 and 21.10122 mm, a ratio
of about 24,415. `examples/human/hands/wrist.py` reproduces the uniform rejection
on the earlier hands-grafted native, checks no source mutation or leaked objects,
and records that suspect face. It is a rejection audit, not a successful brush.
The inverse-length experiment is only retained in ignored local runs.

`graft.replace_hand` now welds stock-only vertices within 0.01 mm, after mesh
construction and before orientation checks. No retained body vertex is included
in the weld. Both hands merged 50 stock vertices. The report's 218 seam triangles
are the pre-weld candidate triangles, not a post-weld count.
Blender 5.2.2 LTS: exact retained vertices, 59,731 original above-wrist points,
source/topology, closed/oriented edges, invalid cuts, late-failure cleanup,
native readback and input hash pass. Latest native:
`runs/human/hands-grafted-welded/hands-grafted.blend`.
Two actual views inspected, one process/two threads, exited.

A subsequent low-strength uniform relaxation on the welded model still exceeded
the 3 mm cap; it produced no result native. The remaining large density mismatch
and long bridge triangles require intermediate wrist sections before further
fairing. Do not raise caps or weaken polygon guards. Finger/palm refinement and
stage D remain unfinished.

![](../../../assets/human/hands/welded/front.png)
![](../../../assets/human/hands/welded/oblique.png)

## Intermediate wrist sections and successful fairing

`graft.replace_hand` now inserts four 64-vertex rings. It samples the existing
boundary loops, measures nearby radial sections 8 mm above/below them and uses
cubic Hermite interpolation to carry the local slope across the gap. Boundary
vertices remain unchanged during reconstruction. Interior-origin/exit-normal,
height and degenerate-triangle guards reject unsupported configurations.
Source-specific upright wrist limitations remain; this is not arbitrary grafting.

Each seam has 730 pre-weld candidate triangles. Fifty near-coincident stock
vertices per side are still merged without merging retained body vertices.
`attach.py` verifies exact retention, original topology/geometry, closed oriented
edges, invalid cuts, injected late failure cleanup, native readback and hash.
Reconstructed native: `runs/human/hands-ring-bridge/hands-grafted.blend`.

`examples/human/hands/fair_wrist.py` then applies four existing uniform-neighbor
volume-preserving strokes, radius 20 mm, strength 0.12, three iterations, unchanged
3 mm cap. The same low-strength setting rejected on the long-triangle bridge
now passes. No brush algorithm, cap or polygon guard was relaxed.
Blender 5.2.2 LTS: maximum move 0.48410 mm, 149,715 protected vertices exact;
source/topology, layer rollback, exact invalid-second-mode rejection, injected
finish-failure cleanup, stored-volume checks, native readback and input hash pass.
Finger vertices below Z=.875 are outside all edit boxes and remain exact.

Current integrated native: `runs/human/wrist-ring-faired/wrist-transitions.blend`,
object `Wrist transition study`. The reconstructed boundaries are preserved on
the input snapshot; subsequent local motion is reversible. Two matched views
inspected; one process/two threads throughout, exited. A broad wrist contour
remains, while the brush-blocking topology problem is resolved for this operation.
Palm/web slab shape and blunt fingertips remain; next is palm/web shaping.
Stage D and full goal remain active.

Reconstructed whole-hand view:

![](../../../assets/human/hands/rings/bridge-front.png)

| Fairing view | Before | After |
| --- | --- | --- |
| Front | ![](../../../assets/human/hands/rings/before-front.png) | ![](../../../assets/human/hands/rings/after-front.png) |
| Oblique | ![](../../../assets/human/hands/rings/before-oblique.png) | ![](../../../assets/human/hands/rings/after-oblique.png) |
