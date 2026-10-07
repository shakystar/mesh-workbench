"""Persisted nested recipe graph, semantic regeneration and atomic forks.

This is explicit static rebuilding, never a file-load handler. Logical part IDs
stay stable while each committed revision points at new physical objects.
"""

import copy
import hashlib
import json
import uuid
import bpy
import numpy as np
from . import (
    assembly,
    attachments,
    enclosure,
    inserts,
    mechanical,
    remesh,
    sculpt,
    semantic,
    construction,
    relief,
)

KEY = "mw_nested_assembly"


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _stamp(obj):
    digest = hashlib.sha256(attachments.revision(obj).encode())
    for uv in obj.data.uv_layers:
        digest.update(uv.name.encode())
        digest.update(np.array([v.uv[:] for v in uv.data], dtype=np.float32).tobytes())
    for g in obj.vertex_groups:
        digest.update(g.name.encode())
    for v in obj.data.vertices:
        digest.update(_json([(g.group, g.weight) for g in v.groups]).encode())
    digest.update(_json([m.name if m else None for m in obj.data.materials]).encode())
    digest.update(_json([p.material_index for p in obj.data.polygons]).encode())
    for key in (
        "mw_masks",
        "mw_semantic_queries",
        "mw_skin_roles",
        "mw_surface_binding",
        "mw_insert",
        "mw_part_frame",
    ):
        if key in obj:
            digest.update(str(obj[key]).encode())
    return digest.hexdigest()


def _resolve(value, parameters):
    if isinstance(value, dict):
        if "param" in value:
            if (
                set(value) - {"param", "scale", "offset"}
                or value["param"] not in parameters
            ):
                raise ValueError("Unknown parameter expression")
            return parameters[value["param"]] * value.get("scale", 1) + value.get(
                "offset", 0
            )
        return {k: _resolve(v, parameters) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, parameters) for v in value]
    return value


def _order(nodes):
    result = []
    active = set()

    def visit(key):
        if key in active:
            raise ValueError("Nested assembly dependency cycle")
        if key in result:
            return
        if key not in nodes:
            raise ValueError("Unknown part ID: " + str(key))
        active.add(key)
        kind = nodes[key]["kind"]
        deps = nodes[key].get("deps", [])
        consuming = {
            "hollow": 1,
            "partition": 1,
            "cut_box": 1,
            "cut_cylinder": 1,
            "insert": 1,
            "relief": 1,
            "union": 2,
        }
        if kind in consuming and (
            len(deps) != consuming[kind]
            or any(d.get("use", "geometry") != "geometry" for d in deps)
        ):
            raise ValueError(
                "Geometry-consuming builder requires explicit geometry dependencies"
            )
        for dep in nodes[key].get("deps", []):
            if set(dep) - {"id", "use"} or dep.get("use", "geometry") not in (
                "geometry",
                "frame",
            ):
                raise ValueError("Invalid dependency mode")
            visit(dep["id"])
        active.remove(key)
        result.append(key)

    for key in nodes:
        visit(key)
    return result


def load():
    if KEY not in bpy.context.scene:
        raise ValueError("No nested assembly")
    state = json.loads(bpy.context.scene[KEY])
    if state.get("version") != 2:
        raise ValueError("Expected nested assembly version 2")
    _order(state["nodes"])
    for key, record in state["outputs"].items():
        obj = bpy.data.objects.get(record["object"])
        if obj is None or _stamp(obj) != record["stamp"]:
            raise ValueError("Missing or externally edited part: " + key)
    return state


def _checkpoint(phase):
    """Test hook for recovery at actual mutation boundaries."""


def _build(node, args, deps, name):
    kind = node["kind"]
    source = deps[0] if deps else None
    if kind == "enclosure":
        return enclosure.create(name, **args)
    if kind == "hollow":
        return enclosure.hollow(source, name, **args)
    if kind == "partition":
        return enclosure.partition(source, name, **args)
    if kind == "cut_box":
        return mechanical.cut_box(source, name, **args)
    if kind == "box":
        return mechanical.box(name, **args)
    if kind == "annulus":
        return mechanical.annulus(name, **args)
    if kind == "cylinder":
        return construction.strut(name, **args)
    if kind == "prism":
        return mechanical.prism(name, **args)
    if kind == "jaw":
        return mechanical.jaw(name, **args)
    if kind == "cage":
        return mechanical.radial_cage(name, **args)
    if kind == "insert":
        return inserts.create(source, name=name, **args)
    if kind == "cut_cylinder":
        cutter = construction.strut(
            name + " cutter",
            args["start"],
            args["end"],
            radius=args["radius"],
            segments=48,
        )
        if len(source.data.materials) > 2:
            cutter.data.materials.append(source.data.materials[2])
        try:
            return enclosure.boolean(source, cutter, "DIFFERENCE", name)
        finally:
            mechanical.remove(cutter)
    if kind == "relief":
        query = args.pop("query")
        region = semantic.resolve(source, query)
        # Anchors are selected by world-space semantic patch and ray direction.
        points = args.pop("points")
        distance = args.pop("max_distance", 40)
        pattern = relief.dots(source, points, name, max_distance=distance, **args)
        attachments.bind_relief(source, pattern, max_distance=0.1)
        binding = json.loads(pattern["mw_surface_binding"])
        vertices = {
            v for i in region["indices"] for v in source.data.polygons[i].vertices
        }
        if any(not set(a["vertices"]) <= vertices for a in binding["anchors"]):
            mechanical.remove(pattern)
            raise ValueError("Pattern anchor outside declared semantic patch")
        return pattern
    if kind == "union":
        return enclosure.boolean(deps[0], deps[1], "UNION", name)
    raise ValueError("Unknown nested builder: " + str(kind))


def _validate(state, objects):
    reports = []
    for check in state.get("checks", []):
        kind = check["kind"]
        parts = [objects[k] for k in check["parts"]]
        options = _resolve(check.get("options", {}), state["parameters"])
        if kind == "wall":
            report = enclosure.gauge(parts[0], **options)
        elif kind == "clearance":
            report = assembly.clearance(*parts, **options)
        elif kind == "semantic":
            region = semantic.resolve(parts[0], options["query"])
            report = {
                "passed": True,
                "faces": len(region["indices"]),
                "components": region["components"],
            }
        elif kind == "gap":
            report = partition_gap(*parts, **options)
        else:
            raise ValueError("Unknown nested validation: " + str(kind))
        reports.append({"kind": kind, "parts": check["parts"], **report})
    return reports


def partition_gap(left, right, minimum=0.5, maximum=1.1):
    # Both seams are planar cuts of the same continuous hollow envelope. Query
    # actual vertices on the declared cut planes, in both directions.
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    meshes = []
    for obj in (left, right):
        state = json.loads(obj["mw_partition"])
        x = sculpt.coordinates(obj)
        plane = state["plane"]
        faces = [
            list(f.vertices)
            for f in obj.data.polygons
            if all(abs(x[v, 1] - plane) < 1e-4 for v in f.vertices)
        ]
        if not faces:
            raise ValueError("Missing physical split-plane faces")
        tree = BVHTree.FromPolygons(x.tolist(), faces)
        ids = {v for f in faces for v in f}
        probes = [x[i] for i in ids] + [x[f].mean(axis=0) for f in faces]
        meshes.append((tree, probes))
    values = []
    bad = []
    for target, points in ((meshes[0][0], meshes[1][1]), (meshes[1][0], meshes[0][1])):
        for p in points:
            hit, n, i, d = target.find_nearest(Vector(p), maximum * 4)
            if hit is None:
                bad.append(
                    {"reason": "split correspondence missed", "point": p.tolist()}
                )
            else:
                values.append(float(d))
                if not minimum <= d <= maximum:
                    bad.append(
                        {"reason": "split gap", "value": float(d), "point": p.tolist()}
                    )
    return {
        "passed": not bad,
        "samples": sum(len(m[1]) for m in meshes),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "violations": bad,
    }


def initialize(name, nodes, parameters, ranges, checks=None):
    if KEY in bpy.context.scene:
        raise ValueError("Nested assembly already registered")
    state = {
        "version": 2,
        "name": name,
        "nodes": copy.deepcopy(nodes),
        "parameters": copy.deepcopy(parameters),
        "ranges": copy.deepcopy(ranges),
        "checks": copy.deepcopy(checks or []),
        "outputs": {},
        "revision": -1,
    }
    return _transaction(state, parameters, None, initial=True)


def update(parameters=None, remesh_request=None):
    state = load()
    return _transaction(state, parameters or {}, remesh_request)


def _transaction(state, changes, remesh_request, initial=False):
    if set(changes) - set(state["parameters"]):
        raise ValueError("Unknown parameter")
    state["parameters"].update(changes)
    for key, value in state["parameters"].items():
        lo, hi = state["ranges"][key]
        sculpt.number(value, lo, hi, key)
    order = _order(state["nodes"])
    if remesh_request and remesh_request["part"] not in state["nodes"]:
        raise ValueError("Unknown remesh part ID")
    if remesh_request and changes:
        raise ValueError("Use distinct parameter and topology transactions")
    before_objects = set(bpy.data.objects)
    before_meshes = set(bpy.data.meshes)
    visible = {
        o: (o.hide_get(), o.hide_render, o.hide_viewport, o.select_get())
        for o in before_objects
    }
    active = bpy.context.view_layer.objects.active
    old_graph = bpy.context.scene.get(KEY)
    originals = {
        key: bpy.data.objects[r["object"]] for key, r in state["outputs"].items()
    }
    objects = dict(originals)
    outputs = copy.deepcopy(state["outputs"])
    staged = {}
    reports = []
    token = "DA " + uuid.uuid4().hex[:8] + " "
    try:
        for key in order:
            node = state["nodes"][key]
            args = _resolve(node.get("args", {}), state["parameters"])
            frame = _resolve(
                node.get("frame", {"origin": [0, 0, 0], "axis": [1, 0, 0]}),
                state["parameters"],
            )
            deps = node.get("deps", [])
            dep_objects = [objects[d["id"]] for d in deps]
            dependency_stamps = [
                [outputs[d["id"]]["stamp"], outputs[d["id"]]["object"]]
                if d.get("use", "geometry") == "geometry"
                else outputs[d["id"]]["frame"]
                for d in deps
            ]
            digest = hashlib.sha256(
                _json(
                    [node["kind"], args, frame, node.get("material"), dependency_stamps]
                ).encode()
            ).hexdigest()
            force = remesh_request and remesh_request["part"] == key
            if key in outputs and outputs[key]["input_hash"] == digest and not force:
                continue
            if force:
                if key not in originals:
                    raise ValueError("Remesh requires an existing output")
                selection = semantic.resolve(originals[key], remesh_request["query"])
                obj = remesh.remesh(
                    originals[key], selection, token + key, **remesh_request["options"]
                )
            else:
                obj = _build(node, copy.deepcopy(args), dep_objects, token + key)
            staged[key] = obj
            objects[key] = obj
            _checkpoint("after_build")
            obj["mw_part_id"] = key
            obj["mw_part_frame"] = _json(frame)
            if node.get("material"):
                style = node["material"]
                mat = bpy.data.materials.get(style["name"])
                if mat is None:
                    mat = bpy.data.materials.new(style["name"])
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    bsdf.inputs["Base Color"].default_value = [*style["color"], 1]
                    bsdf.inputs["Metallic"].default_value = style.get("metallic", 0)
                    bsdf.inputs["Roughness"].default_value = style.get("roughness", 0.4)
                count = max(1, len(obj.data.materials))
                indices = [f.material_index for f in obj.data.polygons]
                obj.data.materials.clear()
                for slot in range(count):
                    role_name = style["name"] + " role " + str(slot)
                    role = bpy.data.materials.get(role_name)
                    if role is None:
                        role = mat.copy()
                        role.name = role_name
                    obj.data.materials.append(role)
                for f, i in zip(obj.data.polygons, indices):
                    f.material_index = i
            # Explicit re-resolution after every topology operation, not index reuse.
            for region, query in _resolve(
                node.get("regions", {}), state["parameters"]
            ).items():
                semantic.register(obj, region, query)
            _checkpoint("after_transfer")
            enclosure._valid(obj)
            outputs[key] = {
                "object": obj.name,
                "input_hash": digest,
                "stamp": _stamp(obj),
                "frame": frame,
            }
        reports = _validate(state, objects)
        if not all(r["passed"] for r in reports):
            raise ValueError("Nested assembly acceptance failed")
        _checkpoint("after_validate")
        state["outputs"] = outputs
        state["revision"] += 1
        bpy.context.scene[KEY] = _json(state)
        for key, obj in staged.items():
            if key in originals:
                originals[key].hide_set(True)
                originals[key].hide_render = True
            show = state["nodes"][key].get("visible", True)
            obj.hide_set(not show)
            obj.hide_render = not show
        _checkpoint("after_commit")
        load()
        # Constructor intermediates must not leak into the saved assembly.
        keep = set(staged.values())
        for obj in list(bpy.data.objects):
            if obj not in before_objects and obj not in keep:
                mechanical.remove(obj)
        for mesh in list(bpy.data.meshes):
            if mesh not in before_meshes and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        return {
            "passed": True,
            "revision": state["revision"],
            "updated": list(staged),
            "unchanged": [k for k in order if k not in staged],
            "checks": reports,
            "objects": {k: objects[k].name for k in order},
        }
    except Exception as exc:
        if old_graph is None:
            if KEY in bpy.context.scene:
                del bpy.context.scene[KEY]
        else:
            bpy.context.scene[KEY] = old_graph
        for obj in list(bpy.data.objects):
            if obj not in before_objects:
                mechanical.remove(obj)
        for mesh in list(bpy.data.meshes):
            if mesh not in before_meshes and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for obj, values in visible.items():
            obj.hide_set(values[0])
            obj.hide_render = values[1]
            obj.hide_viewport = values[2]
            obj.select_set(values[3])
        bpy.context.view_layer.objects.active = active
        raise assembly.Rejected(
            {
                "passed": False,
                "rolled_back": True,
                "reason": str(exc),
                "staged": list(staged),
                "checks": reports,
            }
        ) from exc
