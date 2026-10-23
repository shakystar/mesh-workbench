"""Mesh Workbench: data-driven modeling inside Blender. GPL-3.0-or-later."""

__version__ = "0.1.0"

# Keep public module imports stable across functional source folders.
from pathlib import Path as _Path
__path__.extend(str(_Path(__file__).parent / name) for name in ['anatomy', 'geometry', 'forms', 'mechanisms', 'details', 'workflow'])
