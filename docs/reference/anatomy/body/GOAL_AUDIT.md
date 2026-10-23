# Bounded anatomy-tool goal acceptance

2026-10-24. The A–G scope recorded before implementation is complete.
This is a static procedural tool/application milestone, not a finished realistic
human or a validated anatomical model. Clothing, hair and rigging were excluded.

Existing native files, images and verification reports were checked for the
following stages. Passed geometry checks were not rerun for this audit.
All recorded Blender runs use 5.2.2 LTS; other versions are untested here.

| Stage | Evidence and local native folder under `runs/human/` | Acceptance |
| --- | --- | --- |
| A face | [Face handoff](../CHIN_CONTOUR.md), [eyelids](../EYELID_SUPPORT.md), [oral](../ORAL_RELIEF.md); supported-eyelids-collar, oral-relief, chin-contour | Registered controls, source/protection, reversible layers, failure cleanup, saved readback and rendered views |
| B ears/neck | [Ear curves](../AURICLE_RELIEF.md), [neck reconstruction](../NECK_TRANSITIONS.md); continuous-ears-faired, rebuilt-underside | Continuous local ridges and repaired underside; retained boundaries, face protection, failure cleanup and saved views |
| C torso | [Torso handoff](TORSO.md); flank-transition and its recorded preceding stages | Thorax, abdomen, back and pelvic transition controls; protected geometry, rollback, invalid registration, saved views |
| D arms/hands | [Arms](ARMS.md), [hand handoff](HANDS.md); arm-relief, rounded-caps and preceding hand snapshots | Arm/elbow and palm/finger controls; connected separated digits, preserved body, rollback/failure checks and saved views |
| E legs/feet | [Lower-limb handoff](LEGS.md); feet-tapered and preceding leg snapshots | Thigh/knee/calf/ankle controls and toe grafts; retained pelvis/body, eight sampled toe gaps, ten toe hits and saved views |
| F integration | [Assembly and guide](INTEGRATION.md); integrated, guided-complete | Saved complete body with eyes; grounded assembly, 40 surface markers across 17 regions, readback and front/back renders |
| G reuse | [Variant and actual reuse](VARIANTS.md); variant-b-limbs, variant-reuse | Distinct face/body proportions; separate registration, unchanged oral/calf APIs, 132 controls, 40 re-registered guides, rollback/invalid-input/late-failure checks and comparisons |

Native and PNG artifacts exist for every listed final stage. Their inspected
verification reports record successful source preservation, relevant failure
paths and native readback. G additionally preserves 189,736 outside-region
vertices exactly and has a maximum surface-fitting residual of .02517 mm.
The original proportion variant and first character remain available separately.

## Remaining limits

The actual renders retain a rough nose, simplified facial planes, shallow ears,
rounded torso/joints, hand-root and toe-root irregularities and ankle bulges.
These are not hidden by successful geometric checks. The source-based diagrams
encode relationships and authored control values, not measured universal anatomy.
Guide names are manually assigned; automatic anatomical recognition is absent.

Reuse was demonstrated for mouth and calves on a same-topology proportion
variant, not for every module or arbitrary imported topology. Eye globes share
the proportion field and are not constrained to remain rigid spheres. Sampled
digit clearance does not prove global collision freedom. New-topology snapshots
keep original masks/layers on the preserved originals rather than transferring
them blindly. Production retopology, rigs and deformation animation remain outside
this completed scope.
