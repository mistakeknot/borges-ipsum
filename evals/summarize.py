#!/usr/bin/env python3
"""Table of passes, mean scores and cost per spec from run_matrix results.

    python3 summarize.py evals/out/matrix/*/results.jsonl
"""
import json
import sys

print(f"{'spec':34} {'pass':>5} {'replaced':>8} {'kept':>5} {'objects':>7} "
      f"{'tok in':>8} {'cached':>8} {'tok out':>7} {'$':>6} {'secs':>5}")
for path in sys.argv[1:]:
    rows = [json.loads(l) for l in open(path) if l.strip()]
    if not rows:
        continue
    n = len(rows)
    mean = lambda k: sum(r["score"].get(k, 0) for r in rows) / n
    tot = lambda k: sum(r["usage"].get(k) or 0 for r in rows)
    cost = [r["usage"].get("cost_usd") for r in rows]
    c = f"{sum(cost):.2f}" if all(x is not None for x in cost) else "-"
    print(f"{rows[0]['spec']:34} {sum(r['score']['pass'] for r in rows)}/{n:<3} "
          f"{mean('replaced'):8.3f} {mean('kept'):5.2f} {mean('objects'):7.2f} "
          f"{tot('input'):8d} {tot('cached'):8d} {tot('output'):7d} {c:>6} "
          f"{sum(r['seconds'] for r in rows):5d}")
