---
name: borges-ipsum
description: Anonymize a screenshot before sharing it by replacing its text with Borges ipsum, words from Borges (Tlön, Uqbar, Funes, Lönnrot, simurgh, hrönir), set in the original colours and widths so the layout survives. Use when someone wants to redact, scrub, anonymize, or lorem-ipsum the text in a screenshot or UI image before posting it publicly.
---

# Borges ipsum

`scripts/borges_ipsum.py` finds text by stroke shape, without OCR, and redraws
it as Borges words in the original colour, width and typeface style. It needs
Pillow, numpy and scipy, or `uv run`.

```bash
python3 <skill-dir>/scripts/borges_ipsum.py in.png out.png [--keep x0,y0,x1,y1 ...]
```

1. Get the real size: `python3 -c "from PIL import Image; print(Image.open('in.png').size)"`.
   Coordinates are in those pixels. Scale anything you measured on a smaller view.
2. Replace everything by default. Pass `--keep` (repeatable) only for regions the
   user wants kept, such as a menu bar or generic labels. Names, emails, hosts,
   paths, repos, IDs, tokens, IPs, amounts and message text are never safe to
   keep. `--only` limits the change to a box.
3. Run it once with no tuning flags. It scales itself to the screenshot and
   picks mono or sans per block; pass `--font serif` only for serif text.
4. It ends by listing any `check x0,y0,x1,y1` regions where ink survived, each
   with a flag to try. Look at each region in the output. If it is still text,
   re-run on the original (never on the output) with the suggested flag. Icons,
   outlined buttons and patterns are also listed and can be left alone.
5. Report the output path, what you kept, and any region you left. Text is the
   only thing changed: avatars, photos, logos and QR codes stay as they are, so
   offer to blur them if they identify anyone.
