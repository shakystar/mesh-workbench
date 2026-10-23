# Workspace entry points

| What to open | Location |
| --- | --- |
| Current human model | `runs/human-ear-fit/fitted-ears.blend` |
| Current renders | `docs/assets/human-current-front.png`, `human-current-three-quarter.png` |
| Human scripts and target JSON | [`examples/human/`](../examples/human/README.md) |
| Modeling library | `src/mesh_workbench/` |
| Anatomy knowledge data | `src/mesh_workbench/knowledge/` |
| Current scope and evidence | [STATUS.md](STATUS.md) |
| Historical anonymous test runs | `runs/_archive/tests/` |

2,282 `test-<uuid>` directories were moved from the top of `runs/` into
`runs/_archive/tests/`. The ignored `runs/_archive/test-moves.json` records each
original and new path. No model or evidence files were deleted. This organizes
files without reclaiming disk space. New anonymous integration runs use that
subfolder directly.

17 human example/config/render files were collected under `examples/human/`;
script roots and documentation references were updated. Named drill, camera and
human history folders remain in `runs/` as stage inputs and evidence. Their
cleanup is not claimed complete.
