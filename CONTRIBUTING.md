# Contributing

Open an issue with the Blender version, a minimal asset-free recipe, expected result and audit/error output. Avoid attaching private models or credentials. Contributions are accepted under GPL-3.0-or-later.

Keep geometry operations separate from host CLI code. Preserve source objects on topology changes. Add numerical checks for new behavior and rejected inputs; an operator returning FINISHED is not sufficient. Run Blender integration tests and affected examples. Save generated output under `runs/`, never commit private `.blend` files.

Current priorities: broader Blender/platform coverage, persistent element IDs, surface-geodesic refinement, pattern tangent continuity and collision diagnostics, perspective maps, and interactive front-end integration. These are roadmap items, not current guarantees.
