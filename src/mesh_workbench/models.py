"""Multi-model assembly, CSG, voxel fusion and explicit correspondence blending."""

from pathlib import Path
import bpy
from mathutils import Vector
from . import geometry, sculpt, layers


def activate(obj):
    layers.object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def primitive(kind, name, location=(0, 0, 0), scale=(1, 1, 1), **options):
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    location = geometry.vector(location)
    scale = geometry.vector(scale)
    if min(scale) <= 0:
        raise ValueError("Positive scales required")
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=options.get("segments", 32),
            ring_count=options.get("rings", 16),
            location=location,
        )
    elif kind == "plane":
        bpy.ops.mesh.primitive_plane_add(size=2, location=location)
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=options.get("segments", 32), location=location
        )
    else:
        raise ValueError("Unknown primitive")
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.context.view_layer.update()
    return obj


def load_blend(path, names, prefix="imported_"):
    path = Path(path).resolve()
    original_names = tuple(names)
    if path.suffix.lower() != ".blend" or not path.is_file():
        raise ValueError("Expected existing .blend file")
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        if (
            not names
            or len(set(names)) != len(names)
            or any(n not in source.objects for n in names)
        ):
            raise ValueError("Missing/duplicate source object")
        if any(prefix + n in bpy.data.objects for n in names):
            raise ValueError("Imported name exists")
        target.objects = list(original_names)
    for obj, old_name in zip(target.objects, original_names):
        obj.name = prefix + old_name
        bpy.context.collection.objects.link(obj)
    return target.objects


def transform(obj, location=None, rotation=None, scale=None):
    values = {
        name: geometry.vector(value, name)
        for name, value in [
            ("location", location),
            ("rotation_euler", rotation),
            ("scale", scale),
        ]
        if value is not None
    }
    if "scale" in values and min(values["scale"]) <= 0:
        raise ValueError("Positive scales required")
    for name, value in values.items():
        setattr(obj, name, value)
    bpy.context.view_layer.update()
    return obj


def load_mesh(path, prefix="imported_"):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("Missing mesh file")
    extension = path.suffix.lower()
    if extension not in (".obj", ".stl", ".ply", ".glb", ".gltf"):
        raise ValueError("Unsupported mesh format")
    existing = set(bpy.data.objects)
    try:
        if extension == ".obj":
            bpy.ops.wm.obj_import(filepath=str(path))
        elif extension == ".stl":
            bpy.ops.wm.stl_import(filepath=str(path))
        elif extension == ".ply":
            bpy.ops.wm.ply_import(filepath=str(path))
        else:
            bpy.ops.import_scene.gltf(filepath=str(path))
        added = sorted(set(bpy.data.objects) - existing, key=lambda o: o.name)
        names = [prefix + o.name for o in added]
        if len(set(names)) != len(names) or any(
            n in {o.name for o in existing} for n in names
        ):
            raise ValueError("Imported name exists")
        for obj, name in zip(added, names):
            obj.name = name
        return added
    except Exception:
        for obj in set(bpy.data.objects) - existing:
            bpy.data.objects.remove(obj, do_unlink=True)
        raise


def combine(objects, name, voxel=None):
    if not objects or any(o.type != "MESH" for o in objects):
        raise ValueError("Mesh inputs required")
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    if voxel is not None:
        voxel = sculpt.number(voxel, 0.001, 100, "voxel size")
    vertices = []
    faces = []
    material_indices = []
    materials = []
    for obj in objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m = evaluated.to_mesh()
        offset = len(vertices)
        mat_offset = len(materials)
        vertices.extend(obj.matrix_world @ v.co for v in m.vertices)
        for p in m.polygons:
            faces.append(tuple(offset + i for i in p.vertices))
            material_indices.append(mat_offset + p.material_index)
        materials.extend(m.materials)
        evaluated.to_mesh_clear()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for mat in materials:
        mesh.materials.append(mat)
    for p, index in zip(mesh.polygons, material_indices):
        p.material_index = index
    result = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(result)
    try:
        if voxel is not None:
            activate(result)
            modifier = result.modifiers.new("MW voxel fusion", "REMESH")
            modifier.mode = "VOXEL"
            modifier.voxel_size = voxel
            modifier.use_smooth_shade = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        return result
    except Exception:
        bpy.data.objects.remove(result, do_unlink=True)
        raise


def boolean(left, right, operation, name):
    if operation not in ("UNION", "DIFFERENCE", "INTERSECT"):
        raise ValueError("Invalid boolean operation")
    if left == right or left.type != "MESH" or right.type != "MESH":
        raise ValueError("Two distinct mesh inputs required")
    result = geometry.fork(left, name)
    try:
        activate(result)
        modifier = result.modifiers.new("MW boolean", "BOOLEAN")
        modifier.object = right
        modifier.operation = operation
        modifier.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return result
    except Exception:
        bpy.data.objects.remove(result, do_unlink=True)
        raise


def blend(left, right, name, weight=0.5):
    """Linear world-space vertex correspondence; identical indexed topology only."""
    sculpt.editable(left)
    sculpt.editable(right)
    if geometry.signature(left) != geometry.signature(right):
        raise ValueError("Blend requires identical indexed topology")
    weight = sculpt.number(weight, 0, 1, "blend weight")
    a, b = sculpt.coordinates(left), sculpt.coordinates(right)
    result = geometry.fork(left, name)
    inverse = result.matrix_world.inverted()
    for vertex, co in zip(result.data.vertices, a * (1 - weight) + b * weight):
        vertex.co = inverse @ Vector(co)
    return result
