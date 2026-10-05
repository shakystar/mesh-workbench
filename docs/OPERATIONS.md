# Recipe operations (version 1)

Top-level fields: `version: 1`, optional `source` (`.blend` relative to the recipe), optional `camera`, and ordered `operations`. The runner creates a new output directory and preserves source files. Object names identify existing scene objects. New names must be unused.

| Operation | Required fields | Optional fields / behavior |
|---|---|---|
| primitive | kind, name | location, scale, options; cube/sphere/plane/cylinder |
| rounded_box | name, dimensions | options: location, radius, segments; full world-unit dimensions |
| revolve | name, profile | options: segments, closed, location; positive radius/Z profile |
| strut | name, start, end | options: radius, segments; world-space endpoints |
| sweep | name, centers, radii | options: segments, reference; one elliptical radius pair per center |
| fair | object, center, radius | options: iterations, positive, negative, label; reversible layer, rejects detected overlaps |
| relief_dots | target, points, name | options: radii, height, embed, segments, rings, max_distance, direction, gap, clearance |
| bind_relief | target, object | options: max_distance; store anchors before deforming a static baked target |
| attachment_status | target, object | current / needs_refresh / incompatible |
| refresh_relief | target, object, name | options: max_distance; new pattern, retained radii/material, original preserved |
| diagnose | object | evaluated mesh counts, component sizes and nonadjacent overlap candidates |
| material | objects, name, color | options: metallic, roughness; new named Principled material, replaces target slots |
| load_blend | path, objects | prefix; append named objects from another file |
| load_mesh | path | prefix; OBJ/STL/PLY/glTF/GLB |
| transform | object, transform | location/rotation (Euler radians)/scale |
| duplicate | object, name | evaluated mesh fork |
| bake | object | explicitly collapses modifiers/keys on that object; duplicate first to retain history |
| combine | objects, name | voxel: world-space voxel size; omitted means plain join |
| boolean | left, right, operation, name | operation UNION/DIFFERENCE/INTERSECT |
| blend | left, right, name | weight in [0,1]; same indexed topology |
| select | object, name | selection: domain VERT/EDGE/FACE, indices, box, sphere, grow |
| move | object, selection, delta | label; world-space vector, independent layer |
| mesh_edit | object, selection, operation, name | options, listed below; always a new object |
| inspect | object | counts, bounds, boundary/nonmanifold edges, finite geometry |
| mesh_export | object, name | output subdirectory with mesh.npz and mesh.json |
| camera | camera | position, target, scale, size |
| light | name, position | target, energy, size; area light |
| visible | objects, value | changes render visibility; viewport: true also updates viewport hiding |
| capture | name | render (default true); paired PNG and dense arrays |
| views | name, views | render; views contain name/position/target/scale/size |
| activate_map | map | restores a captured camera, still checks geometry on subsequent use |
| query | map | pixels; summarized map data |
| mask | map, command | object/name/pixels/radius; hard, invert, metric |
| stroke | map, command | object/mode/points/radius; see below |
| layer | object, layer, value | value in [0,1] |
| project | target, points | options: max_distance, offset, direction |
| conform | object, selection, target, name | same projection options; new mesh |
| seam | target, points, name | options: radius, spacing, offset, max_distance |
| scatter | target, motif, points, name | options: scale, offset, max_distance, minimum_spacing |
| uv | object | name; world-Z cylindrical unwrap |
| weave | object, uv | options: frequency, depth, RGBA color; replaces material slots explicitly |
| checkpoint | name | save new .blend under the run directory |

Mesh-edit options: subdivide `cuts` (1..16); extrude world `delta` (FACE); inset local `thickness` (FACE); bevel local `offset` and `segments` (EDGE); weld local `distance` (VERT); delete by the selection domain; triangulate (FACE). Selection queries combine indices, box and sphere by intersection. Vertex `grow` follows edge adjacency.

Stroke modes: grab/pinch/smooth/normal. Points are top-left render pixels. Optional fields: `label`, per-point `pressures`, `strength`, pixel `spacing`, `metric` (geodesic/sphere), `mask`, `symmetry_x`, `symmetry_plane`, and signed world `distance` for normal strokes. Re-capture after edits; stale maps are rejected. Grab may end outside the object because it latches the first surface point.

Names used as output subpaths must remain inside the run directory. Recipes do not run arbitrary Python, but asset loading is not a security sandbox: use trusted local inputs. Rendering uses Cycles CPU by default for reproducible headless operation; no GPU is required.

An example operation:

```json
{"op":"mesh_edit","object":"Block","selection":"top","operation":"extrude","name":"Tower","options":{"delta":[0,0,0.8]}}
```

See [DESIGN.md](DESIGN.md) for units, correspondence, remeshing and pattern limitations.

## Integrated construction example

`examples/field-speaker.json` builds a complete procedural product study through the host CLI. It uses dimensioned shells, boolean apertures, revolved drivers, a swept handle, surface relief controls, materials, diagnostics and two paired render/coordinate captures.

```sh
mesh-workbench run examples/field-speaker.json --output runs/speaker
```

Construction/fairing/relief parameter limits are enforced by their Python APIs. New object and material names must be unused. `material` validates all targets before assignment and copies shared object data so an unlisted linked object keeps its original material. Color is RGBA in shader space. These are simple Principled materials, not a general node-graph interface.

`diagnose` reports evidence, not a universal quality pass: zero nonadjacent overlap candidates does not cover all adjacent-face folds or mechanical collisions. Relief clearance is sampled. Fairing requires a static baked mesh; rounded-box modifiers can be explicitly collapsed with `bake` when deformation is needed.

Operation exceptions record `failed_operation` (zero-based index and operation name) in `audit.json`. Earlier successful operations remain recorded; the recipe as a whole is not transactional. A failed run is not marked complete and does not receive the final `result.blend`; explicit earlier checkpoints may still exist. The host CLI returns nonzero on failure. Run the CLI in its standard fresh Blender process; direct `runner.run` assumes that process setup and is not an interactive-scene reset API.

## Surface attachments

Create relief with the current tool, then call `bind_relief` before changing the target. Binding stores original triangle vertex IDs and barycentric weights in the pattern object's custom properties. After a topology-preserving deformation or object transform, `attachment_status` reports `needs_refresh`; `refresh_relief` creates a new pattern on the new surface. Hide the old pattern explicitly if the new one is selected.

The binding requires a static baked target. Changed connectivity, a renamed/different target, collapsed triangles or incompatible surface projection require explicit rebinding. This is not automatic retopology correspondence or an animation rig. Fixed world-space radii are retained, and hand edits to the generated motifs are not replayed. Old reliefs without saved generation settings must first be regenerated with the current tool.

`current` reports target revision compatibility, not a general quality certificate for later manual changes to the pattern. Reprojection still uses the relief tool's clearance and spacing checks. Binding and generation settings survive native `.blend` saves.
