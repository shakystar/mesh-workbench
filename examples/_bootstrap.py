"""Shared imports for repository examples stored in topic/task folders."""
import sys


def configure(root):
    folders={p.parent for p in (root/'examples').rglob('*.py')}
    paths=[str(root/'src'),*(str(p) for p in sorted(folders))]
    sys.path[:0]=[p for p in paths if p not in sys.path]
