"""Host CLI; no bpy import, no global Blender configuration changes."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mesh-workbench")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("recipe", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--blender", default=os.environ.get("BLENDER_BIN", "blender"))
    inspect = sub.add_parser("inspect")
    inspect.add_argument("folder", type=Path)
    inspect.add_argument("--pixel", type=int, nargs=2)
    args = parser.parse_args(argv)
    if args.command == "inspect":
        info = json.loads((args.folder / "surface.json").read_text(encoding="utf-8"))
        if args.pixel is not None:
            try:
                import numpy as np
            except ImportError:
                parser.error("Pixel inspection requires mesh-workbench[analysis]")
            x, y = args.pixel
            if not 0 <= x < info["size"][0] or not 0 <= y < info["size"][1]:
                parser.error("Pixel outside map")
            with np.load(args.folder / "surface.npz") as data:
                ident = int(data["object_id"][y, x])
                info = {"pixel": [x, y], "object": info["objects"].get(str(ident))}
                if ident:
                    info.update(
                        world=data["world"][y, x].tolist(),
                        normal=data["normal"][y, x].tolist(),
                        depth=float(data["depth"][y, x]),
                        face=int(data["face_id"][y, x]),
                    )
        print(json.dumps(info, indent=2))
        return 0
    recipe = args.recipe.resolve()
    output = args.output.resolve()
    if not recipe.is_file():
        parser.error("Recipe file does not exist")
    if output.exists():
        parser.error("Output directory already exists")
    executable = shutil.which(args.blender)
    if executable is None:
        parser.error("Blender executable not found; use --blender or BLENDER_BIN")
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_name(output.name + ".log")
    if log.exists():
        parser.error("Log already exists")
    command = [
        executable,
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python-exit-code",
        "2",
        "--python",
        str(Path(__file__).with_name("bootstrap.py")),
        "--",
        "--recipe",
        str(recipe),
        "--output",
        str(output),
    ]
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    audit_path = output / "audit.json"
    audit = (
        json.loads(audit_path.read_text(encoding="utf-8"))
        if audit_path.exists()
        else {}
    )
    success = (
        process.returncode == 0
        and audit.get("status") == "complete"
        and (output / "result.blend").is_file()
    )
    print(
        json.dumps(
            {
                "status": "complete" if success else "failed",
                "exit_code": process.returncode,
                "output": str(output),
                "log": str(log),
            }
        )
    )
    return 0 if success else 1
