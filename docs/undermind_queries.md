# Undermind queries for STEP

Undermind takes a research question in prose, not a Boolean string, and runs an
iterative agentic search. That difference is the point: it is a genuinely
independent retrieval mechanism from the PubMed and Europe PMC Boolean queries
in `config/search.yml`, so its hits are a fair test of what those queries
missed.

Run these one at a time. After each, export the results (CSV or BibTeX, either
works) and hand the file back. `scripts/06_recall_check.py` will match every
record against the harvest by DOI, then PMID, then fuzzy title, and report
exactly which ones our query failed to retrieve.

```
python scripts/06_recall_check.py --input data/external/<file> --arm A --label undermind_armA
```

---

## Query 1. Arm A, policy evaluations (run this first)

Paste this into Undermind:

> I am looking for empirical evaluations of government policies, laws,
> ordinances, or school-level rules that restrict children's or adolescents'
> access to smartphones, social media platforms, or online games. I want
> studies that measured what happened after such a measure took effect, using
> any design: randomised, cluster-randomised, difference-in-differences,
> regression discontinuity, interrupted time series, synthetic control,
> controlled before-after, or uncontrolled pre-post. Outcomes of interest are
> device or platform use, mental health symptoms, wellbeing, sleep, self-harm,
> suicidal ideation, suicide attempt, and suicide death. Relevant jurisdictions
> include Australia's social media minimum age law, South Korea's online game
> shutdown law, China's minor gaming restrictions, France's and Brazil's school
> phone bans, US state school phone restrictions, Japan's Kagawa and Toyoake
> ordinances, the UK Online Safety Act, and Sweden's screen guidance. Exclude
> studies of adults only, and exclude studies whose only outcome is myopia,
> obesity, or musculoskeletal.

**What I am testing.** Our arm A query returned 4,995 PubMed records and 13,529
Europe PMC records, but it required only intervention terms, not design terms,
on purpose. If Undermind surfaces an evaluation we do not hold, the query has a
term gap and the Methods section cannot yet claim completeness.

**What counts as a real miss.** Anything Undermind returns that our corpus does
not contain, and that our screening criteria would have kept. A record we
missed but would have excluded anyway (adult sample, myopia outcome) is not a
recall failure, but it still has to be recorded with a reason rather than
quietly dropped.

---

## Query 2. Primary sources for the policy inventory

All 13 entries in Table 1 are currently `verified: false`, meaning their
details come from secondary coverage rather than from a primary source. This
query is aimed at the ones where a peer-reviewed description exists.

> I need primary-source descriptions and any published evaluations of these
> specific measures: Australia's Online Safety Amendment (Social Media Minimum
> Age) Act 2024; South Korea's Youth Protection Revision Act "shutdown law" of
> 2011 and its 2021 repeal; China's 2021 National Press and Publication
> Administration restrictions on minors' online gaming; Brazil's 2025 law on
> smartphones in schools; France's Loi 2018-698 banning phones in schools;
> Japan's Kagawa Prefecture 2020 internet and game addiction ordinance and the
> 2022 Takamatsu District Court ruling upholding it; and Sweden's 2024 Public
> Health Agency screen time recommendations. For each I want the legal
> instrument itself, the stated justification, and any published assessment of
> its effects.

---

## Query 3. Arm B, the evidence beneath the policies

Run this after arm A. It sharpens the "evidence beneath the policies is real,
and small" section and the Link 2 grade in Figure 1.

> I am looking for studies capable of supporting a causal claim about the
> effect of screen time or social media use on mental health, depressive
> symptoms, self-harm, or suicide in people under 25. Designs of interest:
> randomised experiments that reduced or removed social media use,
> within-person and fixed-effects longitudinal analyses, co-twin and sibling
> designs, instrumental variable and natural experiment designs, Mendelian
> randomisation, preregistered replications, and specification curve analyses.
> I am specifically interested in how effect sizes from these stronger designs
> compare with those from cross-sectional correlational studies, and in whether
> any of them estimate effects on self-harm or suicide rather than on symptom
> scales alone.

---

## Notes on handing the export back

* CSV, TSV, BibTeX, RIS, or a plain list of DOIs or PMIDs all work. The reader
  finds the identifier column under any reasonable spelling.
* If Undermind produces a written report as well as a reference list, that is
  worth having too. It will not go into the manuscript, but its reasoning about
  which studies matter is a useful cross-check on our appraisal.
* Nothing from Undermind will be cited without verification against the indexed
  record. Every reference in the manuscript is checked against PubMed before it
  is allowed to lose its `[Verify ...]` flag.
