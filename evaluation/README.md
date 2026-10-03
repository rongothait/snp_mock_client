# Privacy-agent evaluation benchmark

This directory is a self-contained benchmark that measures the `privacy-agent`
plugin's detection accuracy and engine overhead **against this mock client**. The
agent itself is never modified — the benchmark injects labeled violations into the
clinic code and runs the real plugin over them.

It produces the numbers for the tech report's §4 (Evaluation and Results):
Precision, Recall, False-Positive Rate (§4.2) and scan latency / memory (§4.3).

## How it is built

- **Clean baseline (precision on real code):** the original `clinic/` modules are
  deliberately compliant. Any finding on them is a false positive.
- **Injected corpus (recall + trap FP):** realistic "feature" files added on the
  `eval/benchmark` branch —
  `clinic/integrations/{telemetry,analytics,debug_routes}.py` and
  `web/patient_portal.js` — containing seeded violations for all eight rules
  (HIPAA/GDPR 001–004) interleaved with compliant *lookalikes* (false-positive
  traps: `example.invalid`, 555 numbers, reserved IPs, pseudonymous-id logs,
  boolean flags, generic code vocab).
- **Ground truth:** [`labels.json`](labels.json). No labels appear in the scanned
  source, so the reviewing model is not biased. `labels.json` lives here and is
  excluded from scans (`.privacy-agent` `exclude_prefixes`).

## Metric definitions

Both HIPAA and GDPR policies are active, so each violation line accepts a **set**
of rule IDs (`rule_ids`), and a finding is correct if its rule is in that set.

| Metric | Definition |
|---|---|
| **Recall** | violation lines caught / total violation lines |
| **Precision** | correct findings / all findings (finding level) |
| **FP rate** | negative-trap lines flagged / total negative-trap lines *(the "against negative traps" definition)* |

`score.py` also breaks false positives down by kind (`trap`, `wrong_rule`,
`injected_other`, `clean_code`) and reports per-rule recall and the list of missed
violations.

### Borderline cases (not scored)

`clinic/integrations/borderline_cases.py` holds six lines the policies genuinely
don't give a clean answer for (a partially-masked email, a departmental fax
line, initials-only identifiers, a personal email in a comment, a whole object
logged through a field marked `repr=False`, a full ZIP code in an aggregate
export). These are excluded from precision/recall/FP entirely — scoring them
pass/fail would just be *our* opinion, not ground truth. Instead, `score.py`
records whether each was flagged, and `aggregate.py` reports whether repeated
runs agree (`UNANIMOUS`) or disagree (`SPLIT`) on each one. **This is where
run-to-run variance is expected and meaningful** — unlike the main corpus, whose
cases are unambiguous and should converge to ~0% variance across runs.

## Files

| File | Purpose |
|---|---|
| `labels.json` | ground-truth violations + negative traps |
| `verify_labels.py` | asserts every labeled line still matches its `expect` substring |
| `score.py` | one audit log + labels → precision / recall / FP rate |
| `aggregate.py` | combine N per-run scores → mean / median / std |
| `bench_latency.py` | deterministic engine latency + peak memory (excludes model time) |
| `RUN_PROTOCOL.md` | exact steps to produce real, scored agent runs |
| `runs/` | run outputs (audit logs, per-run scores, latency, aggregate) |

## Quick reproduce

```bash
# 0. integrity check
python evaluation/verify_labels.py

# 1. produce audit logs from REAL plugin runs — see RUN_PROTOCOL.md
#    (writes e.g. evaluation/runs/fullscan_run1.json)

# 2. score each run
python evaluation/score.py evaluation/runs/fullscan_run1.json \
    --scope full --json evaluation/runs/score_full_1.json

# 3. aggregate repeated runs (the judge is stochastic — use N >= 5)
python evaluation/aggregate.py evaluation/runs/score_full_*.json \
    --json evaluation/runs/aggregate_full.json

# 4. engine latency + memory
uv run --project ../snp-final-version python evaluation/bench_latency.py \
    --json evaluation/runs/latency.json
```

## Caveats

- **Latency/memory is the deterministic engine only** (`prepare_scan` +
  `submit_findings`), excluding the model's review time, which is not a
  reproducible engine metric. `peak_memory_mb` is the Python-heap allocation of
  the engine path (via `tracemalloc`), not process RSS.
- **Accuracy comes from real agent runs.** The reviewing model is stochastic, so
  report mean ± std over several independent runs. A judging session must not open
  `evaluation/labels.json`.
- **A line that's "too easy" is also a validity risk.** The original
  `debug_routes.py` clinical-narrative line was almost a verbatim copy of the
  HIPAA policy's own few-shot example, which tests pattern-matching against the
  prompt rather than generalization. It was rewritten with original wording that
  no regex detector matches, so catching it requires real semantic judgment.
