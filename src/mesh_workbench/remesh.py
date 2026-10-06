"""Conservative local triangle remeshing with frozen feature charts.

World-space baked output; boundaries, sharp/material/UV seams are pinned.
Correspondence is measured projection within a connected source chart, not
an exact inverse or a general quad retopology solver.
"""

import copy
import json
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import geometry, sculpt, attachments, regions, fairing


def _edges(faces):
    out = {}
    for i, f in enumerate(faces):
        for a, b in zip(f, f[1:] + f[:1]):
            out.setdefault(tuple(sorted((a, b))), []).append(i)
    return out


def _normal(x, f):
    a, b, c = [x[i] for i in f]
    n = np.cross(b - a, c - a)
    return n


def _quality(x, f):
    a, b, c = [x[i] for i in f]
    den = np.dot(a - b, a - b) + np.dot(b - c, b - c) + np.dot(c - a, c - a)
    return (
        float(2 * math.sqrt(3) * np.linalg.norm(np.cross(b - a, c - a)) / den)
        if den
        else 0
    )


def _weights(point, triangle):
    a, b, c = np.asarray(triangle)
    w = np.linalg.lstsq(
        np.column_stack((b - a, c - a)), np.asarray(point) - a, rcond=None
    )[0]
    weights = np.array([1 - w.sum(), *w])
    if weights.min() < -1e-4:
        raise ValueError("Unstable surface correspondence")
    weights = np.maximum(weights, 0)
    return weights / weights.sum()


def _samples(x, faces):
    # Vertices, all edge midpoints and triangle centroids; sampled, not Hausdorff.
    return (
        list(x)
        + [(x[a] + x[b]) / 2 for a, b in _edges(faces)]
        + [np.mean([x[i] for i in f], axis=0) for f in faces]
    )


def _tree(x, faces):
    return BVHTree.FromPolygons(np.asarray(x).tolist(), faces, all_triangles=True)


def _snapshot(source, selection, sharp_angle):
    sculpt.editable(source)
    sel = geometry.validate_selection(source, selection)
    if sel["domain"] != "FACE" or not sel["indices"]:
        raise ValueError("Nonempty face selection required")
    ev = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        faces = [list(t.vertices) for t in mesh.loop_triangles]
        parents = [t.polygon_index for t in mesh.loop_triangles]
        loops = [list(t.loops) for t in mesh.loop_triangles]
        uvs = {
            uv.name: [[list(uv.data[j].uv) for j in ls] for ls in loops]
            for uv in mesh.uv_layers
        }
    finally:
        ev.to_mesh_clear()
    x = sculpt.coordinates(source)
    if not faces or len(faces) > 100000 or not np.isfinite(x).all():
        raise ValueError("Expected finite surface with 1..100000 triangles")
    if any(np.linalg.norm(_normal(x, f)) < 1e-10 for f in faces):
        raise ValueError("Degenerate source triangle")
    edges = _edges(faces)
    if len({v for f in faces for v in f}) != len(x):
        raise ValueError("Loose source vertices are unsupported")
    if any(len(v) > 2 for v in edges.values()):
        raise ValueError("Nonmanifold source")
    active = [p in set(sel["indices"]) for p in parents]
    normals = [_normal(x, f) for f in faces]
    normals = [n / np.linalg.norm(n) for n in normals]
    explicit = {
        tuple(sorted(e.vertices))
        for e in source.data.edges
        if e.use_seam or e.use_edge_sharp
    }
    feature = set()
    adjacency = [[] for _ in faces]
    for edge, fs in edges.items():
        locked = len(fs) != 2 or edge in explicit
        if not locked:
            a, b = fs
            locked = (
                active[a] != active[b]
                or source.data.polygons[parents[a]].material_index
                != source.data.polygons[parents[b]].material_index
                or np.dot(normals[a], normals[b]) < math.cos(math.radians(sharp_angle))
            )
            for uv in uvs.values():
                for v in edge:
                    if not np.allclose(
                        uv[a][faces[a].index(v)],
                        uv[b][faces[b].index(v)],
                        atol=1e-7,
                        rtol=0,
                    ):
                        locked = True
        if locked:
            feature.add(edge)
        else:
            a, b = fs
            adjacency[a].append(b)
            adjacency[b].append(a)
    charts = [-1] * len(faces)
    for i in range(len(faces)):
        if charts[i] >= 0:
            continue
        todo = [i]
        charts[i] = i
        while todo:
            a = todo.pop()
            for b in adjacency[a]:
                if charts[b] < 0:
                    charts[b] = i
                    todo.append(b)
    pinned = {v for e in feature for v in e}
    pinned.update(v for f, act in zip(faces, active) if not act for v in f)
    return x, faces, parents, uvs, active, charts, pinned


def remesh(
    source, selection, name, target_length, iterations=3, max_error=0.1, sharp_angle=40
):
    target_length = sculpt.number(target_length, 1e-5, 1e5, "target edge length")
    max_error = sculpt.number(max_error, 1e-7, 1e4, "surface error")
    sharp_angle = sculpt.number(sharp_angle, 1, 89, "feature angle")
    if type(iterations) != int or not 1 <= iterations <= 12 or name in bpy.data.objects:
        raise ValueError("Expected 1..12 passes and unused output name")
    original, initial, parents, uvs, active, charts, pinned = _snapshot(
        source, selection, sharp_angle
    )
    if fairing.overlap_candidates(source):
        raise ValueError("Source has triangle overlap candidates")
    trees = {}
    chart_ids = {}
    for c in set(charts):
        ids = [i for i, t in enumerate(charts) if t == c]
        chart_ids[c] = ids
        trees[c] = _tree(original, [initial[i] for i in ids])

    def project(p, c):
        hit, n, index, d = trees[c].find_nearest(Vector(p))
        if hit is None or d > max_error:
            return None
        return np.asarray(hit, dtype=float)

    x = [p.copy() for p in original]
    faces = copy.deepcopy(initial)
    labels = list(charts)
    enabled = list(active)
    counts = {"split": 0, "collapse": 0, "flip": 0}
    for _ in range(iterations):
        for operation in ("split", "collapse", "flip"):
            edges = _edges(faces)
            incident = {i: set() for i in range(len(x))}
            for i, f in enumerate(faces):
                for v in f:
                    incident[v].add(i)
            removed = set()
            appended = []
            touched = set()
            for (a, b), fs in edges.items():
                if len(fs) != 2 or a in pinned or b in pinned:
                    continue
                neighborhood = incident[a] | incident[b]
                if neighborhood & touched or not all(enabled[i] for i in neighborhood):
                    continue
                if len({labels[i] for i in neighborhood}) != 1:
                    continue
                length = float(np.linalg.norm(x[a] - x[b]))
                c = labels[fs[0]]
                replacements = []
                old_indices = fs
                changed = None
                if operation == "split":
                    if length <= target_length * 4 / 3:
                        continue
                    point = project((x[a] + x[b]) / 2, c)
                    if point is None:
                        continue
                    v = len(x)
                    x.append(point)
                    for i in fs:
                        f = faces[i]
                        k = next(
                            k for k in range(3) if {f[k], f[(k + 1) % 3]} == {a, b}
                        )
                        u, w, z = f[k], f[(k + 1) % 3], f[(k + 2) % 3]
                        replacements.extend([(i, [u, v, z]), (i, [v, w, z])])
                elif operation == "collapse":
                    if length >= target_length * 0.65:
                        continue
                    na = {v for i in incident[a] for v in faces[i]} - {a, b}
                    nb = {v for i in incident[b] for v in faces[i]} - {a, b}
                    opposite = {v for i in fs for v in faces[i]} - {a, b}
                    if na & nb != opposite:
                        continue  # link condition
                    point = project((x[a] + x[b]) / 2, c)
                    if point is None:
                        continue
                    old_indices = list(neighborhood)
                    changed = x[a].copy()
                    x[a] = point
                    replacements = [
                        (i, [a if v == b else v for v in faces[i]])
                        for i in old_indices
                        if i not in fs
                    ]
                else:
                    i, j = fs
                    f = faces[i]
                    k = next(k for k in range(3) if {f[k], f[(k + 1) % 3]} == {a, b})
                    u, v, w = f[k], f[(k + 1) % 3], f[(k + 2) % 3]
                    z = next(vv for vv in faces[j] if vv not in (a, b))
                    if tuple(sorted((w, z))) in edges:
                        continue
                    new = [[w, z, v], [z, w, u]]
                    if (
                        min(_quality(x, t) for t in new)
                        <= min(_quality(x, faces[ii]) for ii in fs) + 1e-4
                    ):
                        continue
                    replacements = list(zip(fs, new))
                valid = True
                for i, f in replacements:
                    n = _normal(x, f)
                    old = _normal(x, faces[i])
                    if changed is not None:
                        xx = [changed if v == a else x[v] for v in faces[i]]
                        old = np.cross(xx[1] - xx[0], xx[2] - xx[0])
                    if (
                        np.linalg.norm(n) < 1e-10
                        or np.dot(n, old) <= 0
                        or _quality(x, f) < 1e-4
                    ):
                        valid = False
                        break
                    for p in [np.mean([x[v] for v in f], axis=0)] + [
                        (x[f[k]] + x[f[(k + 1) % 3]]) / 2 for k in range(3)
                    ]:
                        if project(p, c) is None:
                            valid = False
                            break
                    if not valid:
                        break
                if not valid:
                    if changed is not None:
                        x[a] = changed
                    if operation == "split":
                        x.pop()
                    continue
                counts[operation] += 1
                removed.update(old_indices)
                touched.update(neighborhood)
                appended.extend((f, labels[i], enabled[i]) for i, f in replacements)
            records = [
                (f, c, act)
                for i, (f, c, act) in enumerate(zip(faces, labels, enabled))
                if i not in removed
            ] + appended
            faces = [f for f, _, _ in records]
            labels = [c for _, c, _ in records]
            enabled = [a for _, _, a in records]
            if len(faces) > 200000:
                raise ValueError("Remesh triangle budget exceeded")
    used = sorted({v for f in faces for v in f})
    index = {v: i for i, v in enumerate(used)}
    x = np.asarray([x[i] for i in used])
    faces = [[index[v] for v in f] for f in faces]
    forward = _tree(original, initial)
    reverse = _tree(x, faces)
    distances = [float(forward.find_nearest(Vector(p))[3]) for p in _samples(x, faces)]
    backwards = [
        float(reverse.find_nearest(Vector(p))[3]) for p in _samples(original, initial)
    ]
    if max(distances + backwards) > max_error:
        raise ValueError(
            "Bidirectional sampled surface error %.9g exceeds limit %.9g"
            % (max(distances + backwards), max_error)
        )
    edges = _edges(faces)
    if any(len(v) > 2 for v in edges.values()) or len(
        {tuple(sorted(f)) for f in faces}
    ) != len(faces):
        raise ValueError("Invalid remesh connectivity")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(x.tolist(), [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    try:
        if fairing.overlap_candidates(obj):
            raise ValueError("Remesh introduced overlap candidates")
        # Per-vertex mapping stays within its original connected feature chart.
        vertex_chart = {v: labels[i] for i, f in enumerate(faces) for v in f}
        mapping = []

        def correspondence(point, c):
            hit, n, t, d = trees[c].find_nearest(Vector(point))
            i = chart_ids[c][t]
            return i, _weights(hit, original[initial[i]])

        for v, p in enumerate(x):
            i, w = correspondence(p, vertex_chart[v])
            mapping.append({"vertices": initial[i], "weights": w.tolist()})
        source_edges = {
            tuple(sorted(e.vertices)): (e.use_seam, e.use_edge_sharp)
            for e in source.data.edges
        }
        for edge in mesh.edges:
            old_edge = tuple(sorted(used[v] for v in edge.vertices))
            if old_edge in source_edges:
                edge.use_seam, edge.use_edge_sharp = source_edges[old_edge]
        for mat in source.data.materials:
            mesh.materials.append(mat)
        face_parents = []
        for i, f in enumerate(mesh.polygons):
            t, w = correspondence(x[list(f.vertices)].mean(axis=0), labels[i])
            parent = parents[t]
            face_parents.append(parent)
            f.material_index = source.data.polygons[parent].material_index
            f.use_smooth = source.data.polygons[parent].use_smooth
        for uv_name, values in uvs.items():
            layer = mesh.uv_layers.new(name=uv_name)
            for i, f in enumerate(mesh.polygons):
                for loop in f.loop_indices:
                    v = mesh.loops[loop].vertex_index
                    t, w = correspondence(x[v], labels[i])
                    layer.data[loop].uv = np.asarray(values[t]).T @ w
        for group in source.vertex_groups:
            output = obj.vertex_groups.new(name=group.name)
            values = np.zeros(len(original))
            for v in source.data.vertices:
                for g in v.groups:
                    if g.group == group.index:
                        values[v.index] = g.weight
            for v, record in enumerate(mapping):
                weight = float(values[record["vertices"]] @ record["weights"])
                if weight > 0:
                    output.add([v], weight, "REPLACE")
        masks = json.loads(source.get("mw_masks", "{}"))
        for record in masks.values():
            if (
                record["topology"] != sculpt.topology(source)
                or source.vertex_groups.get(record["group"]) is None
            ):
                raise ValueError("Stale or missing source mask")
            record["topology"] = sculpt.topology(obj)
        if masks:
            obj["mw_masks"] = json.dumps(masks)
        report = {
            "operations": counts,
            "selected_triangles_before": sum(active),
            "selected_triangles_after": sum(enabled),
            "vertices_before": len(original),
            "vertices_after": len(x),
            "triangles_before": len(initial),
            "triangles_after": len(faces),
            "pinned_vertices": len(pinned),
            "pinned_error": float(
                max(
                    (np.linalg.norm(x[index[v]] - original[v]) for v in pinned),
                    default=0,
                )
            ),
            "sampled_error_max": max(distances + backwards),
            "forward_samples": len(distances),
            "reverse_samples": len(backwards),
            "quality_mean_before": float(
                np.mean([_quality(original, f) for f in initial])
            ),
            "quality_mean_after": float(np.mean([_quality(x, f) for f in faces])),
            "max_error": max_error,
        }
        obj["mw_remesh"] = json.dumps(
            {
                "version": 1,
                "source": source.name,
                "source_revision": attachments.revision(source),
                "target_revision": attachments.revision(obj),
                "mapping": mapping,
                "parents": face_parents,
                "charts": labels,
                "source_charts": charts,
                "source_triangles": initial,
                "pinned_pairs": [[v, index[v]] for v in sorted(pinned)],
                "report": report,
            }
        )
        for region_name in json.loads(source.get("mw_regions", "{}")):
            regions.define(
                obj,
                region_name,
                transfer_selection(source, obj, regions.resolve(source, region_name)),
            )
        return obj
    except Exception:
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        raise


def _state(source, target):
    state = json.loads(target.get("mw_remesh", "{}"))
    if (
        state.get("version") != 1
        or state["source"] != source.name
        or state["source_revision"] != attachments.revision(source)
        or state["target_revision"] != attachments.revision(target)
    ):
        raise ValueError("Stale or foreign remesh correspondence")
    return state


def transfer_selection(source, target, selection):
    state = _state(source, target)
    sel = geometry.validate_selection(source, selection)
    chosen = set(sel["indices"])
    if sel["domain"] == "FACE":
        ids = [i for i, p in enumerate(state["parents"]) if p in chosen]
    elif sel["domain"] == "VERT":
        ids = [
            i
            for i, r in enumerate(state["mapping"])
            if sum(w for v, w in zip(r["vertices"], r["weights"]) if v in chosen)
            >= 1 - 1e-6
        ]
    else:
        raise ValueError("Edge selection transfer is unsupported")
    return geometry.selection(target, sel["domain"], ids)


def transfer_binding(source, target, binding, max_distance=None):
    state = _state(source, target)
    limit = (
        state["report"]["max_error"]
        if max_distance is None
        else sculpt.number(max_distance, 1e-7, 1e4, "binding error")
    )
    hits = attachments.resolve(source, binding)
    x = sculpt.coordinates(target)
    faces = [list(f.vertices) for f in target.data.polygons]
    lookup = {
        tuple(sorted(t)): c
        for t, c in zip(state["source_triangles"], state["source_charts"])
    }
    anchors = []
    errors = []
    for anchor, hit in zip(binding["anchors"], hits):
        chart = lookup.get(tuple(sorted(anchor["vertices"])))
        ids = [i for i, c in enumerate(state["charts"]) if c == chart]
        if not ids:
            raise ValueError("Anchor chart unavailable")
        tree = _tree(x, [faces[i] for i in ids])
        p, n, t, d = tree.find_nearest(Vector(hit["position"]))
        if p is None or d > limit or Vector(hit["normal"]).dot(n) < 0.5:
            raise ValueError("Anchor projection failed distance or normal gate")
        f = faces[ids[t]]
        anchors.append({"vertices": f, "weights": _weights(p, x[f]).tolist()})
        errors.append(float(d))
    result = {
        "version": 1,
        "target": target.name,
        "topology": geometry.signature(target),
        "anchors": anchors,
    }
    attachments.resolve(target, result)
    return result, {
        "samples": len(errors),
        "max_error": max(errors, default=0),
        "method": "same connected feature chart; distance and normal gates",
    }


def transfer_pattern(source, target, pattern, name, max_distance=None):
    from . import relief, precision

    if name in bpy.data.objects:
        raise ValueError("Output name already exists")
    binding, report = transfer_binding(
        source, target, json.loads(pattern["mw_surface_binding"]), max_distance
    )
    if "mw_relief_settings" in pattern:
        hits = attachments.resolve(target, binding)
        obj = relief.dots(
            target,
            [h["position"] for h in hits],
            name,
            max_distance=0.3,
            **json.loads(pattern["mw_relief_settings"]),
        )
    elif "mw_seam_settings" in pattern:
        obj = precision._seam(
            target, binding, name, **json.loads(pattern["mw_seam_settings"])
        )
    else:
        raise ValueError("Supported bound relief or seam required")
    for mat in pattern.data.materials:
        obj.data.materials.append(mat)
    obj["mw_surface_binding"] = json.dumps(binding)
    obj["mw_attachment_revision"] = attachments.revision(target)
    obj["mw_transfer_report"] = json.dumps(report)
    return obj
