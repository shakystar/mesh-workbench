# Contributing

Open an issue with the Blender version, a minimal asset-free recipe, expected result and audit/error output. Avoid attaching private models or credentials. Contributions to the original project code and documentation are accepted under MIT. Submit only material you have permission to license this way, and retain third-party notices.

Keep geometry operations separate from host CLI code. Preserve source objects on topology changes. Add numerical checks for new behavior and rejected inputs; an operator returning FINISHED is not sufficient. Run Blender integration tests and affected examples. Save generated output under `runs/`, never commit private `.blend` files.

Current priorities: broader Blender/platform coverage, persistent element IDs, surface-geodesic refinement, pattern tangent continuity and collision diagnostics, perspective maps, and interactive front-end integration. These are roadmap items, not current guarantees.

## Development workflow

1. Fork the repository and create a focused branch.
2. Install Blender separately, then `python -m pip install -e .`.
3. Add a minimal procedural example and geometric/failure-path checks for changed behavior.
4. Run the commands in README.md, then open a pull request with the problem, change, tested Blender version and evidence.

Documentation fixes, reproducible bug reports, new recipes and portability results are welcome. Commercial reuse, modification and redistribution of the original project code are permitted under MIT, subject to its notice requirements. See [dependency licensing](THIRD_PARTY_NOTICES.md) for Blender and optional libraries.
