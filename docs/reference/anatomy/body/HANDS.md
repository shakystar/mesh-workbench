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
