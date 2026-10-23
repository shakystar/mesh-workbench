# Whole-character integration

## Grounded whole-character assembly - 2026-10-24

Added `assembly.ground(body, attachments, floor_z, name)`: copies an explicit
unparented mesh assembly into a new collection and applies one rigid vertical
translation. Source meshes/keys and the floor are preserved. Duplicate members,
existing collection, parented inputs and placement beyond 50 mm are rejected.
Failure removes new objects/meshes/collection.

Blender 5.2.2 LTS: current body and both eye globes shifted -7.871014 mm together;
relative positions and topology preserved. Left/right sole minima are .015010/0
mm above the studio floor, within .2 mm. Source/floor coordinates, duplicate
rejection, injected second-member failure cleanup, native readback and input
hash pass. This is lowest-point grounding, not full sole contact or pose solving.

Actual front/back full-character renders inspected. Face, ears/neck, torso,
limbs, separate digits and eye globes coexist in the saved assembly. Known
simplifications remain: rounded anatomy, shallow ear detail, hand/foot root
ridges and limited joint definition. No realistic anatomy or production rig claim.
Stage E's bounded static tool/application evidence is reviewed; F is active.
The saved assembly map records provenance and placement, not a complete merged
anatomical landmark diagram. That integration and stage-G reuse remain pending.

Current native: `runs/human/integrated/integrated.blend`, body
`Grounded character body`, plus two named attachments. `assembly.json` and
`verification.json` are adjacent. Example: `examples/human/integration/ground.py`
takes feet-tapered native and a fresh folder. One process/two threads, exited.

## Stage-E evidence handoff

| Required capability | Existing evidence inspected |
| --- | --- |
| Thigh/knee direction and transition | thigh-knee and knee-transition reports plus matched front/oblique views |
| Shin/calf profile | calf-continuous source protection, posterior probes and front/back views |
| Ankle/heel/instep/arch | foot-relief registered controls, sole protection and actual views |
| Toe divisions and connection | feet-tapered closed seams, eight gap rays, ten toe hits, retained points and views |
| Pelvis and original preservation | region outside-box checks and graft retention; original native hashes/readback |

Reviewed corresponding example assertions and reports; no passed regional checks
were repeated. These are bounded static modeling-tool criteria, not validated
human anatomy. F/G remain unfinished, including merged landmarks and reuse on
another face/body.

| Front | Back |
| --- | --- |
| ![](../../../assets/human/integration/front.png) | ![](../../../assets/human/integration/back.png) |
