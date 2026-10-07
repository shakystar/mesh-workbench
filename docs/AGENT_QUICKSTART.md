# Use Mesh Workbench with a coding agent

Mesh Workbench is an MIT-licensed Python/JSON toolkit for coordinate-driven 3D modeling inside Blender. Use it to inspect mesh/render coordinates, edit polygons, combine models, build surface patterns, and regenerate parametric assemblies. It runs locally through a CLI or Blender Python, not a hosted API or MCP server.

## Install and execute a first recipe

Requirements: Python 3.11+, separately installed Blender. Integration tests have passed on Blender 4.0.2 (Linux) and 5.2.2 LTS (Windows); other versions are not certified.

```sh
git clone https://github.com/shakystar/mesh-workbench.git
cd mesh-workbench
python -m pip install -e .
mesh-workbench run examples/polygon-edit.json --output runs/first-model
```

Blender must be on PATH, or set `BLENDER_BIN` / pass `--blender` with the executable path. Use a new output path for each run. A successful run returns exit code 0 and saves `result.blend`, `recipe.json`, and `audit.json` with status `complete`. Read the audit and inspect the actual output; process startup alone is not success. The CLI log is beside the output folder. Failures return nonzero and may include an audit with status `failed`.

## Choose an operation

| Task | Entry point |
| --- | --- |
| Vertex/face edits | [Polygon recipe](../examples/polygon-edit.json), [operation reference](reference/OPERATIONS.md) |
| Parametric assemblies | [Assembly recipe](../examples/assembly.json), `nested_initialize`, `nested_update` |
| Surface details | `surface_paths`, `profiled_ring`, `variable_bevel` |
| Local patch reconstruction | `rebuild_patch`, explicit selection and error bounds |
| Full modeling example | [Detailed drill recipe](../examples/drill-surface.json), [measured study](studies/DRILL_SURFACE_STUDY.md) |
| Current verified behavior | [Status](STATUS.md), [architecture and limits](reference/DESIGN.md) |

Read operation argument definitions before building a recipe. Python geometry operations require Blender's `bpy`; the host CLI launches Blender with factory startup and automatic script execution disabled. Do not install PyPI `bpy` as a substitute for the documented Blender runtime.

## Editing and verification contract

Preserve input models. Topology changes create new objects; selections, maps and masks must match current topology. UV/material seam crossing and unsupported projections can be rejected. Check numerical geometry and failure recovery, then render the result. Motion and shape-error bounds are sampled, not continuous collision or manufacturing certification. Arbitrary quad retopology and persistent manual edits across full procedural regeneration are not supported.

Run changed examples and the [test commands](../README.md#tests). Report Blender version, minimal asset-free recipe, output audit and expected behavior in [GitHub issues](https://github.com/shakystar/mesh-workbench/issues). Submit improvements through [pull requests](../CONTRIBUTING.md).

## Discovery files

[llms.txt](../llms.txt) is a short documentation index. [tool-manifest.json](../tool-manifest.json) is a descriptive local-tool manifest with commands, prerequisites and documentation URLs. Neither guarantees discovery, indexing or installation by an agent. The HTML documentation is readable without JavaScript.
