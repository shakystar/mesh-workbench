"""Apply KB guide: INPUT.blend OBJECT TARGET.json OUTPUT_DIR (no render)."""
import json
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy_fit


def run(source,name,target,folder):
    folder=Path(folder)
    if folder.exists():raise ValueError('Use a fresh output directory')
    settings=json.loads(Path(target).read_text())
    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    source_obj=bpy.data.objects[name]
    obj,diagram,reports=anatomy_fit.apply(source_obj,settings,'Fitted oral guide')
    # Display the result without coplanar overlap; source geometry and keys survive.
    source_obj.hide_render=True;source_obj.hide_set(True)
    folder.mkdir(parents=True)
    (folder/'diagram.json').write_text(json.dumps(diagram,indent=2))
    (folder/'brush-report.json').write_text(json.dumps(reports,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str((folder/'fitted.blend').resolve()))
    print('ANATOMY_FIT_COMPLETE',obj.name,flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
