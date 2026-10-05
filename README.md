# Mesh Workbench

Coordinate-driven modeling tools that operate **inside Blender**. Inspect render pixels and mesh data, edit vertices and polygons, combine models, and place patterns on surfaces through reproducible JSON recipes or a Python API. No simulated mouse input or external generation service.

Early **0.1.0** implementation. Built for iterative work by people and coding agents, with explicit failure checks and source-preserving operations.

## Features

- Orthographic render-to-surface maps: world position, geometric normal, depth, object/face IDs, geometry/camera revision checks.
- Coordinate Grab, Pinch, Smooth and signed normal strokes; path interpolation, pressure, edge-distance neighborhoods, masks, X symmetry and independent layers.
- Multiple models: selected `.blend` append; OBJ/STL/PLY/glTF import; transforms; copies; mesh joining; exact booleans; voxel fusion; indexed-topology morph blending.
- Vertex/edge/face selection by indices or world bounds; vertex growth; precise displacement; subdivision, extrusion, inset, bevel, weld, deletion and triangulation.
- Surface projection and conforming; raised seam curves; repeated real mesh motifs; cylindrical UVs and a procedural woven material.
- Dimensioned boxes, revolved profiles, anchored struts, transported section sweeps, local fairing and conforming relief dots through Python and JSON recipes.
- Simple materials, mesh diagnostics/export, multi-view capture, saved-file checkpoints and structured failure audits.

Topology edits and combinations create new objects. Deformation layers can be disabled independently. Existing inputs and files are preserved.

## Quick start

Install Blender separately and make `blender` available on PATH, or set `BLENDER_BIN` to its executable.

```sh
python -m pip install -e .
mesh-workbench run examples/assembly.json --output runs/assembly
mesh-workbench inspect runs/assembly/review --pixel 192 192
```

Pixel inspection on the host requires `python -m pip install -e ".[analysis]"`. Official Blender builds include NumPy. Distribution packages may require it separately (Ubuntu: `python3-numpy`). No PyPI `bpy` package is required.

From a checkout without installation:

```sh
PYTHONPATH=src python -m mesh_workbench run examples/polygon-edit.json --output runs/polygon-edit
```

PowerShell equivalent: `$env:PYTHONPATH='src'`. Alternatively use the installed `mesh-workbench` command. Output paths must be new; each run produces `result.blend`, `recipe.json`, `audit.json` and requested captures. Logs are stored beside the run directory.

![Procedural assembly example](docs/assembly.png)

## Recipes and API

See [operation reference](docs/OPERATIONS.md), [design and limits](docs/DESIGN.md), [validation status](docs/STATUS.md), and the asset-free [examples](examples).

```python
# Inside Blender Python, with this package on sys.path
from mesh_workbench import geometry, models

base = models.primitive('cube', 'Base')
top = geometry.selection(base, 'FACE', box=[[-2, -2, .99], [2, 2, 1.01]])
tower = geometry.edit_topology(base, top, 'extrude', 'Tower', delta=[0, 0, .5])
```

This is an API/CLI toolkit, not a finished interactive sculpting application. The current surface camera is orthographic. Pattern anchor spacing does **not** guarantee collision-free geometry. Blending requires matching vertex correspondence. Topology-changing results require fresh selections/maps/masks. No automatic retopology or animation rigging is claimed.

## Tests

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python tests/blender_tests.py
python -m unittest discover -s tests -p "test_*.py"
```

## License

GPL-3.0-or-later; see [LICENSE](LICENSE). No third-party character models, contest references, textures or proprietary assets are bundled. Included examples are generated procedurally by this repository. Blender is a separate dependency; this is an independent project, not an official Blender product.

## Modeled design studies

Two original procedural designs, their actual Blender renders, iterative critique and reproduction commands are available in the [design journal](docs/DESIGN_STUDIES.md). Reusable dimensioned construction helpers are exposed through the Python API.

The [organic study](examples/organic_study.py) adds a third design family and records reversible edits from captured render coordinates. Its section-sweep tool is also reused to improve the lantern handle; see the journal for before/after evidence and remaining limits.

The [field speaker recipe](examples/field-speaker.json) demonstrates the integrated construction tools without a custom Blender script. Run it with the same CLI command as the introductory recipes.
