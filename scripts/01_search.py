#!/usr/bin/env python3
"""Systematic search: policy evaluations (Arm A) and risk-factor evidence (Arm B).

Both arms run against PubMed and Europe PMC. The query strings are composed
from ``config/search.yml`` rather than hard-coded, and the exact strings
executed are written to ``data/interim/queries/`` so the search is reportable
in a PRISMA diagram without anyone having to reconstruct it afterwards.

One design choice deserves stating because it determines the paper's central
finding. **Arm A does not require study-design terms in the query.** Requiring
"randomised" or "difference-in-differences" would retrieve only policies that
were evaluated, and the proportion evaluated is exactly what this study is
measuring. Design is coded at appraisal, on the retrieved set, not imposed at
retrieval.

Usage
-----
    python scripts/01_search.py --arm A
    python scripts/01_search.py --arm B
    python scripts/01_search.py --arm both --count-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from step import http  # noqa: E402
from step.sources import europepmc, pubmed  # noqa: E402

RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
MAILTO = os.environ.get("STEP_MAILTO", os.environ.get("SRED_MAILTO", "step@example.org"))

(ROOT / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(ROOT / "logs" / "search.log")])
log = logging.getLogger("search")


def cfg() -> dict:
    with open(ROOT / "config" / "search.yml") as fh:
        return yaml.safe_load(fh)


def _or(terms: list[str], field: str) -> str:
    return "(" + " OR ".join(f'"{t}"[{field}]' if not t.endswith("*")
                             else f"{t}[{field}]" for t in terms) + ")"


def pubmed_query(c: dict, arm: str) -> str:
    """Compose the PubMed query for one arm.

    Structure is population AND exposure AND outcome AND (arm-specific block),
    date-limited. Age is expressed with MeSH filters rather than free text
    because NLM's age tags are indexer-assigned and far more reliable than
    hoping "adolescent" appears in the abstract.
    """
    pop = "(" + " OR ".join(c["population"]["pubmed_age_filters"]) + ")"
    exp = _or(c["exposure"]["terms"], "Title/Abstract")
    out_terms = c["outcomes"]["mental_health"] + c["outcomes"]["suicide"]
    out = _or(out_terms, "Title/Abstract")

    dr = c["date_range"]
    dates = f'("{dr["start"][:4]}"[Date - Publication] : "{dr["end"][:4]}"[Date - Publication])'

    if arm == "A":
        # No outcome clause. See the header comment in config/search.yml: a
        # query that requires a mental health outcome cannot be used to count
        # how many evaluations reported one.
        block = _or(c["arm_a_policy"]["intervention_terms"], "Title/Abstract")
        return f"{pop} AND {exp} AND {block} AND {dates}"

    block = _or(c["arm_b_riskfactor"]["preferred_designs"], "Title/Abstract")
    return f"{pop} AND {exp} AND {out} AND {block} AND {dates}"


def epmc_query(c: dict, arm: str) -> str:
    exp = "(" + " OR ".join(f'"{t}"' for t in c["exposure"]["terms"]) + ")"
    out_terms = c["outcomes"]["mental_health"] + c["outcomes"]["suicide"]
    out = "(" + " OR ".join(f'"{t}"' for t in out_terms) + ")"
    pop = "(" + " OR ".join(f'"{t}"' for t in c["population"]["free_text"]) + ")"
    key = ("arm_a_policy", "intervention_terms") if arm == "A" else \
          ("arm_b_riskfactor", "preferred_designs")
    block = "(" + " OR ".join(f'"{t}"' for t in c[key[0]][key[1]]) + ")"
    dr = c["date_range"]
    span = f"(PUB_YEAR:[{dr['start'][:4]} TO {dr['end'][:4]}]) AND (HAS_ABSTRACT:Y)"
    if arm == "A":
        return f"{pop} AND {exp} AND {block} AND {span}"
    return f"{pop} AND {exp} AND {out} AND {block} AND {span}"


class Shard:
    """Append-only NDJSON writer with a completion marker, as in SRED."""

    def __init__(self, path: Path):
        self.path = path
        self.done = path.with_suffix(".done")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.n = 0

    def complete(self) -> bool:
        return self.done.exists()

    def __enter__(self):
        self._fh = open(self.path, "w", encoding="utf-8")
        return self

    def write(self, paper) -> None:
        self._fh.write(json.dumps(paper.to_dict(), ensure_ascii=False) + "\n")
        self.n += 1

    def __exit__(self, exc, *_):
        self._fh.close()
        if exc is None:
            self.done.write_text(str(self.n))
            log.info("shard complete: %s (%d records)", self.path.name, self.n)
        return False


def count_pubmed(query: str) -> int:
    _, _, n = pubmed.esearch_year(query, 0, mailto=MAILTO) if False else (None, None, 0)
    return n


def run_pubmed(c: dict, arm: str, count_only: bool) -> int:
    q = pubmed_query(c, arm)
    (INTERIM / "queries").mkdir(parents=True, exist_ok=True)
    (INTERIM / "queries" / f"pubmed_arm{arm}.txt").write_text(q)
    log.info("PubMed arm %s query written (%d chars)", arm, len(q))

    y0, y1 = int(c["date_range"]["start"][:4]), int(c["date_range"]["end"][:4])
    total = 0
    for year in range(y0, y1 + 1):
        webenv, qkey, n = pubmed.esearch_year(q, year, mailto=MAILTO)
        total += n
        if count_only:
            log.info("pubmed arm %s %d: %d", arm, year, n)
            continue
        shard = Shard(RAW / f"pubmed_arm{arm}" / f"{year}.ndjson")
        if shard.complete():
            continue
        if not n:
            with shard:
                pass
            continue
        with shard as w:
            for start in range(0, n, 200):
                xml = pubmed.efetch_batch(webenv, qkey, start, 200, mailto=MAILTO)
                for p in pubmed.parse_efetch(xml):
                    w.write(p)
    log.info("PubMed arm %s total: %d", arm, total)
    return total


def run_epmc(c: dict, arm: str, count_only: bool) -> int:
    terms_q = epmc_query(c, arm)
    (INTERIM / "queries").mkdir(parents=True, exist_ok=True)
    (INTERIM / "queries" / f"epmc_arm{arm}.txt").write_text(terms_q)
    y0, y1 = int(c["date_range"]["start"][:4]), int(c["date_range"]["end"][:4])
    total = 0
    for year in range(y0, y1 + 1):
        shard = Shard(RAW / f"epmc_arm{arm}" / f"{year}.ndjson")
        if shard.complete() and not count_only:
            continue
        n = 0
        if count_only:
            continue
        with shard as w:
            yq = terms_q.replace(f"PUB_YEAR:[{y0} TO {y1}]", f"PUB_YEAR:{year}")
            for p in europepmc.harvest_raw(yq, mailto=MAILTO):
                w.write(p)
                n += 1
        total += n
    log.info("Europe PMC arm %s total: %d", arm, total)
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["A", "B", "both"], default="both")
    ap.add_argument("--sources", default="pubmed,epmc")
    ap.add_argument("--count-only", action="store_true")
    args = ap.parse_args()

    http.set_cache(RAW / "_httpcache", enabled=True)
    c = cfg()
    arms = ["A", "B"] if args.arm == "both" else [args.arm]
    srcs = [s.strip() for s in args.sources.split(",")]

    summary = {"run_utc": datetime.now(timezone.utc).isoformat(), "arms": {}}
    for arm in arms:
        summary["arms"][arm] = {}
        if "pubmed" in srcs:
            summary["arms"][arm]["pubmed"] = run_pubmed(c, arm, args.count_only)
        if "epmc" in srcs:
            summary["arms"][arm]["europepmc"] = run_epmc(c, arm, args.count_only)

    INTERIM.mkdir(parents=True, exist_ok=True)
    (INTERIM / "search_summary.json").write_text(json.dumps(summary, indent=2))
    log.info("summary: %s", json.dumps(summary["arms"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
