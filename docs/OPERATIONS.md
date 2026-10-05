# Recipe operations (version 1)

Top-level fields: `version: 1`, optional `source` (`.blend` relative to the recipe), optional `camera`, and ordered `operations`. The runner creates a new output directory and preserves source files. Object names identify existing scene objects. New names must be unused.

| Operation | Required fields | Optional fields / behavior |
|---|---|---|
| primitive | kind, name | location, scale, options; cube/sphere/plane/cylinder |
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
| visible | objects, value | changes render visibility |
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
