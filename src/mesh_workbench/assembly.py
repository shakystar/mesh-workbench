"""Persisted static assembly recipes with staged, atomic geometry updates.

Object names are stable IDs. Renames/topology changes require explicit registration.
No handlers, global preferences or automatic execution on file load.
"""

import copy
import hashlib
import json
import uuid

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import attachments, fairing, geometry, layers, precision, relief, sculpt, shells

KEY = "mw_assembly_graph"


class Rejected(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(report["reason"])


def _props(obj):
    return {
        k: obj[k].to_list()
        if hasattr(obj[k], "to_list")
        else obj[k].to_dict()
        if hasattr(obj[k], "to_dict")
        else obj[k]
        for k in obj.keys()
    }


def _setprops(obj, values):
    for k in list(obj.keys()):
        del obj[k]
    for k, v in values.items():
        obj[k] = v


def _object(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError("Missing assembly object: " + name)
    sculpt.editable(obj)
    if obj.parent or obj.constraints or obj.get("mw_pending"):
        raise ValueError("Assembly requires unparented, unconstrained idle meshes")
    return obj


def _order(graph):
    if graph.get("version") != 1 or not graph.get("nodes"):
        raise ValueError("Expected assembly graph version 1 and nodes")
    nodes = graph["nodes"]
    if len({n["object"] for n in nodes.values()}) != len(nodes):
        raise ValueError("Duplicate assembly output")
    result, visiting = [], set()

    def visit(key):
        if key in visiting:
            raise ValueError("Assembly dependency cycle")
        if key in result:
            return
        if key not in nodes:
            raise ValueError("Missing assembly dependency: " + key)
        visiting.add(key)
        node = nodes[key]
        if node["kind"] not in ("source", "shell", "relief", "seam", "anchor"):
            raise ValueError("Unsupported assembly node")
        deps = node.get("deps", [])
        if (node["kind"] == "source" and deps) or (
            node["kind"] != "source" and not deps
        ):
            raise ValueError("Invalid assembly dependency count")
        for dep in deps:
            visit(dep)
        visiting.remove(key)
        result.append(key)

    for key in nodes:
        visit(key)
    return result


def _input(node, objects):
    payload = {
        k: v
        for k, v in node.items()
        if k not in ("input_hash", "topology", "output_revision")
    }
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode())
    for index, dep in enumerate(node.get("deps", [])):
        obj = objects[dep]
        coords = sculpt.coordinates(obj)
        if node["kind"] == "shell" and index == 0:
            # Include the entire one-ring around selected faces for vertex normals.
            used = {v for i in node["faces"] for v in obj.data.polygons[i].vertices}
            seed = set(used)
            used.update(
                v
                for f in obj.data.polygons
                if any(v in seed for v in f.vertices)
                for v in f.vertices
            )
            coords = coords[sorted(used)]
        elif node["kind"] in ("relief", "seam") and index == 0:
            hits = _resolve(obj, node["binding"])
            options = node.get("options", {})
            radii = options.get("radii", options.get("radius", 1))
            radius = max(radii) if isinstance(radii, list) else radii
            used = {i for a in node["binding"]["anchors"] for i in a["vertices"]}
            for hit in hits:
                nearby = np.where(
                    np.linalg.norm(coords - np.asarray(hit["position"]), axis=1)
                    <= radius * 3 + 1
                )[0]
                used.update(int(i) for i in nearby)
            seed = set(used)
            used.update(
                v
                for f in obj.data.polygons
                if any(v in seed for v in f.vertices)
                for v in f.vertices
            )
            ids = sorted(used)
            h.update(np.asarray(ids, dtype=np.int64).tobytes())
            coords = coords[ids]
        elif node["kind"] == "anchor" and index == 0:
            coords = np.asarray([x["position"] for x in _resolve(obj, node["binding"])])
        h.update(coords.tobytes())
        h.update(geometry.signature(obj).encode())
    return h.hexdigest()


def _resolve(target, binding):
    binding = copy.deepcopy(binding)
    binding["target"] = target.name
    return attachments.resolve(target, binding)


def register(name, nodes, checks=None):
    graph = {
        "version": 1,
        "name": name,
        "nodes": copy.deepcopy(nodes),
        "checks": copy.deepcopy(checks or []),
        "revision": 0,
    }
    order = _order(graph)
    objects = {k: _object(n["object"]) for k, n in graph["nodes"].items()}
    for key in order:
        node = graph["nodes"][key]
        if node["kind"] == "shell":
            node["source_name"] = objects[node["deps"][0]].name
        node["topology"] = geometry.signature(objects[key])
        node["output_revision"] = attachments.revision(objects[key])
        node["input_hash"] = _input(node, objects)
    # Validate constraints now: never register an already invalid assembly.
    reports = validate(graph, objects)
    if not all(r["passed"] for r in reports):
        raise Rejected(
            {"reason": "Initial assembly constraints failed", "checks": reports}
        )
    bpy.context.scene[KEY] = json.dumps(graph)
    return status()


def load():
    if KEY not in bpy.context.scene:
        raise ValueError("No registered assembly")
    graph = json.loads(bpy.context.scene[KEY])
    _order(graph)
    for node in graph["nodes"].values():
        obj = _object(node["object"])
        if geometry.signature(obj) != node["topology"]:
            raise ValueError("Assembly topology changed: " + obj.name)
        if attachments.revision(obj) != node["output_revision"]:
            raise ValueError("Assembly edited outside transaction: " + obj.name)
    return graph


def status():
    graph = load()
    return {
        "name": graph["name"],
        "revision": graph["revision"],
        "order": _order(graph),
        "nodes": len(graph["nodes"]),
    }


def _build(node, objects, name):
    target = objects[node["deps"][0]]
    options = node.get("options", {})
    if node["kind"] == "shell":
        obj = shells.extract(
            target, geometry.selection(target, "FACE", node["faces"]), name, **options
        )
        state = json.loads(obj["mw_shell"])
        state["source"] = node["source_name"]
        obj["mw_shell"] = json.dumps(state)
        return obj
    if node["kind"] == "relief":
        hits = _resolve(target, node["binding"])
        obj = relief.dots(
            target, [h["position"] for h in hits], name, max_distance=0.3, **options
        )
        attachments.bind_relief(target, obj, max_distance=0.3)
        return obj
    if node["kind"] == "seam":
        binding = copy.deepcopy(node["binding"])
        binding["target"] = target.name
        return precision._seam(target, binding, name, **options)
    if node["kind"] == "anchor":
        old = _object(node["object"])
        obj = old.copy()
        obj.data = old.data.copy()
        obj.name = name
        bpy.context.collection.objects.link(obj)
        point = Vector(_resolve(target, node["binding"])[0]["position"])
        obj.location = point + Vector(node["offset"])
        return obj
    raise ValueError("Cannot build source node")


def _tree(obj):
    coords = sculpt.coordinates(obj)
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return BVHTree.FromPolygons(
            coords.tolist(),
            [list(t.vertices) for t in mesh.loop_triangles],
            all_triangles=True,
        )
    finally:
        ev.to_mesh_clear()


def clearance(pattern, target, minimum=0):
    settings = json.loads(pattern["mw_relief_settings"])
    count = 1 + settings["segments"] * settings["rings"]
    coords = sculpt.coordinates(pattern)
    faces = [
        list(f.vertices)
        for f in pattern.data.polygons
        if all(i % (2 * count) < count for i in f.vertices)
    ]
    ids = sorted({i for f in faces for i in f})
    edges = {tuple(sorted((a, b))) for f in faces for a, b in zip(f, f[1:] + f[:1])}
    probes = [coords[i] for i in ids] + [(coords[a] + coords[b]) / 2 for a, b in edges]
    probes += [coords[f].mean(axis=0) for f in faces]
    tree = _tree(target)
    values, violations = [], []
    for p in probes:
        hit, normal, _, _ = tree.find_nearest(Vector(p))
        value = (Vector(p) - hit).dot(normal)
        values.append(value)
        if value < minimum - 1e-6:
            violations.append({"position": list(p), "value": value})
    return {
        "kind": "clearance",
        "passed": not violations,
        "samples": len(values),
        "minimum": min(values),
        "violations": violations,
    }


def validate(graph, objects=None):
    objects = objects or {k: _object(n["object"]) for k, n in graph["nodes"].items()}
    reports = []
    for check in graph["checks"]:
        kind = check["kind"]
        args = [objects[k] for k in check["nodes"]]
        options = check.get("options", {})
        if kind == "thickness":
            report = shells.thickness(*args, **options)
        elif kind == "gap":
            report = shells.gap(*args, **options)
        elif kind == "clearance":
            report = clearance(*args, **options)
        elif kind == "intersection":
            report = shells.intersections(*args)
            report["passed"] = report["triangle_pair_count"] == 0
        else:
            raise ValueError("Unknown assembly check: " + kind)
        reports.append({"kind": kind, "nodes": check["nodes"], **report})
    return reports


def _edit(obj, edit):
    coords = sculpt.coordinates(obj)
    kind = edit["kind"]
    if kind == "dimension":
        axis = edit["axis"]
        if type(axis) is not int or axis not in (0, 1, 2):
            raise ValueError("Invalid dimension axis")
        delta = sculpt.number(edit["delta"], -10000, 10000, "dimension delta")
        extent = float(np.ptp(coords[:, axis]))
        if extent < 1e-8 or extent + delta <= 0:
            raise ValueError("Nonpositive dimension")
        pivot = sculpt.number(
            edit.get("pivot", float(coords[:, axis].min())), -1e6, 1e6, "pivot"
        )
        coords[:, axis] = pivot + (coords[:, axis] - pivot) * (extent + delta) / extent
    elif kind == "radial":
        center = np.asarray(geometry.vector(edit["center"]))
        radius = sculpt.number(edit["radius"], 1e-5, 1e5, "radius")
        delta = np.asarray(geometry.vector(edit["delta"]))
        t = np.maximum(0, 1 - np.linalg.norm(coords - center, axis=1) / radius)
        weights = t * t * (3 - 2 * t)
        if edit.get("normalize_peak", False):
            if weights.max() <= 0:
                raise ValueError("Empty radial edit region")
            weights /= weights.max()
        coords += weights[:, None] * delta
    else:
        raise ValueError("Unsupported assembly edit")
    key = layers.begin(obj)
    inv = obj.matrix_world.inverted()
    for v, co in zip(key.data, coords):
        v.co = inv @ Vector(co)
    layers.finish(obj).name = "Assembly " + kind


def update(source, edit):
    graph = load()
    if source not in graph["nodes"] or graph["nodes"][source]["kind"] != "source":
        raise ValueError("Edit requires a source node")
    originals = {k: _object(n["object"]) for k, n in graph["nodes"].items()}
    objects = dict(originals)
    before_objects = set(bpy.data.objects)
    before_meshes = set(bpy.data.meshes)
    old_graph = bpy.context.scene[KEY]
    staged, backups, changed = {}, {}, []
    reports = []
    token = "MW stage " + uuid.uuid4().hex[:10]
    try:
        root = originals[source].copy()
        root.data = originals[source].data.copy()
        root.name = token + source
        bpy.context.collection.objects.link(root)
        root.hide_set(False)
        root.hide_viewport = False
        objects[source] = staged[source] = root
        _edit(root, edit)
        if np.array_equal(
            sculpt.coordinates(root), sculpt.coordinates(originals[source])
        ):
            return {
                "passed": True,
                "revision": graph["revision"],
                "updated": [],
                "unchanged": list(originals),
                "checks": [],
            }
        if fairing.overlap_candidates(root):
            raise ValueError("Source edit introduced overlaps")
        for key in _order(graph):
            node = graph["nodes"][key]
            if node["kind"] == "source":
                continue
            digest = _input(node, objects)
            if digest == node["input_hash"]:
                continue
            obj = _build(node, objects, token + key)
            obj.data.materials.clear()
            for material in originals[key].data.materials:
                obj.data.materials.append(material)
            objects[key] = staged[key] = obj
            node["input_hash"] = digest
        for key, obj in staged.items():
            if geometry.signature(obj) != graph["nodes"][key]["topology"]:
                raise ValueError("Regeneration changed indexed topology: " + key)
            if geometry.inspect(obj)["nonmanifold_edges"] or fairing.overlap_candidates(
                obj
            ):
                raise ValueError("Invalid regenerated geometry: " + key)
        reports = validate(graph, objects)
        if not all(r["passed"] for r in reports):
            raise ValueError("Assembly constraints failed")
        # Backup original pointers/properties; nothing above changes a live output.
        for key, obj in staged.items():
            old = originals[key]
            backups[key] = (old.data, old.matrix_world.copy(), _props(old))
            changed.append(key)
            old.data = obj.data
            old.matrix_world = obj.matrix_world.copy()
            props = _props(obj)
            # Preserve user metadata except generated geometry metadata.
            merged = dict(backups[key][2])
            merged.update(props)
            _setprops(old, merged)
        # Rewrite staged references to stable object IDs after the atomic swap.
        names = {obj.name: originals[k].name for k, obj in staged.items()}
        for key in staged:
            obj = originals[key]
            for prop in ("mw_shell", "mw_surface_binding"):
                if prop in obj:
                    value = json.loads(obj[prop])
                    for field in ("source", "target"):
                        if value.get(field) in names:
                            value[field] = names[value[field]]
                    obj[prop] = json.dumps(value)
            node = graph["nodes"][key]
            if "mw_surface_binding" in obj:
                obj["mw_attachment_revision"] = attachments.revision(
                    originals[node["deps"][0]]
                )
            node["topology"] = geometry.signature(obj)
            node["output_revision"] = attachments.revision(obj)
        graph["revision"] += 1
        bpy.context.scene[KEY] = json.dumps(graph)
        # Preserve all previous geometry in hidden revision objects for explicit recovery.
        for key, (mesh, matrix, props) in backups.items():
            archive = bpy.data.objects.new(
                "MW revision %d %s" % (graph["revision"] - 1, key), mesh
            )
            bpy.context.scene.collection.objects.link(archive)
            archive.matrix_world = matrix
            _setprops(archive, props)
            archive.hide_render = True
            archive.hide_set(True)
        return {
            "passed": True,
            "revision": graph["revision"],
            "updated": list(staged),
            "unchanged": [k for k in objects if k not in staged],
            "checks": reports,
        }
    except Exception as exc:
        for key in changed:
            obj = originals[key]
            obj.data, obj.matrix_world = backups[key][:2]
            _setprops(obj, backups[key][2])
        bpy.context.scene[KEY] = old_graph
        for obj in list(bpy.data.objects):
            if obj not in before_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        raise Rejected(
            {
                "passed": False,
                "rolled_back": True,
                "reason": str(exc),
                "checks": reports,
            }
        ) from exc
    finally:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(token):
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh not in before_meshes and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.context.view_layer.update()


def remesh_source(source, selection, name, **options):
    """Fork a source and its direct bound details; atomically switch the graph.

    Shell partitions and nested dependents need independent correspondence and
    are rejected before editing. The original assembly remains as hidden objects.
    """
    from . import remesh

    graph = load()
    if source not in graph["nodes"] or graph["nodes"][source]["kind"] != "source":
        raise ValueError("Remesh requires a source node")
    affected = {source}
    for key in _order(graph):
        node = graph["nodes"][key]
        if any(dep in affected for dep in node.get("deps", [])):
            if node["deps"] != [source] or node["kind"] not in (
                "relief",
                "seam",
                "anchor",
            ):
                raise ValueError(
                    "Remesh assembly supports direct bound details; shell/nested correspondence required"
                )
            affected.add(key)
    before_objects = set(bpy.data.objects)
    before_meshes = set(bpy.data.meshes)
    old_graph = bpy.context.scene[KEY]
    originals = {k: _object(n["object"]) for k, n in graph["nodes"].items()}
    visibility = {k: (o.hide_get(), o.hide_render) for k, o in originals.items()}
    objects = dict(originals)
    reports = []
    transfers = {}
    try:
        root = remesh.remesh(originals[source], selection, name, **options)
        objects[source] = root
        graph["nodes"][source]["object"] = root.name
        for key in _order(graph):
            if key not in affected or key == source:
                continue
            node = graph["nodes"][key]
            node["binding"], transfers[key] = remesh.transfer_binding(
                originals[source], root, node["binding"]
            )
            obj = _build(node, objects, name + " " + key)
            obj.data.materials.clear()
            for mat in originals[key].data.materials:
                obj.data.materials.append(mat)
            objects[key] = obj
            node["object"] = obj.name
        for key in affected:
            if fairing.overlap_candidates(objects[key]):
                raise ValueError("Remeshed assembly has overlap candidates: " + key)
        reports = validate(graph, objects)
        if not all(r["passed"] for r in reports):
            raise ValueError("Remeshed assembly constraints failed")
        for key, node in graph["nodes"].items():
            node["topology"] = geometry.signature(objects[key])
            node["output_revision"] = attachments.revision(objects[key])
            node["input_hash"] = _input(node, objects)
        graph["revision"] += 1
        bpy.context.scene[KEY] = json.dumps(graph)
        for key in affected:
            originals[key].hide_set(True)
            originals[key].hide_render = True
            objects[key].hide_set(False)
            objects[key].hide_render = False
        status()  # Validate committed references; failures still roll back.
        return {
            "passed": True,
            "revision": graph["revision"],
            "updated": sorted(affected),
            "objects": {k: objects[k].name for k in affected},
            "transfers": transfers,
            "checks": reports,
            "remesh": json.loads(root["mw_remesh"])["report"],
        }
    except Exception as exc:
        bpy.context.scene[KEY] = old_graph
        for key, obj in originals.items():
            obj.hide_set(visibility[key][0])
            obj.hide_render = visibility[key][1]
        for obj in list(bpy.data.objects):
            if obj not in before_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh not in before_meshes and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise Rejected(
            {
                "passed": False,
                "rolled_back": True,
                "reason": str(exc),
                "checks": reports,
            }
        ) from exc
