"""Apply paired side-view ear guides after the included eye pass; no render."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from human_eyes import run

if __name__=='__main__':
    run(*sys.argv[sys.argv.index('--')+1:],source_name='Fitted eye guides',
        target_file='human-ear-targets.json',prefix='Ear',filename='fitted-ears.blend',
        scope='Side-surface ear relief; no canal or cartilage thickness. No visual quality validation.')
