"""Measure saved detail geometry independently of its descriptive metadata."""

import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import nested, assembly, sculpt


def verify(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    state = nested.load()
    objects = {k: bpy.data.objects[v["object"]] for k, v in state["outputs"].items()}
    spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())
    design = spec["surface_phase"]["detail_design"]
    checks = []

    def check(name, measured, expected, tolerance=1e-4):
        error = float(np.max(np.abs(np.asarray(measured) - np.asarray(expected))))
        checks.append(
            dict(
                name=name,
                measured=measured,
                expected=expected,
                tolerance=tolerance,
                error=error,
                passed=error <= tolerance,
            )
        )

    def ring_row(key, x, cutoff):
        xyz = np.array(
            [objects[key].matrix_world @ v.co for v in objects[key].data.vertices]
        )
        origin = np.array(spec["construction"][key]["start"])
        xyz -= origin
        row = xyz[np.abs(xyz[:, 0] - x) < 1e-4]
        radii = np.linalg.norm(row[:, 1:], axis=1)
        row, radii = row[radii > cutoff], radii[radii > cutoff]
        return radii[np.argsort(np.arctan2(row[:, 2], row[:, 1]))]

    def valleys(r):
        return int(
            np.count_nonzero((r < np.roll(r, 1) - 1e-4) & (r < np.roll(r, -1) - 1e-4))
        )

    for key, label in [("chuck_body", "chuck"), ("torque_ring", "torque_ring")]:
        d = design[label]
        row = next(r for r in d["profile"] if r[3] == 1)
        radii = ring_row(key, row[0], (row[1] + row[2]) / 2)
        check(key + " flute count", valleys(radii), d["grip_flutes"], 0)
        check(key + " flute depth", float(np.ptp(radii)), d["flute_depth"])
        for i in [0, -1]:
            r = d["profile"][i]
            check(
                key + " end radius " + str(i),
                float(ring_row(key, r[0], (r[1] + r[2]) / 2).max()),
                r[1],
            )
    r = ring_row("torque_ring", 1.2, 19)
    check("index tick count", valleys(r), 12, 0)
    check(
        "sampled index tick depth", float(np.ptp(r)), 0.2 * math.sin(math.pi * 1.2 / 3)
    )

    stock, trigger = (
        assembly._tree(objects["trigger_stock"]),
        assembly._tree(objects["trigger"]),
    )
    for z in design["trigger"]["groove_z"]:
        ray = Vector((40, 0, z))
        a = stock.ray_cast(ray, Vector((-1, 0, 0)), 80)[0]
        b = trigger.ray_cast(ray, Vector((-1, 0, 0)), 80)[0]
        check(
            "trigger groove at " + str(z),
            float(a.x - b.x),
            design["trigger"]["groove_depth"],
        )

    for side in ["left", "right"]:
        obj = objects["texture_" + side]
        adj = {v.index: set() for v in obj.data.vertices}
        for e in obj.data.edges:
            a, b = e.vertices
            adj[a].add(b)
            adj[b].add(a)
        remaining = set(adj)
        count = 0
        while remaining:
            todo = [remaining.pop()]
            count += 1
            while todo:
                for v in adj[todo.pop()]:
                    if v in remaining:
                        remaining.remove(v)
                        todo.append(v)
        check(side + " separate perimeter and ribs", count, 10, 0)
        record = json.loads(obj["mw_surface_paths"])
        src = bpy.data.objects[record["source"]]
        anchors = record["binding"]["anchors"]
        heights = []
        for i, a in enumerate(anchors):
            base = sum(
                (
                    (src.matrix_world @ src.data.vertices[v].co) * w
                    for v, w in zip(a["vertices"], a["weights"])
                ),
                Vector((0, 0, 0)),
            )
            heights.append(((obj.matrix_world @ obj.data.vertices[i].co) - base).length)
        check(side + " maximum raised height", max(heights), 0.4)
        embedded = []
        for i, a in enumerate(anchors):
            base = sum(
                (
                    (src.matrix_world @ src.data.vertices[v].co) * w
                    for v, w in zip(a["vertices"], a["weights"])
                ),
                Vector((0, 0, 0)),
            )
            embedded.append(
                (
                    (obj.matrix_world @ obj.data.vertices[i + len(anchors)].co) - base
                ).length
            )
        check(
            side + " embedded depth range", [min(embedded), max(embedded)], [0.12, 0.12]
        )
        sharp = sum(e.use_edge_sharp for e in objects["housing_" + side].data.edges)
        checks.append(
            dict(
                name=side + " physical role sharp edges",
                measured=sharp,
                passed=sharp > 0,
            )
        )

    for i, c in enumerate(design["battery_shroud"]["covers"]):
        obj = objects["battery_cover_" + str(i)]
        xyz = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        low, high = xyz.min(axis=0), xyz.max(axis=0)
        check("cover dimensions " + str(i), (high - low).tolist(), c["dimensions"])
        for label, z, offset in [
            ("upper", high[2], c["upper"]),
            ("lower", low[2], c["lower"]),
        ]:
            plane = xyz[np.abs(xyz[:, 2] - z) < 1e-4]
            check(
                "cover " + str(i) + " " + label + " y offsets",
                [float(plane[:, 1].min() - low[1]), float(high[1] - plane[:, 1].max())],
                [offset, offset],
            )
    report = dict(
        checks=checks,
        source_sha256=digest,
        source_preserved=digest == hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    report["passed"] = all(c["passed"] for c in checks) and report["source_preserved"]
    sculpt.dump(out / "details.json", report)
    for c in checks:
        if not c["passed"]:
            print("DETAIL_FAILURE", c, flush=True)
    if not report["passed"]:
        raise AssertionError("Actual detail dimensions differ")
    print("SURFACE_DETAILS", report["passed"], len(checks), flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :]
    verify(*args)
