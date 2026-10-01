#!/usr/bin/env python3
"""Pull token use out of an agent log: claude --output-format json, codex --json.

    python3 usage.py claude|codex LOG
"""
import json
import sys

runner, path = sys.argv[1], sys.argv[2]
res = {"input": 0, "cached": 0, "output": 0, "cost_usd": None, "turns": 0}
for line in open(path, errors="replace"):
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if runner == "claude" and ev.get("type") == "result":
        u = ev.get("usage", {})
        res["input"] = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        res["cached"] = u.get("cache_read_input_tokens", 0)
        res["output"] = u.get("output_tokens", 0)
        res["cost_usd"] = ev.get("total_cost_usd")
        res["turns"] = ev.get("num_turns", 0)
    elif runner == "codex" and ev.get("type") == "turn.completed":
        u = ev.get("usage", {})
        res["input"] += u.get("input_tokens", 0) - u.get("cached_input_tokens", 0)
        res["cached"] += u.get("cached_input_tokens", 0)
        res["output"] += u.get("output_tokens", 0) + u.get("reasoning_output_tokens", 0)
        res["turns"] += 1
print(json.dumps(res))
