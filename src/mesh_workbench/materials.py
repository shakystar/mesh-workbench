"""Validated simple materials for reproducible modeling recipes."""

import math
import json

import bpy

from . import sculpt


def finish(
    objects,
    name,
    role,
    color,
    roughness=0.4,
    variation=0.06,
    grain_mm=0.18,
    bump_mm=0.015,
    seed=0,
    slot=0,
):
    """Seeded object-space finish at explicit physical scale; replace one slot."""
    import numpy as np

    if (
        role not in ("plastic", "rubber", "metal")
        or not isinstance(name, str)
        or not name
        or name in bpy.data.materials
    ):
        raise ValueError("Known finish role and new material name required")
    rgba = np.asarray(color, dtype=float)
    if (
        rgba.shape != (4,)
        or not np.isfinite(rgba).all()
        or np.any(rgba < 0)
        or np.any(rgba > 1)
    ):
        raise ValueError("Finite RGBA color in [0,1] required")
    roughness = sculpt.number(roughness, 0, 1, "roughness")
    variation = sculpt.number(
        variation, 0, min(roughness, 1 - roughness), "roughness variation"
    )
    grain_mm = sculpt.number(grain_mm, 0.001, 100, "grain size mm")
    bump_mm = sculpt.number(bump_mm, 0, grain_mm / 2, "bump height mm")
    if (
        type(seed) is not int
        or not 0 <= seed <= 1000000
        or type(slot) is not int
        or slot < 0
    ):
        raise ValueError("Nonnegative integer seed and slot required")
    units = bpy.context.scene.unit_settings
    if units.system != "METRIC":
        raise ValueError("Explicit metric scene scale required")
    mm_per_unit = sculpt.number(
        float(units.scale_length) * 1000, 1e-6, 1e6, "scene scale"
    )
    if not objects or len(set(objects)) != len(objects):
        raise ValueError("Unique nonempty material targets required")
    for obj in objects:
        if obj.type != "MESH" or slot >= max(1, len(obj.data.materials)):
            raise ValueError("Valid mesh material slot required")
        linear = np.array(obj.matrix_world)[:3, :3]
        if not np.allclose(linear.T @ linear, np.eye(3), atol=1e-7):
            raise ValueError("Apply object scale before physical finish")
    previous = [(obj, obj.data, list(obj.data.materials)) for obj in objects]
    material = None
    copies = []
    try:
        material = bpy.data.materials.new(name)
        material.diffuse_color = rgba.tolist()
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = rgba.tolist()
        shader.inputs["Metallic"].default_value = 1 if role == "metal" else 0
        shader.inputs["Roughness"].default_value = roughness
        coord = nodes.new("ShaderNodeTexCoord")
        scale = nodes.new("ShaderNodeVectorMath")
        scale.operation = "SCALE"
        scale.inputs[3].default_value = mm_per_unit / grain_mm
        links.new(coord.outputs["Object"], scale.inputs[0])
        shift = nodes.new("ShaderNodeVectorMath")
        shift.operation = "ADD"
        shift.inputs[1].default_value = [
            (seed * factor % 104729) / 101 for factor in (17, 43, 71)
        ]
        links.new(scale.outputs["Vector"], shift.inputs[0])
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 1
        noise.inputs["Detail"].default_value = 2
        links.new(shift.outputs["Vector"], noise.inputs["Vector"])
        remap = nodes.new("ShaderNodeMapRange")
        remap.inputs["From Min"].default_value = 0
        remap.inputs["From Max"].default_value = 1
        remap.inputs["To Min"].default_value = roughness - variation
        remap.inputs["To Max"].default_value = roughness + variation
        links.new(noise.outputs["Fac"], remap.inputs["Value"])
        links.new(remap.outputs[0], shader.inputs["Roughness"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 1
        bump.inputs["Distance"].default_value = bump_mm / mm_per_unit
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        settings = {
            "schema": 1,
            "role": role,
            "grain_mm": grain_mm,
            "bump_mm": bump_mm,
            "seed": seed,
            "roughness": roughness,
            "variation": variation,
            "mm_per_unit": mm_per_unit,
            "slot": slot,
        }
        material["mw_finish"] = json.dumps(settings)
        for obj in objects:
            if obj.data.users > 1:
                obj.data = obj.data.copy()
                copies.append(obj.data)
            if len(obj.data.materials):
                obj.data.materials[slot] = material
            else:
                obj.data.materials.append(material)
        return {"material": name, "objects": [o.name for o in objects], **settings}
    except Exception:
        for obj, mesh, slots in previous:
            obj.data = mesh
            if len(mesh.materials) == len(slots):
                for index, mat in enumerate(slots):
                    mesh.materials[index] = mat
            else:
                mesh.materials.clear()
                for mat in slots:
                    mesh.materials.append(mat)
        if material is not None:
            bpy.data.materials.remove(material)
        for mesh in copies:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise


def assign(objects, name, color, metallic=0, roughness=0.4):
    if not isinstance(name, str) or not name or name in bpy.data.materials:
        raise ValueError("Material name must be new and nonempty")
    if len(color) != 4 or any(
        not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1
        for v in color
    ):
        raise ValueError("Color must contain four finite values in [0,1]")
    metallic = sculpt.number(metallic, 0, 1, "metallic")
    roughness = sculpt.number(roughness, 0, 1, "roughness")
    if not objects or any(o.type not in ("MESH", "CURVE", "FONT") for o in objects):
        raise ValueError("Material targets must be mesh or curve objects")
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Alpha"].default_value = color[3]
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    for obj in objects:
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.data.materials.clear()
        obj.data.materials.append(material)
    return {"material": material.name, "objects": [o.name for o in objects]}
