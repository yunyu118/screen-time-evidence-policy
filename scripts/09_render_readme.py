#!/usr/bin/env python3
"""Render README.md from README.template.md and table_counts.json.

The README carried "96,641 records, 1989-2025" for a day after the corpus grew
to 103,528 records running to 2026, because those numbers were typed by hand.
Same failure the manuscript build already prevents, same fix: the numbers are
placeholders, and an unresolved one is a build error rather than a stale fact.

Usage
-----
    python scripts/09_render_readme.py
    python scripts/09_render_readme.py --check    # fail if README.md is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "README.template.md"
TARGET = ROOT / "README.md"
RESULTS = ROOT / "data" / "processed" / "table_counts.json"

PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.]+)(\[\d+\])?(\|,)?\}\}")


def resolve(key: str, index: str | None, results: dict):
    cur = results
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(key)
        cur = cur[part]
    if index:
        cur = cur[int(index.strip("[]"))]
    return cur


def render(template: str, results: dict) -> str:
    # table_counts.json is flat; expose it under a "counts" namespace so the
    # template reads the same way the manuscript's placeholders do.
    results = {"counts": results}

    def sub(m: re.Match) -> str:
        val = resolve(m.group(1), m.group(2), results)
        return f"{val:,}" if m.group(3) else str(val)

    out = PLACEHOLDER.sub(sub, template)
    left = PLACEHOLDER.findall(out)
    if left:
        raise SystemExit(f"unresolved placeholders: {left}")
    if "—" in out:
        bad = [l for l in out.splitlines() if "—" in l]
        raise SystemExit(f"em dash in README, {len(bad)} line(s): {bad[0][:80]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if README.md differs from the render")
    args = ap.parse_args()

    results = json.loads(RESULTS.read_text())
    out = render(TEMPLATE.read_text(), results)

    if args.check:
        current = TARGET.read_text() if TARGET.exists() else ""
        if current != out:
            print("README.md is stale; run scripts/09_render_readme.py",
                  file=sys.stderr)
            return 1
        print("README.md is current")
        return 0

    TARGET.write_text(out)
    print(f"wrote README.md ({results['n_policies']} policies, "
          f"{results['n_evaluations_table2']} evaluations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
