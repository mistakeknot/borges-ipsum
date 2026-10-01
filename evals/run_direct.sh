#!/usr/bin/env bash
# Baseline: run the script directly with the flags a careful operator would pass.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-evals/out/direct}
mkdir -p "$out"
S=scripts/borges_ipsum.py F=evals/fixtures
python3 $S $F/dark-chat.png "$out/dark-chat.png" --keep 0,0,1600,40 --font mono
python3 $S $F/light-doc.png "$out/light-doc.png"
python3 $S $F/mixed-panes.png "$out/mixed-panes.png" --keep 460,30,620,80
python3 $S $F/colorful.png "$out/colorful.png" --font serif
rc=0
for f in dark-chat light-doc mixed-panes colorful; do
  printf '%-12s ' "$f"; python3 evals/score.py $F/$f.json "$out/$f.png" --json || rc=1
done
exit $rc
