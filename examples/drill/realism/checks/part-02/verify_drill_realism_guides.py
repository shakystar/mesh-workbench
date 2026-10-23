"""Check host-authored camera projections against Blender's native camera math."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench.runner import camera
from drill_realism_guides import camera_basis, project, rings, resolve_parts


def verify(output, masks=None):
    if output.exists():
        raise ValueError("Use a fresh verification path")
    target = json.loads((ROOT / "examples/drill/realism/recipes/part-01/drill-realism-target.json").read_text())
    points = np.array(list(target["authored_landmarks"].values()))
    reports = []
    for name in target["comparison"]["primary_views"]:
        view = target["capture"]["views"][name]
        camera(**view, size=[768, 768])
        actual = np.array([world_to_camera_view(bpy.context.scene,
                           bpy.context.scene.camera, Vector(p))[:2] for p in points])
        actual[:, 0] *= 768
        actual[:, 1] = (1-actual[:, 1])*768
        expected = project(points, view, 768)
        error = float(np.linalg.norm(actual-expected, axis=1).max())
        reports.append({"view": name, "points": len(points),
                        "maximum_pixel_error": error, "passed": error < .001})
    report = {"blender": bpy.app.version_string, "camera_checks": reports,
              "passed": all(r["passed"] for r in reports),
              "scope": "Camera coordinate agreement only; not silhouette or photo accuracy"}
    if masks is not None:
        guide = json.loads((ROOT / "examples/drill/realism/recipes/part-01/drill-realism-guide-sections.json").read_text())
        vertices, polygons, owners = [], [], []
        for owner, design in enumerate(resolve_parts(guide, target).values()):
            sections = rings(design)
            offset, n = len(vertices), len(sections[0])
            vertices.extend(np.concatenate(sections).tolist())
            faces = []
            for i in range(len(sections)-1):
                for j in range(n):
                    a, b = offset+i*n+j, offset+i*n+(j+1)%n
                    faces.extend([(a, b, b+n), (a, b+n, a+n)])
            for start in (offset, offset+(len(sections)-1)*n):
                faces.extend((start, start+j, start+j+1) for j in range(1, n-1))
            polygons.extend(faces)
            owners.extend([owner]*len(faces))
        tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
        visibility = []
        for name in target["comparison"]["primary_views"]:
            data = np.load(masks / f"{name}-labels.npz")
            labels = data["labels"]
            if list(data["parts"]) != list(guide["parts"]):
                raise ValueError("Mask role order differs from guide")
            view = target["capture"]["views"][name]
            right, up, center = camera_basis(view)
            backward = np.cross(right, up)
            size = labels.shape[0]
            checked, mismatches = 0, []
            # Subpixel-edge ties are excluded before comparison by requiring a
            # homogeneous 3x3 label neighborhood; record the denominator.
            for y in range(4, size-1, 7):
                for x in range(4, size-1, 7):
                    expected = int(labels[y, x])
                    if not np.all(labels[y-1:y+2, x-1:x+2] == expected):
                        continue
                    origin = (center + right*((x+.5)/size-.5)*view["scale"]
                              + up*(.5-(y+.5)/size)*view["scale"] + backward*1000)
                    hit = tree.ray_cast(Vector(origin), Vector(-backward), 2000)
                    actual = -1 if hit[0] is None else owners[hit[2]]
                    checked += 1
                    if actual != expected:
                        mismatches.append([x, y, expected, actual])
            visibility.append({"view": name, "checked_rays": checked,
                               "mismatches": mismatches, "passed": not mismatches})
        report["visibility_checks"] = visibility
        report["passed"] &= all(r["passed"] for r in visibility)
        report["scope"] += "; sampled guide visibility checked using native BVH rays"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print("GUIDE_CAMERA_CHECK", json.dumps(report), flush=True)
    if not report["passed"]:
        raise ValueError("Authored camera projection differs from Blender")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    verify(Path(args[0]), Path(args[1]) if len(args) > 1 else None)
