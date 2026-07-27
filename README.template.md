# Screen Time Evidence and Policy (STEP)

**What is actually known about whether youth screen time and social media policies work.**

**{{counts.n_policies}} policies · {{counts.n_jurisdictions}} jurisdictions · {{counts.n_prespecified}} with a prespecified evaluation · {{counts.n_never_evaluated}} never evaluated · {{counts.n_evaluations_reporting_suicide_or_self_harm}} of {{counts.n_evaluations_table2}} evaluations reporting suicide or self-harm**

---

## What this is

Governments in {{counts.n_jurisdictions}} jurisdictions have restricted children's access to social media, smartphones, or online games. Professional bodies have issued detailed usage guidance. This repository asks a narrow question about all of it: how much rests on evidence that the *intervention works*, as distinct from evidence that the *exposure is associated with harm*?

Those are different claims. Only the second has substantial support.

The repository contains the policy inventory, the systematic search that looked for evaluations of each measure, the appraisal of what was found, and the code that turns all of it into the tables, figures, and every number in the manuscript.

## The finding in one table

| | |
|---|---|
| Policies inventoried | {{counts.n_policies}} across {{counts.n_jurisdictions}} jurisdictions |
| Enacted with a prespecified evaluation | **{{counts.n_prespecified}}** |
| Never evaluated at all | **{{counts.n_never_evaluated}}** |
| Resting on correlational evidence alone | **{{counts.n_correlational_only}} of {{counts.n_policies}}** |
| Published evaluations identified | {{counts.n_evaluations_table2}} |
| ...reporting any mental health outcome | {{counts.n_evaluations_reporting_mental_health}} |
| ...reporting suicide or self-harm | **{{counts.n_evaluations_reporting_suicide_or_self_harm}}** |

Suicide is the outcome invoked most often in advocacy for these laws. It is measured in none of the studies of whether they work.

## Quick start

```bash
git clone https://github.com/yunyu118/screen-time-evidence-policy.git
cd screen-time-evidence-policy
pip install -e ".[dev]"
export STEP_MAILTO="you@example.edu"

python scripts/01_search.py --arm both      # systematic search, both arms
python scripts/03_make_tables.py            # config -> tables + counts
python scripts/04_make_figure.py            # svg + png(3x) + pdf
python manuscript/build.py                  # substitute, check limits, fail loudly
node manuscript/make_docx.js                # Arial, US Letter, line numbers
```

## Two design decisions that determine the result

**The policy-evaluation arm requires no study-design terms.** Requiring "randomised" or "difference-in-differences" would retrieve only policies that *were* evaluated, and the proportion evaluated is precisely what this study measures. Design is coded at appraisal instead.

**The policy-evaluation arm requires no outcome terms either, and this correction matters more.** The original query required a mental health or suicide term in the title or abstract. That silently excluded every evaluation whose only outcome was behavioural, which is most of them, and which is the central finding. It excluded Barnes et al. (*BMJ* 2026), the Australian regression discontinuity this project cites as load-bearing evidence: the record is indexed in PubMed, matches the intervention clause, and fails only the outcome clause because it measured platform use rather than symptoms. A query that presupposes the outcome cannot count which outcomes were chosen.

That error was found by running an independent search (Undermind) against the corpus and measuring the overlap. Recall was 45.6%. The recall check lives in `scripts/06_recall_check.py` and is worth running against any systematic search.

## What's in the box

```
config/
  search.yml              two-arm search specification, with the reasoning
  policy_inventory.yml    the 13 policies. Source of Table 1
  evaluations.yml         appraised evaluations. Source of Table 2 and 3
src/step/                 http with rate limits and caching, schema, sources
scripts/
  01_search.py            composes queries from config, writes the exact strings
  03_make_tables.py       config -> tables.md + table_counts.json
  04_make_figure.py       the inferential-chain figure
  06_recall_check.py      external search vs this corpus, by DOI, PMID, fuzzy title
manuscript/
  manuscript.md           placeholders only. No literal numbers
  build.py                substitutes, checks limits, fails on an em dash
  make_docx.js            Arial, US Letter, landscape tables
data/interim/queries/     the exact executed query strings, for PRISMA-S
data/raw/**/*.done        per-year record counts, for the PRISMA diagram
```

## What this repository does not contain

**No full-text articles.** Publisher PDFs used during appraisal are excluded. Every source is identified by DOI or PMID.

**No harvested records.** The NDJSON shards are 1.6 GB and rebuildable from `config/search.yml` with one command. The `.done` markers carrying the per-year counts are tracked, because they are the evidence behind the PRISMA numbers.

## Status

Pre-submission. The policy inventory entries are marked `verified: false` until each has been checked against its primary legislative source rather than press coverage; do not cite Table 1 until that is done. The systematic review and its component meta-analyses are a separate, forthcoming paper.

## Licence

Code MIT. Derived data CC BY 4.0. See [`LICENSE`](LICENSE).
