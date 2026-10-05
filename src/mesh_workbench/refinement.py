"""Surface-preserving triangle fan refinement with explicit provenance transfer.

Only selected evaluated triangles are split at their centroids. This is not
arbitrary retopology/remeshing. Original objects and their bindings are retained.
"""

import copy
import json
import bpy
import numpy as np
from . import attachments, geometry, sculpt, regions


def split(source, selection, name):
    sel = geometry.validate_selection(source, selection)
    if sel["domain"] != "FACE" or not sel["indices"] or name in bpy.data.objects:
        raise ValueError("Nonempty face selection and new name required")
    xyz = sculpt.coordinates(source).tolist()
    provenance = [{str(i): 1.0} for i in range(len(xyz))]
    selected = set(sel["indices"])
    triangles = {}
    ev = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated = ev.to_mesh()
    try:
        evaluated.calc_loop_triangles()
        for t in evaluated.loop_triangles:
            triangles.setdefault(t.polygon_index, []).append(list(t.vertices))
    finally:
        ev.to_mesh_clear()
    faces = []
    parents = []
    children = {}
    for face in source.data.polygons:
        if face.index not in selected:
            faces.append(list(face.vertices))
            parents.append(face.index)
            continue
        for ids in triangles[face.index]:
            center = len(xyz)
            xyz.append(np.asarray([xyz[i] for i in ids]).mean(axis=0).tolist())
            provenance.append({str(i): 1 / 3 for i in ids})
            child = [
                [ids[0], ids[1], center],
                [ids[1], ids[2], center],
                [ids[2], ids[0], center],
            ]
            children[",".join(map(str, sorted(ids)))] = child
            faces.extend(child)
            parents.extend([face.index] * 3)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(xyz, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    try:
        for mat in source.data.materials:
            mesh.materials.append(mat)
        for f, parent in zip(mesh.polygons, parents):
            f.material_index = source.data.polygons[parent].material_index
            f.use_smooth = source.data.polygons[parent].use_smooth
        obj["mw_refinement"] = json.dumps(
            {
                "version": 1,
                "source": source.name,
                "source_topology": geometry.signature(source),
                "source_revision": attachments.revision(source),
                "topology": geometry.signature(obj),
                "parents": parents,
                "provenance": provenance,
                "children": children,
            }
        )
        for group in source.vertex_groups:
            out = obj.vertex_groups.new(name=group.name)
            weights = {
                v.index: next((g.weight for g in v.groups if g.group == group.index), 0)
                for v in source.data.vertices
            }
            for i, record in enumerate(provenance):
                weight = sum(weights[int(j)] * w for j, w in record.items())
                if weight:
                    out.add([i], weight, "REPLACE")
        masks = json.loads(source.get("mw_masks", "{}"))
        for entry in masks.values():
            if entry["topology"] != sculpt.topology(source):
                raise ValueError("Stale source mask")
            if source.vertex_groups.get(entry["group"]) is None:
                raise ValueError("Missing source mask group")
            entry["topology"] = sculpt.topology(obj)
        if masks:
            obj["mw_masks"] = json.dumps(masks)
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
    state = json.loads(target.get("mw_refinement", "{}"))
    if (
        state.get("version") != 1
        or state["source"] != source.name
        or state["source_topology"] != geometry.signature(source)
        or state["topology"] != geometry.signature(target)
        or state["source_revision"] != attachments.revision(source)
    ):
        raise ValueError("Stale or foreign refinement provenance")
    return state


def transfer_selection(source, target, selection):
    sel = geometry.validate_selection(source, selection)
    state = _state(source, target)
    chosen = set(sel["indices"])
    if sel["domain"] == "FACE":
        ids = [i for i, p in enumerate(state["parents"]) if p in chosen]
    elif sel["domain"] == "VERT":
        ids = [
            i
            for i, record in enumerate(state["provenance"])
            if all(int(j) in chosen for j in record)
        ]
    else:
        raise ValueError("Only vertex and face selections have explicit transfer rules")
    return geometry.selection(target, sel["domain"], ids)


def transfer_binding(source, target, binding):
    attachments.resolve(source, binding)
    state = _state(source, target)
    result = copy.deepcopy(binding)
    result["target"] = target.name
    result["topology"] = geometry.signature(target)
    for anchor in result["anchors"]:
        ids = anchor["vertices"]
        weights = anchor["weights"]
        children = state["children"].get(",".join(map(str, sorted(ids))))
        if children is None:
            continue
        found = False
        for child in children:
            matrix = np.asarray(
                [[state["provenance"][v].get(str(i), 0) for v in child] for i in ids]
            )
            w = np.linalg.solve(matrix, np.asarray(weights))
            if w.min() >= -1e-6 and w.max() <= 1 + 1e-6:
                anchor["vertices"] = child
                anchor["weights"] = w.tolist()
                found = True
                break
        if not found:
            raise ValueError("Anchor could not be transferred within parent triangle")
    attachments.resolve(target, result)
    return result


def transfer_pattern(source, target, pattern, name):
    from . import relief, precision

    binding = transfer_binding(
        source, target, json.loads(pattern["mw_surface_binding"])
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
    for material in pattern.data.materials:
        obj.data.materials.append(material)
    obj["mw_surface_binding"] = json.dumps(binding)
    obj["mw_attachment_revision"] = attachments.revision(target)
    return obj
