"""Render the included procedural human's current native result, without edits."""
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
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
