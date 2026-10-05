# Design and boundaries

The host CLI launches a fresh background Blender process with factory settings and automatic Python execution disabled. Recipes are trusted local inputs, not a sandbox for untrusted `.blend` files. The package does not change global preferences.

Surface maps use top-left pixel centers. Coordinates/normals are world-space; depth is linear camera depth. Maps represent geometric first hits, not alpha coverage, shader bump normals or antialiased boundaries. Unsupported render/viewport evaluation differences fail rather than silently returning inconsistent data.

Deformation layers are additive deltas relative to Basis. Turning an early layer off keeps later deltas; it does not replay the later strokes. Stroke samples use the initial surface snapshot. Grab latches the first point and uses first-to-last displacement; other modes apply one dab per interpolated point. Denser spacing can therefore increase accumulated deformation.

Edge-path distance approximates a geodesic. It is seeded from the hit polygon to avoid jumping to disconnected nearby sheets. Persistent masks use vertex groups and topology signatures. Selections carry object name and indexed topology signatures; topology changes require reselection. Stable semantic IDs across remeshing are not implemented.

Mesh edits fork evaluated geometry before BMesh operations. Source deformation history survives in the source object; the topology result starts a new editable mesh. Selection transforms and extrusion vectors use world coordinates. Inset, bevel and weld parameters use object-local mesh units; apply/bake the desired scale before these operations when metric consistency is needed.

Join concatenates meshes; it does not weld. Voxel fusion unions overlapping volumes at the supplied resolution and can lose small detail. Exact booleans need suitable solid inputs. Morph blending is linear world-space interpolation with identical indexed topology, not automatic correspondence or retopology.

Projection supports closest-surface and directed ray modes with a maximum distance. Seam samples are projected separately; sparse paths can still cut through very concave surfaces between samples. Motifs use evaluated local coordinates with +Z aligned to each hit normal. The motif object's world transform is intentionally ignored; the scatter scale is explicit. Minimum anchor spacing is not mesh collision detection. No winding-independent orientation or global tangent field is promised.

Cylindrical UVs use world Z and a rear seam; they are not a universal unwrap. Weave is shader relief, while scatter produces actual polygons and seams use beveled curves. UV poles and density distortion require inspection.

All previews use procedural fixtures. Original project-specific assets and machine paths are excluded from the source package.

License background: [Blender licensing](https://www.blender.org/about/license/) and [Blender extension information](https://extensions.blender.org/about/). The repository chooses GPL-3.0-or-later for its code.
