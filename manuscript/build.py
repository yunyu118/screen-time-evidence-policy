#!/usr/bin/env python3
"""Render the submission copy of the manuscript.

Every number the manuscript asserts about its own corpus is a ``{{placeholder}}``
resolved from ``data/processed/table_counts.json``. Nothing is typed twice, so
the prose cannot drift away from the policy inventory the way hand-maintained
counts always eventually do.

The build fails, loudly, on any of:

* an unresolved ``{{placeholder}}``,
* an em dash anywhere in the rendered text (a standing house rule),
* a body word count over the journal limit.

Usage
-----
    python manuscript/build.py
    python manuscript/build.py --allow-overlength   # while still editing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / "manuscript"
PROC = ROOT / "data" / "processed"

WORD_LIMIT = 3000          # JAMA Special Communication
ABSTRACT_LIMIT = 350
REF_LIMIT = 50
REPO_URL = "https://github.com/yunyu118/screen-time-evidence-policy"

NUMBER_WORDS = {
    0: "None", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
    6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven",
    12: "Twelve", 13: "Thirteen",
}

PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def count_words(text: str) -> int:
    """Words in running prose.

    Markdown emphasis markers, table pipes, and heading hashes are stripped
    first so that formatting does not inflate the count, and superscript
    reference markers are not counted as words.
    """
    t = re.sub(r"`[^`]*`", " ", text)
    t = re.sub(r"[*_#>|]", " ", t)
    t = re.sub(r"[⁰-₟]", "", t)          # superscript ref markers
    t = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", t)     # links
    return len([w for w in t.split() if any(c.isalnum() for c in w)])


def section(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


def search_yield(root: Path) -> tuple[dict, bool]:
    """Records retrieved per source and arm, from the shard completion markers.

    Each harvested year writes a ``.done`` file containing the record count for
    that year, so the yield can be recomputed without re-reading 20 000 NDJSON
    records. Coverage is reported honestly: if a source has not finished every
    year in the date range, the sentence built from these numbers says so
    rather than quietly reporting a partial harvest as a complete one.
    """
    expected = len(range(2010, 2027))
    out, complete = {}, True
    for d in sorted((root / "data" / "raw").glob("*_arm*")):
        done = list(d.glob("*.done"))
        n = sum(int((f.read_text().strip() or 0)) for f in done)
        out[d.name] = {"records": n, "years": len(done), "years_expected": expected}
        if len(done) < expected:
            complete = False
    return out, complete


def search_sentence(y: dict, complete: bool) -> str:
    """One sentence reporting the harvest, ordered arm A then arm B."""
    if not y:
        return "[Search yield to be inserted once the harvest completes.]"
    total = sum(v["records"] for v in y.values())
    order = {"pubmed": 0, "epmc": 1}
    parts = []
    for name in sorted(y, key=lambda n: (n.rsplit("_arm", 1)[1],
                                         order.get(n.rsplit("_arm", 1)[0], 9))):
        v = y[name]
        src, arm = name.rsplit("_arm", 1)
        label = {"pubmed": "PubMed", "epmc": "Europe PMC"}.get(src, src)
        frag = f"{label} arm {arm}, {v['records']:,} records"
        if v["years"] < v["years_expected"]:
            frag += f" from {v['years']} of {v['years_expected']} publication years"
        parts.append(frag)
    s = (f"The two arms retrieved {total:,} records before deduplication: "
         f"{'; '.join(parts)}.")
    if not complete:
        s += (" [Provisional: the harvest is still running, and final PRISMA "
              "counts will be inserted before submission.]")
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-overlength", action="store_true")
    args = ap.parse_args()

    src = (MS / "manuscript.md").read_text()
    tables = (MS / "tables.md").read_text()
    counts = json.loads((PROC / "table_counts.json").read_text())

    # Derived, English-language forms of the counts, so the prose can read
    # naturally without anyone retyping a number.
    n_never = counts["n_never_evaluated"]
    ctx = {f"counts.{k}": v for k, v in counts.items()
           if not isinstance(v, (dict, list))}
    ctx["counts.n_never_evaluated_word"] = NUMBER_WORDS[n_never]
    ctx["counts.n_prespecified_word_cap"] = NUMBER_WORDS[counts["n_prespecified"]]
    ctx["counts.n_correlational_only_cap"] = NUMBER_WORDS[counts["n_correlational_only"]]
    ctx["repo.url"] = REPO_URL

    y, complete = search_yield(ROOT)
    ctx["search.sentence"] = search_sentence(y, complete)
    (PROC / "search_yield.json").write_text(
        json.dumps({"by_shard": y, "complete": complete}, indent=2))

    body = src.replace("{{TABLES}}", tables)

    # References are counted from the numbered list, not from the placeholder.
    ref_block = section(body, "## References", None)
    n_refs = len(re.findall(r"^\d+\. ", ref_block, flags=re.M))
    ctx["counts.n_references"] = n_refs

    abstract = section(body, "**Importance.**", "## Introduction")
    prose = section(body, "## Introduction", "## Article Information")
    ctx["wordcount.abstract"] = count_words(abstract)
    ctx["wordcount.body"] = count_words(prose)

    flat = flatten({}) or {}
    flat.update(ctx)

    missing = sorted({m.group(1) for m in PLACEHOLDER.finditer(body)} - set(flat))
    if missing:
        print("ERROR unresolved placeholders: " + ", ".join(missing),
              file=sys.stderr)
        return 1

    out = PLACEHOLDER.sub(lambda m: str(flat[m.group(1)]), body)

    problems = []
    if "—" in out:
        for i, line in enumerate(out.splitlines(), 1):
            if "—" in line:
                problems.append(f"em dash on line {i}: {line[:90]}")
    if ctx["wordcount.abstract"] > ABSTRACT_LIMIT:
        problems.append(f"abstract {ctx['wordcount.abstract']} words "
                        f"(limit {ABSTRACT_LIMIT})")
    if n_refs > REF_LIMIT:
        problems.append(f"{n_refs} references (limit {REF_LIMIT})")
    over = ctx["wordcount.body"] > WORD_LIMIT
    if over and not args.allow_overlength:
        problems.append(f"body {ctx['wordcount.body']} words "
                        f"(limit {WORD_LIMIT}); rerun with --allow-overlength "
                        f"to build anyway")

    (MS / "manuscript_built.md").write_text(out)

    print(f"body      {ctx['wordcount.body']:>5} / {WORD_LIMIT}")
    print(f"abstract  {ctx['wordcount.abstract']:>5} / {ABSTRACT_LIMIT}")
    print(f"refs      {n_refs:>5} / {REF_LIMIT}")
    print(f"tables    {tables.count('**Table ')} | figures 1")
    print(f"wrote     {MS / 'manuscript_built.md'}")

    if problems:
        print("\nPROBLEMS", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
