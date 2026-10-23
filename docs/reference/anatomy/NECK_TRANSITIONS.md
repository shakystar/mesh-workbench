# Registered neck transitions: visual gate open

`mesh_workbench.regions.neck.compile_paths(source, registration)` compiles
explicit skin paths and regional bounds, without editing the input. Required
metre units, finite coordinates, visible-surface residual <=0.1 mm and upper
facial protection are checked. It returns a diagram and commands for
`surface_brush.apply`; the output snapshot has reversible stroke layers.
The new regional source folder is included in package data.

## Knowledge and scope

`neck-transition-v1.json` records relationships from
[UAMS topographical anatomy](https://medicine.uams.edu/neuroscience/education/medical-school-courses/human-structure-module/anatomy-tables/topographical-anatomy-tables/topographical-anatomy-of-the-head-and-neck/):
the anterior cervical triangle relates the midline, SCM anterior border and
mandible; the posterior triangle relates SCM, trapezius and clavicle; the
submental region relates the anterior digastric, midline and hyoid.
No source illustrations or numerical dimensions are copied.

The example's five paths are authored skin registrations: one submental fairing
path, two lower visible SCM ridges and two clavicle-transition fairing paths.
They do not locate bone or actual muscle attachments. Ridge amplitude 0.7 mm,
brush widths, protection height and fairing strengths are modeling choices.
Upper SCM insertion, posterior neck, internal anatomy and rigs are not covered.

## Native and checks

Input: `runs/human/continuous-ears-faired/continuous-ears.blend`.
Current trial native: `runs/human/neck-submental/neck-transitions.blend`.
Run `examples/human/neck/transitions.py` in factory-startup background Blender
with two CPU/numerical threads, passing input and a fresh output folder.
An optional third argument reuses existing matched source renders after checking
their report's input SHA256. It does not reuse result geometry.

Blender 5.2.2 LTS: source/topology preservation, 88,934 unchanged protected
vertices, 29,478 unchanged face/ear vertices above Z=1.535 m, all-layer rollback,
two invalid registrations, injected late failure cleanup, saved-coordinate
readback and unchanged input hash pass. Maximum combined movement is 1.61868 mm.
Two CPU/numerical threads, one Blender at a time; all processes exited.

## Visual evidence and unresolved defect

The first front-projected pass produced two before/two after 640px/16-sample
renders. The under-chin band remained. Changing submental traversal to an
inferior-front oblique view `[0, 0.8, 0.6]` and inspecting two new result views
still leaves a thin lower-chin projection. The visual gate therefore remains
open. The shallow neck-ridge changes do not resolve this defect.

A read-only saved-scene inspection found only the current head/body mesh,
two intended eyeballs and the studio floor visible for rendering. It is not an
overlapping preserved-head object. Next: inspect and reshape the local underside
surface itself, instead of repeating the same relaxation operation.

| Source profile | Current trial profile |
| --- | --- |
| ![Source](../../assets/human/neck/before-profile.png) | ![Trial](../../assets/human/neck/after-profile.png) |

![Current front](../../assets/human/neck/after-front.png)

Stage B and the whole goal remain incomplete. A successful numerical test is not
evidence that the neck attachment is visually finished.
