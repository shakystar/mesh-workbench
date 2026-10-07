"""Re-resolvable geometric face regions; no persisted polygon-index identity."""

import json
from . import geometry, sculpt


def resolve(obj, query):
    sculpt.editable(obj)
    allowed = {
        "box",
        "normal",
        "normal_min",
        "materials",
        "components",
        "min_faces",
        "seed",
        "seed_distance",
    }
    if set(query) - allowed:
        raise ValueError("Unknown semantic query fields")
    selection = geometry.selection(obj, "FACE", box=query.get("box"))
    ids = []
    normal = query.get("normal")
    matrix = obj.matrix_world.inverted().transposed().to_3x3()
    direction = geometry.vector(normal).normalized() if normal is not None else None
    if direction is not None and direction.length < 0.9:
        raise ValueError("Invalid semantic normal")
    materials = query.get("materials")
    if materials is not None and (
        not materials
        or any(
            type(i) != int or not 0 <= i < len(obj.data.materials) for i in materials
        )
    ):
        raise ValueError("Invalid semantic material roles")
    threshold = sculpt.number(
        query.get("normal_min", 0.5), -1, 1, "semantic normal gate"
    )
    for i in selection["indices"]:
        face = obj.data.polygons[i]
        if materials is not None and face.material_index not in materials:
            continue
        if (
            direction is not None
            and (matrix @ face.normal).normalized().dot(direction) < threshold
        ):
            continue
        ids.append(i)
    if len(ids) < query.get("min_faces", 1):
        raise ValueError("Empty or insufficient semantic region")
    adjacency = {i: set() for i in ids}
    edges = {}
    for i in ids:
        f = list(obj.data.polygons[i].vertices)
        for a, b in zip(f, f[1:] + f[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append(i)
    for faces in edges.values():
        for a in faces:
            adjacency[a].update(set(faces) - {a})
    remaining = set(ids)
    groups = []
    while remaining:
        stack = [remaining.pop()]
        group = []
        while stack:
            a = stack.pop()
            group.append(a)
            for b in adjacency[a] & remaining:
                remaining.remove(b)
                stack.append(b)
        groups.append(group)
    if "seed_distance" in query and "seed" not in query:
        raise ValueError("Component distance requires an explicit seed")
    if "seed" in query:
        from mathutils.bvhtree import BVHTree

        seed = geometry.vector(query["seed"])
        limit = sculpt.number(
            query.get("seed_distance", 1), 1e-6, 1e6, "component seed distance"
        )
        coords = sculpt.coordinates(obj)
        candidates = []
        for group in groups:
            tree = BVHTree.FromPolygons(
                coords.tolist(), [list(obj.data.polygons[i].vertices) for i in group]
            )
            hit = tree.find_nearest(seed)
            if hit[0] is not None:
                candidates.append((float(hit[3]), group))
        candidates.sort(key=lambda value: value[0])
        if not candidates or candidates[0][0] > limit:
            raise ValueError("No semantic component near the declared seed")
        if len(candidates) > 1 and abs(candidates[1][0] - candidates[0][0]) <= 1e-6:
            raise ValueError("Ambiguous semantic component seed")
        groups = [candidates[0][1]]
        ids = groups[0]
        if len(ids) < query.get("min_faces", 1):
            raise ValueError("Seeded component has insufficient faces")
    expected = query.get("components", 1)
    if type(expected) != int or expected < 1 or len(groups) != expected:
        raise ValueError(
            "Ambiguous semantic region: expected %s components, found %s"
            % (expected, len(groups))
        )
    result = geometry.selection(obj, "FACE", ids)
    result["query"] = query
    result["components"] = len(groups)
    return result


def register(obj, name, query):
    if not isinstance(name, str) or not name or len(name) > 64:
        raise ValueError("Invalid semantic region name")
    result = resolve(obj, query)
    registry = json.loads(obj.get("mw_semantic_queries", "{}"))
    registry[name] = query
    obj["mw_semantic_queries"] = json.dumps(registry)
    return result


def named(obj, name):
    registry = json.loads(obj.get("mw_semantic_queries", "{}"))
    if name not in registry:
        raise ValueError("Unknown semantic region")
    return resolve(obj, registry[name])
