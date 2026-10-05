"""Run: blender --background --factory-startup --python-exit-code 2 --python tests/blender_tests.py"""

import json
import sys
import uuid
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import bpy
import numpy as np
from mesh_workbench import (
    geometry as g,
    models as m,
    patterns as p,
    sculpt as s,
    surface,
)
from mesh_workbench.runner import camera


class Modeling(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.root = ROOT / "runs" / ("test-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)

    def test_sweep_transport_geometry_and_rejections(self):
        from mesh_workbench.sweep import sweep
        import bmesh

        centers = [[0, 0, 0], [0, 0, 1], [0.4, 0, 1.8], [1.1, 0.2, 2.1]]
        radii = [[0.2, 0.1]] * 4
        obj = sweep("Curved", centers, radii, segments=32)
        world = s.coordinates(obj)
        for i, point in enumerate(centers):
            ring = world[i * 32 : (i + 1) * 32]
            np.testing.assert_allclose(ring.mean(axis=0), point, atol=1e-6)
            lengths = np.linalg.norm(ring - point, axis=1)
            self.assertAlmostEqual(float(lengths.min()), 0.1, places=6)
            self.assertAlmostEqual(float(lengths.max()), 0.2, places=6)
        self.assertEqual(g.inspect(obj)["nonmanifold_edges"], 0)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        self.assertGreater(bm.calc_volume(signed=True), 0)
        bm.free()
        # First-width and transported width axes must remain perpendicular to tangents.
        np.testing.assert_allclose(world[0], [0.2, 0, 0], atol=1e-6)
        for i in [1, 2]:
            a = np.array(centers[i]) - centers[i - 1]
            b = np.array(centers[i + 1]) - centers[i]
            tangent = a / np.linalg.norm(a) + b / np.linalg.norm(b)
            self.assertAlmostEqual(
                float((world[i * 32] - centers[i]) @ tangent), 0, places=6
            )
        count = len(bpy.data.objects)
        for pts, rs, ref in [
            ([[0, 0, 0], [0, 0, 0]], [[1, 1]] * 2, [1, 0, 0]),
            ([[0, 0, 0], [0, 0, 1], [0, 0, 0]], [[1, 1]] * 3, [1, 0, 0]),
            (centers, [[0, 1]] * 4, [1, 0, 0]),
            (centers, radii, [0, 0, 1]),
        ]:
            with self.assertRaises(ValueError):
                sweep("Bad", pts, rs, reference=ref)
            self.assertEqual(len(bpy.data.objects), count)

    def test_construction_dimensions_profiles_and_anchors(self):
        from mesh_workbench import construction as c
        import bmesh
        from mathutils import Vector

        ring = c.revolve(
            "Ring", [(0.8, -0.1), (1, -0.1), (1, 0.1), (0.8, 0.1)], closed=True
        )
        self.assertEqual(g.inspect(ring)["nonmanifold_edges"], 0)
        bm = bmesh.new()
        bm.from_mesh(ring.data)
        self.assertGreater(bm.calc_volume(signed=True), 0)
        bm.free()
        beam = c.strut("Beam", [1, 2, 3], [2, 4, 6], 0.1)
        world = s.coordinates(beam)
        np.testing.assert_allclose(world[:64].mean(axis=0), [1.5, 3, 4.5], atol=1e-6)
        # Each endpoint ring center must coincide with the requested anchor.
        np.testing.assert_allclose(world[:32].mean(axis=0), [1, 2, 3], atol=1e-6)
        np.testing.assert_allclose(world[32:].mean(axis=0), [2, 4, 6], atol=1e-6)
        box = c.rounded_box("Rounded", [2, 3, 4], [1, 2, 3], 0.2)
        evaluated = box.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bounds = np.array(
            [evaluated.matrix_world @ Vector(v) for v in evaluated.bound_box]
        )
        np.testing.assert_allclose(
            bounds.max(axis=0) - bounds.min(axis=0), [2, 3, 4], atol=1e-6
        )
        count = len(bpy.data.objects)
        for fn in [
            lambda: c.strut("Bad", [0, 0, 0], [0, 0, 0]),
            lambda: c.revolve("Bad", [(0, 0), (1, 1)]),
            lambda: c.revolve("Bad", [(1, 0), (1, 0)]),
            lambda: c.rounded_box("Bad", [1, 1, 1], radius=0.5),
            lambda: c.revolve("Ring", [(1, 0), (1, 1)]),
        ]:
            with self.assertRaises(ValueError):
                fn()
            self.assertEqual(len(bpy.data.objects), count)

    def test_selection_move_undo_and_stale(self):
        a = m.primitive("cube", "A", scale=[2, 1, 0.5])
        before = s.coordinates(a)
        sel = g.selection(a, "VERT", box=[[0, -2, -2], [3, 2, 2]])
        result = g.move(a, sel, [0.2, 0, 0.1])
        after = s.coordinates(a)
        self.assertEqual(len(sel["indices"]), 4)
        for i in range(8):
            np.testing.assert_allclose(
                after[i] - before[i],
                [0.2, 0, 0.1] if i in sel["indices"] else [0, 0, 0],
                atol=1e-6,
            )
        s.set_layer(a, result["layer"], 0)
        np.testing.assert_array_equal(s.coordinates(a), before)
        faces = g.selection(a, "FACE")
        b = g.edit_topology(a, faces, "subdivide", "B", cuts=1)
        with self.assertRaises(ValueError):
            g.move(b, sel, [1, 0, 0])
        np.testing.assert_array_equal(s.coordinates(a), before)

    def test_topology_operations(self):
        a = m.primitive("cube", "Cube")
        top = g.selection(a, "FACE", box=[[-2, -2, 0.99], [2, 2, 1.01]])
        self.assertEqual(len(top["indices"]), 1)
        extruded = g.edit_topology(a, top, "extrude", "Extruded", delta=[0, 0, 0.5])
        self.assertAlmostEqual(g.inspect(extruded)["bounds"][1][2], 1.5, places=5)
        self.assertEqual(g.inspect(extruded)["nonmanifold_edges"], 0)
        inset = g.edit_topology(a, top, "inset", "Inset", thickness=0.2)
        self.assertGreater(len(inset.data.polygons), len(a.data.polygons))
        bevel = g.edit_topology(
            a, g.selection(a, "EDGE"), "bevel", "Bevel", offset=0.1, segments=2
        )
        self.assertGreater(len(bevel.data.polygons), 6)
        tri = g.edit_topology(a, g.selection(a, "FACE"), "triangulate", "Tri")
        self.assertEqual(len(tri.data.polygons), 12)
        deleted = g.edit_topology(a, top, "delete", "Open")
        self.assertEqual(g.inspect(deleted)["boundary_edges"], 4)
        weld = g.edit_topology(a, g.selection(a), "weld", "Weld", distance=0.001)
        self.assertEqual(len(weld.data.vertices), 8)
        with self.assertRaises(ValueError):
            g.edit_topology(a, top, "subdivide", "Failure", cuts=-1)
        self.assertNotIn("Failure", bpy.data.objects)

    def test_combine_boolean_fuse_and_blend(self):
        a = m.primitive("cube", "A")
        b = m.primitive("cube", "B", location=[1, 0, 0])
        old = s.coordinates(a).copy()
        join = m.combine([a, b], "Join")
        self.assertEqual(len(join.data.vertices), 16)
        union = m.boolean(a, b, "UNION", "Union")
        self.assertEqual(g.inspect(union)["nonmanifold_edges"], 0)
        self.assertAlmostEqual(g.inspect(union)["bounds"][1][0], 2, places=5)
        cut = m.boolean(a, b, "DIFFERENCE", "Cut")
        self.assertLess(g.inspect(cut)["bounds"][1][0], 0.001)
        fused = m.combine([a, b], "Fuse", voxel=0.15)
        self.assertEqual(g.inspect(fused)["nonmanifold_edges"], 0)
        blend = m.blend(a, b, "Blend", 0.5)
        np.testing.assert_allclose(s.coordinates(blend), old + [0.5, 0, 0], atol=1e-6)
        with self.assertRaises(ValueError):
            m.blend(a, union, "Invalid")
        np.testing.assert_array_equal(s.coordinates(a), old)

    def test_projection_patterns_uv(self):
        a = m.primitive("sphere", "Surface")
        motif = m.primitive("cube", "Motif")
        hits = p.project(a, [[0, 0, 2]], max_distance=2)
        self.assertAlmostEqual(hits[0]["position"][2], 1, places=5)
        with self.assertRaises(ValueError):
            p.project(a, [[0, 0, 3]], max_distance=0.1)
        seam = p.seam(a, [[0, -1, 0], [0.5, -1, 0]], "Seam", spacing=0.1)
        self.assertGreater(len(seam.data.splines[0].points), 2)
        pattern = p.scatter(
            a,
            motif,
            [[0, -1, 0], [0.6, -1, 0]],
            "Studs",
            scale=0.05,
            minimum_spacing=0.2,
        )
        self.assertEqual(len(pattern.data.vertices), 16)
        with self.assertRaises(ValueError):
            p.scatter(
                a, motif, [[0, -1, 0], [0, -1, 0]], "Overlap", minimum_spacing=0.2
            )
        self.assertNotIn("Overlap", bpy.data.objects)
        uv = p.cylindrical_uv(a)
        self.assertTrue(
            all(np.isfinite(v.uv[:]).all() for v in a.data.uv_layers[uv].data)
        )
        p.weave(a, uv)
        self.assertTrue(a.data.materials[0].use_nodes)
        floating = m.primitive(
            "plane", "Floating", location=[0, 0, 1.3], scale=[0.2, 0.2, 0.2]
        )
        conformed = p.conform(
            floating,
            g.selection(floating),
            a,
            "Conformed",
            max_distance=0.7,
            offset=0.01,
        )
        self.assertLess(g.inspect(conformed)["bounds"][1][2], 1.1)

    def test_surface_brush_mask_and_reopen(self):
        a = m.primitive("sphere", "Ball")
        camera([0, -5, 0], [0, 0, 0], 3, [64, 64])
        surface.capture(self.root / "before", False)
        before = s.coordinates(a).copy()
        surface_data = s.Surface(self.root / "before")
        point, normal = surface_data.point([32, 32], "Ball")
        self.assertLess(point[1], -0.9)
        s.mask(
            self.root / "before",
            {"object": "Ball", "name": "hold", "pixels": [[32, 32]], "radius": 0.12},
        )
        r = s.path_stroke(
            self.root / "before",
            {
                "object": "Ball",
                "mode": "grab",
                "points": [[38, 32], [42, 32]],
                "radius": 0.6,
                "mask": "hold",
            },
        )
        self.assertGreater(r["changed_vertices"], 0)
        self.assertEqual(r["protected_max_displacement"], 0)
        delta = s.coordinates(a) - before
        self.assertGreater(delta[:, 0].max(), 0)
        self.assertLess(np.abs(delta[:, 1:]).max(), 1e-6)
        with self.assertRaises(ValueError):
            s.Surface(self.root / "before")
        s.set_layer(a, r["layer"], 0)
        np.testing.assert_array_equal(before, s.coordinates(a))
        for mode in ("pinch", "smooth", "normal"):
            result = s.path_stroke(
                self.root / "before",
                {
                    "object": "Ball",
                    "mode": mode,
                    "points": [[34, 32], [38, 32]],
                    "radius": 0.5,
                    "symmetry_x": True,
                },
            )
            self.assertGreater(result["changed_vertices"], 0)
            s.set_layer(a, result["layer"], 0)
        checkpoint = self.root / "saved.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
        bpy.ops.wm.open_mainfile(
            filepath=str(checkpoint), load_ui=False, use_scripts=False
        )
        np.testing.assert_array_equal(before, s.coordinates(bpy.data.objects["Ball"]))
        library = self.root / "library.blend"
        shutil.copy2(checkpoint, library)
        imported = m.load_blend(library, ["Ball"], "copy_")
        self.assertEqual(imported[0].name, "copy_Ball")

    def test_obj_import(self):
        path = self.root / "triangle.obj"
        path.write_text("o Triangle\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        result = m.load_mesh(path, "external_")
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].data.vertices), 3)

    def test_geodesic_does_not_cross_disconnected_sheet(self):
        verts = []
        faces = []
        side = 15
        count = side * side
        for layer in range(2):
            for y in range(side):
                for x in range(side):
                    verts.append(((x - 7) / 7, (y - 7) / 7, -layer * 0.03))
            for y in range(side - 1):
                for x in range(side - 1):
                    i = layer * count + y * side + x
                    faces.append((i, i + 1, i + 1 + side, i + side))
        mesh = bpy.data.meshes.new("Sheets")
        mesh.from_pydata(verts, [], faces)
        a = bpy.data.objects.new("Sheets", mesh)
        bpy.context.collection.objects.link(a)
        a.scale = (1.2, 0.8, 1.4)
        camera([0, 0, 5], [0, 0, 0], 3, [64, 64])
        surface.capture(self.root / "sheets", False)
        before = s.coordinates(a)
        result = s.path_stroke(
            self.root / "sheets",
            {
                "object": "Sheets",
                "mode": "normal",
                "points": [[40, 32]],
                "radius": 0.4,
                "distance": 0.05,
                "symmetry_x": True,
            },
        )
        after = s.coordinates(a)
        np.testing.assert_array_equal(before[count:], after[count:])
        self.assertGreater(result["changed_vertices"], 0)
        delta = (after - before)[:count].reshape(side, side, 3)
        mirror = delta[:, ::-1, :].copy()
        mirror[:, :, 0] *= -1
        np.testing.assert_allclose(delta, mirror, atol=1e-6)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Modeling)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        "MESH_WORKBENCH_TEST_RESULT",
        json.dumps(
            {
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
            }
        ),
        flush=True,
    )
    if not result.wasSuccessful():
        raise RuntimeError("Blender integration tests failed")
