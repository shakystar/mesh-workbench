"""World-space elliptical section sweep using parallel-transport frames."""

import math

import bmesh
import bpy

from .geometry import vector


def sweep(name, centers, radii, segments=32, reference=(1, 0, 0)):
    """Create a capped mesh along an open polyline.

    radii has one positive (width,height) pair per center. Reference specifies
    the initial width axis; it must not be parallel to the first tangent.
    Adjacent tangents cannot reverse. No self-intersection/clearance solver.
    Geometry is in world coordinates with identity object transform.
    """
    points = [vector(p) for p in centers]
    if len(points) < 2 or len(radii) != len(points):
        raise ValueError("At least two centers and one radius pair per center required")
    sizes = []
    for r in radii:
        if len(r) != 2 or any(not math.isfinite(float(v)) or float(v) <= 0 for v in r):
            raise ValueError("Positive finite radius pairs required")
        sizes.append(tuple(float(v) for v in r))
    if type(segments) is not int or not 3 <= segments <= 256:
        raise ValueError("Segments must be 3..256")
    steps = [b - a for a, b in zip(points, points[1:])]
    if any(d.length < 1e-8 for d in steps):
        raise ValueError("Coincident adjacent centers")
    directions = [d.normalized() for d in steps]
    if any(a.dot(b) < -0.999 for a, b in zip(directions, directions[1:])):
        raise ValueError("Reversing path")
    tangents = (
        [directions[0]]
        + [(a + b).normalized() for a, b in zip(directions, directions[1:])]
        + [directions[-1]]
    )
    axis = vector(reference)
    axis -= tangents[0] * axis.dot(tangents[0])
    if axis.length < 1e-8:
        raise ValueError("Reference parallel to initial tangent")
    axis.normalize()
    if name in bpy.data.objects:
        raise ValueError("Output object exists")
    vertices = []
    for i, (point, tangent, (rx, ry)) in enumerate(zip(points, tangents, sizes)):
        if i:
            axis = tangents[i - 1].rotation_difference(tangent) @ axis
            axis -= tangent * axis.dot(tangent)
            axis.normalize()
        second = tangent.cross(axis).normalized()
        vertices.extend(
            point
            + axis * (rx * math.cos(j * math.tau / segments))
            + second * (ry * math.sin(j * math.tau / segments))
            for j in range(segments)
        )
    faces = []
    for i in range(len(points) - 1):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append(
                (
                    i * segments + j,
                    i * segments + k,
                    (i + 1) * segments + k,
                    (i + 1) * segments + j,
                )
            )
    # Triangle fans give end caps an explicit center and editable face domains.
    start_center = len(vertices)
    vertices.extend([points[0], points[-1]])
    for j in range(segments):
        k = (j + 1) % segments
        faces.append((start_center, k, j))
        offset = (len(points) - 1) * segments
        faces.append((start_center + 1, offset + j, offset + k))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = len(p.vertices) == 4
    bpy.context.view_layer.update()
    return obj
