"""Validated simple materials for reproducible modeling recipes."""

import math

import bpy

from . import sculpt


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
