"""Derive orthographic drawing polygons from the frozen authored section brief.

Run once in factory Blender: -- NEW_REFERENCE_JSON. No candidate mesh is read.
The front drawing is explicitly a convex projected envelope; top/side retain
longitudinal concavity. Section bounds are sampled independently at guide planes.
"""

import json
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import loft, reference

spec = json.loads((ROOT / "examples/mouse-target.json").read_text())
output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
if output.exists():
    raise ValueError("Frozen reference already exists")
ys = sorted(
    set(np.linspace(-62, 62, 257).tolist() + [s["y"] for s in spec["sections"]])
)
values = loft.section_values(spec["sections"], spec["seam_height"], ys)
angles = np.linspace(0, math.tau, 513)[:-1]
rows = []
edit = spec["local_edit"]
center = np.asarray(edit["center"])
for y, v in zip(ys, values):
    coords = loft.cross_section(y, v, spec["seam_height"], spec["tilt"], angles)
    weight = np.clip(1 - np.linalg.norm(coords - center, axis=1) / edit["radius"], 0, 1)
    coords += (
        weight[:, None] ** 2
        * (3 - 2 * weight[:, None])
        * np.array(edit["displacement"])
    )
    rows.append(coords)
rows = np.array(rows)
# XY top and YZ side are envelopes along each authored Y section.
top = np.concatenate(
    (
        np.column_stack((rows[:, :, 0].min(1), ys)),
        np.column_stack((rows[::-1, :, 0].max(1), ys[::-1])),
    )
)
side = np.concatenate(
    (
        np.column_stack((ys, rows[:, :, 2].min(1))),
        np.column_stack((ys[::-1], rows[::-1, :, 2].max(1))),
    )
)


def hull(points):
    points = sorted(set(map(tuple, points)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    halves = []
    for seq in [points, reversed(points)]:
        part = []
        for p in seq:
            while len(part) >= 2 and cross(part[-2], part[-1], p) <= 0:
                part.pop()
            part.append(p)
        halves.append(part[:-1])
    return halves[0] + halves[1]


front = hull(rows[:, :, [0, 2]].reshape(-1, 2))
ref = {
    "version": 1,
    "name": "Authored mouse drawing polygons",
    "source_brief_sha256": reference.fingerprint(spec),
    "views": spec["views"],
    "components": {
        k: {
            "view": k,
            "shapes": [
                {"kind": "polygon", "points": np.round(np.asarray(v), 6).tolist()}
            ],
        }
        for k, v in [("top", top), ("side", side), ("front", front)]
    },
    "section_bounds": [],
    "limitation": "Derived authored design envelopes, not measured product data; front uses a convex envelope.",
}
for sec in spec["sections"][1:-1]:
    idx = ys.index(sec["y"])
    ref["section_bounds"].append(
        {
            "y": sec["y"],
            "bounds": [rows[idx].min(0).tolist(), rows[idx].max(0).tolist()],
        }
    )
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(ref, indent=2) + "\n", encoding="utf-8")
print("FROZEN_REFERENCE", reference.fingerprint(ref), flush=True)
