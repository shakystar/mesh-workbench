"""Render independent authored envelope drawings, without loading candidate meshes.

These are design guides, not photographs or acceptance results. Part masks are
amodal (hidden parts included); the assembly mask is their union. All dimensions
are millimetres. Run with host Python and NumPy/Pillow.
"""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = _WORKSPACE


def camera_basis(view):
    eye, target = np.asarray(view["position"]), np.asarray(view["target"])
    backward = eye - target
    backward = backward / np.linalg.norm(backward)
    up = np.array([0., 0., 1.])
    if abs(backward @ up) > .999:
        up = np.array([0., 1., 0.])
    right = np.cross(up, backward)
    right /= np.linalg.norm(right)
    up = np.cross(backward, right)
    return right, up, target


def project(points, view, size):
    right, up, target = camera_basis(view)
    local = np.asarray(points) - target
    return np.column_stack((size / 2 + local @ right * size / view["scale"],
                            size / 2 - local @ up * size / view["scale"]))


def depth_mask(sections, view, size):
    """Pixel-center orthographic triangle rasterization; larger depth is nearer."""
    right, up, target = camera_basis(view)
    backward = np.cross(right, up)
    xyz = np.concatenate(sections)
    xy = project(xyz, view, size)
    depth = (xyz-target) @ backward
    n = len(sections[0])
    faces = []
    for i in range(len(sections)-1):
        for j in range(n):
            a, b = i*n+j, i*n+(j+1)%n
            faces.extend(((a, b, b+n), (a, b+n, a+n)))
    # Convex section caps. Interior fan vertices are on the same cap plane.
    for offset in (0, (len(sections)-1)*n):
        faces.extend((offset, offset+j, offset+j+1) for j in range(1, n-1))
    result = np.full((size, size), -np.inf)
    for face in faces:
        p = xy[list(face)]
        lo = np.maximum(0, np.ceil(p.min(axis=0)-.5).astype(int))
        hi = np.minimum(size-1, np.floor(p.max(axis=0)-.5).astype(int))
        if np.any(hi < lo):
            continue
        a, b, c = p
        denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denominator) < 1e-10:
            continue
        y, x = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1].astype(float)
        x, y = x+.5, y+.5
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
        w = 1-u-v
        inside = (u >= -1e-9) & (v >= -1e-9) & (w >= -1e-9)
        d = depth[list(face)]
        local = np.where(inside, u*d[0]+v*d[1]+w*d[2], -np.inf)
        area = result[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        np.maximum(area, local, out=area)
    return result


def rings(design):
    """Explicit authored sections; deliberately independent of enclosure builder."""
    angle = np.linspace(0, 2*np.pi, 128, endpoint=False)
    exponent = design.get("exponent", 2)
    a = np.sign(np.cos(angle))*abs(np.cos(angle))**(2/exponent)
    b = np.sign(np.sin(angle))*abs(np.sin(angle))**(2/exponent)
    result = []
    for station, center, half_a, half_b in design["sections"]:
        if min(half_a, half_b) <= 0:
            raise ValueError("Positive section radii required")
        if design["axis"] == "z":
            result.append(np.column_stack((center + a*half_a, b*half_b,
                                           np.full(len(a), station))))
        elif design["axis"] == "x":
            result.append(np.column_stack((np.full(len(a), station), a*half_a,
                                           center + b*half_b)))
        else:
            raise ValueError("Unsupported guide axis")
    return result


def resolve_parts(guide, target):
    """Resolve the authored side drawing independently of the Blender builders.

    Side outline controls own X/Z; independently authored width stations own Y.
    This prevents contradictory side and multiview briefs before modeling.
    """
    parts = copy.deepcopy(guide["parts"])
    profile = np.asarray(target["authored_side_polygon"], dtype=float).copy()
    t = np.clip((140-profile[:, 1])/40, 0, 1)
    profile[:, 1] -= target["overrides"]["parameters"]["grip_length"]*t*t*(3-2*t)
    trim = target["overrides"]["envelope"]["corner_trim"]
    curve = []
    for i, p in enumerate(profile):
        before, after = profile[i-1]-p, profile[(i+1)%len(profile)]-p
        distance = min(trim, .45*np.linalg.norm(before), .45*np.linalg.norm(after))
        a, c = p+before*distance/np.linalg.norm(before), p+after*distance/np.linalg.norm(after)
        for u in np.linspace(0, 1, 128):
            curve.append((1-u)**2*a+2*(1-u)*u*p+u*u*c)
    curve = np.array(curve)
    following = np.roll(curve, -1, axis=0)
    for design in parts.values():
        if "outline_z_range" not in design:
            continue
        lower = max(design["outline_z_range"][0], curve[:, 1].min()+.001)
        upper = min(design["outline_z_range"][1], curve[:, 1].max()-.001)
        stations = np.linspace(lower, upper, int(np.ceil(upper-lower))+1)
        widths = np.asarray(design["width_stations"])
        rows = []
        for z in stations:
            crossing = (curve[:, 1] > z) != (following[:, 1] > z)
            a, b = curve[crossing], following[crossing]
            x = a[:, 0]+(z-a[:, 1])*(b[:, 0]-a[:, 0])/(b[:, 1]-a[:, 1])
            if len(x) != 2:
                raise ValueError("Authored outline must have exactly two intersections per height")
            rows.append([float(z), float(x.mean()), float(np.ptp(x)/2),
                         float(np.interp(z, widths[:, 0], widths[:, 1]))])
        design["sections"] = rows
    return parts


def generate(target, output, size=768):
    from PIL import Image, ImageDraw

    if output.exists():
        raise ValueError("Use a fresh output directory")
    spec = json.loads(target.read_text(encoding="utf-8"))
    guide_path = target.with_name("drill-realism-guide-sections.json")
    guide = json.loads(guide_path.read_text(encoding="utf-8"))
    parts = resolve_parts(guide, spec)
    output.mkdir(parents=True)
    palette = {"housing": (224, 164, 64), "grip": (90, 116, 137),
               "chuck": (172, 184, 196), "battery": (75, 85, 99),
               "bit": (215, 223, 230), "trigger": (62, 68, 76),
               "direction_switch": (170, 77, 45)}
    manifest = {"schema": 1, "status": "authored proposal; not candidate acceptance",
                "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "sections_sha256": hashlib.sha256(guide_path.read_bytes()).hexdigest(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "mask_semantics": "amodal part envelopes plus depth-tested visible masks; union assembly silhouette",
                "size": [size, size], "views": {}, "candidate_loaded": False}
    panels = []
    for name in spec["comparison"]["primary_views"]:
        view = spec["capture"]["views"][name]
        union = np.zeros((size, size), dtype=bool)
        preview = Image.new("RGB", (size, size), (24, 30, 39))
        records = {}
        depths = {}
        for part, design in parts.items():
            depth = depth_mask(rings(design), view, size)
            depths[part] = depth
            values = np.isfinite(depth)
            mask = Image.fromarray(values.astype(np.uint8)*255)
            if not values.any() or values[[0, -1]].any() or values[:, [0, -1]].any():
                raise ValueError(f"Empty or clipped guide: {name}/{part}")
            union |= values
            path = output / f"{name}-{part}.png"
            mask.save(path)
            records[part] = {"path": path.name, "pixels": int(values.sum()),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        ordered_parts = list(depths)
        stacked = np.stack(list(depths.values()))
        labels = np.argmax(stacked, axis=0)
        np.savez_compressed(output / f"{name}-labels.npz",
                            labels=np.where(union, labels, -1).astype(np.int16),
                            parts=np.array(ordered_parts))
        for index, part in enumerate(ordered_parts):
            visible = union & (labels == index)
            visible_mask = Image.fromarray(visible.astype(np.uint8)*255)
            path = output / f"{name}-{part}-visible.png"
            visible_mask.save(path)
            records[part].update({"visible_path": path.name,
                "visible_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "visible_pixels": int(visible.sum()),
                "occluded_pixels": records[part]["pixels"]-int(visible.sum())})
            preview.paste(palette[part], mask=visible_mask)
        assembly_path = output / f"{name}-assembly.png"
        Image.fromarray(union.astype(np.uint8)*255).save(assembly_path)
        draw = ImageDraw.Draw(preview)
        draw.text((16, 16), f"{name.upper()} / AUTHORED ENVELOPE PROPOSAL", fill="white")
        draw.text((16, 34), "Depth-tested authored parts; no candidate or photo used", fill="white")
        preview.save(output / f"{name}-guide.png")
        panels.append(preview.resize((384, 384)))
        y, x = np.where(union)
        manifest["views"][name] = {"camera": view, "parts": records,
            "assembly_path": assembly_path.name,
            "assembly_sha256": hashlib.sha256(assembly_path.read_bytes()).hexdigest(),
            "assembly_pixels": int(union.sum()),
            "bbox_xyxy": [int(x.min()), int(y.min()), int(x.max()), int(y.max())],
            "authored_landmarks_xy": {key: project([point], view, size)[0].tolist()
                                       for key, point in spec["authored_landmarks"].items()},
            "landmark_visibility": "unclassified; projections are not scored"}
    sheet = Image.new("RGB", (384*3, 384*2), (24, 30, 39))
    for i, panel in enumerate(panels):
        sheet.paste(panel, ((i % 3)*384, (i // 3)*384))
    sheet.save(output / "contact-sheet.png")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({"views": len(panels), "parts_per_view": len(guide["parts"]),
                      "output": str(output), "status": manifest["status"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--target", type=Path, default=ROOT / "examples/drill/realism/recipes/part-01/drill-realism-target.json")
    args = parser.parse_args()
    generate(args.target, args.output)
