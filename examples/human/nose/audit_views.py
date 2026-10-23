"""Read-only views of the current procedural nose; never saves the input blend."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0, str(ROOT/'src'))
from mesh_workbench.runner import camera


def run(source, output, only=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Use a fresh output folder')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    assert not bpy.data.objects['Surface brushed nose'].hide_render
    output.mkdir(parents=True)
    scene = bpy.context.scene
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    views = [
        ('front', (0, -4, 1.63), (0, -.075, 1.63), .11),
        ('profile', (4, -.075, 1.63), (0, -.075, 1.63), .11),
        ('basal', (0, -1.5, .05), (0, -.078, 1.613), .105),
    ]
    if only:
        if only not in {v[0] for v in views}:
            raise ValueError('Unknown view')
        views = [v for v in views if v[0] == only]
    for name, position, target, scale in views:
        camera(position=position, target=target, scale=scale, size=(560, 560))
        scene.cycles.samples = 16
        scene.cycles.use_denoising = True
        scene.render.filepath = str(output/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    (output/'manifest.json').write_text(json.dumps({
        'source_sha256': digest, 'object': 'Surface brushed nose',
        'blender': bpy.app.version_string, 'source_unchanged': True,
        'views': views, 'scope': 'Visual structural audit; no anatomical fit measurement',
    }, indent=2), encoding='utf-8')
    print('READ_ONLY_NOSE_AUDIT_COMPLETE', flush=True)


if __name__ == '__main__':
    run(*sys.argv[sys.argv.index('--')+1:])
