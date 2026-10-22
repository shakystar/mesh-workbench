"""Original procedural stroke numerals projected onto one surface chart."""

import json

import numpy as np

from . import sculpt, surfacedetail

STROKES = {
    "a": [(0.15, 1), (0.85, 1)],
    "b": [(1, 0.85), (1, 0.6)],
    "c": [(1, 0.4), (1, 0.15)],
    "d": [(0.15, 0), (0.85, 0)],
    "e": [(0, 0.15), (0, 0.4)],
    "f": [(0, 0.6), (0, 0.85)],
    "g": [(0.15, 0.5), (0.85, 0.5)],
    "r": [(0.1, 0.05), (0.8, 0.5), (0.1, 0.95)],
    "l": [(0.9, 0.05), (0.2, 0.5), (0.9, 0.95)],
}
DIGITS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgecd",
    "7": "abc",
    "8": "abcdefg",
    "9": "abfgcd",
    "-": "g",
    ">": "r",
    "<": "l",
}


def surface_marking(
    source,
    name,
    text,
    origin,
    horizontal,
    vertical,
    query,
    size=3,
    tracking=0.3,
    width=0.12,
    height=0.025,
    **projection,
):
    if (
        not isinstance(text, str)
        or not 1 <= len(text) <= 8
        or any(char not in DIGITS for char in text)
    ):
        raise ValueError(
            "Markings support 1..8 procedural digits, minus signs or arrows"
        )
    frame = np.asarray([origin, horizontal, vertical], dtype=float)
    if frame.shape != (3, 3) or not np.isfinite(frame).all():
        raise ValueError("Finite marking frame required")
    origin, horizontal, vertical = frame
    if not np.allclose(frame[1:] @ frame[1:].T, np.eye(2), atol=1e-7):
        raise ValueError("Orthonormal marking axes required")
    size = sculpt.number(size, 0.1, 100, "marking size")
    tracking = sculpt.number(tracking, 0.1, 2, "tracking")
    width = sculpt.number(width, 0.01, size * 0.09, "stroke width")
    height = sculpt.number(height, 0.001, size * 0.1, "marking height")
    paths = []
    for i, char in enumerate(text):
        for segment in DIGITS[char]:
            paths.append(
                {
                    "points": [
                        (
                            origin
                            + horizontal * (x + i * (1 + tracking)) * size
                            + vertical * y * size
                        ).tolist()
                        for x, y in STROKES[segment]
                    ]
                }
            )
    if set(projection) - {"projection_axis", "side", "max_distance"}:
        raise ValueError("Unknown marking projection option")
    settings = json.dumps(
        {
            "schema": 1,
            "text": text,
            "origin": origin.tolist(),
            "horizontal": horizontal.tolist(),
            "vertical": vertical.tolist(),
            "size": size,
            "tracking": tracking,
            "width": width,
            "height": height,
            "query": query,
            "projection": projection,
        },
        allow_nan=False,
    )
    result = surfacedetail.paths(
        source,
        name,
        query,
        paths,
        width=width,
        height=height,
        embed=min(height / 2, 0.01),
        spacing=max(0.05, size / 12),
        cross_samples=4,
        **projection,
    )
    result["mw_marking"] = settings
    return result
