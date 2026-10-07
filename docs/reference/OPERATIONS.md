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


## Reference-driven precision tools

See [the speaker study](../studies/PRECISION_STUDY.md) and its frozen [target drawing data](../../examples/speaker-target.json).

| Operation | Required fields | Optional fields |
| --- | --- | --- |
| `rounded_panel` | `name`, `dimensions` (X,Y,Z), `corner_radius`, `edge_radius` | `options`: `location`, `segments` (per quarter), `edge_segments` |
| `bezier_tube` | `name`, `controls` (cubic segments, four XYZ controls each) | `options`: `radius`, `samples`, `segments`, `reference` |
| `define_region` | `object`, `name` | `selection`: vertex `indices`, `box`, `sphere`, `grow` |
| `profile_edit` | `object`, `region`, `axis`, `displacement_axis`, `knots` | `options`: `label`, `max_displacement` |
| `bound_seam` | `target`, `points`, `name` | `options`: `radius`, `offset`, `max_distance`, `spacing` |
| `refresh_seam` | `target`, `object`, `name` | None |
| `compare_reference` | `object`, `path` (target JSON), `component` | `supersample` (1..4, resulting axis maximum 1024), `overlay` (new relative PNG) |
| `activate_candidate` | `objects` (selected names), `alternatives` (all affected names) | None |
| `restore_candidate` | None | None |

`rounded_panel` is a closed XZ rounded outline extruded along Y. Outline radius is independent of thickness; edge radius must be smaller than half the thickness and the outline radius. It creates a solid panel, not a hollow shell.

`bezier_tube` requires connected cubic segments with matching tangent directions at joins. It samples a capped section sweep, without guarantees of exact circular arcs, uniform arc-length spacing or collision-free bends.

Named regions survive saves and topology-preserving edits. Vertex membership is fixed; a spatial box is not reevaluated. Changed connectivity is rejected. No remesh transfer or semantic recognition is implied. Profile edits require a single-user static baked mesh. Axes are world XYZ indices 0/1/2. Ordered `[coordinate, displacement]` knots use smoothstep interpolation and must start/end at zero. Outside the knot range the displacement is zero. Only selected vertices move. Vertices at the same input coordinate receive one translation, preserving cross-section differences. Shape-key layers permit undo. Detected nonadjacent triangle overlaps reject and roll back edits; this is not a full collision certificate.

Bound seams are capped meshes swept through sampled surface anchors plus normal offsets. Refresh creates a new seam after topology-preserving deformation and preserves the old one. Use `attachment_status` for revision compatibility. Strong curvature, sparse sampling or extreme deformation may still cause collisions; inspect the resulting mesh.

Target JSON uses `version: 1`, `views`, and `components`. Each view has orthonormal `horizontal`, `vertical`, `direction`, `bounds: [xmin,xmax,ymin,ymax]`, `depth: [near,far]` and `size: [width,height]`. Each component has a `view` and ordered `shapes`: `rounded_rect` (`center`, `size`, `radius`) or `circle` (`center`, `radius`). `subtract: true` removes coverage. Target data is hashed; reports record sampling size. Measurements use one evaluated mesh independently of visibility and occlusion. Empty/clipped masks, incompatible modifiers and excessive boundary complexity fail explicitly. PNG colors: gray agreement, orange excess, blue missing.

IoU and symmetric nearest-boundary distances measure sampled silhouette agreement in drawing units, not complete 3D likeness. Increase sampling to distinguish raster-boundary error from geometry error; keep the same resolution across candidates. No photo segmentation, perspective camera calibration or hidden-surface recovery is implemented.

Python `candidates.rank(entries, components, min_iou=0.99, max_boundary=0.012)` requires matching target hashes, matching per-component sampling and complete reports. Entries have `name`, `reports`, `nonmanifold_edges`, `overlap_candidates`. Ranking checks supplied diagnostics and does not change geometry. `activate` changes only the listed alternatives, retaining a visibility snapshot in the scene; `restore` restores it. Shared parts are untouched. Nested transactions and missing objects fail explicitly.

API reference: [Blender BVHTree](https://docs.blender.org/api/current/mathutils.bvhtree.html). Queries use explicit world-space triangles; functionality is verified by executed Blender tests.


## Guide lofts and measured shells

See the [six-milestone mouse study](../studies/MOUSE_STUDY.md), full [Python example](../../examples/mouse_study.py), and [ordinary JSON recipe](../../examples/mouse-shell.json).

| JSON operation | Required fields | Optional fields |
| --- | --- | --- |
| `guide_loft` | `name`, `sections` | `options`: `seam_height`, `tilt`, `rows`, `segments`, `end_refinement` |
| `radial_edit` | `object`, `region`, `center`, `radius`, `delta` | `options`: `label` |
| `extract_shell` | `object`, `selection` (existing named FACE selection), `name` | `options`: `thickness`, `trim` |
| `measure_thickness` | `object`, `name` (measurement key) | `options`: `minimum`, `maximum`, `method` (`nearest` or `normal`) |
| `measure_gap` | `left`, `right`, `name` (measurement key) | `options`: `minimum`, `maximum` |
| `mark_violations` | `measurement`, `name` | `options`: `radius`, `limit` |
| `section` | `object`, `axis`, `value` | `expected_bounds`: ordered min/max XYZ vectors |
| `intersection_candidates` | `left`, `right` | None |

`guide_loft` creates a closed asymmetric ring loft. Each ordered section has `y`, positive interior `left`/`right` half-widths, `top`, `bottom`. End poles require zero widths and top/bottom equal to `seam_height`. Squared radii use shape-preserving cubic Hermite interpolation. The cross section has a smooth asymmetric lateral mapping and a normalized upper tilt. This is a bounded loft family, not arbitrary NURBS fitting or global curvature optimization. Angular `segments` must be divisible by four. `end_refinement` blends uniform Y sampling (0) and cosine sampling (1); default 0.5. Nearly identical guide/sample rows snap to the exact guide. More sampling does not guarantee a valid offset shell.

`radial_edit` applies frozen smooth radial weights to an existing named vertex region. It requires a single-user static mesh, preserves all unselected coordinates and adds an independently toggleable layer. Zero influence and detected introduced overlaps fail explicitly. The mouse retains a thumb layer enabled and a separate palm trial disabled.

`extract_shell` preserves its master and creates a closed, independent snapshot of a face patch. Boundary loops must be disjoint and manifold. Trim displacement spreads through a geodesic collar and projects to the master; interpolated normals define the inner offset. Reversed outer edges/cells and detected nonadjacent overlaps fail. Rejected outputs are removed without changing the source. Full arbitrary concave offsetting is not promised. Source edits require explicit regeneration, not an automatic feature-tree update.

`measure_thickness` samples triangle centroids on the recorded outer skin against the actual inner mesh. Default `nearest` reports shortest opposite-skin distances; `normal` shoots geometric face-normal rays. The latter can miss the finite inner patch by exiting a rim, and such misses remain failed samples. Reports always include the method, min/max/mean, sample and miss counts, pass flag, and every violating coordinate. This is a sampled opposite-skin gauge, not a continuous minimum-thickness proof or rim-thickness measurement. It does not simply return the construction's nominal thickness.

`measure_gap` requires patches from the same indexed master. It finds their shared source boundary edges and samples both directions at endpoints and midpoints, measuring nearest distance to the opposite corresponding edge. It checks outer trim boundaries, not every interior clearance. Reports retain all violating coordinates. `mark_violations` creates native octahedral location markers, bounded by `limit`; it fails if there are no violations.

A measurement returning `passed: false` is a completed measurement, not a runner exception. Callers must check the flag before accepting a candidate. Invalid inputs, stale topology, or invalid shell construction throw and mark the recipe audit failed. Changed connectivity invalidates stored shell gauge metadata.

`section` intersects evaluated triangles with a world-coordinate plane (axis 0/1/2). It returns line segments and XYZ bounds, or compares bounds with `expected_bounds`. A missed/coplanar section fails rather than returning an empty success. Section bounds do not by themselves constrain the whole contour.

`intersection_candidates` reports cross-object triangle pairs without excluding contacts. It does not detect full containment without a surface crossing. Use it alongside shell gauges and visual review; intentionally embedded relief bottoms are a different contact class.

Reference drawings also support `polygon` shapes with finite XY `points` (3..4096). Ordered simple polygons use even-odd filling. Candidate rows can include a nonnegative integer `constraint_violations`; nonzero counts reject otherwise high-overlap candidates. The mouse uses this for section constraints.


## Persisted assemblies and motion inspection

All commands execute inside Blender. Register existing **static, unparented, unconstrained meshes** with matching generation recipes. One graph is stored per scene in `mw_assembly_graph`; registration replaces the previous graph. Object names are stable IDs. Renames, external coordinate edits, animation and indexed topology changes are rejected; register again explicitly after intentional external edits.

| JSON operation | Required fields | Result |
| --- | --- | --- |
| `assembly_register` | `name`, `nodes`; optional `checks` | Validated persisted dependency graph |
| `assembly_status` | none | Revision, node count, dependency order |
| `assembly_update` | `source` node ID, `edit` | Updated/unchanged node IDs and constraint reports |
| `assembly_validate` | none | Actual geometry measurements for registered checks |
| `motion_inspect` | `object`, `obstacles`; optional `options` | Discrete overlap/clearance results; transform restored exactly |

Python equivalents are `assembly.register`, `assembly.status`, `assembly.update`, `assembly.validate(assembly.load())`, and `motion.inspect`. See [assembly-basic.json](../../examples/assembly-basic.json) for CLI syntax and [assembly_mouse.py](../../examples/assembly_mouse.py) for the full nine-node model.

Each node has `object`, `kind`, and (except a source) `deps`. The first dependency is its generating surface. Additional dependencies conservatively invalidate the node when their coordinates change.

- `source`: editable input mesh; updates add a reversible deformation layer.
- `shell`: indexed source `faces`, `options` for thickness and trim.
- `relief`: persistent barycentric `binding`, `options` from `mw_relief_settings`.
- `seam`: persistent `binding`, `options` with radius and offset.
- `anchor`: persistent one-point `binding`, world-space `offset`; translates the existing rigid part while preserving its orientation.

Edits: `{"kind":"dimension","axis":0,"delta":6}` changes the measured world bounding dimension by six scene units; optional `pivot` defaults to the minimum coordinate. `{"kind":"radial","center":[-31,-14,14],"radius":24,"delta":[2,0,0],"normalize_peak":true}` normalizes the strongest sampled displacement to 2 units. Outside vertices remain pinned. Units are Blender scene units; the mouse uses millimeters.

Checks contain `kind`, `nodes` and optional `options`. Supported checks: `thickness`, `gap`, `clearance` (relief top against actual split shell), and `intersection` (triangle overlap candidates). Wall and gap options accept minimum/maximum; relief clearance accepts minimum. Empty checks means **no dimensional acceptance constraints**, not a manufacturing approval.

Updates stage all geometry, enforce unchanged indexed topology, validate, then swap data on the existing output objects. Materials and visibility survive. Previous geometry is retained as hidden `MW revision ...` objects. Errors restore source/outputs/metadata/graph and discard staged data; `assembly.Rejected.report` contains the rejection reason and any measured violations. CLI failures also save this as `audit.json.rejection`. `shells.markers` can turn violation coordinates into native marker geometry. A no-op does not create a revision.

Selective hashes use shell face vertices and adjacent faces; surface details use binding vertices, a nearby footprint and adjacent faces. This is a static same-topology system, not arbitrary remesh correspondence or a background Blender handler. Legacy `attachments.status` uses a conservative whole-surface revision, so it can report `needs_refresh` for an unchanged local attachment after another region moves; assembly-local tracking is separate.

Motion options: `translation`, rotation `axis`/`angle` (radians), optional world `pivot`, `steps` (intervals), `probe_limit` (vertex-distance sampling cap), and `minimum` (sampled clearance threshold). Reports retain every pose, overlap counts, up to 32 overlapping triangle index pairs and moving-triangle centers, and the nearest sampled clearance probe. Triangle centers identify affected faces, not exact contact points. Every pose includes full triangle-overlap candidate detection; distances use sampled moving vertices. No continuous collision or complete-containment guarantee is made. Geometry-inspection `passed:false` is a completed measurement; `assembly_update` raises when a registered constraint fails.


## Surface quality, explicit refinement, paths and hinges

See [headphone-tools.json](../../examples/headphone-tools.json) for runnable JSON and the [headphone study](../studies/HEADPHONE_STUDY.md) for measured native results. Units follow world coordinates; the study uses millimeters.

| Operation | Key inputs | Behavior |
| --- | --- | --- |
| `curvature` | `object`, optional `options.indices` / `attribute` | Evaluated-triangle cotangent mean-curvature magnitudes and interior edge-gradient statistics; optional point attribute |
| `fair_patch` | `object`, named vertex `selection`, `options` | Reversible local correction; pins outside vertices, the selection boundary and mesh boundaries |
| `reflection_bands` | `object`, optional frequency/name | Assigns a diagnostic reflected-view-direction stripe material |
| `refine_faces` | `object`, face `selection`, new `name` | Splits selected evaluated triangles into centroid fans on a new mesh |
| `transfer_selection` | `source`, `target`, named `selection`, new selection `name` | Transfers faces or vertices through explicit provenance |
| `transfer_pattern` | `source`, `target`, bound `pattern`, new `name` | Migrates barycentric anchors and regenerates relief or a bound seam |
| `path_create` | `name`, `centers`, `radii`, `options` | Open transported elliptical sweep or a closed planar loop |
| `path_reshape` | source `object`, new `centers`, new `name` | Rebuilds with the stored radius pairs and matching center count |
| `path_sections` | `object` | Measures ring centers and covariance-derived ellipse radii |
| `ring_bridge` | equal-count `start` / `end` rings and `start_tangent` / `end_tangent` arrays | Cubic Hermite ring transition, optionally capped |
| `joints_register` | `joints` | Stores named groups, axes, world pivots, radian limits and rest matrices |
| `joints_inspect` | angle map `angles`, fixed object names `fixed`, `options` | Samples simultaneous hinge paths and restores input transforms exactly |

Python modules mirror these operations. Additional Python functions: `quality.curvature_material` renders a shared-scale diagnostic color map, `refinement.transfer_binding` transfers raw anchors, `pathmodel.bridge_report` measures endpoint positions/tessellated tangent angles, and `joints.pose` / `joints.restore` provide an absolute pose and its restoration snapshot.

`fair_patch` supports `method="laplacian"` (paired passes) or `method="quadratic"` (weighted local quadratic fits). Options include iterations, strength, reverse Laplacian step, fit radius and maximum displacement. Quadratic neighborhoods are frozen in world space and filtered by normal direction; insufficient or rank-deficient support rejects the edit. Pinned vertices do not move. The operation reports quality changes; smoothing alone is not a guarantee of better shape. Failed post-edit measurement or overlap checks restore the layer state.

Curvature comparisons need matching topology, physical scale and selected region. Mesh boundaries are excluded from summary statistics. The color map defaults to a maximum of 0.1 inverse scene units; it is a diagnostic, not a surface tolerance certificate.

Refinement retains parent-face IDs and sparse vertex weights. Face selections expand to all children. A new vertex joins a vertex selection only if **all** of its contributing source vertices were selected. Named regions follow the same rule. Vertex groups interpolate linearly; registered protection masks update their topology signature. Edge selections have no defined transfer rule and are rejected. Foreign/stale source geometry, masks or provenance are rejected. Inputs and previous bindings stay intact. Existing shape layers, UVs, custom corner attributes, shell metadata and arbitrary modifier history are not transferred to the new output. Assembly graph registration must be explicit after topology changes.

Closed paths require a planar loop and its plane normal as `reference`; duplicate closure points are not included. Open paths use transported frames. `path_reshape` rebuilds from saved section parameters and does not carry arbitrary manual surface edits. A ring bridge interpolates supplied endpoint derivatives; it does not discover or stitch unrelated mesh boundaries automatically. No general self-intersection solver is implied; run geometry diagnostics on outputs.

A hinge entry has `name`, `objects`, `axis`, `pivot` and `limits=[low,high]` in radians, including zero. Objects are static, unparented and unconstrained. An object can belong to only one group. `pose` uses the registered rest matrices, so repeated equal angles are idempotent and cannot silently accumulate beyond the limit. Inspection accepts interval `steps`, a `probe_limit`, and explicit `ignore_pairs` if a known interface must be excluded; the study excludes none. Same-group pairs are not tested. Reports retain per-pose overlapping triangle IDs and nearest sampled clearance probes. This is discrete rigid-group inspection, not a nested rig, continuous collision solver or material deformation simulation.


## Local triangle remeshing

`remesh.remesh(source, face_selection, name, target_length, iterations=3, max_error=0.1, sharp_angle=40)` creates a baked, world-space triangle mesh. It pins boundary/feature vertices, splits long interior edges, collapses short ones after the link condition, and flips diagonals only when the minimum local triangle quality improves. Entire source geometry is triangulated for processing; local edge changes are restricted to selected chart interiors. A sampled bidirectional distance gate and overlap/connectivity checks reject invalid output. Original object and history remain intact.

UV seams in every layer, explicit seam/sharp flags, material discontinuities, angle features and the face-selection boundary define frozen charts. Vertex groups and registered masks transfer by barycentric weights; each UV corner samples its own chart. Material slots and face indices transfer. Other custom attributes and edit history do not transfer. Saved `mw_remesh` JSON contains mapping, source/target revisions, parent classification, fixed vertex pairs and measurement report. Both revisions must match before subsequent migration calls.

- `remesh.transfer_selection(source, target, selection)` supports FACE centroid classification and conservative VERT support membership. EDGE is rejected.
- `remesh.transfer_binding(source, target, binding, max_distance=None)` returns `(binding, report)` after same-chart distance and normal gates. The default distance is the remesh error limit.
- `remesh.transfer_pattern(source, target, pattern, name, max_distance=None)` regenerates supported bound relief or seam geometry.
- `assembly.remesh_source(source_node_id, selection, name, **options)` stages a new source and its direct bound relief/seam/anchor children. It validates constraints before switching graph object references and hiding old objects. Rejection restores graph/visibility and removes staged objects/meshes. Shell and nested topology dependencies are explicitly rejected.

JSON operations are `remesh`, `remesh_selection`, `remesh_pattern` and `assembly_remesh`; see [complete executable recipe](../../examples/local-remesh.json). `remesh` returns an object name plus measurements in the audit. `assembly_remesh` returns updated nodes, actual object names, transfers and constraint results. Same-topology `assembly_update` remains supported afterward.

These tools do not establish a continuous geometric error bound, guarantee mesh-quality convergence, perform UV repacking, or implement general quad retopology. See [drill evidence and limitations](../studies/DRILL_STUDY.md).


## Nested dimensioned assemblies

`nested.initialize(name, nodes, parameters, ranges, checks)` creates a version-2 scene graph. `nested.update(parameters=None, remesh_request=None)` forks affected outputs, validates the entire assembly, then commits object references. `nested.load()` checks geometry, UVs, deform groups, materials and registered correspondence before any update. This graph is independent of the earlier version-1 assembly API.

Each node declares `kind`, `args`, optional `frame`, `material`, `visible`, and `deps=[{"id":"parent","use":"geometry"}]`. A frame-only dependency uses `use="frame"`; it is appropriate only when geometry is independently specified. A value such as `{"param":"grip_width","scale":0.5,"offset":14}` is a bounded scalar expression. No Python expression evaluation or file-load handler is installed. Logical IDs persist; physical object names change per revision. Old geometry remains hidden and recoverable.

Builders include `enclosure`, `hollow`, `partition`, `cut_box`, `cut_cylinder`, `box`, `annulus`, `cylinder`, `prism`, `jaw`, `cage`, `insert`, `relief` and `union`. Checks include opposite-skin `wall`, split-plane `gap`, `clearance` and `semantic`. A remesh request names `part`, a semantic face `query`, and existing `remesh.remesh` options. Parameters and topology updates are separate transactions. Direct external edits invalidate the registered output rather than silently overwriting it.

`semantic.resolve(object, query)` and `semantic.register/named` select face regions by world box, normal, material roles and required connected-component count. Queries are re-resolved after topology changes. Indexed face IDs are not stable identities.

`inserts.create` projects an independently sampled ellipse onto one connected facing surface, transfers named weights and per-corner UV samples, and creates a closed offset patch. Every projection must have support. A selected region crossing a UV chart or material discontinuity is rejected; general seam-aware patch retopology is not implemented. `enclosure.boolean` preserves native Blender deform and corner layers; newly cut surfaces are generated data, not claimed source-face correspondence. Numerical tangent slivers are dissolved at 1e-5 world units before validation.

JSON operations: `nested_initialize`, `nested_status`, `nested_update`, `nested_reconfigure`. `nested.reconfigure(nodes, checks=None)` explicitly revises recipes while preserving the logical ID set; it uses the same staged validation and rollback. Recipe-level `units` accepts `mm`, `cm` or `m` and sets native scene units without rescaling mesh coordinates. The [drill recipe](../../examples/drill-assembly.json) builds the complete assembly and edits its grip width. After running it to `runs/drill-assembly-cli`, the [rejected-edit recipe](../../examples/drill-assembly-rejected.json) loads that saved result and must exit nonzero for an out-of-range width. Inputs are hashed and preserved.

## Prismatic and radial mechanism inspection

`actuators.register(parts, channels, interlocks=None)` records static unparented meshes and rest matrices. Parts map stable IDs to physical object names. A channel declares `limits`, `rest`, `max_step`, and per-part translation `vectors` per unit. Several channels can affect one part, such as latch release and battery translation. Three radial vectors can represent a jaw diameter. Interlocks declare `channel`, `above`, `requires`, and `at_least`.

`actuators.pose(values)` is absolute relative to rest. `actuators.sweep(channel, start, end, pairs, base=None, step=None, contacts=None)` checks explicit cross-part pairs at bounded intervals and always restores initial transform channels. Contacts name a pair, exact channel value, maximum sampled penetration (at most 0.01) and optional maximum separation. No pair is silently ignored. Same rigid-group internal contacts should be documented separately; moving cross-jaw pairs must be included.

Reports combine triangle-overlap candidates and bidirectional vertex/edge/centroid distances. Bounding boxes provide conservative lower bounds for distant probes. Containment uses three ray-parity directions, with float64 solid-angle classification when votes disagree. Remaining ambiguity fails. Distances and penetration are sampled, not continuous collision or global separation proofs. Geometry changes invalidate an actuator registration; register again after rebuilding a graph.

JSON operations: `actuators_register`, `actuators_sweep`. A failed sweep raises a structured rejection in the CLI audit. See the [completed drill evidence](../studies/DRILL_ASSEMBLY_STUDY.md) for current validation status.
