# Project instructions

- Read README.md and docs/STATUS.md before implementation.
- This is a standalone open-source Blender tool. Keep character/reference assets, private data, credentials and machine-specific paths out of tracked files.
- Preserve inputs. Topology edits and model combinations create new objects; deformation edits use reversible layers. Do not silently invalidate selections or masks.
- Use factory-startup background Blender for tests. Do not modify user preferences or install global add-ons.
- Validate geometric effects and failure paths, not only operator return codes. Run `tests/blender_tests.py` and the affected example recipes.
- Record tested Blender versions and remaining limits. Do not claim arbitrary retopology, collision-free patterns or production-ready rigs.
- Generated runs belong in ignored `runs/`. Public preview images must come only from included procedural examples.
