#!/usr/bin/env bash
# Baseline: run the script directly with the flags a careful operator would pass.
# The zz-holdout-* fixtures are not used while tuning; they check it generalises.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-evals/out/direct}
mkdir -p "$out"
S=scripts/borges_ipsum.py F=evals/fixtures
declare -A FLAGS=(
  [dark-chat]="--keep 0,0,1600,40"
  [mixed-panes]="--keep 460,30,620,80"
  [colorful]="--font serif"
  [retina]="--keep 0,0,2880,56"
  [chrome]="--keep 0,0,1500,44 --keep 0,44,260,340"
  [zz-holdout-table]="--keep 40,40,1260,82"
)
rc=0
for f in dark-chat light-doc mixed-panes colorful retina faint-bold media chrome \
         zz-holdout-terminal zz-holdout-chat zz-holdout-table; do
  # shellcheck disable=SC2086
  python3 $S $F/$f.png "$out/$f.png" ${FLAGS[$f]:-} >/dev/null
  printf '%-20s ' "$f"; python3 evals/score.py $F/$f.json "$out/$f.png" --json || rc=1
done
exit $rc
