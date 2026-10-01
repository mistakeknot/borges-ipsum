#!/usr/bin/env python3
"""Score an anonymized image against its fixture's ground truth.

    python3 score.py fixtures/dark-chat.json out/dark-chat.png [--json]

A word counts as replaced when its patch in the output no longer correlates
with the original (NCC < 0.5) and still carries ink, so blanking it out does
not pass. One leaked word fails the fixture. A kept word must be unchanged
(NCC > 0.95). A non-text object (icon, avatar, QR code, rule, button) must
survive: under 2% of its pixels may move by more than 40 grey levels, not
counting text the fixture placed on top of it.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

THRESHOLDS = {"replaced": 1.0, "kept": 0.95, "objects": 0.90, "not_blank": 0.90}


def ncc(a, b):
    a, b = a - a.mean(), b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 1e-6 else (1.0 if np.allclose(a, b) else 0.0)


def score(truth_path, out_path):
    truth = json.load(open(truth_path))
    src = os.path.join(os.path.dirname(truth_path), truth["image"])
    a = np.asarray(Image.open(src).convert("L")).astype(float)
    b = np.asarray(Image.open(out_path).convert("L")).astype(float)
    if a.shape != b.shape:
        return {"error": f"size changed: {a.shape[::-1]} -> {b.shape[::-1]}", "pass": False}

    def patch(img, box, pad=1):
        l, t, r, bt = box
        return img[max(0, t - pad):bt + pad, max(0, l - pad):r + pad]

    red = [w for w in truth["words"] if w["expect"] == "redact"]
    keep = [w for w in truth["words"] if w["expect"] == "keep"]
    replaced = blank = 0
    leaks = []
    for w in red:
        pa, pb = patch(a, w["box"]), patch(b, w["box"])
        if ncc(pa, pb) < 0.5:
            replaced += 1
            # a fresh word may land a little off the old box; look a few px around it
            if patch(b, w["box"], pad=6).std() < 6:
                blank += 1
        else:
            leaks.append(w["text"])
    kept = sum(ncc(patch(a, w["box"]), patch(b, w["box"])) > 0.95 for w in keep)
    text_px = np.zeros(a.shape, bool)
    for w in truth["words"]:
        l, t, r, bt = w["box"]
        text_px[max(0, t - 4):bt + 4, max(0, l - 4):r + 4] = True

    def survives(o):
        moved = np.abs(patch(a, o["box"], 0) - patch(b, o["box"], 0)) > 40
        return (moved & ~patch(text_px, o["box"], 0)).mean() < 0.02

    obj_ok = sum(survives(o) for o in truth["objects"])
    rate = lambda n, d: round(n / d, 3) if d else 1.0
    res = {
        "replaced": rate(replaced, len(red)),
        "kept": rate(kept, len(keep)),
        "objects": rate(obj_ok, len(truth["objects"])),
        "not_blank": rate(replaced - blank, replaced),
        "leaked_words": leaks[:20],
        "counts": {"redact": len(red), "keep": len(keep), "objects": len(truth["objects"])},
    }
    res["pass"] = all(res[k] >= v for k, v in THRESHOLDS.items())
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("truth")
    ap.add_argument("output")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(args.output):
        res = {"error": "no output image", "pass": False}
    else:
        res = score(args.truth, args.output)
    print(json.dumps(res, indent=None if args.json else 1, ensure_ascii=False))
    sys.exit(0 if res["pass"] else 1)
