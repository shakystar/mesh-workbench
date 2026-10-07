"""Create authored target sheets before evaluating a generated candidate."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = json.loads((ROOT / "examples/drill-surface-target.json").read_text())
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1100" viewBox="0 0 1400 1100">',
        '<rect width="1400" height="1100" fill="#111b26"/>',
        '<g fill="#eaf2f8" font-family="sans-serif"><text x="35" y="40" font-size="25">DRILL / SURFACE DESIGN 01</text><text x="35" y="68" font-size="14">Authored target envelopes and detail intent - millimetres - not manufacturer drawings</text></g>',
    ]

    def poly(points, color="#e7b45e"):
        return (
            '<polygon points="'
            + " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            + f'" fill="none" stroke="{color}" stroke-width="2"/>'
        )

    profile = spec["envelope"]["profile_xz"]
    # The six views are dimension envelopes, not rounded-mesh pixel masks.
    front = [
        (-14, 43),
        (-16, 85),
        (-15, 110),
        (-23, 145),
        (-27, 165),
        (-25, 180),
        (0, 192),
        (25, 180),
        (27, 165),
        (23, 145),
        (15, 110),
        (16, 85),
        (14, 43),
    ]
    top = [
        (-62, -22),
        (-45, -27),
        (0, -27),
        (47, -23),
        (47, 23),
        (0, 27),
        (-45, 27),
        (-62, 22),
    ]
    for i, name in enumerate(["LEFT", "RIGHT", "FRONT", "REAR", "TOP", "BOTTOM"]):
        ox = 35 + (i % 3) * 455
        oy = 95 + (i // 3) * 330
        svg.append(
            f'<rect x="{ox}" y="{oy}" width="430" height="310" rx="10" fill="#1a2938"/>'
        )
        svg.append(
            f'<text x="{ox + 16}" y="{oy + 28}" fill="white" font-family="sans-serif" font-size="18">{name}</text>'
        )
        pts = profile if i < 2 else front if i < 4 else top
        if i < 4:
            coords = [
                (ox + 210 + (-x if i in (1, 3) else x) * 1.28, oy + 290 - z * 1.28)
                for x, z in pts
            ]
        else:
            coords = [(ox + 220 + x * 2.4, oy + 164 + y * 2.4) for x, y in pts]
        svg.append(poly(coords))
        note = (
            "Sloped crown / finger relief"
            if i < 2
            else "Independent palm and head widths"
            if i < 4
            else "Front taper / crowned side panels"
        )
        svg.append(
            f'<text x="{ox + 16}" y="{oy + 300}" fill="#a8c4d9" font-family="sans-serif" font-size="12">{note}</text>'
        )
    for i, (title, lines) in enumerate(
        [
            (
                "CHUCK + TORQUE",
                [
                    "X 45-60: 18 flutes, 0.8 depth",
                    "X 60-93: 24 flutes, 0.7 depth",
                    "Inner radii >= 14 / 12; 1.2 end chamfer",
                ],
            ),
            (
                "GRIP + TRIGGER",
                [
                    "Broader rubber patch, 0.6 perimeter",
                    "0.4 ribs; preserve contact lands",
                    "Trigger grooves <= 0.3; travel 0-3",
                ],
            ),
            (
                "BATTERY INTERFACE",
                [
                    "Side shrouds move with battery",
                    "Open rear withdrawal / latch window",
                    "Noncontact clearance >= 0.2",
                ],
            ),
        ]
    ):
        x = 35 + i * 455
        y = 785
        svg.append(
            f'<rect x="{x}" y="{y}" width="430" height="255" rx="10" fill="#1a2938"/>'
        )
        svg.append(
            f'<text x="{x + 16}" y="{y + 32}" fill="#e7b45e" font-family="sans-serif" font-size="19">{title}</text>'
        )
        for j, line in enumerate(lines):
            svg.append(
                f'<text x="{x + 16}" y="{y + 65 + j * 24}" fill="white" font-family="sans-serif" font-size="13">{line.replace(">", "&gt;").replace("<", "&lt;")}</text>'
            )
        if i == 0:
            svg.append(
                poly(
                    [
                        (x + 45, y + 205),
                        (x + 45, y + 150),
                        (x + 135, y + 150),
                        (x + 135, y + 158),
                        (x + 330, y + 158),
                        (x + 350, y + 170),
                        (x + 350, y + 205),
                    ]
                )
            )
            for q in range(12):
                svg.append(
                    f'<path d="M{x + 152 + q * 14} {y + 160}v43" stroke="#8197a5"/>'
                )
        elif i == 1:
            svg.append(
                poly(
                    [
                        (x + 110, y + 140),
                        (x + 185, y + 146),
                        (x + 148, y + 235),
                        (x + 80, y + 224),
                    ]
                )
            )
            for q in range(6):
                svg.append(
                    f'<path d="M{x + 115 - q * 4} {y + 157 + q * 11}l42 8" stroke="#8197a5" stroke-width="3"/>'
                )
        else:
            svg.append(
                poly(
                    [
                        (x + 70, y + 230),
                        (x + 70, y + 180),
                        (x + 120, y + 180),
                        (x + 120, y + 145),
                        (x + 290, y + 145),
                        (x + 290, y + 180),
                        (x + 340, y + 180),
                        (x + 340, y + 230),
                    ]
                )
            )
            svg.append(
                f'<path d="M{x + 140} {y + 150}v35h130v-35" fill="none" stroke="#8197a5" stroke-width="3"/>'
            )
    svg.append(
        '<text x="35" y="1074" fill="#a8c4d9" font-family="sans-serif" font-size="13">Envelope guides omit rounded corners and hidden hardware. JSON specification owns exact section fields, pins, cameras and gates.</text></svg>'
    )
    p = ROOT / "docs/assets/drill-surface-target.svg"
    p.write_text("\n".join(svg), encoding="utf-8")
    a = ROOT / "docs/audits/DRILL_SURFACE_BRIEF.json"
    brief = json.loads(a.read_text())
    brief.update(
        {
            "status": "M6 target specification and six-view/detail guide frozen; candidate acceptance pending",
            "guide": "docs/assets/drill-surface-target.svg",
            "guide_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
    )
    a.write_text(json.dumps(brief, indent=2) + "\n")
    print("GUIDES_FROZEN", brief["guide_sha256"])


if __name__ == "__main__":
    main()
