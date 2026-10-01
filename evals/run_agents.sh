#!/usr/bin/env bash
# Hand each fixture to an agent with only SKILL.md and the task, then score.
#
#   evals/run_agents.sh claude-sonnet codex ...
#
# Agents: claude-haiku claude-sonnet claude-opus codex gemini
# Agents stay fenced: claude gets a tool allowlist, codex the workspace-write
# sandbox. Nothing runs with permissions bypassed.
# Each run gets a fresh workspace holding the skill and the input image, not
# the ground truth. Results land in evals/out/<agent>/ with a log per fixture
# and a results.jsonl line per run.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FIX=$ROOT/evals/fixtures
TIMEOUT=${TIMEOUT:-900}

run_one() {
  local agent=$1 name=$2 ws prompt start rc
  ws=$(mktemp -d "/tmp/borges-eval-$agent-$name-XXXX")
  mkdir -p "$ws/skills/borges-ipsum/scripts" "$ws/in" "$ws/out"
  cp "$ROOT/SKILL.md" "$ws/skills/borges-ipsum/"
  cp "$ROOT/scripts/borges_ipsum.py" "$ws/skills/borges-ipsum/scripts/"
  cp "$FIX/$name.png" "$ws/in/"
  prompt="You have an agent skill at ./skills/borges-ipsum. Read ./skills/borges-ipsum/SKILL.md and follow it.
Task: $(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['task'])" "$FIX/$name.json")
Input: in/$name.png. Write the result to out/$name.png. Work without asking questions."
  local log=$ROOT/evals/out/$agent/$name.log
  start=$(date +%s)
  case $agent in
    claude-*) (cd "$ws" && timeout "$TIMEOUT" claude -p "$prompt" --model "${agent#claude-}" \
                 --strict-mcp-config --allowedTools Read Write Edit Glob Grep \
                 'Bash(python3:*)' 'Bash(uv run:*)' 'Bash(ls:*)' 'Bash(file:*)') ;;
    codex)    timeout "$TIMEOUT" codex exec --skip-git-repo-check -C "$ws" -m "${CODEX_MODEL:-gpt-6.1-sol}" \
                 -c model_reasoning_effort="${CODEX_EFFORT:-medium}" --sandbox workspace-write "$prompt" ;;
    gemini)   (cd "$ws" && timeout "$TIMEOUT" gemini -p "$prompt" --approval-mode auto_edit) ;;
    *) echo "unknown agent $agent"; return 2 ;;
  esac >"$log" 2>&1
  rc=$?
  local secs=$(( $(date +%s) - start ))
  [ -f "$ws/out/$name.png" ] && cp "$ws/out/$name.png" "$ROOT/evals/out/$agent/$name.png"
  local score
  score=$(python3 "$ROOT/evals/score.py" "$FIX/$name.json" "$ws/out/$name.png" --json)
  printf '{"agent":"%s","fixture":"%s","exit":%d,"seconds":%d,"score":%s}\n' \
    "$agent" "$name" "$rc" "$secs" "$score" >>"$ROOT/evals/out/$agent/results.jsonl"
  echo "$agent $name exit=$rc ${secs}s $score"
  rm -rf "$ws"
}

for agent in "$@"; do
  mkdir -p "$ROOT/evals/out/$agent"
  : >"$ROOT/evals/out/$agent/results.jsonl"
  (
    for f in "$FIX"/*.json; do run_one "$agent" "$(basename "$f" .json)"; done
  ) &
done
wait
