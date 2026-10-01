# borges-ipsum

An agent skill that anonymizes a screenshot before you post it. Every piece of
text is replaced with words from Borges (Tlön, Uqbar, Funes, Lönnrot, simurgh,
hrönir), set in the original colour, size and width so the layout survives and
the words do not.

| before | after |
|---|---|
| ![](docs/dark-chat-before.png) | ![](docs/dark-chat-after.png) |
| ![](docs/light-doc-before.png) | ![](docs/light-doc-after.png) |

The text in these examples is invented.

## Install

```bash
npx skills add mistakeknot/borges-ipsum
```

Or copy this directory into your agent's skills folder, for example
`~/.claude/skills/borges-ipsum/`. Then ask your agent to "borges-ipsum this
screenshot" or "anonymize the text in this image before I post it".

## Use it directly

```bash
uv run scripts/borges_ipsum.py in.png out.png --font mono --keep 0,0,1600,40
# or: pip install pillow numpy scipy && python3 scripts/borges_ipsum.py ...
```

`--keep` and `--only` take pixel boxes and can be repeated. `--font` takes
`mono`, `sans`, `serif` or a font path. `--debug-mask mask.png` shows what was
detected as text. See [SKILL.md](SKILL.md) for the full workflow and the
tuning flags.

## How it works

It never reads the text. No OCR is involved. Strokes that are thinner than a
filter size and stand out from a locally flat background count as ink. It uses
a grey opening for light-on-dark text and a grey closing for dark-on-light,
and picks between them for each region. Ink is grouped into lines and word
runs. Each run is painted over with its own background colour and redrawn as
Borges words fitted to the original width.

It changes text only. Avatars, faces, photos, logos and QR codes are left
alone, and text on photos or gradients is detected unreliably. Check the
output before you post it.

## Evals

`evals/make_fixtures.py` builds four synthetic screenshots with ground truth:

- a dark chat UI with a menu bar to keep;
- a light document with a heading, links, a code chip and checkboxes;
- mixed dark and light panes with one heading to keep;
- coloured panels.

Their text is fake PII: names, emails, tokens, hostnames, paths.
`evals/score.py` checks each word box. A word counts as replaced when its
correlation with the original falls below 0.5 and the box is not blank. A kept
word must stay at correlation above 0.95. Icons and rules must survive.

```bash
evals/run_direct.sh                 # the script with operator-chosen flags
evals/run_agents.sh claude-sonnet codex   # agents given only SKILL.md and the task
```

| runner | dark-chat | light-doc | mixed-panes | colorful |
|---|---|---|---|---|
| direct (operator flags) | pass | pass | pass | pass |

All four direct runs score 1.0 on replaced, kept, objects and not-blank.
Cross-agent results will be added here once they have been run.

## License

MIT
