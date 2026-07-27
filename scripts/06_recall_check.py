#!/usr/bin/env python3
"""Recall check: what did an external search find that our query missed?

A Boolean query in PubMed and Europe PMC is only as good as the terms someone
thought to include. The standard way to find out what it missed is to run an
independent search with a different retrieval mechanism and check how many of
its hits our corpus already contains. Anything it finds that we do not have is
either a term we should add, or a record our screening will exclude for a
stated reason. Both are reportable; silently missing records is not.

This script takes an export from an external tool (Undermind, Elicit, Scopus,
Web of Science, a hand-built list, anything) and matches it against the arm A
and arm B harvests.

Input formats accepted
----------------------
* ``.csv`` / ``.tsv``  any file with a DOI, PMID, or Title column, under any
                       reasonable spelling of those names
* ``.ris``             tag-based (DO, TI, ID)
* ``.bib``             BibTeX (doi, title fields)
* ``.txt``             one identifier or title per line

Matching cascade
----------------
DOI, then PMID, then a blocked fuzzy title match at ratio >= 92 using
``rapidfuzz.token_sort_ratio``. The cascade is the same one SRED uses for
cross-source deduplication, so a record judged "already present" here would
also have been merged there.

Usage
-----
    python scripts/06_recall_check.py --input data/external/undermind_armA.csv
    python scripts/06_recall_check.py --input <file> --arm A --report
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
EXT = ROOT / "data" / "external"

(ROOT / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(ROOT / "logs" / "recall.log")])
log = logging.getLogger("recall")

TITLE_RATIO = 92

DOI_COLS = {"doi", "dois", "doi_url", "article doi", "digital object identifier"}
PMID_COLS = {"pmid", "pubmed id", "pubmed_id", "pubmedid", "pm id"}
TITLE_COLS = {"title", "article title", "paper title", "document title", "name"}

DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)
PMID_RE = re.compile(r"^\d{7,8}$")


# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------
def norm_doi(v: str | None) -> str | None:
    if not v:
        return None
    m = DOI_RE.search(str(v).strip())
    if not m:
        return None
    return m.group(0).lower().rstrip(".,;)")


def norm_title(v: str | None) -> str | None:
    """Lowercase, strip accents and punctuation, collapse whitespace.

    Titles arriving from a reference manager frequently carry a trailing
    period, curly braces from BibTeX, or an HTML entity from a publisher feed.
    None of that should decide whether two records are the same paper.
    """
    if not v:
        return None
    t = unicodedata.normalize("NFKD", str(v))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("{", " ").replace("}", " ")
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def title_block(t: str) -> str:
    """Blocking key: first two content words plus length bucket.

    Comparing every external title against every corpus title is 10^4 x 10^4.
    Blocking on a cheap key first cuts that to something that runs in seconds,
    at the cost of missing pairs whose first two words differ, which for
    published titles is rare enough to accept and is reported in the output.
    """
    words = [w for w in t.split() if len(w) > 2][:2]
    return " ".join(words) + f"|{len(t) // 25}"


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------
def read_delimited(path: Path) -> list[dict]:
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh, delimiter=delim))
    if not rows:
        return []
    lookup = {(k or "").strip().lower(): k for k in rows[0]}

    def pick(names: set[str]) -> str | None:
        for want in names:
            if want in lookup:
                return lookup[want]
        for low, orig in lookup.items():
            if any(w in low for w in names):
                return orig
        return None

    dc, pc, tc = pick(DOI_COLS), pick(PMID_COLS), pick(TITLE_COLS)
    if not any((dc, pc, tc)):
        raise SystemExit(
            f"{path.name}: no DOI, PMID, or Title column found. "
            f"Columns present: {list(lookup.values())[:12]}")
    log.info("columns: doi=%r pmid=%r title=%r", dc, pc, tc)
    out = []
    for r in rows:
        out.append({
            "doi": norm_doi(r.get(dc)) if dc else None,
            "pmid": (str(r.get(pc)).strip() if pc and r.get(pc) else None),
            "title": (str(r.get(tc)).strip() if tc and r.get(tc) else None),
            "raw": {k: v for k, v in r.items() if v},
        })
    return out


def read_ris(path: Path) -> list[dict]:
    recs, cur = [], {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - (.*)$", line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            if cur:
                recs.append(cur)
            cur = {}
        elif tag in ("DO", "DI"):
            cur["doi"] = norm_doi(val)
        elif tag in ("TI", "T1"):
            cur["title"] = val
        elif tag in ("ID", "AN") and PMID_RE.match(val):
            cur["pmid"] = val
        elif tag == "ER":
            recs.append(cur)
            cur = {}
    if cur:
        recs.append(cur)
    return [{"doi": r.get("doi"), "pmid": r.get("pmid"),
             "title": r.get("title"), "raw": r} for r in recs if r]


def read_bib(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    recs = []
    for entry in re.split(r"\n@", text)[0 if text.startswith("@") else 1:]:
        doi = re.search(r"doi\s*=\s*[{\"]([^}\"]+)", entry, re.I)
        ttl = re.search(r"title\s*=\s*[{\"](.+?)[}\"]\s*,\s*\n", entry,
                        re.I | re.S)
        pmid = re.search(r"pmid\s*=\s*[{\"]?(\d{7,8})", entry, re.I)
        if not (doi or ttl):
            continue
        recs.append({"doi": norm_doi(doi.group(1)) if doi else None,
                     "pmid": pmid.group(1) if pmid else None,
                     "title": ttl.group(1).strip() if ttl else None,
                     "raw": {}})
    return recs


def read_lines(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        d = norm_doi(s)
        if d:
            out.append({"doi": d, "pmid": None, "title": None, "raw": {}})
        elif PMID_RE.match(s):
            out.append({"doi": None, "pmid": s, "title": None, "raw": {}})
        else:
            out.append({"doi": None, "pmid": None, "title": s, "raw": {}})
    return out


READERS = {".csv": read_delimited, ".tsv": read_delimited, ".ris": read_ris,
           ".bib": read_bib, ".txt": read_lines, ".md": read_lines}


# --------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------
def load_corpus(arms: list[str]) -> tuple[dict, dict, dict, int]:
    """Index the harvest by DOI, PMID, and blocked normalised title."""
    by_doi, by_pmid, by_block = {}, {}, {}
    n = 0
    for arm in arms:
        for d in sorted(RAW.glob(f"*_arm{arm}")):
            for f in sorted(d.glob("*.ndjson")):
                for line in f.open(encoding="utf-8"):
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    n += 1
                    ref = {"source": r.get("source"),
                           "source_id": r.get("source_id"),
                           "title": r.get("title"), "year": r.get("year"),
                           "journal": r.get("journal_raw"), "arm": arm}
                    doi = norm_doi(r.get("doi"))
                    if doi:
                        by_doi.setdefault(doi, ref)
                    pmid = r.get("pmid") or (r.get("source_id")
                                             if r.get("source") == "pubmed" else None)
                    if pmid:
                        by_pmid.setdefault(str(pmid), ref)
                    t = norm_title(r.get("title"))
                    if t:
                        by_block.setdefault(title_block(t), []).append((t, ref))
    return by_doi, by_pmid, by_block, n


def fuzzy_hit(title: str, by_block: dict):
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return None, 0
    key = title_block(title)
    best, score = None, 0
    for cand, ref in by_block.get(key, []):
        s = fuzz.token_sort_ratio(title, cand)
        if s > score:
            best, score = ref, s
    return (best, score) if score >= TITLE_RATIO else (None, score)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True,
                    help="Undermind or other external export")
    ap.add_argument("--arm", choices=["A", "B", "both"], default="both")
    ap.add_argument("--label", default=None,
                    help="Name for this external search, used in the output")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"not found: {path}")

    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise SystemExit(f"unsupported format: {path.suffix}. "
                         f"Accepted: {', '.join(sorted(READERS))}")
    external = reader(path)
    external = [r for r in external if r.get("doi") or r.get("pmid") or r.get("title")]
    log.info("external records read: %d", len(external))

    arms = ["A", "B"] if args.arm == "both" else [args.arm]
    by_doi, by_pmid, by_block, n_corpus = load_corpus(arms)
    log.info("corpus indexed: %d records, %d DOIs, %d PMIDs, %d title blocks",
             n_corpus, len(by_doi), len(by_pmid), len(by_block))
    if not n_corpus:
        raise SystemExit("corpus is empty; run scripts/01_search.py first")

    matched, missed = [], []
    how = Counter()
    for r in external:
        hit, via, score = None, None, None
        if r.get("doi") and r["doi"] in by_doi:
            hit, via = by_doi[r["doi"]], "doi"
        elif r.get("pmid") and str(r["pmid"]) in by_pmid:
            hit, via = by_pmid[str(r["pmid"])], "pmid"
        elif r.get("title"):
            t = norm_title(r["title"])
            if t:
                hit, score = fuzzy_hit(t, by_block)
                via = "title" if hit else None
        if hit:
            how[via] += 1
            matched.append({**r, "matched_via": via, "score": score,
                            "corpus": hit})
        else:
            how["missed"] += 1
            missed.append(r)

    n = len(external)
    recall = len(matched) / n if n else 0.0
    summary = {
        "label": args.label or path.stem,
        "input": str(path.relative_to(ROOT)),
        "arms_checked": arms,
        "n_external": n,
        "n_matched": len(matched),
        "n_missed": len(missed),
        "recall": round(recall, 4),
        "matched_via": dict(how),
        "corpus_records_indexed": n_corpus,
        "title_ratio_threshold": TITLE_RATIO,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    stem = (args.label or path.stem).replace(" ", "_")
    (OUT / f"recall_{stem}.json").write_text(json.dumps(summary, indent=2))
    if missed:
        with open(OUT / f"recall_{stem}_missed.csv", "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["doi", "pmid", "title"])
            for r in missed:
                w.writerow([r.get("doi") or "", r.get("pmid") or "",
                            r.get("title") or ""])

    print(json.dumps(summary, indent=2))
    if missed:
        print(f"\n{len(missed)} record(s) our query did not retrieve:")
        for r in missed[:40]:
            ident = r.get("doi") or r.get("pmid") or ""
            print(f"  - {(r.get('title') or ident)[:110]}"
                  + (f"  [{ident}]" if ident and r.get("title") else ""))
        if len(missed) > 40:
            print(f"  ... and {len(missed) - 40} more "
                  f"(see recall_{stem}_missed.csv)")
        print("\nEach of these needs a decision: add a term to the query, or "
              "record a screening exclusion reason.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
