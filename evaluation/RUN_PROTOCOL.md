# Run protocol — producing real, scored agent runs

These steps generate the §4.2 accuracy numbers by running the **real** plugin over
the benchmark and scoring its audit logs. Nothing here modifies the agent.

## Prerequisites

- `uv` and Git installed.
- The agent checkout available at `../snp-final-version`.
- This repo on the `eval/benchmark` branch:
  ```bash
  cd snp_mock_client && git switch eval/benchmark
  python evaluation/verify_labels.py   # expect: labels OK
  ```
- `.privacy-agent/` is already committed with both policies active. For a fresh
  clone instead run, inside the Claude session: `/privacy-agent:init` then
  `/privacy-agent:config both`.

## Load the plugin

Launch Claude Code in this repo with the plugin loaded from the sibling checkout:

```bash
claude --plugin-dir ../snp-final-version
```

> Do **not** open `evaluation/labels.json` during a judging session — it is the
> answer key and would bias the review.

## One run

In the Claude Code session:

1. **Full scan** (covers both precision-on-clean-code and recall):
   ```
   /privacy-agent:full-scan
   ```
   The server selects targets + regex hints, the model reviews the files and
   judges them, and the server validates and writes
   `.privacy-agent/audit-logs/latest.json`.

2. Save the audit log for this run (from a normal shell):
   ```bash
   cp .privacy-agent/audit-logs/latest.json evaluation/runs/fullscan_runN.json
   ```

3. Score it:
   ```bash
   python evaluation/score.py evaluation/runs/fullscan_runN.json \
       --scope full --json evaluation/runs/score_full_N.json
   ```

### Diff-scan variant (realistic pre-commit scenario)

The injected files are the branch's diff against `main`, so a diff scan sees
exactly the seeded changes:

```
/privacy-agent:diff-scan main
```
```bash
cp .privacy-agent/audit-logs/latest.json evaluation/runs/diffscan_runN.json
python evaluation/score.py evaluation/runs/diffscan_runN.json \
    --scope diff --json evaluation/runs/score_diff_N.json
```

## Repeat and aggregate

The reviewing model is stochastic. Do **N ≥ 5** independent full-scan runs
(fresh scans / sessions), then:

```bash
python evaluation/aggregate.py evaluation/runs/score_full_*.json \
    --json evaluation/runs/aggregate_full.json
```

## Engine latency + memory (§4.3)

```bash
uv run --project ../snp-final-version python evaluation/bench_latency.py \
    --repeats 50 --json evaluation/runs/latency.json
```

## Map to the paper

| Report field | Source |
|---|---|
| §4.2 Precision / Recall / FP rate | `aggregate_full.json` → `metrics.*.mean` (± `stdev`) |
| §4.2 per-rule / missed | `score_full_*.json` → `per_rule_recall`, `missed_violations` |
| §4.3 small/medium latency | `latency.json` → `small_commit` / `medium_commit` `cycle_mean_ms` |
| §4.3 memory | `latency.json` → `peak_memory_mb` |
| §5 discussion (judgment consistency) | `aggregate_full.json` → `borderline_agreement` |

## Note on `evaluation/runs/archive_v1_pre_hardening/`

Those 5 runs were scored against an earlier version of the benchmark before two
fixes: a ground-truth gap (`debug_routes.py:12` is also a valid GDPR-003 case,
not just HIPAA) and a too-easy line that duplicated the HIPAA policy's own
example almost verbatim. They're kept for the investigation trail but are
**stale** — the corpus has since changed (that line's wording, plus a new
`borderline_cases.py` file), so don't mix them into a current aggregate. Produce
a fresh N≥5 under `evaluation/runs/` against the current corpus instead.
