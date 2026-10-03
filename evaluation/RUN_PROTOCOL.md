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

## One run (interactive)

In the Claude Code session:

1. **Full scan** (covers both precision-on-clean-code and recall):
   ```
   /privacy-agent:full-scan
   ```
   The server selects targets + regex hints, the model reviews the files and
   judges them, and the server validates and writes
   `.privacy-agent/audit-logs/latest.json`.
2. Exit the session (`/exit`).
3. Save the audit log for this run (from a normal shell):
   ```bash
   cp .privacy-agent/audit-logs/latest.json evaluation/runs/fullscan_runN.json
   ```
4. Score it:
   ```bash
   python evaluation/score.py evaluation/runs/fullscan_runN.json \
       --scope full --json evaluation/runs/score_full_N.json
   ```

## One run (headless — recommended for N ≥ 10)

`/privacy-agent:full-scan`'s own command definition (`commands/full-scan.md`)
declares `allowed-tools: ...prepare_scan, ...submit_findings,
...get_latest_report, Read, Grep, Glob` in its frontmatter, which pre-authorizes
exactly what the scan needs. That means headless mode (`-p`) runs with **zero
permission prompts and no bypass flag** — confirmed via `permission_denials: []`
in the JSON output:

```bash
claude --plugin-dir ../snp-final-version -p "/privacy-agent:full-scan" \
    --output-format json < /dev/null > /dev/null
cp .privacy-agent/audit-logs/latest.json evaluation/runs/fullscan_runN.json
python evaluation/score.py evaluation/runs/fullscan_runN.json \
    --scope full --json evaluation/runs/score_full_N.json
```

### Using a different model

`--model <alias>` selects the reviewing model, e.g. `--model haiku` (resolves
to `claude-haiku-4-5-20251001`) for a cheaper/faster judge:

```bash
claude --plugin-dir ../snp-final-version --model haiku \
    -p "/privacy-agent:full-scan" --output-format json < /dev/null > /dev/null
```

A weaker model is a real, useful evaluation axis on its own (does detection
accuracy hold up with a cheaper judge?) — keep runs from different models in
separate `evaluation/runs/` subfolders or filename prefixes so they don't get
aggregated together into a single misleading number.

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

The reviewing model is stochastic. Do **N ≥ 5** independent full-scan runs for
a baseline reading, or **N ≈ 20** for tighter variance bounds (headless mode
makes this cheap: each run is ~1–2 min and well under $1 with Haiku), then:

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

## Note on the `evaluation/runs/archive_*/` folders

Both are **stale** — kept for the investigation trail, not for aggregating
into current numbers, because the corpus changed after each was produced:

- `archive_v1_pre_hardening/`: before the ground-truth gap fix
  (`debug_routes.py:12` is also valid GDPR-003) and before the too-easy line
  (copied near-verbatim from the HIPAA policy's own example) was rewritten.
- `archive_v2_sonnet_baseline/`: Sonnet 5, N=5, against the hardened corpus
  *before* the prompt-injection cases and second-domain corpus were added.
  Real, valid results for that narrower corpus (see `evaluation/RESULTS.md`
  for the write-up) — just not comparable file-for-file with a current run.

Produce a fresh batch under `evaluation/runs/` against the current corpus
(`python evaluation/verify_labels.py` confirms its shape) for any new numbers.
