---
name: borges-ipsum
description: Anonymize a screenshot before sharing it by replacing its text with Borges ipsum, words from Borges (Tlön, Uqbar, Funes, Lönnrot, simurgh, hrönir), set in the original colours and widths so the layout survives. Use when someone wants to redact, scrub, anonymize, or lorem-ipsum the text in a screenshot or UI image before posting it publicly.
---

# Borges ipsum

`scripts/borges_ipsum.py` finds text in an image without reading it. Strokes
thinner than a filter size are treated as ink, grouped into words, painted over
with the local background, and redrawn as Borges words in the original colour
and width. It needs Python 3 with Pillow (10.1 or later), numpy and scipy:
`pip install pillow numpy scipy`, or run it with `uv run` (the script declares
its own dependencies).

## Workflow

1. **Look at the image first.** Find its real pixel size, because image viewers
   often show a downscaled copy and every coordinate you pass must be in the
   original's pixels:

   ```bash
   python3 -c "from PIL import Image; print(Image.open('in.png').size)"
   ```

   If you measured a position on a downscaled view, multiply it by
   original width ÷ shown width.

2. **Decide what stays.** By default, replace everything. Keep only what the
   user asks you to keep, plus generic chrome that identifies nobody, if the
   user wants it kept: OS menu bars, app menu names, labels like "New thread" or
   "Settings". Names, emails, hostnames, paths, repository and branch names,
   ticket IDs, tokens, IP addresses, amounts and message text are never generic.
   For each region to keep, pass `--keep x0,y0,x1,y1`. To change only part of
   the image, pass `--only x0,y0,x1,y1`. Both flags can be repeated.

3. **Match the look.** Pass `--font mono` when the text is monospaced (terminals,
   code, many agent UIs), `serif` for serif text, and `sans` otherwise (the
   default). You can also pass a path to a `.ttf` file. The tool works out
   light-on-dark versus dark-on-light for each region. Pass `--theme dark` or
   `--theme light` only if the automatic choice is wrong.

4. **Run it.** Write to a new file and never overwrite the source:

   ```bash
   python3 <skill-dir>/scripts/borges_ipsum.py in.png out.png --font mono \
       --keep 0,0,3840,34
   ```

5. **Check the output yourself.** Open the output and look at crops at full
   resolution, not only at a thumbnail. Hunt for anything that is still
   readable, especially names, emails, URLs and numbers. Common fixes:
   - Large or bold headings survived: raise `--stroke`, which must exceed the
     stroke width (try 15), and `--max-height`.
   - Faint grey text survived: lower `--contrast` (try 18).
   - Words in a line are run together or split oddly: adjust `--word-gap`.
   - Run with `--debug-mask mask.png` to see exactly what was detected as text.

   Re-run from the original each time. Do not run the tool again on its own
   output.

6. **Report back.** Give the output path and say what you kept. Also say what
   the tool cannot touch, because it changes text only. Avatars, faces,
   photos, logos, QR codes and text inside embedded images stay as they are.
   If any of those identify someone, offer to blur those regions, for example
   with Pillow's `ImageFilter.GaussianBlur` on a crop.

## Limits

- The tool does not use OCR, so it cannot keep particular words. Keep regions
  are rectangles.
- Text on photos, gradients or busy textures is detected unreliably. Check
  those areas closely, and blur them if the text survives.
- Icons that are a single blob (dots, spinners, checkboxes) are left alone.
  Multi-part icons next to text are sometimes turned into a short word.
- Word choice is seeded (`--seed`, default 1899), so the same input always
  gives the same output.
