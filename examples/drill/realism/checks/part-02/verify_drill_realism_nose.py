"""Verify the declared recessed chuck-nose sectors without closing jaw slots."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / 'src'))
from mesh_workbench import nested


def verify(source, output):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()), load_ui=False, use_scripts=False)
    state = nested.load()
    obj = bpy.data.objects[state['outputs']['chuck_nose_support']['object']]
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    faces = [list(p.vertices) for p in obj.data.polygons]
    tree = BVHTree.FromPolygons(vertices, faces)
    # Fixed before first nose trial inspection. Exclude the three functional
    # slots by angular bounds, not by deleting individual failed rays.
    samples = []
    for sector in range(3):
        for angle in range(15, 106, 3):
            theta = math.radians(sector * 120 + angle)
            for radius in (6, 7, 8):
                origin = Vector((110, radius * math.cos(theta), 160 + radius * math.sin(theta)))
                hit, normal, face, distance = tree.ray_cast(origin, Vector((-1, 0, 0)), 15)
                samples.append({'sector':sector, 'angle':angle, 'radius':radius,
                                'hit':list(hit) if hit is not None else None,
                                'passed':hit is not None and 96 - 1e-5 <= hit.x <= 98 + 1e-5})
    edge_use = {}
    for face in faces:
        for a,b in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((a,b)))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    finite = all(math.isfinite(c) for v in vertices for c in v)
    nonmanifold = sum(n != 2 for n in edge_use.values())
    report = {'blender':bpy.app.version_string, 'source_sha256':digest,
              'source_preserved':digest == hashlib.sha256(source.read_bytes()).hexdigest(),
              'scope':'279 axial rays through declared nose sectors, radii 6/7/8 mm; functional jaw slots and central bit bore excluded. Separate motion checks required.',
              'rays':len(samples), 'samples':samples, 'finite':finite,
              'nonmanifold_edges':nonmanifold}
    report['passed'] = report['source_preserved'] and finite and nonmanifold == 0 and all(s['passed'] for s in samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('NOSE_SECTORS',report['passed'],len(samples),flush=True)
    if not report['passed']:
        raise ValueError('Declared chuck-nose sector coverage or closed mesh failed')

if __name__ == '__main__':
    verify(*map(Path, sys.argv[sys.argv.index('--')+1:]))
