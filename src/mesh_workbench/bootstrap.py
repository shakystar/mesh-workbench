"""Blender file entry point, works from source checkout or installed wheel."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mesh_workbench.runner import run
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--recipe", required=True)
parser.add_argument("--output", required=True)
a = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
run(a.recipe, a.output)
