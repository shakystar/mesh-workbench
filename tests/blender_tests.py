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

    def test_shell_role_normals_preserve_geometry(self):
        from mesh_workbench import enclosure

        obj = m.primitive("cube", "Role shading")
        for label in ["Outer", "Cut"]:
            obj.data.materials.append(bpy.data.materials.new(label))
        obj.data.polygons[0].material_index = 1
        obj["mw_skin_roles"] = json.dumps({"outer": 0, "cut": 1})
        before = s.coordinates(obj).copy()
        enclosure.sharp_role_edges(obj)
        self.assertEqual(json.loads(obj["mw_role_shading"])["marked_edges"], 4)
        self.assertEqual(sum(e.use_edge_sharp for e in obj.data.edges), 4)
        np.testing.assert_array_equal(s.coordinates(obj), before)

    def test_semantic_seed_selects_unique_component_and_rejects_ties(self):
        from mesh_workbench import enclosure, semantic

        obj = enclosure._mesh(
            "Two patches",
            [
                [-4, -1, 0],
                [-2, -1, 0],
                [-2, 1, 0],
                [-4, 1, 0],
                [2, -1, 0],
                [4, -1, 0],
                [4, 1, 0],
                [2, 1, 0],
            ],
            [[0, 1, 2, 3], [4, 5, 6, 7]],
        )
        query = {"normal": [0, 0, 1], "normal_min": 0.9, "components": 1}
        with self.assertRaises(ValueError):
            semantic.resolve(obj, query)
        selected = semantic.resolve(
            obj, {**query, "seed": [-3, 0, 0], "seed_distance": 0.1}
        )
        self.assertEqual(selected["indices"], [0])
        for seed, distance in [([0, 0, 0], 3), ([100, 0, 0], 0.1)]:
            with self.assertRaises(ValueError):
                semantic.resolve(
                    obj, {**query, "seed": seed, "seed_distance": distance}
                )

    def test_patch_preserves_unedited_polygons_and_quad_binding(self):
        from mesh_workbench import remesh, attachments

        bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6, size=6)
        obj = bpy.context.object
        obj.name = "Quad source"
        selected = g.selection(obj, "FACE", box=[[0, -4, -1], [4, 4, 1]])
        binding = attachments.bind(obj, [[-2, 0.2, 0]], max_distance=0.01)
        old_uv = {
            tuple(sorted(tuple(obj.data.vertices[v].co) for v in f.vertices)): [
                tuple(obj.data.uv_layers[0].data[l].uv) for l in f.loop_indices
            ]
            for f in obj.data.polygons
            if f.index not in selected["indices"]
        }
        result = remesh.remesh(
            obj,
            selected,
            "Mixed patch",
            0.7,
            iterations=2,
            max_error=0.001,
            relaxation=0.5,
            preserve_polygons=True,
        )
        report = json.loads(result["mw_remesh"])["report"]
        self.assertEqual(report["preserved_polygons"], len(old_uv))
        found = 0
        for f in result.data.polygons:
            key = tuple(sorted(tuple(result.data.vertices[v].co) for v in f.vertices))
            if key in old_uv:
                found += 1
                self.assertEqual(
                    [
                        tuple(result.data.uv_layers[0].data[l].uv)
                        for l in f.loop_indices
                    ],
                    old_uv[key],
                )
        self.assertEqual(found, len(old_uv))
        transferred, check = remesh.transfer_binding(obj, result, binding)
        self.assertLess(check["max_error"], 1e-5)
        np.testing.assert_allclose(
            attachments.resolve(result, transferred)[0]["position"],
            [-2, 0.2, 0],
            atol=1e-5,
        )

        # A fully pinned single face cannot improve; reject without leaking output.
        plane = m.primitive("plane", "Pinned patch")
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with self.assertRaises(ValueError):
            remesh.rebuild_patch(
                plane, g.selection(plane, "FACE"), "No gain", 1, iterations=1
            )
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))

    def test_patch_rebuild_quality_boundary_and_attributes(self):
        from mesh_workbench import remesh

        bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=10)
        obj = bpy.context.object
        obj.name = "Uneven patch"
        for v in obj.data.vertices:
            if abs(v.co.x) < 4.9 and abs(v.co.y) < 4.9:
                v.co.x += 0.32 * np.sin(v.index * 1.7)
                v.co.y += 0.28 * np.cos(v.index * 2.1)
        obj.data.update()
        xyz = s.coordinates(obj)
        before = xyz.copy()
        uv = obj.data.uv_layers.active
        for loop in obj.data.loops:
            uv.data[loop.index].uv = xyz[loop.vertex_index, :2] / 10 + 0.5
        group = obj.vertex_groups.new(name="Known mask")
        for i, point in enumerate(xyz):
            group.add([i], float(point[0] / 10 + 0.5), "REPLACE")
        obj["mw_masks"] = json.dumps(
            {"known": {"group": group.name, "topology": s.topology(obj)}}
        )
        result = remesh.rebuild_patch(
            obj,
            g.selection(obj, "FACE"),
            "Rebuilt patch",
            1.2,
            iterations=6,
            max_error=0.001,
        )
        state = json.loads(result["mw_remesh"])
        report = state["report"]
        self.assertGreater(
            report["patch_after"]["quality_p10"], report["patch_before"]["quality_p10"]
        )
        self.assertLess(
            report["patch_after"]["edge_length_cv"],
            report["patch_before"]["edge_length_cv"],
        )
        self.assertGreater(report["operations"]["relax"], 0)
        self.assertEqual(report["pinned_error"], 0)
        np.testing.assert_array_equal(s.coordinates(obj), before)
        rx = s.coordinates(result)
        for loop in result.data.loops:
            np.testing.assert_allclose(
                result.data.uv_layers[0].data[loop.index].uv,
                rx[loop.vertex_index, :2] / 10 + 0.5,
                atol=1e-5,
            )
        for v in result.data.vertices:
            weight = next(
                (
                    g.weight
                    for g in v.groups
                    if g.group == result.vertex_groups["Known mask"].index
                ),
                0,
            )
            self.assertAlmostEqual(weight, rx[v.index, 0] / 10 + 0.5, places=5)

    def test_surface_ribbons_grooves_attributes_and_rejection(self):
        from mesh_workbench import surfacedetail, assembly
        from mathutils import Vector

        obj = m.primitive("cube", "Path input", scale=(4, 4, 1))
        xyz = s.coordinates(obj)
        before = xyz.copy()
        uv = obj.data.uv_layers.new(name="PathXY")
        for loop in obj.data.loops:
            uv.data[loop.index].uv = xyz[loop.vertex_index, :2] / 8 + 0.5
        group = obj.vertex_groups.new(name="Path mask")
        for i, point in enumerate(xyz):
            group.add([i], float(point[0] / 8 + 0.5), "REPLACE")
        obj["mw_masks"] = json.dumps(
            {"path": {"group": group.name, "topology": s.topology(obj)}}
        )
        query = {"normal": [0, 0, 1], "normal_min": 0.9, "components": 1}
        paths = [{"points": [[-2, 0, 0], [2, 0, 0]]}]
        rib = surfacedetail.paths(
            obj,
            "Raised",
            query,
            paths,
            projection_axis=2,
            side=1,
            width=1,
            height=0.4,
            embed=0.1,
        )
        hit = assembly._tree(rib).ray_cast(Vector((0, 0, 5)), Vector((0, 0, -1)), 10)[0]
        self.assertAlmostEqual(hit.z, 1.4, places=5)
        rx = s.coordinates(rib)
        for loop in rib.data.loops:
            np.testing.assert_allclose(
                rib.data.uv_layers["PathXY"].data[loop.index].uv,
                rx[loop.vertex_index, :2] / 8 + 0.5,
                atol=1e-5,
            )
        for v in rib.data.vertices:
            self.assertAlmostEqual(
                rib.vertex_groups["Path mask"].weight(v.index),
                rx[v.index, 0] / 8 + 0.5,
                places=5,
            )
        groove = surfacedetail.paths(
            obj,
            "Grooved",
            query,
            paths,
            projection_axis=2,
            side=1,
            width=1,
            height=0.2,
            embed=0.3,
            mode="groove",
        )
        hit = assembly._tree(groove).ray_cast(
            Vector((0, 0, 5)), Vector((0, 0, -1)), 10
        )[0]
        self.assertAlmostEqual(hit.z, 0.7, places=5)
        self.assertEqual(g.inspect(groove)["nonmanifold_edges"], 0)
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        for bad in [
            {"side": -1},
            {"side": 1, "paths": [{"points": [[20, 0, 0], [22, 0, 0]]}]},
        ]:
            kwargs = {"paths": paths, "projection_axis": 2, "side": 1}
            kwargs.update(bad)
            with self.assertRaises(ValueError):
                surfacedetail.paths(obj, "Rejected path", query, **kwargs)
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        np.testing.assert_array_equal(s.coordinates(obj), before)

    def test_profiled_ring_real_flutes_and_cleanup(self):
        from mesh_workbench import detail

        profile = [[0, 9, 5, 0], [1, 10, 5, 1], [9, 8, 5, 1], [10, 7, 5, 0]]
        obj = detail.profiled_ring(
            "Profiled", [0, 0, 0], profile, flutes=12, depth=0.6, segments=96
        )
        xyz = s.coordinates(obj)
        section = xyz[np.abs(xyz[:, 0] - 1) < 1e-5]
        radii = np.linalg.norm(section[:, 1:], axis=1)
        outer = radii[radii > 6]
        self.assertAlmostEqual(float(outer.max()), 10, places=5)
        self.assertAlmostEqual(float(outer.min()), 9.4, places=5)
        self.assertEqual(g.inspect(obj)["nonmanifold_edges"], 0)
        self.assertIsNotNone(obj.data.uv_layers.get("AxialSurface"))
        ticked = detail.profiled_ring(
            "Ticked",
            [0, 0, 0],
            profile,
            flutes=12,
            depth=0.6,
            segments=96,
            ticks=4,
            tick_depth=0.2,
            tick_range=[0, 2],
        )
        tx = s.coordinates(ticked)
        self.assertTrue(
            np.any(np.linalg.norm(tx - np.array([1, 9.8, 0]), axis=1) < 1e-5)
        )
        cover = detail.edge_box(
            "Cover", [12, 3, 6], [0, 0, 0], upper=0.6, lower=0.2, vertical=0.4
        )
        self.assertEqual(g.inspect(cover)["nonmanifold_edges"], 0)
        self.assertEqual(json.loads(cover["mw_edge_box"])["lower"], 0.2)

        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        for kwargs in [{"depth": 6, "segments": 96}, {"depth": 0.6, "segments": 95}]:
            with self.assertRaises(ValueError):
                detail.profiled_ring("Bad", [0, 0, 0], profile, flutes=12, **kwargs)
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))

    def test_variable_bevel_geometry_attributes_and_rollback(self):
        from mesh_workbench import detail, enclosure
        from unittest.mock import patch

        obj = m.primitive("cube", "Bevel input")
        xyz = s.coordinates(obj)
        before = xyz.copy()
        uv = obj.data.uv_layers.new(name="LinearUV")
        for loop in obj.data.loops:
            x, y, z = xyz[loop.vertex_index]
            uv.data[loop.index].uv = ((x + 1) / 2, (y + 1) / 2)
        group = obj.vertex_groups.new(name="LinearMask")
        for i, point in enumerate(xyz):
            group.add([i], float((point[2] + 1) / 2), "REPLACE")
        obj["mw_masks"] = json.dumps(
            {"linear": {"group": group.name, "topology": s.topology(obj)}}
        )
        ids = [
            e.index
            for e in obj.data.edges
            if abs(xyz[e.vertices[0], 2] - xyz[e.vertices[1], 2]) > 1
        ]
        sel = g.selection(obj, "EDGE", ids)
        result = detail.variable_bevel(obj, sel, "Beveled", [0.1, 0.2, 0.3, 0.4])
        self.assertGreater(len(result.data.vertices), len(obj.data.vertices))
        self.assertEqual(g.inspect(result)["nonmanifold_edges"], 0)
        np.testing.assert_array_equal(s.coordinates(obj), before)
        rx = s.coordinates(result)
        self.assertEqual(
            json.loads(result["mw_masks"])["linear"]["topology"], s.topology(result)
        )
        for v in result.data.vertices:
            self.assertAlmostEqual(
                {item.group: item.weight for item in v.groups}.get(
                    result.vertex_groups["LinearMask"].index, 0
                ),
                (rx[v.index, 2] + 1) / 2,
                places=5,
            )
        for loop in result.data.loops:
            expected = (rx[loop.vertex_index, :2] + 1) / 2
            np.testing.assert_allclose(
                result.data.uv_layers["LinearUV"].data[loop.index].uv,
                expected,
                atol=1e-5,
            )
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with patch.object(
            enclosure, "_valid", side_effect=ValueError("Injected bevel rejection")
        ):
            with self.assertRaises(ValueError):
                detail.variable_bevel(obj, sel, "Rejected bevel", [0.1] * 4)
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        np.testing.assert_array_equal(s.coordinates(obj), before)

    def test_section_width_field_pins_and_rejection(self):
        from mesh_workbench import sectionshape

        outline = [[-10, 0], [10, 0], [10, 20], [-10, 20]]
        points = np.array(
            [[0, -5, 10], [0, 5, 10], [0, 0, 10], [-8, 5, 10]], dtype=float
        )
        controls = {
            "rows": [[0, 0, 0, 0], [10, 0, 0, 2], [20, 0, 0, 0]],
            "pins": [[-8, 10, 1, 3]],
            "maximum_displacement": 3,
        }
        before = points.copy()
        result, report = sectionshape.apply(points, outline, np.full(4, 5.0), controls)
        np.testing.assert_array_equal(points, before)
        np.testing.assert_allclose(result[:3], [[0, -7, 10], [0, 7, 10], [0, 0, 10]])
        np.testing.assert_array_equal(result[3], points[3])
        self.assertEqual(report["fixed_error"], 0)
        self.assertEqual(report["fixed_vertices"], 1)
        for bad in [
            {**controls, "rows": [[10, 0, 0, 1], [10, 0, 0, 1]]},
            {**controls, "maximum_displacement": 1},
            {**controls, "rows": [[0, -6, -6, 0], [20, -6, -6, 0]]},
            {**controls, "pins": [[0, 0, 3, 2]]},
        ]:
            with self.assertRaises(ValueError):
                sectionshape.apply(points, outline, np.full(4, 5.0), bad)
        np.testing.assert_array_equal(points, before)

    def test_section_shaped_enclosure_attributes_and_cleanup(self):
        from mesh_workbench import enclosure

        args = {
            "profile_xz": [[-12, 0], [12, 0], [12, 30], [-12, 30]],
            "corner_trim": 5,
            "rim_radius": 3,
            "rim_steps": 12,
            "head_half_width": 7,
            "grip_half_width": 7,
        }
        controls = {
            "rows": [[0, 0, 0, 0], [15, 0, 0, 1], [30, 0, 0, 0]],
            "maximum_displacement": 2,
        }
        obj = enclosure.create("Shaped", **args, section_controls=controls)
        self.assertEqual(g.inspect(obj)["nonmanifold_edges"], 0)
        self.assertGreater(json.loads(obj["mw_section_shape"])["changed"], 0)
        self.assertIsNotNone(obj.data.uv_layers.get("DesignXZ"))
        skin = enclosure.hollow(obj, "Shaped skin", thickness=1)
        report = enclosure.gauge(skin, minimum=0.8, maximum=1.4)
        self.assertTrue(report["passed"], report)
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with self.assertRaises(ValueError):
            enclosure.create(
                "Rejected",
                **args,
                section_controls={**controls, "maximum_displacement": 0.01},
            )
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))

    def test_nested_thin_wall_rejection_restores_scene(self):
        from mesh_workbench import nested, assembly

        nodes = {
            "master": {
                "kind": "enclosure",
                "args": {
                    "profile_xz": [[-12, 0], [12, 0], [12, 30], [-12, 30]],
                    "corner_trim": 5,
                    "rim_radius": 3,
                    "rim_steps": 12,
                    "head_half_width": 7,
                    "grip_half_width": 7,
                },
            },
            "skin": {
                "kind": "hollow",
                "deps": [{"id": "master"}],
                "args": {"thickness": 1},
            },
            "left": {
                "kind": "partition",
                "deps": [{"id": "skin"}],
                "args": {"side": "left"},
            },
        }
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with self.assertRaises(assembly.Rejected) as caught:
            nested.initialize(
                "thin wall",
                nodes,
                {},
                {},
                [
                    {
                        "kind": "wall",
                        "parts": ["left"],
                        "options": {"minimum": 1.6, "maximum": 2.6},
                    }
                ],
            )
        self.assertTrue(caught.exception.report["rolled_back"])
        self.assertFalse(caught.exception.report["checks"][0]["passed"])
        self.assertNotIn(nested.KEY, bpy.context.scene)
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))

    def test_nested_recipe_revision_and_rollback(self):
        from mesh_workbench import nested, assembly
        from unittest.mock import patch
        import copy

        nodes = {
            "body": {
                "kind": "box",
                "args": {"dimensions": [4, 4, 4], "center": [0, 0, 0]},
            }
        }
        nested.initialize("recipe revision", nodes, {}, {})
        state = nested.load()
        original = state["outputs"]["body"]["object"]
        revised = copy.deepcopy(nodes)
        revised["body"]["frame"] = {"origin": [0, 0, 2], "axis": [1, 0, 0]}
        before = bpy.context.scene[nested.KEY]
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)

        def fail(phase):
            if phase == "after_commit":
                raise RuntimeError("reconfigure commit failure")

        with patch.object(nested, "_checkpoint", side_effect=fail):
            with self.assertRaises(assembly.Rejected):
                nested.reconfigure(revised)
        self.assertEqual(before, bpy.context.scene[nested.KEY])
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        result = nested.reconfigure(revised)
        self.assertEqual(result["updated"], ["body"])
        self.assertNotEqual(original, result["objects"]["body"])
        np.testing.assert_array_equal(
            s.coordinates(bpy.data.objects[original]),
            s.coordinates(bpy.data.objects[result["objects"]["body"]]),
        )
        self.assertEqual(nested.load()["outputs"]["body"]["frame"]["origin"], [0, 0, 2])
        with self.assertRaisesRegex(ValueError, "logical part IDs"):
            nested.reconfigure({})

    def test_mechanical_constructor_failure_preserves_scene(self):
        from mesh_workbench import mechanical, enclosure
        from unittest.mock import patch

        source = m.primitive("cube", "preserved")
        before = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        coords = s.coordinates(source).copy()
        with self.assertRaises(ValueError):
            mechanical.annulus("bad axis", 3, 2, [0, 0, 0], 2, axis=[0, 0, 0])
        with patch.object(enclosure, "_valid", side_effect=ValueError("invalid solid")):
            with self.assertRaises(ValueError):
                mechanical.box("bad solid", [3, 3, 3], [0, 0, 0])
        self.assertEqual(before, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        np.testing.assert_array_equal(coords, s.coordinates(source))

    def test_actuator_contacts_interlock_containment_and_recovery(self):
        from mesh_workbench import actuators, joints
        from unittest.mock import patch

        moving = m.primitive("cube", "slider")
        stop = m.primitive("cube", "stop", location=[5, 0, 0])
        latch = m.primitive("cube", "latch", location=[0, 10, 0])
        actuators.register(
            {"slider": moving.name, "stop": stop.name, "latch": latch.name},
            {
                "slide": {
                    "limits": [0, 3],
                    "rest": 0,
                    "max_step": 0.25,
                    "vectors": {"slider": [1, 0, 0]},
                },
                "release": {
                    "limits": [0, 2],
                    "rest": 0,
                    "max_step": 0.25,
                    "vectors": {"latch": [0, 0, -1]},
                },
            },
            [{"channel": "slide", "above": 0, "requires": "release", "at_least": 2}],
        )
        before = joints.snapshot([moving.name, stop.name, latch.name])
        with self.assertRaisesRegex(ValueError, "interlock"):
            actuators.pose({"slide": 1})
        self.assertEqual(before, joints.snapshot(list(before)))
        with self.assertRaises(ValueError):
            actuators.pose({"slide": 3.1, "release": 2})
        report = actuators.sweep(
            "slide",
            0,
            3,
            [["slider", "stop"]],
            base={"release": 2},
            contacts=[{"parts": ["slider", "stop"], "at": 3, "max_penetration": 0.01}],
        )
        self.assertTrue(report["passed"], report)
        self.assertTrue(report["rest_restored"])
        self.assertEqual(
            report["samples"][-1]["pairs"][0]["category"], "intentional contact"
        )
        with patch.object(
            actuators, "pair", side_effect=RuntimeError("measurement failure")
        ):
            with self.assertRaises(RuntimeError):
                actuators.sweep(
                    "slide", 0, 3, [["slider", "stop"]], base={"release": 2}
                )
        self.assertEqual(before, joints.snapshot(list(before)))
        outer = m.primitive("cube", "container", scale=[3, 3, 3])
        result = actuators.pair(moving, outer)
        self.assertFalse(result["passed"])
        self.assertGreater(result["maximum_sampled_penetration"], 1)
        moving.data.vertices[0].co.x -= 0.1
        with self.assertRaisesRegex(ValueError, "geometry changed"):
            actuators.pose({})

    def test_nested_shell_insert_regeneration_and_atomic_failures(self):
        from mesh_workbench import nested, assembly, attachments
        from unittest.mock import patch

        query = {
            "box": [[-8, -12, 5], [8, -4, 25]],
            "normal": [0, -1, 0],
            "normal_min": 0.8,
            "materials": [0],
            "components": 1,
        }
        nodes = {
            "master": {
                "kind": "enclosure",
                "visible": False,
                "args": {
                    "profile_xz": [[-12, 0], [12, 0], [12, 30], [-12, 30]],
                    "corner_trim": 5,
                    "rim_radius": 3,
                    "rim_steps": 12,
                    "edge_spacing": 2,
                    "cap_spacing": 3,
                    "head_half_width": 7,
                    "grip_half_width": 7,
                    "grip_width": {"param": "width"},
                },
            },
            "skin": {
                "kind": "hollow",
                "visible": False,
                "deps": [{"id": "master"}],
                "args": {"thickness": 1},
            },
            "left": {
                "kind": "partition",
                "deps": [{"id": "skin"}],
                "args": {"side": "left"},
            },
            "insert": {
                "kind": "insert",
                "deps": [{"id": "left"}],
                "args": {
                    "query": query,
                    "center": [0, 0, 15],
                    "radii": [5, 8],
                    "rings": 4,
                    "segments": 24,
                    "offset": 0.4,
                    "thickness": 0.6,
                },
            },
            "dot": {
                "kind": "relief",
                "deps": [{"id": "insert"}],
                "args": {
                    "query": {"normal": [0, -1, 0], "normal_min": 0.8, "components": 1},
                    "points": [[0, -12, 15]],
                    "radii": 0.35,
                    "height": 0.2,
                    "embed": 0.08,
                    "clearance": 0.06,
                    "max_distance": 10,
                    "direction": [0, 1, 0],
                },
            },
            "fixed": {
                "kind": "annulus",
                "deps": [{"id": "master", "use": "frame"}],
                "args": {
                    "outer_radius": 2,
                    "inner_radius": 1,
                    "start": [30, 0, 15],
                    "length": 3,
                },
            },
        }
        result = nested.initialize(
            "test nested",
            nodes,
            {"width": 0},
            {"width": [0, 2]},
            [
                {
                    "kind": "wall",
                    "parts": ["left"],
                    "options": {"minimum": 0.8, "maximum": 1.2},
                }
            ],
        )
        self.assertTrue(result["passed"])
        state = nested.load()
        fixed = state["outputs"]["fixed"]["object"]
        old = bpy.context.scene[nested.KEY]
        original_objects = set(bpy.data.objects)
        original_meshes = set(bpy.data.meshes)
        visibility = {
            o.name: (o.hide_get(), o.hide_render, o.hide_viewport)
            for o in bpy.data.objects
        }
        before = {
            k: attachments.revision(bpy.data.objects[r["object"]])
            for k, r in state["outputs"].items()
        }
        for phase in (
            "after_build",
            "after_transfer",
            "after_validate",
            "after_commit",
        ):

            def fail(actual):
                if actual == phase:
                    raise RuntimeError("injected " + phase)

            with patch.object(nested, "_checkpoint", side_effect=fail):
                with self.assertRaises(assembly.Rejected):
                    nested.update({"width": 1})
            self.assertEqual(old, bpy.context.scene[nested.KEY])
            self.assertEqual(original_objects, set(bpy.data.objects))
            self.assertEqual(original_meshes, set(bpy.data.meshes))
            nested.load()
            self.assertEqual(
                visibility,
                {
                    o.name: (o.hide_get(), o.hide_render, o.hide_viewport)
                    for o in bpy.data.objects
                },
            )
            for k, r in state["outputs"].items():
                self.assertEqual(
                    before[k], attachments.revision(bpy.data.objects[r["object"]])
                )
        result = nested.update({"width": 2})
        self.assertEqual(
            set(result["updated"]), {"master", "skin", "left", "insert", "dot"}
        )
        self.assertEqual(result["objects"]["fixed"], fixed)
        current = nested.load()
        parent = bpy.data.objects[current["outputs"]["insert"]["object"]]
        dot = bpy.data.objects[current["outputs"]["dot"]["object"]]
        self.assertEqual(attachments.status(parent, dot)["status"], "current")
        result = nested.update(
            remesh_request={
                "part": "master",
                "query": {
                    "box": [[-7, -12, 7], [7, -4, 23]],
                    "normal": [0, -1, 0],
                    "normal_min": 0.9,
                    "components": 1,
                },
                "options": {"target_length": 1.2, "iterations": 1, "max_error": 0.09},
            }
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["objects"]["fixed"], fixed)
        self.assertEqual(
            set(result["updated"]), {"master", "skin", "left", "insert", "dot"}
        )
        with self.assertRaisesRegex(ValueError, "Unknown"):
            nested.update(
                remesh_request={"part": "missing", "query": {}, "options": {}}
            )
        with self.assertRaisesRegex(ValueError, "cycle"):
            nested._order(
                {
                    "a": {"kind": "box", "deps": [{"id": "b"}]},
                    "b": {"kind": "box", "deps": [{"id": "a"}]},
                }
            )

    def test_enclosure_shell_and_semantic_regions(self):
        from mesh_workbench import enclosure, semantic
        from unittest.mock import patch

        profile = [[-12, 0], [12, 0], [12, 30], [-12, 30]]
        body = enclosure.create(
            "Envelope",
            profile,
            corner_trim=5,
            rim_radius=3,
            rim_steps=12,
            edge_spacing=2,
            cap_spacing=3,
            head_half_width=7,
            grip_half_width=7,
        )
        self.assertEqual(g.inspect(body)["nonmanifold_edges"], 0)
        group = body.vertex_groups.new(name="Z field")
        for v in body.data.vertices:
            group.add([v.index], v.co.z / 30, "REPLACE")
        skin = enclosure.hollow(body, "Skin", 1)
        panel = enclosure.partition(skin, "Left", "left")
        self.assertIn("Z field", panel.vertex_groups)
        self.assertEqual(
            json.loads(panel["mw_masks"])["grip"]["topology"], s.topology(panel)
        )
        report = enclosure.gauge(panel, minimum=0.8, maximum=1.2)
        self.assertTrue(report["passed"], report["violations"][:2])
        self.assertEqual(report["missing_or_invalid"], 0)
        query = {
            "box": [[-7, -8, 7], [7, -5, 23]],
            "normal": [0, -1, 0],
            "normal_min": 0.9,
            "materials": [0],
            "components": 1,
        }
        resolved = semantic.register(panel, "grip", query)
        self.assertGreater(len(resolved["indices"]), 2)
        self.assertFalse(enclosure.gauge(panel, minimum=1.5, maximum=2)["passed"])
        from mesh_workbench import inserts

        patch_obj = inserts.create(
            panel,
            query,
            "Known field insert",
            [0, 0, 15],
            [4, 6],
            offset=0.4,
            thickness=0.6,
            rings=3,
            segments=16,
        )
        for loop in patch_obj.data.loops:
            point = s.coordinates(patch_obj)[loop.vertex_index]
            np.testing.assert_allclose(
                patch_obj.data.uv_layers["DesignXZ"].data[loop.index].uv,
                [point[0] / 120, point[2] / 200],
                atol=1e-6,
            )
        for vertex in patch_obj.data.vertices:
            self.assertAlmostEqual(
                patch_obj.vertex_groups["Z field"].weight(vertex.index),
                vertex.co.z / 30,
                places=5,
            )
        before = set(bpy.data.objects)
        with self.assertRaisesRegex(ValueError, "side"):
            inserts.create(panel, query, "Wrong side", [0, 0, 15], [4, 6], side=1)
        self.assertEqual(before, set(bpy.data.objects))
        face = panel.data.polygons[resolved["indices"][0]]
        loop = face.loop_indices[0]
        uv = panel.data.uv_layers["DesignXZ"].data[loop].uv.copy()
        panel.data.uv_layers["DesignXZ"].data[loop].uv.x += 0.2
        with self.assertRaisesRegex(ValueError, "UV chart seam"):
            inserts.create(panel, query, "Seam crossing", [0, 0, 15], [4, 6])
        panel.data.uv_layers["DesignXZ"].data[loop].uv = uv
        face_index = resolved["indices"][0]
        old_role = panel.data.polygons[face_index].material_index
        panel.data.polygons[face_index].material_index = 1
        material_query = {k: v for k, v in query.items() if k != "materials"}
        with self.assertRaisesRegex(ValueError, "material boundary"):
            inserts.create(
                panel, material_query, "Material crossing", [0, 0, 15], [4, 6]
            )
        panel.data.polygons[face_index].material_index = old_role

        for v in panel.data.vertices:
            if abs(v.co.x) < 6 and 8 < v.co.z < 22:
                self.assertAlmostEqual(
                    panel.vertex_groups["Z field"].weight(v.index),
                    v.co.z / 30,
                    places=5,
                )
        before = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with patch.object(
            enclosure, "_valid", side_effect=ValueError("injected geometry check")
        ):
            with self.assertRaises(ValueError):
                enclosure.hollow(body, "Rejected", 1)
        self.assertEqual(before, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        with self.assertRaisesRegex(ValueError, "Empty"):
            semantic.resolve(panel, {"box": [[200, 200, 200], [210, 210, 210]]})
        # Two nearby disconnected sheets must not be treated as one semantic patch.
        a = m.primitive("plane", "sheet1")
        b = m.primitive("plane", "sheet2", location=[0, 0, 0.01])
        combined = m.combine([a, b], "two sheets")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            semantic.resolve(combined, {"components": 1})

    def test_local_remesh_uv_masks_binding_and_rollback(self):
        from mesh_workbench import remesh, attachments, regions

        # Irregular planar triangulation with a UV seam down its center.
        vertices = [
            (x + (0.16 if y % 2 and x not in (0, 10) else 0), y, 0)
            for y in range(11)
            for x in range(11)
        ]
        faces = []
        for y in range(10):
            for x in range(10):
                a = y * 11 + x
                faces.extend([(a, a + 1, a + 12), (a, a + 12, a + 11)])
        mesh = bpy.data.meshes.new("patch")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new("patch", mesh)
        bpy.context.collection.objects.link(obj)
        uv = mesh.uv_layers.new(name="UVMap")
        for f in mesh.polygons:
            for i in f.loop_indices:
                co = mesh.vertices[mesh.loops[i].vertex_index].co
                uv.data[i].uv = (co.x / 10, co.y / 10)
        group = obj.vertex_groups.new(name="gradient")
        for v in mesh.vertices:
            group.add([v.index], v.co.y / 10, "REPLACE")
        obj["mw_masks"] = json.dumps(
            {"gradient": {"group": "gradient", "topology": s.topology(obj)}}
        )
        regions.define(obj, "all", g.selection(obj, "VERT"))
        binding = attachments.bind(obj, [[4.2, 4.4, 0], [6.2, 6.4, 0]])
        before = s.coordinates(obj).copy()
        result = remesh.remesh(
            obj, g.selection(obj, "FACE"), "reduced", 1.8, iterations=4, max_error=0.001
        )
        state = json.loads(result["mw_remesh"])
        self.assertGreater(state["report"]["operations"]["collapse"], 0)
        self.assertGreater(state["report"]["operations"]["flip"], 0)
        self.assertEqual(state["report"]["pinned_error"], 0)
        np.testing.assert_array_equal(before, s.coordinates(obj))
        for loop in result.data.loops:
            co = result.data.vertices[loop.vertex_index].co
            np.testing.assert_allclose(
                result.data.uv_layers[0].data[loop.index].uv,
                [co.x / 10, co.y / 10],
                atol=1e-6,
            )
        for v in result.data.vertices:
            self.assertAlmostEqual(
                result.vertex_groups["gradient"].weight(v.index) if v.co.y else 0,
                v.co.y / 10,
                places=5,
            )
        transferred, report = remesh.transfer_binding(obj, result, binding)
        self.assertLess(report["max_error"], 1e-5)
        np.testing.assert_allclose(
            [h["position"] for h in attachments.resolve(result, transferred)],
            [[4.2, 4.4, 0], [6.2, 6.4, 0]],
            atol=1e-5,
        )
        finer = remesh.remesh(
            obj, g.selection(obj, "FACE"), "finer", 0.6, iterations=2, max_error=0.001
        )
        self.assertGreater(
            json.loads(finer["mw_remesh"])["report"]["operations"]["split"], 0
        )
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        obj["mw_masks"] = json.dumps(
            {"bad": {"group": "absent", "topology": s.topology(obj)}}
        )
        with self.assertRaisesRegex(ValueError, "mask"):
            remesh.remesh(
                obj, g.selection(obj, "FACE"), "bad", 1.8, iterations=1, max_error=0.001
            )
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        result.data.vertices[0].co.z += 0.1
        with self.assertRaisesRegex(ValueError, "Stale"):
            remesh.transfer_binding(obj, result, binding)

    def test_remesh_features_locality_and_assembly_transaction(self):
        from mesh_workbench import remesh, assembly, attachments, relief
        from unittest.mock import patch

        bpy.ops.mesh.primitive_grid_add(x_subdivisions=12, y_subdivisions=12, size=10)
        obj = bpy.context.object
        obj.name = "grid"
        mesh = obj.data
        uv = mesh.uv_layers.active
        mesh.materials.append(bpy.data.materials.new("left material"))
        mesh.materials.append(bpy.data.materials.new("right material"))
        for face in mesh.polygons:
            face.material_index = int(face.center.x > 0)
        # Mark a full center UV seam; preserve the discontinuous values exactly.
        for f in mesh.polygons:
            side = f.center.x > 0
            for loop in f.loop_indices:
                v = mesh.vertices[mesh.loops[loop].vertex_index]
                uv.data[loop].uv = (v.co.x / 10 + (2 if side else 0), v.co.y / 10)
        for e in mesh.edges:
            if all(abs(mesh.vertices[i].co.x) < 1e-6 for i in e.vertices):
                e.use_seam = True
        selection = g.selection(obj, "FACE", box=[[0, -6, -1], [6, 6, 1]])
        out = remesh.remesh(obj, selection, "local", 0.5, iterations=3, max_error=0.001)
        for f in out.data.polygons:
            self.assertEqual(f.material_index, int(f.center.x > 0))
            for loop in f.loop_indices:
                v = out.data.vertices[out.data.loops[loop].vertex_index]
                expected = [v.co.x / 10 + (2 if f.center.x > 0 else 0), v.co.y / 10]
                np.testing.assert_allclose(
                    out.data.uv_layers[0].data[loop].uv, expected, atol=1e-6
                )
        before = s.coordinates(obj)
        after = s.coordinates(out)
        for co in before[before[:, 0] <= 0]:
            self.assertTrue(np.any(np.all(after == co, axis=1)))
        pattern = relief.dots(
            obj,
            [[1, 1, 0]],
            "dot",
            radii=[0.2],
            height=0.1,
            segments=12,
            rings=2,
            max_distance=0.01,
        )
        attachments.bind_relief(obj, pattern)
        nodes = {
            "body": {"kind": "source", "object": obj.name},
            "dot": {
                "kind": "relief",
                "object": pattern.name,
                "deps": ["body"],
                "binding": json.loads(pattern["mw_surface_binding"]),
                "options": json.loads(pattern["mw_relief_settings"]),
            },
        }
        assembly.register("fixture", nodes)
        old = bpy.context.scene[assembly.KEY]
        objects = set(bpy.data.objects)
        meshes = set(bpy.data.meshes)
        with patch.object(assembly, "validate", return_value=[{"passed": False}]):
            with self.assertRaises(assembly.Rejected):
                assembly.remesh_source(
                    "body",
                    g.selection(obj, "FACE"),
                    "rejected",
                    target_length=0.5,
                    iterations=1,
                    max_error=0.001,
                )
        self.assertEqual(old, bpy.context.scene[assembly.KEY])
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        self.assertFalse(obj.hide_get())
        with patch.object(assembly, "status", side_effect=RuntimeError("commit check")):
            with self.assertRaises(assembly.Rejected):
                assembly.remesh_source(
                    "body",
                    g.selection(obj, "FACE"),
                    "commit rejected",
                    target_length=0.5,
                    iterations=1,
                    max_error=0.001,
                )
        self.assertEqual(old, bpy.context.scene[assembly.KEY])
        self.assertEqual(objects, set(bpy.data.objects))
        self.assertEqual(meshes, set(bpy.data.meshes))
        self.assertFalse(obj.hide_get())
        result = assembly.remesh_source(
            "body",
            g.selection(obj, "FACE"),
            "accepted",
            target_length=0.5,
            iterations=2,
            max_error=0.001,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(set(result["updated"]), {"body", "dot"})
        self.assertTrue(obj.hide_get())
        self.assertEqual(assembly.load()["nodes"]["body"]["object"], "accepted")
        self.assertLess(result["transfers"]["dot"]["max_error"], 1e-5)

    def test_remesh_recipe_and_rejection(self):
        from mesh_workbench.runner import run

        recipe = json.loads((ROOT / "examples/local-remesh.json").read_text())
        path = self.root / "recipe.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "success")
        audit = json.loads((self.root / "success/audit.json").read_text())
        remeshed = next(
            x["result"]["report"] for x in audit["operations"] if x["op"] == "remesh"
        )
        self.assertGreater(remeshed["operations"]["split"], 0)
        self.assertLessEqual(remeshed["sampled_error_max"], 0.05)
        recipe["operations"][5]["options"]["target_length"] = -1
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path.write_text(json.dumps(recipe))
        with self.assertRaises(ValueError):
            run(path, self.root / "failed")
        failed = json.loads((self.root / "failed/audit.json").read_text())
        self.assertEqual(failed["failed_operation"]["op"], "remesh")
        self.assertEqual(failed["status"], "failed")

    def test_headphone_tools_recipe_and_failure(self):
        from mesh_workbench.runner import run

        recipe = json.loads((ROOT / "examples/headphone-tools.json").read_text())
        path = self.root / "tools.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "success")
        audit = json.loads((self.root / "success/audit.json").read_text())
        self.assertEqual(audit["status"], "complete")
        measured = next(
            x["result"] for x in audit["operations"] if x["op"] == "path_sections"
        )
        self.assertLess(measured["radius_error_max"], 1e-5)
        recipe["operations"].append(
            {"op": "joints_inspect", "angles": {"hinge": 3}, "fixed": ["Source"]}
        )
        path.write_text(json.dumps(recipe))
        with self.assertRaises(ValueError):
            run(path, self.root / "failed")
        failed = json.loads((self.root / "failed/audit.json").read_text())
        self.assertEqual(failed["failed_operation"]["op"], "joints_inspect")

    def test_curvature_and_pinned_patch(self):
        from mesh_workbench import quality, pathmodel

        sphere = m.primitive(
            "sphere", "Sphere", scale=[10, 10, 10], segments=48, rings=24
        )
        report = quality.curvature(sphere)
        self.assertAlmostEqual(report["mean"], 0.1, delta=0.01)
        verts = [
            (
                x,
                y,
                0.15
                * np.sin(x * 2)
                * np.sin(y * 2)
                * (1 - (x / 3) ** 2) ** 2
                * (1 - (y / 3) ** 2) ** 2,
            )
            for y in np.linspace(-3, 3, 25)
            for x in np.linspace(-3, 3, 25)
        ]
        faces = [
            (i * 25 + j, i * 25 + j + 1, (i + 1) * 25 + j + 1, (i + 1) * 25 + j)
            for i in range(24)
            for j in range(24)
        ]
        patch = pathmodel._mesh("Patch", verts, faces)
        before = s.coordinates(patch).copy()
        sel = g.selection(patch, "VERT")
        result = quality.fair_patch(
            patch,
            sel,
            iterations=5,
            strength=0.8,
            max_shift=1,
            method="quadratic",
            fit_radius=1.2,
        )
        self.assertEqual(result["pinned_error"], 0)
        self.assertLess(
            result["after"]["roughness_rms"], result["before"]["roughness_rms"]
        )
        patch.data.shape_keys.key_blocks[result["layer"]].value = 0
        np.testing.assert_array_equal(s.coordinates(patch), before)
        with self.assertRaises(ValueError):
            quality.fair_patch(patch, sel, max_shift=1e-6)
        from unittest.mock import patch as mock_patch

        original_curvature = quality.curvature
        call_count = [0]

        def fail_after_edit(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Injected post-edit measurement failure")
            return original_curvature(*args, **kwargs)

        keys_before = len(patch.data.shape_keys.key_blocks)
        with mock_patch.object(quality, "curvature", fail_after_edit):
            with self.assertRaisesRegex(ValueError, "post-edit"):
                quality.fair_patch(patch, sel, iterations=2, max_shift=1)
        self.assertEqual(len(patch.data.shape_keys.key_blocks), keys_before)
        np.testing.assert_array_equal(s.coordinates(patch), before)
        material = quality.reflection_bands(patch)
        self.assertTrue(material.use_nodes)

    def test_refinement_provenance_masks_and_attachments(self):
        from mesh_workbench import refinement, attachments, regions

        source = m.primitive(
            "sphere", "Source", scale=[10, 10, 10], segments=16, rings=8
        )
        coords = s.coordinates(source).copy()
        region = g.selection(source, "VERT")
        regions.define(source, "all", region)
        group = source.vertex_groups.new(name="Protect")
        group.add(list(range(len(coords))), 0.4, "REPLACE")
        source["mw_masks"] = json.dumps(
            {"mask": {"group": group.name, "topology": s.topology(source)}}
        )
        binding = attachments.bind(source, [[10, 0, 0], [0, 0, 10]], max_distance=0.1)
        faces = g.selection(source, "FACE")
        refined = refinement.split(source, faces, "Refined")
        transferred = refinement.transfer_binding(source, refined, binding)
        np.testing.assert_allclose(
            [h["position"] for h in attachments.resolve(source, binding)],
            [h["position"] for h in attachments.resolve(refined, transferred)],
            atol=1e-5,
        )
        self.assertGreater(len(refined.data.vertices), len(source.data.vertices))
        np.testing.assert_allclose(s.protection(refined, "mask"), 0.4, atol=1e-6)
        self.assertEqual(
            len(regions.resolve(refined, "all")["indices"]), len(refined.data.vertices)
        )
        self.assertEqual(
            len(refinement.transfer_selection(source, refined, faces)["indices"]),
            len(refined.data.polygons),
        )
        np.testing.assert_array_equal(s.coordinates(source), coords)
        with self.assertRaises(ValueError):
            refinement.transfer_selection(source, refined, g.selection(source, "EDGE"))
        source.data.vertices[0].co.x += 0.1
        with self.assertRaisesRegex(ValueError, "Stale"):
            refinement.transfer_binding(source, refined, binding)

    def test_refinement_evaluated_surface_and_failed_mask_cleanup(self):
        from mesh_workbench import refinement, pathmodel, assembly
        from mathutils import Vector

        source = pathmodel._mesh(
            "Quad", [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], [(0, 1, 2, 3)]
        )
        g.move(source, g.selection(source, "VERT", indices=[0]), [0, 0, 1])
        target = refinement.split(source, g.selection(source, "FACE"), "Split")
        tree = assembly._tree(source)
        self.assertLess(
            max(tree.find_nearest(Vector(p))[3] for p in s.coordinates(target)), 1e-6
        )
        source["mw_masks"] = json.dumps(
            {"invalid": {"group": "Missing", "topology": "stale"}}
        )
        meshes = set(bpy.data.meshes.keys())
        with self.assertRaisesRegex(ValueError, "Stale source mask"):
            refinement.split(source, g.selection(source, "FACE"), "Rejected")
        self.assertNotIn("Rejected", bpy.data.objects)
        self.assertEqual(meshes, set(bpy.data.meshes.keys()))

        source["mw_masks"] = json.dumps(
            {"invalid": {"group": "Missing", "topology": s.topology(source)}}
        )
        with self.assertRaisesRegex(ValueError, "Missing source mask group"):
            refinement.split(
                source, g.selection(source, "FACE"), "Rejected missing group"
            )
        self.assertNotIn("Rejected missing group", bpy.data.objects)
        self.assertEqual(meshes, set(bpy.data.meshes.keys()))

    def test_path_sections_bridge_and_hinge_limits(self):
        from mesh_workbench import pathmodel, joints

        centers = [[0, 0, 0], [0, 0, 5], [2, 0, 10], [4, 0, 15]]
        path = pathmodel.create(
            "Path", centers, [[2, 1]] * 4, segments=24, reference=[0, 1, 0]
        )
        moved = pathmodel.reshape(
            path, [[0, 0, 0], [0, 0, 5], [4, 0, 10], [8, 0, 15]], "Changed"
        )
        self.assertLess(pathmodel.sections(moved)["radius_error_max"], 1e-5)
        theta = np.linspace(0, np.pi * 2, 16, endpoint=False)
        start = [[2 * np.cos(t), 2 * np.sin(t), 0] for t in theta]
        end = [[3 + 2 * np.cos(t), 2 * np.sin(t), 10] for t in theta]
        bridge = pathmodel.bridge(
            "Bridge", start, end, [[0, 0, 10]] * 16, [[0, 0, 10]] * 16
        )
        self.assertEqual(g.inspect(bridge)["nonmanifold_edges"], 0)
        np.testing.assert_allclose(s.coordinates(bridge)[:16], start, atol=1e-6)
        body = m.primitive("cube", "Rigid", location=[20, 0, 0])
        obstacle = m.primitive("cube", "Obstacle", location=[0, 0, 0])
        joints.register(
            [
                {
                    "name": "hinge",
                    "objects": [body.name],
                    "axis": [0, 1, 0],
                    "pivot": [0, 0, 0],
                    "limits": [-1, 1],
                }
            ]
        )
        before = s.coordinates(body).copy()
        self.assertTrue(
            joints.inspect({"hinge": 0.5}, [obstacle.name], steps=4)["passed"]
        )
        np.testing.assert_array_equal(s.coordinates(body), before)
        original_state = joints.pose({"hinge": 0.5})
        posed = s.coordinates(body).copy()
        joints.pose({"hinge": 0.5})
        np.testing.assert_array_equal(s.coordinates(body), posed)
        joints.restore(original_state)
        with self.assertRaises(ValueError):
            joints.inspect({"hinge": 2}, [obstacle.name])
        np.testing.assert_array_equal(s.coordinates(body), before)
        obstacle.location = [0, 0, -20]
        joints.register(
            [
                {
                    "name": "hinge",
                    "objects": [body.name],
                    "axis": [0, 1, 0],
                    "pivot": [0, 0, 0],
                    "limits": [-2, 2],
                }
            ]
        )
        self.assertFalse(
            joints.inspect({"hinge": np.pi / 2}, [obstacle.name], steps=8)["passed"]
        )

    def test_assembly_dependency_commit_and_rollback(self):
        from mesh_workbench import assembly, attachments, construction

        source = construction.rounded_box("Source", [10, 10, 10], radius=1)
        follower = construction.rounded_box(
            "Follower", [1, 1, 1], location=[0, 0, 7], radius=0.1
        )
        fixed = construction.rounded_box(
            "Fixed", [1, 1, 1], location=[20, 0, 0], radius=0.1
        )
        for item in (source, follower, fixed):
            s.bake(item)
        binding = attachments.bind(source, [[0, 0, 5]], max_distance=0.1)
        nodes = {
            "root": {"kind": "source", "object": source.name},
            "fixed": {"kind": "source", "object": fixed.name},
            "child": {
                "kind": "anchor",
                "object": follower.name,
                "deps": ["root"],
                "binding": binding,
                "offset": [0, 0, 2],
            },
        }
        assembly.register("Test", nodes)
        fixed_mesh = fixed.data
        result = assembly.update("root", {"kind": "dimension", "axis": 2, "delta": 2})
        self.assertEqual(result["updated"], ["root", "child"])
        self.assertIs(fixed.data, fixed_mesh)
        self.assertAlmostEqual(follower.location.z, 9, places=5)
        self.assertEqual(assembly.status()["revision"], 1)
        coords = s.coordinates(source).copy()
        names = set(bpy.data.objects.keys())
        with self.assertRaises(assembly.Rejected):
            assembly.update("root", {"kind": "dimension", "axis": 0, "delta": -20})
        np.testing.assert_array_equal(coords, s.coordinates(source))
        self.assertEqual(names, set(bpy.data.objects.keys()))
        # Fail after dependent geometry was generated, not only during input checks.
        graph = assembly.load()
        graph["checks"] = [{"kind": "unsupported", "nodes": ["root", "child"]}]
        bpy.context.scene[assembly.KEY] = json.dumps(graph)
        original_graph = bpy.context.scene[assembly.KEY]
        with self.assertRaises(assembly.Rejected):
            assembly.update("root", {"kind": "dimension", "axis": 0, "delta": 1})
        self.assertEqual(bpy.context.scene[assembly.KEY], original_graph)
        self.assertEqual(names, set(bpy.data.objects.keys()))
        # Simulate a failure during the actual pointer/property commit.
        from unittest.mock import patch

        graph["checks"] = []
        bpy.context.scene[assembly.KEY] = json.dumps(graph)
        original_props = assembly._setprops
        calls = [0]

        def fail_once(obj, values):
            calls[0] += 1
            if calls[0] == 1:
                raise RuntimeError("Injected commit failure")
            return original_props(obj, values)

        data_before = source.data
        with patch.object(assembly, "_setprops", fail_once):
            with self.assertRaisesRegex(assembly.Rejected, "Injected commit failure"):
                assembly.update("root", {"kind": "dimension", "axis": 0, "delta": 1})
        self.assertEqual(source.data, data_before)
        np.testing.assert_array_equal(coords, s.coordinates(source))
        self.assertEqual(names, set(bpy.data.objects.keys()))
        self.assertEqual(assembly.status()["revision"], 1)
        no_op = assembly.update("root", {"kind": "dimension", "axis": 0, "delta": 0})
        self.assertEqual(no_op["updated"], [])
        self.assertEqual(assembly.status()["revision"], 1)
        # Dependency corruption is rejected before scene mutation.
        graph["nodes"]["child"]["deps"] = ["missing"]
        bpy.context.scene[assembly.KEY] = json.dumps(graph)
        with self.assertRaisesRegex(ValueError, "Missing assembly dependency"):
            assembly.load()
        graph["nodes"]["child"]["deps"] = ["child"]
        bpy.context.scene[assembly.KEY] = json.dumps(graph)
        with self.assertRaisesRegex(ValueError, "cycle"):
            assembly.load()

    def test_assembly_shell_violation_locations(self):
        from mesh_workbench import assembly, shells

        root = m.primitive("sphere", "Root", scale=[10, 10, 10])
        selection = g.selection(root, "FACE", box=[[-20, -20, 0], [20, 20, 20]])
        shell = shells.extract(root, selection, "Shell", thickness=1.6, trim=0.1)
        nodes = {
            "root": {"kind": "source", "object": root.name},
            "shell": {
                "kind": "shell",
                "object": shell.name,
                "deps": ["root"],
                "faces": selection["indices"],
                "options": {"thickness": 1.6, "trim": 0.1},
            },
        }
        assembly.register("Shell", nodes, [{"kind": "thickness", "nodes": ["shell"]}])
        graph = assembly.load()
        graph["nodes"]["shell"]["options"]["thickness"] = 0.7
        bpy.context.scene[assembly.KEY] = json.dumps(graph)
        mesh = shell.data
        names = set(bpy.data.objects.keys())
        with self.assertRaises(assembly.Rejected) as caught:
            assembly.update("root", {"kind": "dimension", "axis": 0, "delta": 1})
        report = caught.exception.report
        self.assertTrue(report["rolled_back"])
        self.assertFalse(report["checks"][0]["passed"])
        self.assertTrue(report["checks"][0]["violations"])
        self.assertEqual(shell.data, mesh)
        self.assertEqual(set(bpy.data.objects.keys()), names)
        marker = shells.markers("Violation locations", report["checks"][0])
        self.assertGreater(len(marker.data.vertices), 0)
        # Manual edits and stale topology cannot silently reuse the recipes.
        root.data.vertices[0].co.x += 0.1
        with self.assertRaisesRegex(ValueError, "outside transaction"):
            assembly.load()

    def test_assembly_recipe_and_saved_graph(self):
        from mesh_workbench import assembly
        from mesh_workbench.runner import run

        recipe = {
            "version": 1,
            "operations": [
                {
                    "op": "rounded_box",
                    "name": "Root",
                    "dimensions": [10, 10, 10],
                    "options": {"radius": 1},
                },
                {"op": "bake", "object": "Root"},
                {
                    "op": "assembly_register",
                    "name": "Recipe",
                    "nodes": {"root": {"kind": "source", "object": "Root"}},
                },
                {
                    "op": "assembly_update",
                    "source": "root",
                    "edit": {"kind": "dimension", "axis": 0, "delta": 2},
                },
                {"op": "assembly_status"},
                {"op": "assembly_validate"},
            ],
        }
        path = self.root / "recipe.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "success")
        bpy.ops.wm.open_mainfile(
            filepath=str(self.root / "success/result.blend"),
            load_ui=False,
            use_scripts=False,
        )
        self.assertEqual(assembly.status()["revision"], 1)
        self.assertAlmostEqual(
            float(np.ptp(s.coordinates(bpy.data.objects["Root"]), axis=0)[0]),
            12,
            places=5,
        )
        recipe["operations"].append(
            {"op": "assembly_update", "source": "root", "edit": {"kind": "invalid"}}
        )
        path.write_text(json.dumps(recipe))
        with self.assertRaises(assembly.Rejected):
            run(path, self.root / "failure")
        audit = json.loads((self.root / "failure/audit.json").read_text())
        self.assertEqual(audit["status"], "failed")
        self.assertEqual(audit["failed_operation"]["op"], "assembly_update")
        self.assertTrue(audit["rejection"]["rolled_back"])

    def test_motion_path_collision_and_restore(self):
        from mesh_workbench import construction, motion

        moving = construction.rounded_box("Moving", [2, 2, 2], radius=0.1)
        obstacle = construction.rounded_box(
            "Obstacle", [2, 2, 2], location=[4, 0, 0], radius=0.1
        )
        s.bake(moving)
        s.bake(obstacle)
        moving.rotation_euler = [0, np.pi / 2, 0]
        bpy.context.view_layer.update()
        matrix = moving.matrix_world.copy()
        coordinates_before = s.coordinates(moving).copy()
        clear = motion.inspect(moving, [obstacle], translation=[0, 1, 0], steps=4)
        self.assertTrue(clear["passed"])
        hit = motion.inspect(moving, [obstacle], translation=[4, 0, 0], steps=8)
        self.assertFalse(hit["passed"])
        self.assertTrue(any(r["triangle_pairs"] for r in hit["samples"]))
        self.assertEqual(matrix, moving.matrix_world)
        np.testing.assert_array_equal(coordinates_before, s.coordinates(moving))

    def test_mouse_recipe_dispatch_and_gauge_independence(self):
        from mesh_workbench import shells
        from mesh_workbench.runner import run

        target = json.loads((ROOT / "examples/mouse-target.json").read_text())
        recipe = {
            "version": 1,
            "operations": [
                {
                    "op": "guide_loft",
                    "name": "Master",
                    "sections": target["sections"],
                    "options": {"tilt": target["tilt"], "rows": 32, "segments": 32},
                },
                {
                    "op": "define_region",
                    "object": "Master",
                    "name": "thumb",
                    "selection": {"sphere": {"center": [-31, -14, 14], "radius": 24}},
                },
                {
                    "op": "radial_edit",
                    "object": "Master",
                    "region": "thumb",
                    "center": [-31, -14, 14],
                    "radius": 24,
                    "delta": [3, 0, 0],
                },
                {
                    "op": "select",
                    "object": "Master",
                    "name": "upper",
                    "selection": {
                        "domain": "FACE",
                        "box": [[-100, -100, 11], [100, 100, 100]],
                    },
                },
                {
                    "op": "select",
                    "object": "Master",
                    "name": "lower",
                    "selection": {
                        "domain": "FACE",
                        "box": [[-100, -100, -100], [100, 100, 11]],
                    },
                },
                {
                    "op": "extract_shell",
                    "object": "Master",
                    "selection": "upper",
                    "name": "Top",
                },
                {
                    "op": "extract_shell",
                    "object": "Master",
                    "selection": "lower",
                    "name": "Base",
                },
                {"op": "measure_thickness", "object": "Top", "name": "wall"},
                {"op": "measure_gap", "left": "Top", "right": "Base", "name": "seam"},
                {"op": "intersection_candidates", "left": "Top", "right": "Base"},
                {"op": "section", "object": "Master", "axis": 1, "value": 0},
                {
                    "op": "extract_shell",
                    "object": "Master",
                    "selection": "upper",
                    "name": "Thin",
                    "options": {"thickness": 0.7},
                },
                {"op": "measure_thickness", "object": "Thin", "name": "bad"},
                {
                    "op": "mark_violations",
                    "measurement": "bad",
                    "name": "Markers",
                    "options": {"limit": 10},
                },
            ],
        }
        path = self.root / "mouse.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "success")
        audit = json.loads((self.root / "success/audit.json").read_text())
        self.assertEqual(audit["status"], "complete")
        self.assertTrue(audit["operations"][7]["result"]["passed"])
        self.assertTrue(audit["operations"][8]["result"]["passed"])
        self.assertEqual(audit["operations"][9]["result"]["triangle_pair_count"], 0)
        thin = bpy.data.objects["Thin"]
        state = json.loads(thin["mw_shell"])
        state["nominal_thickness"] = 200
        thin["mw_shell"] = json.dumps(state)
        self.assertLess(shells.thickness(thin)["max"], 0.71)
        recipe["operations"].append(
            {"op": "measure_thickness", "object": "Master", "name": "not-shell"}
        )
        path.write_text(json.dumps(recipe))
        with self.assertRaises(ValueError):
            run(path, self.root / "failure")
        audit = json.loads((self.root / "failure/audit.json").read_text())
        self.assertEqual(audit["failed_operation"]["op"], "measure_thickness")
        plane = m.primitive("plane", "Plane")
        original = s.coordinates(plane).copy()
        with self.assertRaises(ValueError):
            shells.extract(plane, g.selection(plane, "FACE"), "Folded", trim=3)
        self.assertNotIn("Folded", bpy.data.objects)
        np.testing.assert_array_equal(s.coordinates(plane), original)

    def test_asymmetric_loft_shell_gauges_and_failures(self):
        from mesh_workbench import loft, shells, sections, regions, fairing

        target = json.loads((ROOT / "examples/mouse-target.json").read_text())
        obj = loft.create(
            "Mouse", target["sections"], tilt=target["tilt"], rows=48, segments=64
        )
        self.assertEqual(g.inspect(obj)["nonmanifold_edges"], 0)
        self.assertEqual(fairing.overlap_candidates(obj), 0)
        section = sections.cut(obj, 1, 0)
        self.assertLess(abs(section["bounds"][0][0] + 36), 1e-5)
        self.assertLess(abs(section["bounds"][1][0] - 31), 1e-5)
        self.assertLess(abs(section["bounds"][1][2] - 43), 0.15)
        params = json.loads(obj["mw_loft_face_params"])
        top = [i for i, p in enumerate(params) if p[1] < np.pi]
        base = [i for i, p in enumerate(params) if p[1] >= np.pi]
        upper = shells.extract(obj, g.selection(obj, "FACE", indices=top), "Top")
        lower = shells.extract(obj, g.selection(obj, "FACE", indices=base), "Base")
        self.assertEqual(g.inspect(upper)["nonmanifold_edges"], 0)
        self.assertEqual(g.inspect(lower)["nonmanifold_edges"], 0)
        thickness = shells.thickness(upper)
        print(
            "SHELL_TEST",
            json.dumps({k: v for k, v in thickness.items() if k != "violations"}),
        )
        self.assertTrue(thickness["passed"], thickness["violations"][:3])
        gap = shells.gap(upper, lower)
        print(
            "GAP_TEST", json.dumps({k: v for k, v in gap.items() if k != "violations"})
        )
        self.assertTrue(gap["passed"], gap["violations"][:3])
        thin = shells.extract(
            obj, g.selection(obj, "FACE", indices=top), "Too thin", thickness=0.7
        )
        bad = shells.thickness(thin)
        self.assertFalse(bad["passed"])
        self.assertGreater(len(bad["violations"]), 0)
        marker = shells.markers("Violations", bad, limit=20)
        self.assertLessEqual(len(marker.data.vertices), 120)
        self.assertEqual(g.inspect(marker)["nonmanifold_edges"], 0)
        # A highly concentrated pole sampling can fold an offset interior.
        # It must be rejected atomically rather than returned as a valid shell.
        dense = loft.create(
            "Dense poles", target["sections"], tilt=target["tilt"], end_refinement=1
        )
        dense_params = json.loads(dense["mw_loft_face_params"])
        dense_top = [i for i, p in enumerate(dense_params) if p[1] < np.pi]
        mesh_count = len(bpy.data.meshes)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            shells.extract(
                dense, g.selection(dense, "FACE", indices=dense_top), "Rejected offset"
            )
        self.assertNotIn("Rejected offset", bpy.data.objects)
        self.assertEqual(len(bpy.data.meshes), mesh_count)
        original = s.coordinates(obj).copy()
        region = g.selection(obj, "VERT", box=[[-50, -45, 5], [-10, 20, 32]])
        regions.define(obj, "thumb", region)
        edit = regions.radial_move(obj, "thumb", [-31, -14, 14], 24, [3, 0, 0])
        outside = sorted(set(range(len(original))) - set(region["indices"]))
        np.testing.assert_array_equal(s.coordinates(obj)[outside], original[outside])
        obj.data.shape_keys.key_blocks[edit["layer"]].value = 0
        np.testing.assert_allclose(s.coordinates(obj), original, atol=1e-7)
        with self.assertRaises(ValueError):
            sections.cut(obj, 1, 1000)
        with self.assertRaises(ValueError):
            loft.create("Invalid", target["sections"], segments=17)
        with self.assertRaises(ValueError):
            shells.extract(obj, g.selection(obj, "VERT"), "Bad")
        lower.data.polygons[0].vertices = tuple(
            reversed(lower.data.polygons[0].vertices)
        )
        with self.assertRaises(ValueError):
            shells.gap(upper, lower)

    def test_precision_reference_regions_and_candidate_restore(self):
        from mesh_workbench import (
            precision,
            reference,
            regions,
            candidates,
            attachments,
            fairing,
        )

        spec = json.loads((ROOT / "examples/speaker-target.json").read_text())
        panel = precision.rounded_panel("Precision", **spec["construction"]["case"])
        report, actual, expected = reference.evaluate(panel, spec, "case_front")
        self.assertGreater(report["iou"], 0.995)
        self.assertLess(report["boundary_mean"], 0.006)  # below one 0.01-unit pixel
        self.assertEqual(g.inspect(panel)["nonmanifold_edges"], 0)
        self.assertEqual(fairing.overlap_candidates(panel), 0)
        moved = panel.copy()
        moved.data = panel.data.copy()
        moved.name = "Shifted"
        bpy.context.collection.objects.link(moved)
        moved.location.x += 0.15
        worse, _, _ = reference.evaluate(moved, spec, "case_front")
        self.assertLess(worse["iou"], report["iou"] - 0.05)
        view = spec["views"]["front"]
        with self.assertRaises(ValueError):
            reference.compare(np.zeros_like(actual), expected, view)
        cropped = dict(view, bounds=[-0.1, 0.1, 0.9, 1.1])
        with self.assertRaisesRegex(ValueError, "clips"):
            reference.compare(
                reference.mesh_mask(panel, cropped),
                reference.target_mask(
                    cropped, spec["components"]["case_front"]["shapes"]
                ),
                cropped,
            )
        entries = [
            {"name": n, "reports": [r], "nonmanifold_edges": 0, "overlap_candidates": 0}
            for n, r in [("correct", report), ("shifted", worse)]
        ]
        ranked = candidates.rank(entries, ["case_front"])
        self.assertTrue(ranked[0]["accepted"])
        self.assertFalse(ranked[1]["accepted"])
        broken = json.loads(json.dumps(entries))
        broken[1]["reports"][0]["target_sha256"] = "different"
        with self.assertRaises(ValueError):
            candidates.rank(broken, ["case_front"])
        high, _, _ = reference.evaluate(panel, spec, "case_front", supersample=2)
        self.assertGreater(high["iou"], 0.999)
        mixed = json.loads(json.dumps(entries))
        mixed[1]["reports"][0]["sampling_size"] = [128, 128]
        with self.assertRaisesRegex(ValueError, "sampling"):
            candidates.rank(mixed, ["case_front"])
        snapshot = candidates.activate([panel.name], [panel.name, moved.name])
        self.assertTrue(moved.hide_render)
        with self.assertRaises(ValueError):
            candidates.activate([panel.name], [panel.name, moved.name])
        candidates.restore()
        self.assertEqual(panel.hide_render, snapshot[panel.name]["render"])
        self.assertEqual(moved.hide_get(), snapshot[moved.name]["viewport"])
        coords = s.coordinates(panel)
        sel = g.selection(panel, "VERT", box=[[-2, -1, 1.85], [2, 1, 2.1]])
        regions.define(panel, "top rim", sel)
        seam = precision.bound_seam(
            panel,
            [[-0.8, -0.1, 1.975], [0, -0.1, 1.975], [0.8, -0.1, 1.975]],
            "Seam",
            spacing=0.1,
        )
        old_seam = s.coordinates(seam).copy()
        linked = panel.copy()
        bpy.context.collection.objects.link(linked)
        with self.assertRaisesRegex(ValueError, "single-user"):
            regions.profile(panel, "top rim", 0, 2, [[-1.4, 0], [0, 0.03], [1.4, 0]])
        np.testing.assert_array_equal(s.coordinates(panel), coords)
        bpy.data.objects.remove(linked, do_unlink=True)
        edit = regions.profile(panel, "top rim", 0, 2, [[-1.4, 0], [0, 0.03], [1.4, 0]])
        after = s.coordinates(panel)
        outside = sorted(set(range(len(coords))) - set(sel["indices"]))
        np.testing.assert_array_equal(after[outside], coords[outside])
        self.assertEqual(regions.resolve(panel, "top rim")["indices"], sel["indices"])
        self.assertEqual(attachments.status(panel, seam)["status"], "needs_refresh")
        refreshed = precision.refresh_seam(panel, seam, "Seam refreshed")
        self.assertEqual(attachments.status(panel, refreshed)["status"], "current")
        np.testing.assert_array_equal(s.coordinates(seam), old_seam)
        self.assertEqual(g.inspect(refreshed)["nonmanifold_edges"], 0)
        panel.data.shape_keys.key_blocks[edit["layer"]].value = 0
        np.testing.assert_allclose(s.coordinates(panel), coords, atol=1e-7)
        panel.data.shape_keys.key_blocks[edit["layer"]].value = 1
        filename = self.root / "precision.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(filename))
        bpy.ops.wm.open_mainfile(
            filepath=str(filename), load_ui=False, use_scripts=False
        )
        panel = bpy.data.objects["Precision"]
        self.assertEqual(regions.resolve(panel, "top rim")["indices"], sel["indices"])
        self.assertEqual(
            attachments.status(panel, bpy.data.objects["Seam refreshed"])["status"],
            "current",
        )
        panel.data.polygons[0].vertices = tuple(
            reversed(panel.data.polygons[0].vertices)
        )
        with self.assertRaises(ValueError):
            regions.resolve(panel, "top rim")

    def test_precision_curves_and_recipe_failure(self):
        from mesh_workbench import precision, fairing
        from mesh_workbench.runner import run

        controls = [
            [[0, 0, 0], [0, 0, 0.3], [0.3, 0, 0.5], [0.6, 0, 0.5]],
            [[0.6, 0, 0.5], [0.9, 0, 0.5], [1.2, 0, 0.3], [1.2, 0, 0]],
        ]
        tube = precision.bezier_tube("Curve", controls, radius=0.04)
        self.assertEqual(g.inspect(tube)["nonmanifold_edges"], 0)
        self.assertEqual(fairing.overlap_candidates(tube), 0)
        invalid = json.loads(json.dumps(controls))
        invalid[1][0][0] += 0.1
        with self.assertRaises(ValueError):
            precision.bezier_tube("Bad", invalid)
        self.assertNotIn("Bad", bpy.data.objects)
        with self.assertRaises(ValueError):
            precision.rounded_panel("BadPanel", [2, 0.1, 1], 0.2, 0.1)
        self.assertNotIn("BadPanel", bpy.data.objects)
        spec = json.loads((ROOT / "examples/speaker-target.json").read_text())
        recipe = {
            "version": 1,
            "operations": [
                {"op": "rounded_panel", "name": "Case", **spec["construction"]["case"]}
            ],
        }
        # location belongs in options in the public JSON operation.
        recipe["operations"][0]["options"] = {
            "location": recipe["operations"][0].pop("location")
        }
        recipe["operations"] += [
            {
                "op": "compare_reference",
                "object": "Case",
                "path": str(ROOT / "examples/speaker-target.json"),
                "component": "case_front",
                "overlay": "reference.png",
            },
            {
                "op": "define_region",
                "object": "Case",
                "name": "top",
                "selection": {"box": [[-2, -1, 1.85], [2, 1, 2.1]]},
            },
            {
                "op": "bound_seam",
                "target": "Case",
                "name": "Seam",
                "points": [[-0.8, 0, 1.975], [0.8, 0, 1.975]],
            },
            {
                "op": "profile_edit",
                "object": "Case",
                "region": "top",
                "axis": 0,
                "displacement_axis": 2,
                "knots": [[-1.4, 0], [0, 0.03], [1.4, 0]],
            },
            {
                "op": "refresh_seam",
                "target": "Case",
                "object": "Seam",
                "name": "Refreshed",
            },
            {"op": "bezier_tube", "name": "Tube", "controls": controls},
            {
                "op": "activate_candidate",
                "objects": ["Refreshed"],
                "alternatives": ["Seam", "Refreshed"],
            },
            {"op": "restore_candidate"},
        ]
        path = self.root / "recipe.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "success")
        audit = json.loads((self.root / "success/audit.json").read_text())
        self.assertEqual(audit["status"], "complete")
        self.assertTrue((self.root / "success/reference.png").is_file())
        recipe["operations"].append(
            {
                "op": "profile_edit",
                "object": "Case",
                "region": "missing",
                "axis": 0,
                "displacement_axis": 2,
                "knots": [[-1, 0], [0, 0.1], [1, 0]],
            }
        )
        path.write_text(json.dumps(recipe))
        with self.assertRaises(ValueError):
            run(path, self.root / "failure")
        audit = json.loads((self.root / "failure/audit.json").read_text())
        self.assertEqual(audit["status"], "failed")
        self.assertEqual(audit["failed_operation"]["op"], "profile_edit")

    def test_attachment_follow_persistence_and_topology_rejection(self):
        from mesh_workbench import attachments, relief

        plane = m.primitive("plane", "Target")
        dots = relief.dots(
            plane,
            [[0.2, 0.3, 1]],
            "Dots",
            radii=0.04,
            direction=[0, 0, -1],
            max_distance=2,
        )
        old = s.coordinates(dots).copy()
        attachments.bind_relief(plane, dots)
        binding = json.loads(dots["mw_surface_binding"])
        np.testing.assert_allclose(
            attachments.resolve(plane, binding)[0]["position"], [0.2, 0.3, 0], atol=1e-6
        )
        plane.location.z = 0.5
        plane.scale.y = 1.5
        bpy.context.view_layer.update()
        self.assertEqual(attachments.status(plane, dots)["status"], "needs_refresh")
        np.testing.assert_allclose(
            attachments.resolve(plane, binding)[0]["position"],
            [0.2, 0.45, 0.5],
            atol=1e-6,
        )
        refreshed = attachments.refresh_relief(plane, dots, "Refreshed")
        self.assertEqual(attachments.status(plane, refreshed)["status"], "current")
        np.testing.assert_array_equal(old, s.coordinates(dots))
        np.testing.assert_allclose(
            np.array(refreshed["mw_relief_anchors"]), [0.2, 0.45, 0.5], atol=1e-6
        )
        saved = self.root / "bound.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(saved))
        bpy.ops.wm.open_mainfile(filepath=str(saved), load_ui=False, use_scripts=False)
        plane = bpy.data.objects["Target"]
        dots = bpy.data.objects["Dots"]
        refreshed = bpy.data.objects["Refreshed"]
        self.assertEqual(attachments.status(plane, refreshed)["status"], "current")
        saved_coords = [v.co.copy() for v in plane.data.vertices]
        ids = json.loads(refreshed["mw_surface_binding"])["anchors"][0]["vertices"]
        for i in ids:
            plane.data.vertices[i].co = [0, 0, 0]
        self.assertEqual(attachments.status(plane, refreshed)["status"], "incompatible")
        for v, co in zip(plane.data.vertices, saved_coords):
            v.co = co
        changed = g.edit_topology(
            plane, g.selection(plane, "FACE"), "subdivide", "Changed", cuts=1
        )
        plane.data = changed.data.copy()
        self.assertEqual(attachments.status(plane, refreshed)["status"], "incompatible")
        count = len(bpy.data.objects)
        with self.assertRaises(ValueError):
            attachments.refresh_relief(plane, refreshed, "Invalid")
        self.assertEqual(count, len(bpy.data.objects))
        np.testing.assert_array_equal(old, s.coordinates(dots))

    def test_attachment_recipe_dispatch(self):
        from mesh_workbench.runner import run

        recipe = {
            "version": 1,
            "operations": [
                {"op": "primitive", "kind": "plane", "name": "Target"},
                {
                    "op": "relief_dots",
                    "target": "Target",
                    "name": "Dots",
                    "points": [[0, 0, 1]],
                    "options": {"direction": [0, 0, -1], "max_distance": 2},
                },
                {"op": "bind_relief", "target": "Target", "object": "Dots"},
                {
                    "op": "transform",
                    "object": "Target",
                    "transform": {"location": [0, 0, 0.3]},
                },
                {"op": "attachment_status", "target": "Target", "object": "Dots"},
                {
                    "op": "refresh_relief",
                    "target": "Target",
                    "object": "Dots",
                    "name": "Updated",
                },
                {"op": "attachment_status", "target": "Target", "object": "Updated"},
            ],
        }
        path = self.root / "attachments.json"
        path.write_text(json.dumps(recipe))
        run(path, self.root / "result")
        audit = json.loads((self.root / "result" / "audit.json").read_text())
        self.assertEqual(audit["operations"][4]["result"]["status"], "needs_refresh")
        self.assertEqual(audit["operations"][6]["result"]["status"], "current")
        self.assertAlmostEqual(
            bpy.data.objects["Updated"]["mw_relief_anchors"][2], 0.3, places=6
        )

    def test_material_assignment_isolates_shared_meshes(self):
        from mesh_workbench import materials

        a = m.primitive("cube", "A")
        materials.assign([a], "Old", [0.1, 0.2, 0.3, 1])
        b = a.copy()
        b.data = a.data
        bpy.context.collection.objects.link(b)
        materials.assign([a], "New", [0.7, 0.4, 0.2, 0.5], roughness=0.25)
        self.assertNotEqual(a.data, b.data)
        self.assertEqual(b.data.materials[0].name, "Old")
        shader = a.data.materials[0].node_tree.nodes.get("Principled BSDF")
        self.assertAlmostEqual(shader.inputs["Alpha"].default_value, 0.5)
        before = set(bpy.data.materials)
        with self.assertRaises(ValueError):
            materials.assign([a], "Invalid", [2, 0, 0, 1])
        self.assertEqual(before, set(bpy.data.materials))
        self.assertEqual(a.data.materials[0].name, "New")

    def test_extended_recipe_success_and_failure_audits(self):
        from mesh_workbench.runner import run

        recipe = {
            "version": 1,
            "camera": {"size": [32, 32]},
            "operations": [
                {
                    "op": "rounded_box",
                    "name": "Case",
                    "dimensions": [1, 1, 1],
                    "options": {"radius": 0.1, "location": [-3, 0, 0]},
                },
                {
                    "op": "revolve",
                    "name": "Ring",
                    "profile": [[0.2, 0], [0.3, 0], [0.3, 0.1], [0.2, 0.1]],
                    "options": {"closed": True},
                },
                {
                    "op": "strut",
                    "name": "Strut",
                    "start": [1, 0, 0],
                    "end": [1, 0, 1],
                    "options": {"radius": 0.1},
                },
                {
                    "op": "sweep",
                    "name": "Sweep",
                    "centers": [[2, 0, 0], [2, 0, 1], [2.2, 0, 1.5]],
                    "radii": [[0.1, 0.1]] * 3,
                },
                {
                    "op": "primitive",
                    "kind": "sphere",
                    "name": "Ball",
                    "location": [4, 0, 0],
                },
                {
                    "op": "fair",
                    "object": "Ball",
                    "center": [4, 0, 1],
                    "radius": 0.8,
                    "options": {"iterations": 2, "positive": 0.1, "negative": -0.11},
                },
                {
                    "op": "primitive",
                    "kind": "plane",
                    "name": "Pad",
                    "location": [0, 0, 2],
                },
                {
                    "op": "relief_dots",
                    "target": "Pad",
                    "name": "Dots",
                    "points": [[0, 0, 3]],
                    "options": {"direction": [0, 0, -1], "max_distance": 2},
                },
                {
                    "op": "material",
                    "name": "Red",
                    "objects": ["Case", "Dots"],
                    "color": [0.4, 0.1, 0.1, 1],
                    "options": {"metallic": 0.3},
                },
                {"op": "visible", "objects": ["Pad"], "value": False, "viewport": True},
                {"op": "diagnose", "object": "Dots"},
                {"op": "capture", "name": "map", "render": False},
            ],
        }
        path = self.root / "recipe.json"
        path.write_text(json.dumps(recipe))
        output = self.root / "success"
        run(path, output)
        audit = json.loads((output / "audit.json").read_text())
        self.assertEqual(audit["status"], "complete")
        self.assertEqual(len(audit["operations"]), len(recipe["operations"]))
        diagnostic = audit["operations"][-2]["result"]
        self.assertEqual(len(diagnostic["components"]), 1)
        self.assertEqual(diagnostic["nonmanifold_edges"], 0)
        bpy.ops.wm.open_mainfile(
            filepath=str(output / "result.blend"), load_ui=False, use_scripts=False
        )
        self.assertEqual(bpy.data.objects["Case"].data.materials[0].name, "Red")
        self.assertTrue(bpy.data.objects["Pad"].hide_get())
        self.assertAlmostEqual(bpy.data.objects["Strut"].dimensions.z, 1, places=6)
        self.assertTrue((output / "map" / "surface.npz").is_file())
        recipe["operations"].append(
            {
                "op": "relief_dots",
                "target": "Pad",
                "name": "Rejected",
                "points": [[0, 0, 3], [0, 0, 3]],
                "options": {"direction": [0, 0, -1], "max_distance": 2},
            }
        )
        path.write_text(json.dumps(recipe))
        failed = self.root / "failed"
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with self.assertRaises(ValueError):
            run(path, failed)
        audit = json.loads((failed / "audit.json").read_text())
        self.assertEqual(audit["status"], "failed")
        self.assertEqual(
            audit["failed_operation"],
            {"index": len(recipe["operations"]) - 1, "op": "relief_dots"},
        )
        self.assertNotIn("Rejected", bpy.data.objects)
        self.assertFalse((failed / "result.blend").exists())

    def test_conforming_relief_geometry_and_failures(self):
        from mesh_workbench import relief, fairing

        plane = m.primitive("plane", "Target")
        before = s.coordinates(plane).copy()
        dots = relief.dots(
            plane,
            [[-0.3, 0, 1], [0.3, 0, 1]],
            "Dots",
            radii=0.08,
            height=0.004,
            embed=0.002,
            direction=[0, 0, -1],
            max_distance=2,
        )
        self.assertEqual(len(fairing.components(dots)), 2)
        self.assertEqual(g.inspect(dots)["nonmanifold_edges"], 0)
        coords = s.coordinates(dots)
        self.assertAlmostEqual(float(coords[:, 2].max()), 0.0045, places=6)
        self.assertAlmostEqual(float(coords[:, 2].min()), -0.002, places=6)
        self.assertGreater(dots["mw_relief_sampled_clearance"], 0)
        np.testing.assert_array_equal(before, s.coordinates(plane))
        count = len(bpy.data.objects)
        for pts in [[[0, 0, 1], [0.03, 0, 1]], [[0.98, 0, 1]], [[5, 0, 1]]]:
            with self.assertRaises(ValueError):
                relief.dots(
                    plane, pts, "Bad", radii=0.1, direction=[0, 0, -1], max_distance=2
                )
            self.assertEqual(len(bpy.data.objects), count)
        sphere = m.primitive("sphere", "Sphere")
        with self.assertRaises(ValueError):
            relief.dots(
                sphere,
                [[0, 0, 2]],
                "Coarse",
                radii=0.5,
                rings=1,
                clearance=0.00001,
                direction=[0, 0, -1],
                max_distance=2,
            )
        self.assertNotIn("Coarse", bpy.data.objects)
        curved = relief.dots(
            sphere,
            [[0, 0, 2]],
            "Curved",
            radii=0.06,
            rings=4,
            clearance=0.002,
            direction=[0, 0, -1],
            max_distance=2,
        )
        self.assertEqual(g.inspect(curved)["nonmanifold_edges"], 0)
        self.assertGreater(curved["mw_relief_sampled_clearance"], 0)

    def test_local_fairing_and_intersection_diagnostics(self):
        from mesh_workbench import fairing

        plane = m.primitive("plane", "Base")
        grid = g.edit_topology(
            plane, g.selection(plane, "FACE"), "subdivide", "Grid", cuts=12
        )
        for v in grid.data.vertices:
            v.co.z = 0.15 * np.sin(v.co.x * 13) * np.sin(v.co.y * 13)
        before = s.coordinates(grid)
        result = fairing.region(grid, [0, 0, 0], 1.2, iterations=12)
        after = s.coordinates(grid)
        self.assertLess(float(after[:, 2].std()), float(before[:, 2].std()))
        pinned = (np.abs(before[:, 0]) > 0.99) | (np.abs(before[:, 1]) > 0.99)
        np.testing.assert_array_equal(before[pinned], after[pinned])
        s.set_layer(grid, result["layer"], 0)
        np.testing.assert_allclose(s.coordinates(grid), before, atol=1e-6)
        s.set_layer(grid, result["layer"], 1)
        np.testing.assert_allclose(s.coordinates(grid), after, atol=1e-6)
        self.assertEqual(fairing.components(grid), [len(before)])
        keys = len(grid.data.shape_keys.key_blocks)
        for kw in [{"iterations": 0}, {"positive": 1.1}, {"negative": 0.1}]:
            with self.assertRaises(ValueError):
                fairing.region(grid, [0, 0, 0], 1, **kw)
        with self.assertRaises(ValueError):
            fairing.region(grid, [30, 0, 0], 0.1)
        self.assertEqual(len(grid.data.shape_keys.key_blocks), keys)
        mesh = bpy.data.meshes.new("Crossing")
        mesh.from_pydata(
            [
                (-1, 0, 0),
                (1, 0, 0),
                (0, 1, 0),
                (0, 0.3, -1),
                (0, 0.3, 1),
                (0.5, 0.3, 0),
            ],
            [],
            [(0, 1, 2), (3, 4, 5)],
        )
        ob = bpy.data.objects.new("Crossing", mesh)
        bpy.context.collection.objects.link(ob)
        self.assertEqual(fairing.overlap_candidates(ob), 1)
        self.assertEqual(fairing.components(ob), [3, 3])
        self.assertEqual(fairing.overlap_candidates(plane), 0)

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
