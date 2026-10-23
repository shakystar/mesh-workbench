"""Round four fingertip caps per hand with saved-model evidence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fingers import run
if __name__=='__main__':
    run(*sys.argv[sys.argv.index('--')+1:],source_name='Finger contour study',
        result_name='Rounded fingertip study',profile='caps',native_name='rounded-caps.blend')
