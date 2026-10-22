"""Measure native assembly/part silhouettes and frozen surface landmarks."""

from collections import deque
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from mesh_workbench import nested, registration
from drill_realism_guides import camera_basis, project


def mask_from_png(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Frozen mask changed: " + path.name)
    image = bpy.data.images.load(str(path.resolve()), check_existing=False)
    try:
        w,h = image.size
        rgba = np.empty(w*h*4, dtype=np.float32)
        image.pixels.foreach_get(rgba)
        return (rgba.reshape(h,w,4)[::-1,:,0] > .5).copy()
    finally:
        bpy.data.images.remove(image)


def part_proxy(name, objects, halfspace=None):
    """New measurement-only world mesh; source geometry is never edited."""
    vertices, faces = [], []
    for obj in objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            points = np.array([obj.matrix_world @ v.co for v in mesh.vertices])
            for triangle in mesh.loop_triangles:
                polygon = list(points[list(triangle.vertices)])
                if halfspace is not None:
                    sign, height = halfspace
                    clipped = []
                    for a,b in zip(polygon, polygon[1:]+polygon[:1]):
                        da,db = sign*(a[2]-height), sign*(b[2]-height)
                        if da >= 0:
                            clipped.append(a)
                        if (da < 0) != (db < 0):
                            clipped.append(a+(b-a)*da/(da-db))
                    polygon = clipped
                if len(polygon) < 3:
                    continue
                offset = len(vertices)
                vertices.extend(polygon)
                for j in range(1,len(polygon)-1):
                    tri = [offset,offset+j,offset+j+1]
                    a,b,c = (vertices[i] for i in tri)
                    if np.linalg.norm(np.cross(b-a,c-a)) > 1e-10:
                        faces.append(tri)
        finally:
            evaluated.to_mesh_clear()
    if not faces:
        raise ValueError("No measured geometry for role " + name)
    mesh = bpy.data.meshes.new("Measurement " + name)
    mesh.from_pydata(np.asarray(vertices).tolist(), [], faces)
    mesh.update()
    proxy = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(proxy)
    return proxy, BVHTree.FromPolygons(np.asarray(vertices).tolist(), faces, all_triangles=True)


def fill_enclosed(mask):
    h, w = mask.shape
    outside = np.zeros_like(mask)
    queue = deque()
    for y, x in ([(0,x) for x in range(w)]+[(h-1,x) for x in range(w)]
                 +[(y,0) for y in range(h)]+[(y,w-1) for y in range(h)]):
        if not mask[y,x] and not outside[y,x]:
            outside[y,x] = True
            queue.append((y,x))
    while queue:
        y,x = queue.popleft()
        for a,b in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0 <= a < h and 0 <= b < w and not mask[a,b] and not outside[a,b]:
                outside[a,b] = True
                queue.append((a,b))
    return ~outside


def measure(source, frozen, output):
    if output.exists():
        raise ValueError("Use a fresh measurement directory")
    freeze = json.loads((frozen / "freeze.json").read_text())
    for path,digest in freeze["inputs"].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError("Frozen input changed")
    manifest = json.loads((frozen / "manifest.json").read_text())
    if hashlib.sha256((frozen / "manifest.json").read_bytes()).hexdigest() != freeze["guide_manifest_sha256"]:
        raise ValueError("Frozen guide manifest changed")
    target = json.loads((ROOT / "examples/drill-realism-target.json").read_text())
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    objects = [bpy.data.objects[r["object"]] for key,r in state["outputs"].items()
               if state["nodes"][key].get("visible", True)]
    by_role = {key:bpy.data.objects[r["object"]] for key,r in state["outputs"].items()
               if state["nodes"][key].get("visible", True)}
    body = [k for k in by_role if k.startswith(("housing_", "grip_", "texture_", "fastener_", "vent_baffle_", "vent_support_")) or k == "rear_cover"]
    groups = {"housing": body, "grip": body,
              "chuck": [k for k in by_role if k in ("torque_ring","chuck_body","jaw_cage") or k.startswith("jaw_")],
              "battery": [k for k in by_role if k.startswith(("battery", "rail_", "channel_", "latch_")) or k == "foot"]}
    proxies, trees = {}, {}
    for role, ids in groups.items():
        clip = (1,108) if role == "housing" else (-1,108) if role == "grip" else None
        proxies[role], trees[role] = part_proxy(role, [by_role[k] for k in ids], clip)
    landmarks = {}
    for query in freeze["landmarks"]:
        hit = trees[query["part"]].ray_cast(Vector(query["origin"]), Vector(query["direction"]), 1000)
        landmarks[query["id"]] = None if hit[0] is None else list(hit[0])
    output.mkdir(parents=True)
    reports = {}
    for name,record in manifest["views"].items():
        view = record["camera"]
        right, up, center = camera_basis(view)
        size = manifest["size"][0]
        scale = size/view["scale"]
        matrix = np.array([list(right*scale)+[size/2-center@right*scale],
                           list(-up*scale)+[size/2+center@up*scale], [0,0,0,1]])
        actual_raw = registration.silhouette(objects, {"size": [size,size],
                     "projection": "orthographic", "matrix": matrix.tolist()})
        expected_raw = mask_from_png(frozen / record["assembly_path"], record["assembly_sha256"])
        actual, expected = fill_enclosed(actual_raw), fill_enclosed(expected_raw)
        report = registration.compare_masks(actual, expected, np.ones_like(actual), record["bbox_xyxy"])
        report.update({"actual_filled_hole_pixels": int((actual & ~actual_raw).sum()),
                       "guide_filled_hole_pixels": int((expected & ~expected_raw).sum()),
                       "passed": report["iou"] >= target["comparison"]["silhouette_iou_min"]
                       and report["boundary_p95_fraction"] <= target["comparison"]["boundary_p95_diagonal_max"]})
        reports[name] = report
        np.savez_compressed(output / f"{name}.npz", actual=actual, expected=expected)
        part_reports = {}
        for role,proxy in proxies.items():
            p_actual = fill_enclosed(registration.silhouette([proxy], {"size": [size,size],
                        "projection": "orthographic", "matrix": matrix.tolist()}))
            ref = record["parts"][role]
            p_expected = fill_enclosed(mask_from_png(frozen/ref["path"], ref["sha256"]))
            metrics = registration.compare_masks(p_actual, p_expected, np.ones_like(p_actual), record["bbox_xyxy"])
            metrics["passed"] = metrics["iou"] >= target["comparison"]["part_iou_min"]
            part_reports[role] = metrics
            np.savez_compressed(output/f"{name}-{role}.npz", actual=p_actual, expected=p_expected)
        report["parts"] = part_reports
        ids = freeze["views"][name]["visible_landmarks"]
        missing = [key for key in ids if landmarks[key] is None]
        if missing:
            landmark_report = {"count":len(ids), "missing":missing, "passed":False, "rms_fraction":None}
        else:
            actual_xy = project([landmarks[key] for key in ids], view, size)
            expected_xy = np.array([freeze["views"][name]["expected_pixels"][key] for key in ids])
            errors = np.linalg.norm(actual_xy-expected_xy, axis=1)
            box = np.array(record["bbox_xyxy"])
            rms = float(np.sqrt(np.mean(errors**2))/np.linalg.norm(box[2:]-box[:2]))
            landmark_report = {"count":len(ids), "ids":ids, "missing":[],
                "errors_pixels":dict(zip(ids,errors.tolist())), "rms_fraction":rms,
                "passed":rms <= target["comparison"]["landmark_rms_diagonal_max"]}
        report["landmarks"] = landmark_report
        print("SILHOUETTE", name, json.dumps(report), flush=True)
    result = {"blender": bpy.app.version_string, "source_sha256": source_hash,
              "source_preserved": source_hash == hashlib.sha256(source.read_bytes()).hexdigest(),
              "freeze_sha256": hashlib.sha256((frozen / "freeze.json").read_bytes()).hexdigest(),
              "scope": "assembly/part silhouettes and ray-defined visible landmarks; motion/visual gates remain",
              "role_groups":groups, "candidate_landmarks_xyz":landmarks,
              "views": reports, "passed_silhouette_gates": all(r["passed"] for r in reports.values()),
              "passed_part_gates":all(p["passed"] for r in reports.values() for p in r["parts"].values()),
              "passed_landmark_gates":all(r["landmarks"]["passed"] for r in reports.values())}
    (output / "measurement.json").write_text(json.dumps(result, indent=2)+"\n")
    if not result["source_preserved"]:
        raise ValueError("Native source changed")
    for proxy in proxies.values():
        mesh = proxy.data
        bpy.data.objects.remove(proxy, do_unlink=True)
        bpy.data.meshes.remove(mesh)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    measure(*map(Path, args))
