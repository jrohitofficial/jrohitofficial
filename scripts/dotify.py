#!/usr/bin/env python3
"""
dotify.py - turn a photo into dot-matrix / binary-grid art as an SVG.

Usage
-----
    python scripts/dotify.py me.jpg -o assets/portrait
    python scripts/dotify.py me.jpg -o assets/portrait --mode binary --cols 64
    python scripts/dotify.py me.jpg -o assets/portrait --circle --animate --color

Writes <out>-dark.svg and <out>-light.svg so the README can swap them with
<picture> + prefers-color-scheme. Also writes <out>.txt for the text modes.

Modes
-----
  dots    halftone: one circle per cell, radius scales with brightness
  binary  a grid of 0/1 glyphs, opacity scales with brightness
  ascii   plain ASCII ramp -> .txt (paste inside a ``` code block)
  braille unicode braille blocks -> .txt (4x denser than ascii)
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  python -m pip install Pillow")


# --------------------------------------------------------------------------- #
# themes
# --------------------------------------------------------------------------- #

THEMES = {
    # name: (foreground, dim-foreground, background-or-None)
    "dark": ("#39d353", "#0e4429", None),
    "light": ("#216e39", "#aceebb", None),
}

ASCII_RAMP = "@%#*+=-:. "  # dark -> light
BRAILLE_BASE = 0x2800
# bit order for a 2x4 braille cell: (col, row) -> dot bit
BRAILLE_BITS = [[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]]


# --------------------------------------------------------------------------- #
# image prep
# --------------------------------------------------------------------------- #


def square_crop(img, fx: float, fy: float):
    """Crop to 1:1 around a focus point given in 0..1 image coordinates.

    fx/fy name the point that should end up centred; the window is clamped so
    it never runs off the edge, so a focus near a border just slides flush.
    """
    w, h = img.size
    side = min(w, h)
    left = min(max(fx * w - side / 2, 0), w - side)
    top = min(max(fy * h - side / 2, 0), h - side)
    return img.crop((round(left), round(top), round(left) + side, round(top) + side))


def load_grid(path: Path, cols: int, contrast: float, gamma: float,
              cell_aspect: float, square: bool = False,
              focus: tuple[float, float] = (0.5, 0.5),
              equalize: bool = False, detail: float = 0.0):
    """Return (width, height, lum[y][x] in 0..1, rgb[y][x]).

    If the source has an alpha channel it is treated as a subject cutout: the
    image is flattened onto black, and the mask is carried through so nothing
    is ever drawn outside the subject and so `equalize` only measures the
    subject's own histogram rather than a huge empty background.
    """
    img = ImageOps.exif_transpose(Image.open(path))

    mask = None
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        if img.split()[3].getextrema()[0] < 250:  # a real cutout, not a stray channel
            mask = img.split()[3]
        flat = Image.new("RGBA", img.size, (0, 0, 0, 255))
        flat.alpha_composite(img)
        img = flat
    img = img.convert("RGB")

    if square:
        img = square_crop(img, *focus)
        if mask is not None:
            mask = square_crop(mask, *focus)

    gray = img.convert("L")

    # A lit face against near-black hair spans a far wider range than the ~10
    # tones a dot ramp can show. Equalising against the subject's own histogram
    # buys back the shadow detail; the unsharp pass puts local facial structure
    # back on top of the flattened result.
    if equalize:
        binmask = mask.point(lambda v: 255 if v > 127 else 0) if mask else None
        gray = ImageOps.equalize(gray, mask=binmask)
    if detail > 0:
        radius = max(2, round(min(img.size) / 52))
        gray = gray.filter(ImageFilter.UnsharpMask(
            radius=radius, percent=round(detail * 100), threshold=0))
    if contrast != 1.0:
        gray = ImageEnhance.Contrast(gray).enhance(contrast)
        img = ImageEnhance.Contrast(img).enhance(contrast)

    w, h = img.size
    # cell_aspect is cell width / cell height: 1.0 for square dot cells,
    # ~0.5 for monospace glyphs (which are about twice as tall as they are wide)
    rows = max(1, round(cols * (h / w) * cell_aspect))
    small_g = gray.resize((cols, rows), Image.Resampling.LANCZOS)
    if mask is not None:
        small_m = mask.resize((cols, rows), Image.Resampling.LANCZOS)
        small_g = ImageChops.multiply(small_g, small_m)
    small_c = img.resize((cols, rows), Image.Resampling.LANCZOS)

    gp, cp = small_g.load(), small_c.load()
    rgb, lum = [], []
    for y in range(rows):
        rgb_row, lum_row = [], []
        for x in range(cols):
            rgb_row.append(cp[x, y])
            v = gp[x, y] / 255.0
            lum_row.append(min(1.0, max(0.0, v ** gamma)))
        rgb.append(rgb_row)
        lum.append(lum_row)
    return cols, rows, lum, rgb


def circle_falloff(x, y, cols, rows, feather=0.06):
    """1 inside the inscribed circle, fading to 0 just outside it."""
    nx = (x + 0.5) / cols * 2 - 1
    ny = (y + 0.5) / rows * 2 - 1
    d = math.hypot(nx, ny)
    if d <= 1 - feather:
        return 1.0
    if d >= 1 + feather:
        return 0.0
    return (1 + feather - d) / (2 * feather)


# --------------------------------------------------------------------------- #
# svg builders
# --------------------------------------------------------------------------- #

def svg_header(w, h, rows, opts):
    css = []

    if opts.animate:
        # slow shimmer sweeping across the columns, staggered by lane
        css.append("@keyframes dp{0%,100%{opacity:.45}50%{opacity:1}}")
        css.append(f".d{{animation:dp {opts.duration}s ease-in-out infinite}}")
        css += [f".l{i}{{animation-delay:{i / opts.lanes * opts.duration:.2f}s}}"
                for i in range(opts.lanes)]

    if opts.reveal:
        # Row-by-row load-in. The animation goes on a <g> wrapping each row
        # rather than on the dots themselves: group opacity MULTIPLIES with the
        # children's own opacity, so binary mode keeps its per-glyph tone
        # instead of having it overwritten, and it is one class per row rather
        # than one per dot.
        step = opts.reveal_time / max(rows - 1, 1)
        css.append("@keyframes rv{from{opacity:0}to{opacity:1}}")
        css.append(f".rw{{animation:rv {opts.reveal_fade}s ease-out both}}")
        css += [
            f".r{y}{{animation-delay:{(rows - 1 - y if opts.reveal_dir == 'up' else y) * step:.3f}s}}"
            for y in range(rows)
        ]

    style = f"<style>{''.join(css)}</style>" if css else ""
    bgrect = f'<rect width="100%" height="100%" fill="{opts.bg}"/>' if opts.bg else ""
    pad = opts.pad
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w + 2 * pad} {h + 2 * pad}" '
        f'width="{w + 2 * pad}" height="{h + 2 * pad}" role="img" '
        f'aria-label="dot-matrix portrait">{style}{bgrect}'
        f'<g transform="translate({pad},{pad})">'
    )


def build_dots(cols, rows, lum, rgb, theme, opts):
    fg, dim, _ = THEMES[theme]
    cell = opts.cell
    max_r = cell * 0.5 * opts.dot_scale
    lanes = opts.lanes
    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            v = lum[y][x]
            if opts.invert:
                v = 1 - v
            if opts.circle:
                v *= circle_falloff(x, y, cols, rows)
            if v < opts.floor:
                continue
            r = max_r * (v ** 0.85)
            if r < 0.18:
                continue
            cx = x * cell + cell / 2
            cy = y * cell + cell / 2
            if opts.color:
                cr, cg, cb = rgb[y][x]
                fill = f"#{cr:02x}{cg:02x}{cb:02x}"
            else:
                fill = fg if v > 0.42 else dim
            cls = f' class="d l{x % lanes}"' if opts.animate else ""
            row.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="{fill}"{cls}/>'
            )
        if not row:
            continue
        if opts.reveal:
            out.append(f'<g class="rw r{y}">{"".join(row)}</g>')
        else:
            out += row
    return "".join(out), cols * cell, rows * cell


def build_binary(cols, rows, lum, rgb, theme, opts):
    fg, dim, _ = THEMES[theme]
    cell = opts.cell
    lanes = opts.lanes
    out = [
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
        f'font-size="{cell * 0.92:.2f}" text-anchor="middle">'
    ]
    for y in range(rows):
        row = []
        for x in range(cols):
            v = lum[y][x]
            if opts.invert:
                v = 1 - v
            if opts.circle:
                v *= circle_falloff(x, y, cols, rows)
            if v < opts.floor:
                continue
            # deterministic-but-scattered bit choice, seeded by position + value
            bit = "1" if ((x * 7 + y * 13 + int(v * 37)) % 3) else "0"
            if v > 0.62:
                bit = "1"
            if opts.color:
                cr, cg, cb = rgb[y][x]
                fill = f"#{cr:02x}{cg:02x}{cb:02x}"
            else:
                fill = fg if v > 0.42 else dim
            cls = f' class="d l{x % lanes}"' if opts.animate else ""
            op = f' opacity="{0.25 + 0.75 * v:.2f}"'
            row.append(
                f'<text x="{x * cell + cell / 2:.1f}" y="{y * cell + cell * 0.82:.1f}" '
                f'fill="{fill}"{op}{cls}>{bit}</text>'
            )
        if not row:
            continue
        if opts.reveal:
            out.append(f'<g class="rw r{y}">{"".join(row)}</g>')
        else:
            out += row
    out.append("</g>")
    return "".join(out), cols * cell, rows * cell


def build_ascii(cols, rows, lum, opts):
    lines = []
    n = len(ASCII_RAMP) - 1
    for y in range(rows):
        row = []
        for x in range(cols):
            v = lum[y][x]
            if opts.invert:
                v = 1 - v
            if opts.circle:
                v *= circle_falloff(x, y, cols, rows)
            row.append(ASCII_RAMP[n - min(n, int(v * n + 0.5))])
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


def build_braille(cols, rows, lum, opts):
    lines = []
    for by in range(0, rows - 3, 4):
        row = []
        for bx in range(0, cols - 1, 2):
            bits = 0
            for dy in range(4):
                for dx in range(2):
                    v = lum[by + dy][bx + dx]
                    if opts.invert:
                        v = 1 - v
                    if opts.circle:
                        v *= circle_falloff(bx + dx, by + dy, cols, rows)
                    if v > opts.threshold:
                        bits |= BRAILLE_BITS[dy][dx]
            row.append(chr(BRAILLE_BASE + bits))
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image", type=Path, help="source photo (jpg/png/webp)")
    p.add_argument("-o", "--out", type=Path, default=Path("assets/portrait"),
                   help="output path WITHOUT extension (default: assets/portrait)")
    p.add_argument("--mode", choices=("dots", "binary", "ascii", "braille"),
                   default="dots")
    p.add_argument("--cols", type=int, default=88, help="dots across (default 88)")
    p.add_argument("--cell", type=float, default=10.0, help="SVG units per cell")
    p.add_argument("--dot-scale", type=float, default=0.92,
                   help="max dot diameter as a fraction of the cell")
    p.add_argument("--gamma", type=float, default=1.0,
                   help="<1 brightens midtones, >1 darkens them")
    p.add_argument("--contrast", type=float, default=1.25)
    p.add_argument("--equalize", action="store_true",
                   help="equalise against the subject's own histogram — the fix "
                        "for a lit face against dark hair losing all shadow detail")
    p.add_argument("--detail", type=float, default=0.0, metavar="N",
                   help="local-contrast boost, 0-1.5. Puts facial structure back "
                        "after --equalize flattens it; 0.5 is a good start")
    p.add_argument("--floor", type=float, default=0.06,
                   help="drop cells dimmer than this (keeps the file small)")
    p.add_argument("--threshold", type=float, default=0.45,
                   help="on/off cutoff for braille mode")
    p.add_argument("--cell-aspect", type=float, default=1.0,
                   help="cell width/height; use 0.5 for ascii mode")
    p.add_argument("--square", action="store_true",
                   help="crop to 1:1 before converting")
    p.add_argument("--focus", default="0.5,0.5", metavar="X,Y",
                   help="focus point for --square as fractions of width,height "
                        "(default 0.5,0.5; use e.g. 0.55,0.42 to centre a face "
                        "sitting right of and above the middle)")
    p.add_argument("--invert", action="store_true",
                   help="big dots on DARK areas instead of light ones")
    p.add_argument("--circle", action="store_true",
                   help="mask to a circle (avatar style)")
    p.add_argument("--color", action="store_true",
                   help="tint each dot with the source pixel colour")
    p.add_argument("--animate", action="store_true",
                   help="add a slow shimmer sweeping across the columns")
    p.add_argument("--lanes", type=int, default=14, help="shimmer stagger groups")
    p.add_argument("--duration", type=float, default=4.0, help="shimmer seconds")
    p.add_argument("--reveal", action="store_true",
                   help="draw the image in row by row on load, like a slow scan")
    p.add_argument("--reveal-time", type=float, default=2.5, metavar="SEC",
                   help="how long the full top-to-bottom sweep takes (default 2.5)")
    p.add_argument("--reveal-fade", type=float, default=0.45, metavar="SEC",
                   help="how long one row takes to fade in (default 0.45)")
    p.add_argument("--reveal-dir", choices=("down", "up"), default="down",
                   help="sweep direction (default down)")
    p.add_argument("--pad", type=float, default=8.0)
    p.add_argument("--bg", default="", help="optional background colour")
    args = p.parse_args(argv)

    if args.mode == "ascii" and args.cell_aspect == 1.0:
        args.cell_aspect = 0.5  # monospace glyphs are ~2:1

    if not args.image.exists():
        sys.exit(f"no such image: {args.image}")

    try:
        fx, fy = (float(v) for v in args.focus.split(","))
    except ValueError:
        sys.exit(f"--focus wants two numbers like 0.55,0.42 (got {args.focus!r})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cols, rows, lum, rgb = load_grid(args.image, args.cols, args.contrast,
                                     args.gamma, args.cell_aspect,
                                     args.square, (fx, fy),
                                     args.equalize, args.detail)

    if args.mode in ("ascii", "braille"):
        text = (build_ascii if args.mode == "ascii" else build_braille)(
            cols, rows, lum, args)
        txt = args.out.with_suffix(".txt")
        txt.write_text(text, encoding="utf-8")
        print(f"wrote {txt}  ({cols}x{rows} cells)")
        return

    builder = build_dots if args.mode == "dots" else build_binary
    # In --color mode the dot fills come from the photo, so the light and dark
    # renders would be byte-identical. Emit one theme-neutral file instead.
    themes = ("dark",) if args.color else ("dark", "light")
    for theme in themes:
        body, w, h = builder(cols, rows, lum, rgb, theme, args)
        svg = svg_header(w, h, rows, args) + body + "</g></svg>"
        stem = args.out.name if args.color else f"{args.out.name}-{theme}"
        dest = args.out.with_name(f"{stem}.svg")
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest}  ({len(svg) / 1024:.0f} KB, {cols}x{rows} cells)")


if __name__ == "__main__":
    main()
