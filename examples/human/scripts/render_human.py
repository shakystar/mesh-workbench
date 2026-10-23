"""Render the included procedural human's current native result, without edits."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import sys
from pathlib import Path
import bpy
ROOT=_WORKSPACE
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench.runner import camera

def run(source,output):
    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    for view,pos in [('front',(0,-4,1.63)),('three-quarter',(3,-4,1.65))]:
        camera(position=pos,target=(0,0,1.63),scale=.34,size=(900,900))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str((folder/(view+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    print('HUMAN_PREVIEW_COMPLETE',flush=True)

if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
