"""Selections and transactional polygon editing on explicit mesh forks."""

import hashlib
import json
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from . import sculpt, layers


def vector(value, name="vector"):
    a = np.asarray(value, dtype=float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError("Invalid " + name)
    return Vector(a)


def signature(obj):
    h = hashlib.sha256(sculpt.topology(obj).encode())
    for p in obj.data.polygons:
        h.update(str(tuple(p.vertices)).encode())
    return h.hexdigest()


def selection(obj, domain="VERT", indices=None, box=None, sphere=None, grow=0):
    """Return topology-bound indices; VERT/EDGE/FACE positions use world centers."""
    sculpt.editable(obj)
    if domain not in ("VERT", "EDGE", "FACE"):
        raise ValueError("Invalid selection domain")
    elements = {
        "VERT": obj.data.vertices,
        "EDGE": obj.data.edges,
        "FACE": obj.data.polygons,
    }[domain]
    coords = sculpt.coordinates(obj)
    if indices is None:
        chosen = set(range(len(elements)))
    else:
        if any(type(i) != int or not 0 <= i < len(elements) for i in indices):
            raise ValueError("Index outside mesh")
        chosen = set(indices)
    if box is not None:
        low, high = vector(box[0]), vector(box[1])
        if any(a > b for a, b in zip(low, high)):
            raise ValueError("Invalid box")
    if sphere is not None:
        center = vector(sphere["center"])
        radius = sculpt.number(sphere["radius"], 0, 1e6, "radius")
    for i in list(chosen):
        point = (
            coords[i]
            if domain == "VERT"
            else coords[list(elements[i].vertices)].mean(axis=0)
        )
        if box is not None and any(v < a or v > b for v, a, b in zip(point, low, high)):
            chosen.remove(i)
            continue
        if sphere is not None and np.linalg.norm(point - np.array(center)) > radius:
            chosen.remove(i)
    if type(grow) != int or not 0 <= grow <= 32:
        raise ValueError("Invalid selection grow count")
    if grow and domain != "VERT":
        raise ValueError("Grow currently supports vertex selections")
    for _ in range(grow):
        expanded = set(chosen)
        for edge in obj.data.edges:
            a, b = edge.vertices
            if a in chosen or b in chosen:
                expanded.update((a, b))
        chosen = expanded
    return {
        "object": obj.name,
        "domain": domain,
        "indices": sorted(chosen),
        "topology": signature(obj),
    }


def validate_selection(obj, sel):
    if sel["object"] != obj.name or sel["topology"] != signature(obj):
        raise ValueError("Stale or foreign selection")
    return selection(obj, sel["domain"], sel["indices"])


def move(obj, sel, delta, label="vertex move"):
    sel = validate_selection(obj, sel)
    delta = vector(delta)
    if sel["domain"] == "VERT":
        indices = sel["indices"]
    else:
        elements = obj.data.edges if sel["domain"] == "EDGE" else obj.data.polygons
        indices = sorted({v for i in sel["indices"] for v in elements[i].vertices})
    if not isinstance(label, str) or not 1 <= len(label) <= 48:
        raise ValueError("Invalid label")
    key = layers.begin(obj)
    try:
        local = obj.matrix_world.inverted().to_3x3() @ delta
        for i in indices:
            key.data[i].co += local
        layer = layers.finish(obj)
        layer.name = "MW " + label
    except Exception:
        if obj.get("mw_pending"):
            layers.finish(obj, True)
        raise
    history = json.loads(obj.get("mw_layers", "[]"))
    history.append({"name": layer.name, "topology": sculpt.topology(obj)})
    obj["mw_layers"] = json.dumps(history)
    return {"layer": layer.name, "vertices": indices}


def fork(obj, name):
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    if obj.type != "MESH":
        raise ValueError("Mesh required")
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(
        evaluated, depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    result = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(result)
    result.matrix_world = obj.matrix_world.copy()
    return result


def edit_topology(obj, sel, operation, name, **options):
    """BMesh edits commit to a NEW object; input and deformation history survive."""
    validate_selection(obj, sel)
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    if operation not in (
        "subdivide",
        "extrude",
        "inset",
        "bevel",
        "weld",
        "delete",
        "triangulate",
    ):
        raise ValueError("Unknown mesh operation")
    # Operate on the evaluated copy, then commit only after all checks pass.
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    ev.to_mesh_clear()
    try:
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        domain = sel["domain"]
        seq = {"VERT": bm.verts, "EDGE": bm.edges, "FACE": bm.faces}[domain]
        chosen = [seq[i] for i in sel["indices"]]
        if not chosen:
            raise ValueError("Empty selection")
        if operation == "subdivide":
            cuts = options.get("cuts", 1)
            if type(cuts) != int or not 1 <= cuts <= 16:
                raise ValueError("cuts must be 1..16")
            edges = (
                chosen
                if domain == "EDGE"
                else list(
                    {
                        e
                        for item in chosen
                        for e in (item.edges if domain == "FACE" else item.link_edges)
                    }
                )
            )
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
        elif operation == "extrude":
            if domain != "FACE":
                raise ValueError("Extrude requires faces")
            delta = obj.matrix_world.inverted().to_3x3() @ vector(options["delta"])
            result = bmesh.ops.extrude_face_region(bm, geom=chosen, use_keep_orig=False)
            verts = [v for v in result["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=verts, vec=delta)
            bmesh.ops.delete(
                bm, geom=[f for f in chosen if f.is_valid], context="FACES_ONLY"
            )
            loose = [v for v in bm.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="VERTS")
        elif operation == "inset":
            if domain != "FACE":
                raise ValueError("Inset requires faces")
            thickness = sculpt.number(options["thickness"], 0, 1000, "thickness")
            bmesh.ops.inset_region(
                bm,
                faces=chosen,
                thickness=thickness,
                depth=0,
                use_boundary=True,
                use_even_offset=True,
            )
        elif operation == "bevel":
            if domain != "EDGE":
                raise ValueError("Bevel requires edges")
            offset = sculpt.number(options["offset"], 0, 1000, "offset")
            segments = options.get("segments", 1)
            if type(segments) != int or not 1 <= segments <= 16:
                raise ValueError("Invalid segments")
            bmesh.ops.bevel(
                bm, geom=chosen, offset=offset, segments=segments, affect="EDGES"
            )
        elif operation == "weld":
            if domain != "VERT":
                raise ValueError("Weld requires vertices")
            bmesh.ops.remove_doubles(
                bm,
                verts=chosen,
                dist=sculpt.number(options["distance"], 0, 1000, "distance"),
            )
        elif operation == "delete":
            bmesh.ops.delete(
                bm,
                geom=chosen,
                context={"VERT": "VERTS", "EDGE": "EDGES", "FACE": "FACES"}[domain],
            )
        else:
            if domain != "FACE":
                raise ValueError("Triangulate requires faces")
            bmesh.ops.triangulate(bm, faces=chosen)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if any(not all(math.isfinite(v) for v in p.co) for p in bm.verts):
            raise ValueError("Non-finite mesh")
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        mesh.update()
        for material in obj.data.materials:
            mesh.materials.append(material)
        result = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(result)
        result.matrix_world = obj.matrix_world.copy()
        return result
    finally:
        bm.free()


def inspect(obj):
    coords = sculpt.coordinates(obj)
    bm = bmesh.new()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    bm.from_mesh(m)
    ev.to_mesh_clear()
    result = {
        "object": obj.name,
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
        "finite": bool(np.isfinite(coords).all()),
        "topology": signature(obj),
    }
    if len(coords):
        result["bounds"] = [coords.min(axis=0).tolist(), coords.max(axis=0).tolist()]
    bm.free()
    return result
