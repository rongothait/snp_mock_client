#!/usr/bin/env python3
"""Latency and memory benchmark for the privacy-agent scanning engine.

This measures ONLY the deterministic server work the plugin does around a scan:
  prepare_scan  - target selection, git-diff parsing, regex-hint collection
  submit_findings - finding validation, redaction, audit-log write

It deliberately EXCLUDES the model's review time, which is non-deterministic and
not a reproducible engine metric. Reported numbers are the tool's own overhead.

The privacy_agent package is imported, never modified. Run it with the agent
checkout on the path, e.g. from snp_mock_client/:

    uv run --project ../snp-final-version python evaluation/bench_latency.py

Buckets match the paper: small commit (< 5 files) and medium commit (5-20 files).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tempfile
import time
import tracemalloc
from pathlib import Path

from privacy_agent.service import PrivacyService

# A file body with a realistic mix of detector-hitting and benign lines.
FILE_TEMPLATE = '''"""Synthetic module {n} for latency benchmarking."""

import logging

logger = logging.getLogger(__name__)

SUPPORT_EMAIL = "help@example.invalid"
TIMEOUT_MS = 1500000000
OWNER = {{"name": "Maria Rossi", "email": "person{n}@gmail.com"}}


def handle_{n}(user, record):
    logger.info("event id=%s", record.id)
    logger.info(f"processed {{user}}")
    logger.debug("contact %s", user.email)
    return record
'''


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _make_repo(root: Path, file_count: int) -> PrivacyService:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "bench@example.invalid")
    _git(root, "config", "user.name", "Benchmark")
    PrivacyService.init_repo(root)
    service = PrivacyService(root)
    service.set_active_policies(["hipaa", "gdpr"])
    for i in range(file_count):
        (root / f"module_{i}.py").write_text(FILE_TEMPLATE.format(n=i), encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "bench fixture")
    return service


def _time_ms(fn, repeats: int) -> list[float]:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


def _summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    return {
        "mean_ms": round(statistics.mean(samples), 2),
        "median_ms": round(statistics.median(samples), 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(min(samples), 2),
        "max_ms": round(max(samples), 2),
    }


def bench_bucket(name: str, file_count: int, repeats: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        service = _make_repo(root, file_count)

        def prepare() -> dict:
            return service.prepare_scan("full-scan")

        prepare_samples = _time_ms(lambda: prepare(), repeats)

        prepared = prepare()
        scan_id = prepared["scan_id"]

        def submit() -> None:
            # Re-prepare each time because submit consumes the pending scan.
            sid = service.prepare_scan("full-scan")["scan_id"]
            service.submit_findings(sid, [])

        submit_samples = _time_ms(submit, repeats)

        tracemalloc.start()
        sid = service.prepare_scan("full-scan")["scan_id"]
        service.submit_findings(sid, [])
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "bucket": name,
            "files": file_count,
            "repeats": repeats,
            "prepare_scan": _summary(prepare_samples),
            "submit_findings_empty": _summary(submit_samples),
            "cycle_mean_ms": round(
                _summary(prepare_samples)["mean_ms"]
                + _summary(submit_samples)["mean_ms"],
                2,
            ),
            "peak_memory_mb": round(peak / (1024 * 1024), 2),
            "hint_count": prepared.get("hints_truncated") and ">300" or len(prepared.get("hints", [])),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=30)
    parser.add_argument("--small", type=int, default=4, help="file count for the small bucket")
    parser.add_argument("--medium", type=int, default=15, help="file count for the medium bucket")
    parser.add_argument("--json", help="write results to this path")
    args = parser.parse_args()

    results = [
        bench_bucket("small_commit", args.small, args.repeats),
        bench_bucket("medium_commit", args.medium, args.repeats),
    ]

    print("privacy-agent engine latency (deterministic only; excludes model inference)")
    for r in results:
        print(f"\n{r['bucket']}  ({r['files']} files, {r['repeats']} reps)")
        print(f"  prepare_scan        mean {r['prepare_scan']['mean_ms']:.2f} ms  "
              f"median {r['prepare_scan']['median_ms']:.2f} ms  p95 {r['prepare_scan']['p95_ms']:.2f} ms")
        print(f"  submit_findings([]) mean {r['submit_findings_empty']['mean_ms']:.2f} ms  "
              f"median {r['submit_findings_empty']['median_ms']:.2f} ms")
        print(f"  full cycle          mean {r['cycle_mean_ms']:.2f} ms")
        print(f"  peak memory         {r['peak_memory_mb']:.2f} MB")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
