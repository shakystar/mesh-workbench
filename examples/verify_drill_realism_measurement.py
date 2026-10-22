"""Analytical checks for the measurement partition and frozen-mask rejection."""

import hashlib
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
from measure_drill_realism import fill_enclosed, mask_from_png, part_proxy


def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=2)
    source = bpy.context.object
    original = np.array([v.co[:] for v in source.data.vertices])
    upper, tree = part_proxy("upper", [source], (1,0))
    points = np.array([v.co[:] for v in upper.data.vertices])
    assert np.allclose(points.min(axis=0), [-1,-1,0])
    assert np.allclose(points.max(axis=0), [1,1,1])
    assert tree.ray_cast(Vector((3,0,.5)), Vector((-1,0,0)))[0] is not None
    assert tree.ray_cast(Vector((3,0,-.5)), Vector((-1,0,0)))[0] is None
    assert np.array_equal(original, np.array([v.co[:] for v in source.data.vertices]))
    mask = np.zeros((16,16), bool)
    mask[2:14,2:14] = True
    mask[5:7,5:7] = False  # Enclosed opening should fill.
    mask[9:11,:6] = False  # Exterior-connected notch must stay open.
    before = mask.copy()
    filled = fill_enclosed(mask)
    assert filled[5:7,5:7].all() and not filled[9:11,:6].any()
    assert np.array_equal(mask, before)
    assert np.array_equal(filled, fill_enclosed(filled))
    path = output.resolve()/"asymmetric-mask.png"
    image = bpy.data.images.new("mask fixture", width=16, height=16, alpha=True)
    data = np.zeros((16,16,4), np.float32)
    data[:,:,3] = 1
    data[2:4,5:8,:3] = 1
    image.pixels.foreach_set(data.ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = data[::-1,:,0] > .5
    assert np.array_equal(mask_from_png(path,digest), expected)
    try:
        mask_from_png(path,"0"*64)
    except ValueError as exc:
        assert "Frozen mask changed" in str(exc)
    else:
        raise AssertionError("Altered mask hash was accepted")
    (output/"verification.txt").write_text("All analytical measurement checks passed\n")
    print("MEASUREMENT_FIXTURE: clip bounds/rays, source preservation, hole policy, PNG orientation and hash rejection passed", flush=True)


if __name__ == "__main__":
    verify(Path(sys.argv[sys.argv.index("--")+1]))
