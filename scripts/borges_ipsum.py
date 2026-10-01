#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10.1", "numpy", "scipy"]
# ///
"""Borges ipsum: replace the text in a screenshot with words from Borges.

The text is never read. It is found as thin strokes that stand out from a
locally flat background: a grey opening removes light strokes from a dark
background, a grey closing removes dark strokes from a light one, and whatever
the filter took away is ink. Ink is grouped into lines and word runs. Each run
is painted over with its own background and redrawn in its own colour, with
Borges words fitted to the original width, so the layout survives and the
words do not.

    python3 borges_ipsum.py in.png out.png [--keep x0,y0,x1,y1 ...]
"""
import argparse
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

BORGES = """labyrinth mirror tiger library Babel Tlön Uqbar Orbis Tertius aleph garden
forking paths compass dream circular ruins Funes memory infinite hexagon lottery
Babylon Zahir Averroës Menard Quixote Asterion minotaur knife gaucho eternity sand
book mask encyclopedia chess lens coin Pampa Ts'ui Pên Yu Tsun sect phoenix immortal
river Heraclitus Kafka precursors secret miracle jaguar script Lönnrot Scharlach
Death compass rhombus Triste-le-Roy Emma Zunz Shakespeare nobody everything Bustos
Domecq Hladík Prague Dahlmann South Martín Fierro Cruz Tadeo Isidoro Herbert Quain
Ashe Adrogué Kublai Coleridge Xanadu rose Paracelsus Ulrica Undr wolf hrönir
Gnostic Basilides Judas Runeberg Zion Moon Pascal sphere center circumference
nowhere Cervantes Homer Argos Cartaphilus Smyrna Troglodyte Ireneo Montevideo Fray
Bentos dagger duel Recoleta Palermo Maldonado arrabal tango milonga cuchillero
orillero bestiary simurgh Thirty birds Attar Ficciones Beatriz Viterbo Carlos
Argentino Daneri Garay staircase cellar cabbalah golem Rabbi Spinoza Swedenborg
Blake Chesterton Stevenson Whitman Lugones Unamuno insomnia cartography empire map
Suárez Miranda dreamtiger blindness twilight hourglass clepsydra refutation idealism
Berkeley Hume Schopenhauer Zeno Achilles tortoise regress Brahma Tzinacán Qaholom
pyramid wheel Alexandria scholar translator Burton Galland Mardrus Thousand Nights
Scheherazade djinn Khayyam""".split()
SMALL = "y o de la el en un se ya mi lo Ur Ka sí no fue".split()

FONT_CANDIDATES = {
    "mono": [
        "/usr/share/fonts/truetype/liberation/LiberationMono-{w}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono{W}.ttf",
        "/System/Library/Fonts/Supplemental/Courier New{S}.ttf",
        "/Library/Fonts/Courier New{S}.ttf",
        "C:/Windows/Fonts/cour{s}.ttf",
    ],
    "sans": [
        "/usr/share/fonts/truetype/lato/Lato-{w}.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-{w}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{W}.ttf",
        "/System/Library/Fonts/Supplemental/Arial{S}.ttf",
        "/Library/Fonts/Arial{S}.ttf",
        "C:/Windows/Fonts/arial{s}.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-{w}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif{W}.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman{S}.ttf",
        "C:/Windows/Fonts/times{s}.ttf",
    ],
}


def find_font(kind, bold):
    if os.path.isfile(kind):
        return kind
    fill = {"w": "Bold" if bold else "Regular", "W": "-Bold" if bold else "",
            "S": " Bold" if bold else "", "s": "bd" if bold else ""}
    for pattern in FONT_CANDIDATES.get(kind, []):
        path = pattern.format(**fill)
        if os.path.isfile(path):
            return path
    return None


def parse_box(text):
    try:
        x0, y0, x1, y1 = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected x0,y0,x1,y1, got {text!r}")
    return x0, y0, x1, y1


def ink_mask(gray, stroke, contrast, theme):
    """Pixels that belong to strokes thinner than `stroke` px."""
    size = (stroke, stroke)
    light_ink = gray - ndi.grey_opening(gray, size=size)   # light text on dark
    dark_ink = ndi.grey_closing(gray, size=size) - gray    # dark text on light
    if theme == "dark":
        return light_ink > contrast
    if theme == "light":
        return dark_ink > contrast
    # auto: decide per neighbourhood from the background's own brightness
    local = ndi.uniform_filter(ndi.grey_opening(gray, size=size), size=61)
    return np.where(local < 128, light_ink > contrast, dark_ink > contrast)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--keep", type=parse_box, action="append", default=[],
                    metavar="X0,Y0,X1,Y1", help="leave text in this box untouched (repeatable)")
    ap.add_argument("--only", type=parse_box, action="append", default=[],
                    metavar="X0,Y0,X1,Y1", help="replace text only inside these boxes (repeatable)")
    ap.add_argument("--theme", choices=["auto", "dark", "light"], default="auto",
                    help="text lighter than background (dark), darker (light), or decide locally")
    ap.add_argument("--font", default="sans",
                    help="mono, sans, serif, or a path to a .ttf/.otf (default: sans)")
    ap.add_argument("--stroke", type=int, default=9,
                    help="filter size; must exceed stroke width (default 9, raise for big bold text)")
    ap.add_argument("--contrast", type=int, default=28, help="ink threshold in grey levels (default 28)")
    ap.add_argument("--word-gap", type=int, default=13,
                    help="px gap that still joins letters into one run (default 13)")
    ap.add_argument("--max-height", type=int, default=60, help="tallest text run, px (default 60)")
    ap.add_argument("--seed", type=int, default=1899, help="word choice seed (default: Borges's birth year)")
    ap.add_argument("--debug-mask", metavar="PNG", help="also write the detected ink mask")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    img = Image.open(args.src).convert("RGB")
    rgb = np.asarray(img).astype(np.int16)
    gray = rgb.mean(axis=2)
    H, W = gray.shape

    mask = ink_mask(gray, args.stroke, args.contrast, args.theme)
    if args.only:
        allowed = np.zeros_like(mask)
        for x0, y0, x1, y1 in args.only:
            allowed[max(0, y0):y1, max(0, x0):x1] = True
        mask &= allowed
    for x0, y0, x1, y1 in args.keep:
        mask[max(0, y0):y1, max(0, x0):x1] = False
    # Panel borders and dividers are ink too; a text run that touches one would
    # fuse with it into one tall shape and be skipped, so lift them out first.
    mask &= ~ndi.binary_opening(mask, structure=np.ones((args.max_height, 1)))
    if args.debug_mask:
        Image.fromarray((mask * 255).astype(np.uint8)).save(args.debug_mask)

    lines_lbl, _ = ndi.label(ndi.binary_dilation(mask, structure=np.ones((1, args.word_gap * 2 + 5))))
    words_lbl, _ = ndi.label(ndi.binary_dilation(mask, structure=np.ones((1, args.word_gap))))
    line_sl = ndi.find_objects(lines_lbl)

    jobs = []
    for ws in ndi.find_objects(words_lbl):
        if ws is None:
            continue
        y0, y1, x0, x1 = ws[0].start, ws[0].stop, ws[1].start, ws[1].stop
        h, w = y1 - y0, x1 - x0
        m = mask[ws]
        if (h < 9 and not (h >= 4 and w >= 40)) or h > args.max_height or w < 10 or m.sum() < 15:
            continue  # borders, separators, specks
        if h < 9 and m.mean(axis=1).max() > 0.85:
            continue  # a rule line, not a short line of text
        cols = np.nonzero(m.any(axis=0))[0]
        if (cols[-1] - cols[0] + 1 < 1.6 * h and ndi.label(m)[1] <= 1) or y1 > H - 6:
            continue  # icons and spinners are one blob; a short word is several glyphs
        sub = lines_lbl[ws][m]
        ls = line_sl[np.bincount(sub[sub > 0]).argmax() - 1]
        ly0, ly1 = ls[0].start, ls[0].stop
        if ly1 - ly0 > args.max_height:
            ly0, ly1 = y0, y1
        pix = rgb[ws][m]
        lum = pix.mean(axis=1)
        fg = tuple(int(c) for c in pix[lum >= np.percentile(lum, 70)].mean(axis=0)) \
            if gray[ws][~m].mean() < 128 else \
            tuple(int(c) for c in pix[lum <= np.percentile(lum, 30)].mean(axis=0))
        pad = 4
        py0, py1, px0, px1 = max(0, y0 - pad), min(H, y1 + pad), max(0, x0 - pad), min(W, x1 + pad)
        region = rgb[py0:py1, px0:px1]
        rmask = ndi.binary_dilation(mask[py0:py1, px0:px1], iterations=2)
        bgpix = region[~rmask] if (~rmask).any() else region.reshape(-1, 3)
        bgc = tuple(int(c) for c in np.median(bgpix, axis=0))
        ink = m.sum() / max(1, m.any(axis=0).sum() * h)
        jobs.append((x0, y0, x1, y1, ly0, ly1, fg, bgc, ink))

    out = img.copy()
    draw = ImageDraw.Draw(out)
    for x0, y0, x1, y1, *_, bgc, _ink in jobs:
        draw.rectangle([x0 - 2, y0 - 2, x1 + 1, y1 + 1], fill=bgc)

    if not jobs:
        out.save(args.dst)
        print(f"0 text runs found; wrote an unchanged copy to {args.dst}", file=sys.stderr)
        return 0

    typical_ink = np.median([j[-1] for j in jobs])
    body = int(np.median([j[5] - j[4] for j in jobs]))
    fonts = {}

    def font(size, bold):
        if (size, bold) not in fonts:
            path = find_font(args.font, bold) or find_font(args.font, False)
            fonts[size, bold] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
        return fonts[size, bold]

    def fill(f, width):
        """Borges words, greedily packed into `width` px."""
        words, used, space = [], 0.0, f.getlength(" ")
        while True:
            room = width - used - (space if words else 0)
            pool = [w for w in BORGES + SMALL if f.getlength(w) <= room + 2]
            if not pool:
                break
            long_ = [w for w in pool if f.getlength(w) >= min(room, 5 * space)]
            w = rng.choice(long_ or pool)
            used += f.getlength(w) + (space if words else 0)
            words.append(w)
        return " ".join(words) or min(SMALL, key=len)

    for x0, y0, x1, y1, ly0, ly1, fg, bgc, ink in jobs:
        size = ly1 - ly0
        size = body if 0.85 * body <= size <= 1.2 * body else max(9, size)
        f = font(size, ink > 1.45 * typical_ink)
        top_off = f.getbbox("T")[1]
        draw.text((x0, ly0 - top_off), fill(f, x1 - x0), font=f, fill=fg)

    out.save(args.dst)
    print(f"{len(jobs)} text runs replaced -> {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
