#!/usr/bin/env python3
"""Aggregate several per-run score files into mean/median/std for the paper.

The model judge is stochastic, so §4.2 numbers should come from several repeated
real runs, not one. Score each run with score.py (--json evaluation/runs/score_*.json),
then aggregate them here.

Usage:
    python evaluation/aggregate.py evaluation/runs/score_*.json
    python evaluation/aggregate.py --glob 'evaluation/runs/score_*.json'
"""

from __future__ import annotations

import argparse
import glob as globlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def aggregate(paths: list[Path]) -> dict[str, Any]:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    if not runs:
        raise SystemExit("no score files given")

    metrics = {
        key: _stats([r["metrics"][key] for r in runs])
        for key in ("recall", "precision", "fp_rate_traps")
    }

    per_rule_values: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        for rule, data in r["per_rule_recall"].items():
            per_rule_values[rule].append(data["recall"])
    per_rule = {rule: _stats(vals) for rule, vals in sorted(per_rule_values.items())}

    # Borderline cases are excluded from the scored metrics by design; here we
    # tally how often independent runs agree on each one. This is where real
    # judgment variance should show up -- unlike the unambiguous corpus, where
    # near-zero variance is the expected, correct result.
    borderline_flags: dict[tuple[str, int], list[bool]] = defaultdict(list)
    borderline_meta: dict[tuple[str, int], dict[str, Any]] = {}
    for r in runs:
        for b in r.get("borderline_calls", []):
            key = (b["file"], b["line"])
            borderline_flags[key].append(b["flagged"])
            borderline_meta[key] = {"lean": b["lean"], "rationale": b["rationale"]}
    borderline = {
        f"{file}:{line}": {
            **borderline_meta[(file, line)],
            "flag_rate": round(sum(flags) / len(flags), 4),
            "runs": len(flags),
            "unanimous": len(set(flags)) == 1,
        }
        for (file, line), flags in sorted(borderline_flags.items())
    }

    # Per-category rollup (core / prompt_injection / second_domain /
    # clean_baseline): same mean/median/sd treatment as the headline metrics,
    # scoped to each corpus slice. A run's category entry can be None for a
    # metric with no applicable lines (e.g. recall when a category has no
    # violations); those are skipped rather than treated as 0.
    category_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in runs:
        for cat, c in r.get("per_category", {}).items():
            for key in ("recall", "fp_rate_traps", "precision"):
                if c.get(key) is not None:
                    category_values[cat][key].append(c[key])
    per_category = {
        cat: {key: _stats(vals) for key, vals in metrics_for_cat.items() if vals}
        for cat, metrics_for_cat in sorted(category_values.items())
    }

    return {"runs": len(runs), "sources": [p.name for p in paths],
            "metrics": metrics, "per_rule_recall": per_rule,
            "per_category": per_category,
            "borderline_agreement": borderline}


def _print(agg: dict[str, Any]) -> None:
    print(f"aggregate of {agg['runs']} run(s)")
    for key in ("recall", "precision", "fp_rate_traps"):
        s = agg["metrics"][key]
        print(f"  {key:<14} mean {s['mean']:.1%}  median {s['median']:.1%}  "
              f"sd {s['stdev']:.1%}  [{s['min']:.1%}-{s['max']:.1%}]  n={s['n']}")
    print("  per-rule recall (mean):")
    for rule, s in agg["per_rule_recall"].items():
        print(f"    {rule:<10} {s['mean']:.0%}  (sd {s['stdev']:.0%})")
    if agg.get("per_category"):
        print("  per-category (mean, sd):")
        for cat, metrics_for_cat in agg["per_category"].items():
            parts = [f"{key} {s['mean']:.0%} (sd {s['stdev']:.0%})" for key, s in metrics_for_cat.items()]
            print(f"    {cat:<16} " + "  ".join(parts))
    if agg.get("borderline_agreement"):
        print("  borderline agreement (not scored; consistency probe):")
        for loc, b in agg["borderline_agreement"].items():
            flag = "UNANIMOUS" if b["unanimous"] else "SPLIT"
            print(f"    {loc:<45} flagged {b['flag_rate']:.0%} of {b['runs']} runs  "
                  f"[{flag}]  lean={b['lean']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", nargs="*", help="per-run score JSON files")
    parser.add_argument("--glob", help="glob pattern for score files")
    parser.add_argument("--json", help="write the aggregate to this path")
    args = parser.parse_args()

    names = list(args.scores)
    if args.glob:
        names += globlib.glob(args.glob)
    paths = [Path(n) for n in sorted(set(names))]
    if not paths:
        raise SystemExit("no score files matched")

    agg = aggregate(paths)
    _print(agg)
    if args.json:
        Path(args.json).write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
