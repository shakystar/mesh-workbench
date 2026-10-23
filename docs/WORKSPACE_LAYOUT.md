# Workspace layout: at most ten direct files per folder

The limit counts files, not subfolders. `.git` and the user-approved `.venv`
exception remain untouched. Every other folder, including generated artifacts,
is included in the final check.

| Category | Location |
| --- | --- |
| Current human native | `runs/human/rebuilt-underside/rebuilt-underside.blend`; preserved input in `runs/human/neck-submental/` |
| Current human images | `docs/assets/human/neck/rebuilt-front.png`, `rebuilt-profile.png`; prior details in `ears/`, `chin/`, `mouth/`, `eyes/`, `nose/` |
| Human scripts / target JSON | `examples/human/scripts/`, `examples/human/eyes/`, `examples/human/nose/`, `examples/human/recipes/` |
| Drill examples | `examples/drill/{assembly,realism,surface,base}/` |
| Other examples | `examples/{camera,mouse,headphones,speaker,organic,lantern,sculpture,general}/` |
| Library implementation | `src/mesh_workbench/{anatomy,geometry,forms,mechanisms,details,workflow}/` |
| Knowledge data | `src/mesh_workbench/knowledge/` |
| Model images | `docs/assets/{human,drill,camera,mouse,...}/` |
| Model runs | `runs/{human,drill,camera,mouse,...}/` |
| Build snapshots / other runs / loose records | `runs/builds/`, `runs/other/`, `runs/loose/` |
| Historical tests and caches | `runs/_archive/` |

Within topics, scripts, checks, recipes, images, logs and records are separated.
A type with more than ten files is split into `part-01`, `part-02`, etc.
Library public imports such as `from mesh_workbench import anatomy` remain valid;
the package searches its functional source directories. The wheel includes those
modules and knowledge data. Example scripts use a shared import bootstrap.

4,938 files were moved; none were deleted. Empty directories were removed.
[Tracked path map](reference/layout/moved-files.json) records public relocations.
The complete local map is `runs/organization/plan.json`; pre-move paths/sizes are
in `runs/organization/moves-before.json`. Historical generated records retain
original contents; use the map to locate an old path referenced inside them.

Verification: all moved destinations exist; no local Markdown links are broken;
Python syntax and literal example resources pass; 48 library modules, four
knowledge resources and two human entrypoints load in Blender 5.2.2 LTS.
Three host CLI checks pass. The built wheel contains all 55 expected source/data
entries. No geometry or render tests were added for this file-layout change.

Run the layout check after adding files or producing artifacts:

```text
python scripts/check_layout.py
```

The verified maximum is ten direct files, with zero violations outside `.git`
and `.venv`. This is organization, not disk-space reclamation.
