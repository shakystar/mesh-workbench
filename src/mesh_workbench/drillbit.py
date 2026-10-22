"""Closed two-flute visual drill bit; not a manufacturing cutter definition."""
import json
import math
import bpy
from . import enclosure, geometry, mechanical


@mechanical._atomic
def create(name, start=(83, 0, 160), radius=3, shank=22, cutting=38, pitch=32,
           segments=96, steps=160):
    values = (radius, shank, cutting, pitch)
    if any(not math.isfinite(float(v)) or v <= 0 for v in values):
        raise ValueError('Positive finite bit dimensions required')
    if shank < radius * 2 or cutting < radius * 4 or pitch < radius * 4:
        raise ValueError('Insufficient shank, cutting length or flute pitch')
    if type(segments) is not int or segments < 32 or segments > 256 or segments % 4:
        raise ValueError('Radial segments must be 32..256 and divisible by four')
    if type(steps) is not int or not 32 <= steps <= 512:
        raise ValueError('Axial steps must be 32..512')
    origin = geometry.vector(start)
    # Straight shank reaches beyond the jaws before the two chip channels begin.
    rows = [(0, 0, 1), (shank, 0, 1)]
    rows += [(shank + cutting * i / steps, min(1, cutting * i / steps / 3), 1)
             for i in range(1, steps + 1)]
    point_length = radius * .6
    rows += [(shank + cutting + point_length * t, 1, 1 - t)
             for t in (.25, .5, .75, .95)]
    vertices, faces, roles = [], [], []
    for x, amplitude, scale in rows:
        phase = math.tau * max(0, min(x-shank, cutting)) / pitch
        for j in range(segments):
            theta = math.tau * j / segments
            # Each half revolution contains a recessed flute and a solid land.
            u = (theta % math.pi) / math.pi
            flute = math.sin(math.pi * u / .72) ** .8 if u < .72 else 0
            r = radius * scale * (1 - .65 * amplitude * flute)
            angle = theta + phase
            vertices.append(origin + geometry.vector((x, r*math.cos(angle), r*math.sin(angle))))
    for i in range(len(rows)-1):
        for j in range(segments):
            faces.append([i*segments+j, i*segments+(j+1)%segments,
                          (i+1)*segments+(j+1)%segments, (i+1)*segments+j])
            u = ((j+.5) % (segments//2)) / (segments//2)
            roles.append(int(rows[i+1][1] > 0 and .05 < u < .67 and i <= steps))
    back = len(vertices)
    vertices.append(origin)
    tip = len(vertices)
    vertices.append(origin + geometry.vector((shank+cutting+point_length, 0, 0)))
    last = (len(rows)-1)*segments
    for j in range(segments):
        faces.extend([[back, (j+1)%segments, j],
                      [tip, last+j, last+(j+1)%segments]])
        roles.extend([0, 0])
    obj = enclosure._mesh(name, vertices, faces)
    enclosure._valid(obj)
    for label, roughness in (('Cutting lands', .22), ('Flute interior', .38)):
        mat = bpy.data.materials.get('Drill bit '+label)
        if mat is None:
            mat = bpy.data.materials.new('Drill bit '+label)
            mat.use_nodes = True
            shader = mat.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value = (.36, .40, .45, 1)
            shader.inputs['Metallic'].default_value = .95
            shader.inputs['Roughness'].default_value = roughness
        obj.data.materials.append(mat)
    for face, role in zip(obj.data.polygons, roles):
        face.material_index = role
        face.use_smooth = face.index < (steps+1)*segments
    obj['mw_twist_bit'] = json.dumps(dict(radius=radius, shank=shank, cutting=cutting,
        pitch=pitch, flutes=2, point_length=point_length, segments=segments, steps=steps))
    return obj
