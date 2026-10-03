# Evaluation results

Produced 2026-10-03 against commit `e64358f` (hardened benchmark) on the
`eval/benchmark` branch of `snp_mock_client`, using real, independent
`claude --plugin-dir ../snp-final-version -p "/privacy-agent:full-scan"` runs
(Claude Sonnet 5, headless, no bypass flags needed — `/privacy-agent:full-scan`
pre-authorizes exactly the tools it needs). Raw data: `evaluation/runs/`.

## §4.2 — Detection accuracy (n = 5 independent full-scans)

Both HIPAA and GDPR policies active. Benchmark: 15 seeded violations across all
8 rules + 14 compliant false-positive traps, injected into realistic feature
files alongside the clean `snp_mock_client` codebase (29 files scanned total).

| Metric | Mean | Median | SD | Range | Target |
|---|---|---|---|---|---|
| Precision | **100.0%** | 100.0% | 0.0% | 100.0–100.0% | >90% |
| Recall | **100.0%** | 100.0% | 0.0% | 100.0–100.0% | >95% |
| False-positive rate (against negative traps) | **0.0%** | 0.0% | 0.0% | 0.0–0.0% | — |

Per-rule recall (mean across runs), all 100% (sd 0%): `HIPAA-001`, `HIPAA-002`,
`HIPAA-003`, `HIPAA-004`, `GDPR-003`, `GDPR-004`. (`GDPR-001`/`GDPR-002` are not
listed separately because every violation line that triggers them also accepts
the corresponding `HIPAA-00x` rule under this benchmark's labeling; see
`evaluation/labels.json`.)

### Borderline judgment consistency (not scored as pass/fail)

Six cases the policies don't give a clean answer for (see
`clinic/integrations/borderline_cases.py` and `evaluation/README.md`). Tracked
for agreement across runs rather than correctness:

| Case | Our lean | Model's call (5/5 runs) | Agreement |
|---|---|---|---|
| Partially masked email (`j***@gmail.com`) | compliant | not flagged | unanimous |
| Departmental fax line, phone-shaped | compliant | not flagged | unanimous |
| Initials-only identifier (`A.C.`) | compliant | not flagged | unanimous |
| Real-looking personal email inside a comment | violation | **flagged** (GDPR-001/HIPAA-001) | unanimous |
| Whole object logged, but PHI fields are `repr=False` | compliant | not flagged | unanimous |
| Full 5-digit ZIP code in an aggregate export | violation | not flagged | unanimous |

All 6 cases were unanimous across the 5 runs — including the one where the
model's judgment differed from our own lean (it treated the ZIP-code export as
acceptable aggregation, not a quasi-identifier leak). That disagreement is
itself informative: it shows the judge reasons about "necessary for the
export's purpose" similarly to the policy's own compliant example
(`df[["user_id", "order_total"]]`), rather than flagging every quasi-identifier
mechanically.

**Caveat:** n=5 independent runs is strong evidence of high consistency, not
proof of zero variance — a rare disagreement could still occur outside this
sample. Before trusting this as a general property, re-run at a larger N.

## §4.3 — Engine performance (deterministic only, excludes model inference time)

Measures only `prepare_scan` + `submit_findings`, the plugin's own
deterministic work (target selection, git-diff parsing, hint collection,
finding validation, redaction, audit-log I/O). Model review time is excluded
because it is non-deterministic and not a property of the engine. 50
repetitions per bucket; see `evaluation/bench_latency.py`.

| Bucket | Files | `prepare_scan` mean | `submit_findings([])` mean | Full cycle mean | Peak memory |
|---|---|---|---|---|---|
| Small commit | 4 | 79.7 ms | 108.7 ms | **188.4 ms** | 0.21 MB |
| Medium commit | 15 | 84.6 ms | 118.3 ms | **202.9 ms** | 0.22 MB |

Latency is dominated by `git` subprocess calls (diff/log/hash), not by file
count in this range — it barely changes from 4 to 15 files. Peak memory is the
Python-heap allocation of the engine path only (`tracemalloc`), not process
RSS.

## Reproduce

```bash
cd snp_mock_client && git switch eval/benchmark
python3 evaluation/verify_labels.py
# see evaluation/RUN_PROTOCOL.md for the full run sequence
```
