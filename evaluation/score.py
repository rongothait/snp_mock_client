#!/usr/bin/env python3
"""Score a privacy-agent audit log against the benchmark ground truth.

Takes an audit log produced by the plugin (`.privacy-agent/audit-logs/*.json`,
e.g. `latest.json`) and `labels.json`, then reports detection accuracy.

Metric definitions (see evaluation/README.md):
  recall      = violation lines caught / total violation lines
  precision   = correct findings / all findings          (finding level)
  fp_rate     = negative-trap lines flagged / total negative-trap lines
                (the "against negative traps" definition chosen for the paper)

A finding (file, line, rule_id) is CORRECT when it lands on a violation line
(within line_tolerance) and its rule_id is in that line's accepted rule_ids.
HIPAA/GDPR rules overlap, so each violation line accepts a set of rule ids.

Usage:
    python evaluation/score.py <audit-log.json> [--labels labels.json]
                               [--scope full|diff] [--json out.json] [--quiet]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def load_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull (file, line, rule_id) findings from an audit-log report."""
    findings = []
    for item in report.get("violations", []):
        findings.append(
            {
                "file": item["file"],
                "line": int(item["line"]),
                "rule_id": item["rule_id"],
                "status": item.get("status", "open"),
            }
        )
    return findings


def score(
    report: dict[str, Any], labels: dict[str, Any], scope: str = "full"
) -> dict[str, Any]:
    tol = int(labels.get("line_tolerance", 0))
    injected = set(labels["injected_files"])

    # (file, line) -> accepted rule ids
    violation_rules: dict[tuple[str, int], set[str]] = {
        (v["file"], v["line"]): set(v["rule_ids"]) for v in labels["violations"]
    }
    # canonical (primary) rule per violation line, for per-rule breakdown
    canonical: dict[tuple[str, int], str] = {
        (v["file"], v["line"]): v["rule_ids"][0] for v in labels["violations"]
    }
    negatives: set[tuple[str, int]] = {
        (n["file"], n["line"]) for n in labels["negatives"]
    }

    def nearest_violation(file: str, line: int) -> tuple[str, int] | None:
        for delta in range(0, tol + 1):
            for cand in ((file, line - delta), (file, line + delta)):
                if cand in violation_rules:
                    return cand
        return None

    def nearest_negative(file: str, line: int) -> tuple[str, int] | None:
        for delta in range(0, tol + 1):
            for cand in ((file, line - delta), (file, line + delta)):
                if cand in negatives:
                    return cand
        return None

    findings = load_findings(report)
    caught_lines: set[tuple[str, int]] = set()
    flagged_negatives: set[tuple[str, int]] = set()
    correct_findings = 0
    fp_detail: list[dict[str, Any]] = []
    fp_by_kind: dict[str, int] = defaultdict(int)

    for f in findings:
        key = (f["file"], f["line"])
        vkey = nearest_violation(*key)
        if vkey is not None and f["rule_id"] in violation_rules[vkey]:
            correct_findings += 1
            caught_lines.add(vkey)
            continue
        # not a correct detection -> classify the false positive
        if vkey is not None:
            kind = "wrong_rule"  # right line, rule not in accepted set
        else:
            nkey = nearest_negative(*key)
            if nkey is not None:
                kind = "trap"
                flagged_negatives.add(nkey)
            elif f["file"] in injected:
                kind = "injected_other"
            else:
                kind = "clean_code"
        fp_by_kind[kind] += 1
        fp_detail.append({**f, "kind": kind})

    total_violations = len(violation_rules)
    total_findings = len(findings)
    false_positives = total_findings - correct_findings

    correct_lines = len(caught_lines)
    recall = correct_lines / total_violations if total_violations else 0.0
    precision = correct_findings / total_findings if total_findings else 0.0
    fp_rate_traps = len(flagged_negatives) / len(negatives) if negatives else 0.0

    # per-canonical-rule recall
    per_rule_total: dict[str, int] = defaultdict(int)
    per_rule_caught: dict[str, int] = defaultdict(int)
    for vkey, rule in canonical.items():
        per_rule_total[rule] += 1
        if vkey in caught_lines:
            per_rule_caught[rule] += 1
    per_rule = {
        rule: {
            "caught": per_rule_caught[rule],
            "total": per_rule_total[rule],
            "recall": per_rule_caught[rule] / per_rule_total[rule],
        }
        for rule in sorted(per_rule_total)
    }

    missed = [
        {"file": f, "line": ln, "rule_ids": sorted(violation_rules[(f, ln)])}
        for (f, ln) in sorted(violation_rules)
        if (f, ln) not in caught_lines
    ]

    return {
        "scope": scope,
        "mode": report.get("mode"),
        "scan_id": report.get("scan_id"),
        "active_policies": report.get("active_policies"),
        "totals": {
            "violation_lines": total_violations,
            "negative_lines": len(negatives),
            "findings": total_findings,
            "correct_findings": correct_findings,
            "false_positives": false_positives,
            "violation_lines_caught": correct_lines,
            "negative_lines_flagged": len(flagged_negatives),
        },
        "metrics": {
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "fp_rate_traps": round(fp_rate_traps, 4),
        },
        "fp_by_kind": dict(fp_by_kind),
        "per_rule_recall": per_rule,
        "missed_violations": missed,
        "false_positive_detail": fp_detail,
    }


def _print(result: dict[str, Any]) -> None:
    m = result["metrics"]
    t = result["totals"]
    print(f"scan_id={result['scan_id']}  mode={result['mode']}  scope={result['scope']}")
    print(f"  recall     {m['recall']:.1%}  ({t['violation_lines_caught']}/{t['violation_lines']} violation lines)")
    print(f"  precision  {m['precision']:.1%}  ({t['correct_findings']}/{t['findings']} findings correct)")
    print(f"  fp_rate    {m['fp_rate_traps']:.1%}  ({t['negative_lines_flagged']}/{t['negative_lines']} traps flagged)")
    if result["fp_by_kind"]:
        print(f"  false positives by kind: {result['fp_by_kind']}")
    print("  per-rule recall:")
    for rule, r in result["per_rule_recall"].items():
        print(f"    {rule:<10} {r['caught']}/{r['total']}  {r['recall']:.0%}")
    if result["missed_violations"]:
        print("  missed violations:")
        for mv in result["missed_violations"]:
            print(f"    {mv['file']}:{mv['line']}  {'/'.join(mv['rule_ids'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_log", help="path to a privacy-agent audit log JSON")
    parser.add_argument("--labels", default=str(HERE / "labels.json"))
    parser.add_argument("--scope", choices=["full", "diff"], default="full")
    parser.add_argument("--json", help="write the full result to this path")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    report = json.loads(Path(args.audit_log).read_text(encoding="utf-8"))
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    result = score(report, labels, scope=args.scope)

    if not args.quiet:
        _print(result)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
