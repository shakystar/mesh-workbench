# Documentation

Start with [current status](STATUS.md), then [next milestones](ROADMAP.md). Study reports are dated evidence; the status page owns current capability and validation statements.

| Location | Purpose |
| --- | --- |
| [STATUS.md](STATUS.md) | Current verified implementation, limits and next work |
| [ROADMAP.md](ROADMAP.md) | Planned drill assembly milestones and acceptance gates |
| [reference/OPERATIONS.md](reference/OPERATIONS.md) | Python and JSON operation reference |
| [reference/DESIGN.md](reference/DESIGN.md) | Architecture and modeling boundaries |
| `studies/` | Reproducible modeling studies and comparison findings |
| `audits/` | Machine-readable evidence from completed runs |
| `assets/` | Native Blender previews and authored dimension sheets |
| [archive/DEVELOPMENT_HISTORY.md](archive/DEVELOPMENT_HISTORY.md) | Preserved chronological development snapshots |

## Study index

| Study | Evidence |
| --- | --- |
| [Cordless drill and local remeshing](studies/DRILL_STUDY.md) | [Audit](audits/DRILL_AUDIT.json) |
| [Folding headphones](studies/HEADPHONE_STUDY.md) | [Audit](audits/HEADPHONE_AUDIT.json) |
| [Regenerating mouse assembly](studies/ASSEMBLY_STUDY.md) | [Audit](audits/ASSEMBLY_AUDIT.json) |
| [Asymmetric mouse](studies/MOUSE_STUDY.md) | [Audit](audits/MOUSE_AUDIT.json) |
| [Speaker precision study](studies/PRECISION_STUDY.md) | [Audit](audits/PRECISION_AUDIT.json) |
| [Original four-design portfolio](studies/PORTFOLIO.md) | [Audit](audits/PORTFOLIO_AUDIT.json) |
| [Early design iteration journal](studies/DESIGN_STUDIES.md) | Evidence and rejected candidates within the journal |

## Maintenance

Keep current state in STATUS and future work in ROADMAP; append historical evidence to the relevant study or archive. New studies link their audit and assets using relative paths. Keep reproduction commands relative to the repository root. Generated `.blend` files and run logs stay in ignored `runs/`; public evidence includes reproducible scripts, measurements and procedural previews. Do not rewrite historical measurements when newer capabilities supersede their limitations.
