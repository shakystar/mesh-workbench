"""Independent deformation transactions; no viewport or file-system dependency."""

import json
import bpy


def object_mode():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def begin(obj):
    object_mode()
    if obj.type != "MESH" or obj.animation_data or obj.get("mw_pending"):
        raise ValueError("Expected idle static mesh")
    if obj.data.shape_keys and obj.data.shape_keys.animation_data:
        raise ValueError("Animated shape keys unsupported")
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis")
    weights = {k.name: k.value for k in obj.data.shape_keys.key_blocks}
    start = obj.shape_key_add(name="MW start", from_mix=True)
    start.relative_key = obj.data.shape_keys.key_blocks[0]
    snapshot = [v.co.copy() for v in start.data]
    edit = obj.shape_key_add(name="MW pending", from_mix=False)
    for v, co in zip(edit.data, snapshot):
        v.co = co
    edit.relative_key = obj.data.shape_keys.key_blocks[0]
    for key in obj.data.shape_keys.key_blocks:
        key.value = 0
    edit.value = 1
    obj["mw_pending"] = json.dumps(
        {"weights": weights, "start": start.name, "edit": edit.name}
    )
    return edit


def finish(obj, cancel=False):
    state = json.loads(obj["mw_pending"])
    keys = obj.data.shape_keys.key_blocks
    start, edit, basis = keys[state["start"]], keys[state["edit"]], keys[0]
    if cancel:
        obj.shape_key_remove(edit)
    else:
        for vertex, old, base in zip(edit.data, start.data, basis.data):
            vertex.co = base.co + (vertex.co - old.co)
        edit.relative_key = basis
        edit.name = "MW layer"
        edit.value = 1
    obj.shape_key_remove(start)
    for name, value in state["weights"].items():
        keys[name].value = value
    del obj["mw_pending"]
    bpy.context.view_layer.update()
    return None if cancel else edit
