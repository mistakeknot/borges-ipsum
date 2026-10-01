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


def pitch(m, h):
    """How well the letters of a run sit on one fixed-pitch lattice: near 1
    for monospace, lower for proportional type. None if too few letters."""
    lefts = np.array(sorted(s[1].start for s in ndi.find_objects(ndi.label(m)[0])))
    lefts = lefts[np.r_[True, np.diff(lefts) > 1]]  # an i and its dot are one letter
    if len(lefts) < 8:
        return None  # a few letters can sit on a lattice by chance
    return max(abs(np.exp(2j * np.pi * lefts / p).mean()) for p in np.arange(0.45 * h, 0.75 * h, 0.1))


def find_runs(mask, rgb, gray, word_gap, max_height, H):
    """Word-sized runs of ink: (x0, y0, x1, y1, ly0, ly1, fg, ink, pitch), plus the specks skipped."""
    lines_lbl, _ = ndi.label(ndi.binary_dilation(mask, structure=np.ones((1, word_gap * 2 + 5))))
    words_lbl, _ = ndi.label(ndi.binary_dilation(mask, structure=np.ones((1, word_gap))))
    line_sl = ndi.find_objects(lines_lbl)
    runs, specks = [], []
    for ws in ndi.find_objects(words_lbl):
        if ws is None:
            continue
        y0, y1, x0, x1 = ws[0].start, ws[0].stop, ws[1].start, ws[1].stop
        h, w = y1 - y0, x1 - x0
        m = mask[ws]
        if not m.any():
            continue
        if (h < 9 and not (h >= 4 and w >= 40)) or w < 10 or m.sum() < 15:
            if h <= max_height:
                specks.append((x0, y0, x1, y1))  # commas, dots, hyphens: erase, don't redraw
            continue
        if h > max_height:
            continue
        if h < 9 and m.mean(axis=1).max() > 0.85:
            continue  # a rule line, not a short line of text
        cols = np.nonzero(m.any(axis=0))[0]
        extent = cols[-1] - cols[0] + 1
        if ndi.label(m)[1] <= 1:
            # One blob is an icon, a spinner or a curve, unless it is joined-up
            # text (an underlined link, a connected script), whose strokes cross
            # many columns more than once where a curve crosses each column once.
            crossings = (np.diff(m.astype(np.int8), axis=0) == 1).sum(axis=0) + m[0]
            if extent < 1.6 * h or (crossings[cols] >= 2).mean() < 0.15:
                continue
        if y1 > H - 6:
            continue
        sub = lines_lbl[ws][m]
        ls = line_sl[np.bincount(sub[sub > 0]).argmax() - 1]
        ly0, ly1 = ls[0].start, ls[0].stop
        if ly1 - ly0 > max_height:
            ly0, ly1 = y0, y1
        # The text colour is whatever in the box lies farthest from the box's
        # typical colour. The mask can catch an outline or halo instead of the
        # letters (white captions on a photo), so it is not used for colour.
        pix = rgb[min(y0, ly0):max(y1, ly1), x0:x1].reshape(-1, 3).astype(float)
        dist = np.abs(pix - np.median(pix, axis=0)).sum(axis=1)
        fg = tuple(int(c) for c in pix[dist >= np.percentile(dist, 92)].mean(axis=0))
        ink = m.sum() / max(1, m.any(axis=0).sum() * h)
        runs.append((x0, y0, x1, y1, ly0, ly1, fg, ink, pitch(m, ly1 - ly0)))
    return runs, specks


def clean_mask(mask, max_height):
    """Lift out panel borders, dividers and box outlines so text inside a box
    does not fuse with the box into one tall shape."""
    mask = mask & ~ndi.binary_opening(mask, structure=np.ones((1, 4 * max_height)))
    return mask & ~ndi.binary_opening(mask, structure=np.ones((max(9, int(0.75 * max_height)), 1)))


def overlaps(a, b, pad=0):
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


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
    ap.add_argument("--font", default="auto",
                    help="auto, mono, sans, serif, or a path to a .ttf/.otf (default auto: mono where "
                         "letters sit on a fixed pitch, otherwise sans)")
    ap.add_argument("--stroke", type=int,
                    help="filter size; must exceed stroke width (default 9, scaled up for 2x screenshots)")
    ap.add_argument("--contrast", type=int, default=20, help="ink threshold in grey levels (default 20)")
    ap.add_argument("--word-gap", type=int,
                    help="px gap that still joins letters into one run (default 13, scaled)")
    ap.add_argument("--max-height", type=int,
                    help="tallest body text run, px (default 60, scaled); larger headings get a second pass")
    ap.add_argument("--seed", type=int, default=1899, help="word choice seed (default: Borges's birth year)")
    ap.add_argument("--debug-mask", metavar="PNG", help="also write the detected ink mask")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    img = Image.open(args.src).convert("RGB")
    rgb = np.asarray(img).astype(np.int16)
    gray = rgb.mean(axis=2)
    H, W = gray.shape

    allowed = np.ones((H, W), bool)
    if args.only:
        allowed[:] = False
        for x0, y0, x1, y1 in args.only:
            allowed[max(0, y0):y1, max(0, x0):x1] = True
    for x0, y0, x1, y1 in args.keep:
        allowed[max(0, y0):y1, max(0, x0):x1] = False

    def detect(stroke, word_gap, max_height, contrast=args.contrast):
        raw = ink_mask(gray, stroke, contrast, args.theme) & allowed
        mask = clean_mask(raw, max_height)
        return raw, mask, *find_runs(mask, rgb, gray, word_gap, max_height, H)

    # Probe at 1x sizes; a 2x (retina) capture has taller lines, so scale up.
    _, _, probe, _ = detect(args.stroke or 9, args.word_gap or 13, args.max_height or 60)
    probe_body = np.median([r[5] - r[4] for r in probe]) if probe else 20
    scale = max(1.0, probe_body / 24)
    stroke = args.stroke or (int(9 * scale) | 1)
    word_gap = args.word_gap or int(13 * scale)
    max_height = args.max_height or int(60 * scale)
    raw, mask, runs, specks = detect(stroke, word_gap, max_height)
    body = np.median([r[5] - r[4] for r in runs]) if runs else 20

    # Second pass for display headings whose strokes are too thick for the
    # first filter. A heading is a wide line of thick ink; box outlines and QR
    # codes are thin ink the first filter already saw, so they are refused.
    _, hmask, heads, _ = detect(int(stroke * 2.5) | 1, int(word_gap * 2.5), max_height * 3)
    for r in heads:
        x0, y0, x1, y1 = r[:4]
        if y1 - y0 < 1.5 * body or x1 - x0 < 2 * (y1 - y0):
            continue
        inside = [q for q in runs if overlaps(r, q)]
        if any(not (q[0] >= x0 - 2 and q[2] <= x1 + 2 and q[1] >= y0 - 2 and q[3] <= y1 + 2) for q in inside):
            continue  # it straddles body text, so it is not a heading on its own
        bands = []
        for q in sorted(inside, key=lambda q: q[1]):
            if bands and q[1] < bands[-1]:
                bands[-1] = max(bands[-1], q[3])
            else:
                bands.append(q[3])
        if len(bands) > 1:
            continue  # stacked body lines the wide filter bridged into one block
        hm = hmask[y0:y1, x0:x1]
        if hm.mean() > 0.6 or (raw[y0:y1, x0:x1] & hm).sum() > 0.6 * hm.sum():
            continue  # a solid block, or thin ink the first pass already judged
        lbl, n = ndi.label(hm)
        hh = y1 - y0
        if n < 3 or any(hm[sl].mean() > 0.7 and min(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) > 0.6 * hh
                        for sl in ndi.find_objects(lbl)):
            continue  # an icon beside a filled button, not a row of letters
        runs = [q for q in runs if q not in inside]  # fragments of the heading the first pass saw
        runs.append(r[:4] + (y0, y1) + r[6:])
        mask[y0:y1, x0:x1] |= hm

    if args.debug_mask:
        Image.fromarray((mask * 255).astype(np.uint8)).save(args.debug_mask)

    # Erase each run, filling from the rows just above and below it so
    # gradients and photos carry through instead of showing a flat patch.
    near = ndi.binary_dilation(mask, iterations=3)

    def loose_punctuation(s):
        """A speck beside a run on flat background; the edge of a dot or an
        avatar sits on its own colour and is left alone."""
        if not any(s[1] >= r[4] - 2 and s[3] <= r[5] + 2 and overlaps(s, r, 2 * word_gap) for r in runs):
            return False
        x0, y0, x1, y1 = max(0, s[0] - 3), max(0, s[1] - 3), s[2] + 3, s[3] + 3
        around = rgb[y0:y1, x0:x1][~near[y0:y1, x0:x1]]
        return around.size == 0 or around.std(axis=0).max() < 10

    # a speck inside a run (a heading's stroke fragment) goes with the run; its
    # own fill would sample the heading's ink and leave a dark bar behind
    specks = [s for s in specks if loose_punctuation(s) and not any(overlaps(s, r) for r in runs)]
    canvas = rgb.copy()
    # erase the whole line height: a run's own box can miss ascenders and
    # descenders when only part of each letter was detected
    for x0, y0, x1, y1 in [(r[0], min(r[1], r[4]), r[2], max(r[3], r[5])) for r in runs] + specks:
        bx0, by0, bx1, by1 = max(0, x0 - 2), max(0, y0 - 2), min(W, x1 + 2), min(H, y1 + 2)
        ring = rgb[max(0, by0 - 4):min(H, by1 + 4), max(0, bx0 - 4):min(W, bx1 + 4)]
        ring_ok = ~near[max(0, by0 - 4):min(H, by1 + 4), max(0, bx0 - 4):min(W, bx1 + 4)]
        flat = np.median(ring[ring_ok] if ring_ok.any() else ring.reshape(-1, 3), axis=0)

        def edge(y):
            if not 0 <= y < H:
                return np.tile(flat, (bx1 - bx0, 1))
            row = rgb[y, bx0:bx1].astype(float)
            row[near[y, bx0:bx1]] = flat
            return ndi.uniform_filter1d(row, 7, axis=0)

        top, bot = edge(by0 - 1), edge(by1)
        t = np.linspace(0, 1, by1 - by0)[:, None, None]
        canvas[by0:by1, bx0:bx1] = (1 - t) * top[None] + t * bot[None]

    out = Image.fromarray(canvas.clip(0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(out)
    if not runs:
        img.save(args.dst)
        print(f"0 text runs found; wrote an unchanged copy to {args.dst}", file=sys.stderr)
        return 0

    typical_ink = np.median([r[7] for r in runs])
    body = int(body)
    fonts = {}

    def font(kind, size, bold):
        if (kind, size, bold) not in fonts:
            path = find_font(kind, bold) or find_font(kind, False)
            fonts[kind, size, bold] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
        return fonts[kind, size, bold]

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

    # --font auto: text whose letters sit on a fixed pitch is monospace. One
    # run is too few letters to judge, so the runs of its block vote: its own
    # line, and runs in the same column within a few lines of it.
    # A screen that is mostly monospace (a terminal, most agent UIs) is set
    # in mono throughout, since touching letters hide the pitch in places.
    judged = [r for r in runs if r[8] is not None]
    all_mono = bool(judged) and np.mean([q[8] > 0.7 for q in judged]) > 0.6

    def mono(r):
        if all_mono:
            return True
        h = r[5] - r[4]
        near = [q[8] for q in judged if abs(q[4] - r[4]) <= 4 * h
                and (q[4:6] == r[4:6] or q[0] < r[2] and r[0] < q[2])]
        return bool(near) and np.median(near) > 0.7

    for r in runs:
        x0, y0, x1, y1, ly0, ly1, fg, ink, _ = r
        size = ly1 - ly0
        size = body if 0.85 * body <= size <= 1.2 * body else max(9, size)
        kind = args.font if args.font != "auto" else "mono" if mono(r) else "sans"
        f = font(kind, size, ink > 1.45 * typical_ink)
        top_off = f.getbbox("T")[1]
        draw.text((x0, ly0 - top_off), fill(f, x1 - x0), font=f, fill=fg)

    out.save(args.dst)
    print(f"{len(runs)} text runs replaced -> {args.dst}")

    # Self-check: look again with a looser filter (thicker strokes, fainter
    # ink, taller lines) for anything text-like that was not replaced.
    erased = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in [(r[0], min(r[1], r[4]), r[2], max(r[3], r[5])) for r in runs] + specks:
        erased[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = True
    _, lmask, loose, _ = detect(int(stroke * 2) | 1, word_gap, max_height * 3, max(8, args.contrast // 2))
    missed = [q for q in loose if (lmask[q[1]:q[3], q[0]:q[2]] & ~erased[q[1]:q[3], q[0]:q[2]]).sum()
              > 0.3 * lmask[q[1]:q[3], q[0]:q[2]].sum()]
    for x0, y0, x1, y1, *_ in missed:
        h = y1 - y0
        hint = (f"tall, try --max-height {h + 10} --stroke {int(h / 3) | 1}" if h > max_height
                else f"faint, try --contrast {max(8, args.contrast // 2)}"
                if (gray[y0:y1, x0:x1].max() - gray[y0:y1, x0:x1].min()) < 2 * args.contrast
                else "bold or tightly set, try --stroke {}".format(int(stroke * 1.6) | 1))
        print(f"  check {x0},{y0},{x1},{y1}: possible text left ({hint})")
    if missed:
        print(f"{len(missed)} region(s) may still hold text, or an icon or pattern; look at each")
    return 0


if __name__ == "__main__":
    sys.exit(main())
