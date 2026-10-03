#!/usr/bin/env python3
"""Integrity check for labels.json.

Confirms every labeled line still carries its `expect` substring, that no line
is labeled both a violation and a negative, and that labels point only at the
declared injected files. Run this whenever the benchmark source changes so a
line shift is caught before it silently corrupts the scores.

Usage:
    python evaluation/verify_labels.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = Path(__file__).resolve().parent / "labels.json"


def _line(path: str, number: int) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    if not 1 <= number <= len(lines):
        raise IndexError(f"{path}:{number} is outside the file (1-{len(lines)})")
    return lines[number - 1]


def main() -> int:
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    injected = set(labels["injected_files"])
    errors: list[str] = []
    seen: dict[tuple[str, int], str] = {}

    for kind in ("violations", "negatives"):
        for entry in labels[kind]:
            key = (entry["file"], entry["line"])
            where = f"{kind} {key[0]}:{key[1]}"
            if entry["file"] not in injected:
                errors.append(f"{where}: file is not in injected_files")
            if key in seen:
                errors.append(f"{where}: also labeled under {seen[key]}")
            seen[key] = kind
            try:
                text = _line(*key)
            except (OSError, IndexError) as exc:
                errors.append(f"{where}: {exc}")
                continue
            if entry["expect"] not in text:
                errors.append(
                    f"{where}: expected {entry['expect']!r} not found; line is {text.strip()!r}"
                )

    for entry in labels["violations"]:
        if not entry.get("rule_ids"):
            errors.append(f"violation {entry['file']}:{entry['line']}: no rule_ids")

    if errors:
        print("LABELS INVALID:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"labels OK: {len(labels['violations'])} violations, "
        f"{len(labels['negatives'])} negatives across {len(injected)} files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
