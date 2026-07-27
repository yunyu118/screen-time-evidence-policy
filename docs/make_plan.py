#!/usr/bin/env python3
"""Generate the STEP two-paper revision plan as a self-contained HTML page.

Usage
-----
    python docs/make_plan.py
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "STEP_PLAN.html"

FONT = "Arial, Helvetica, sans-serif"
INK, MID, LIGHT, RULE = "#141414", "#575757", "#8d8d8d", "#d2d2d2"
RED, REDL, BLUE, BLUEL, PANEL = "#8c1d1d", "#f4ecec", "#1f4e79", "#eef4fa", "#fafafa"
GREEN = "#1a6b3c"

C = json.loads((ROOT / "data" / "processed" / "table_counts.json").read_text())
Y = json.loads((ROOT / "data" / "processed" / "search_yield.json").read_text())
TOTAL_RETRIEVED = sum(v["records"] for v in Y["by_shard"].values())


# ---------------------------------------------------------------- diagram
def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if len(t) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


class SVG:
    def __init__(s, w, h): s.w, s.h, s.p = w, h, []
    def add(s, x): s.p.append(x)

    def text(s, x, y, t, size=12, weight="normal", fill=INK, anchor="start",
             style="normal", spacing=0):
        s.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
              f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
              f'fill="{fill}" text-anchor="{anchor}"'
              + (f' letter-spacing="{spacing}"' if spacing else "")
              + f'>{escape(t)}</text>')

    def para(s, x, y, t, size=11, width=40, lh=14, fill=MID, weight="normal"):
        for i, ln in enumerate(wrap(t, width)):
            s.text(x, y + i * lh, ln, size=size, fill=fill, weight=weight)
        return y + (len(wrap(t, width)) - 1) * lh

    def rect(s, x, y, w, h, fill="#fff", stroke=INK, sw=1.3, rx=4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
              f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(s, x1, y1, x2, y2, stroke=INK, sw=1.3, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
              f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(s, x1, y1, x2, y2, stroke=INK, sw=1.6):
        s.line(x1, y1, x2 - 9, y2, stroke=stroke, sw=sw)
        s.add(f'<path d="M {x2:.1f} {y2:.1f} L {x2-10:.1f} {y2-5.5:.1f} '
              f'L {x2-10:.1f} {y2+5.5:.1f} Z" fill="{stroke}"/>')

    def render(s):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" '
                f'width="100%" role="img" aria-label="STEP two-paper architecture">'
                f'<rect width="{s.w}" height="{s.h}" fill="#fff"/>'
                + "".join(s.p) + "</svg>")


def diagram():
    W, H = 1180, 560
    s = SVG(W, H)
    M = 30
    s.text(M, 32, "One evidence base, two papers, one firewall between them",
           size=18, weight="bold")
    s.text(M, 54, "The split has to be defensible to two editors independently. "
                  "Data goes in Paper 2; argument goes in Paper 1.",
           size=12.5, fill=MID)
    s.line(M, 70, W - M, 70, stroke=RULE)

    # evidence base
    bx, by, bw, bh = M, 100, 330, 300
    s.rect(bx, by, bw, bh, fill=PANEL, stroke=INK, sw=1.4)
    s.text(bx + 14, by + 26, "SHARED EVIDENCE BASE", size=11.5, weight="bold",
           fill=MID, spacing=1.2)
    items = [
        (f"Policy inventory", f"{C['n_policies']} policies, {C['n_jurisdictions']} jurisdictions. "
         f"{C['n_prespecified']} prespecified evaluation, {C['n_never_evaluated']} never evaluated."),
        (f"Arm A: policy evaluations", f"{TOTAL_RETRIEVED:,} records retrieved across both arms. "
         f"{C['n_evaluations_table2']} published evaluations appraised so far."),
        ("Arm B: risk-factor evidence",
         "Causal-capable designs only. This is the arm that can support pooling."),
        ("Undermind recall check",
         "Independent retrieval. Quantifies what the Boolean query missed."),
    ]
    y = by + 52
    for title, body in items:
        s.text(bx + 14, y, title, size=12.5, weight="bold", fill=INK)
        y = s.para(bx + 14, y + 17, body, size=10.8, width=44, lh=13.2) + 24

    # papers
    px = bx + bw + 96
    pw = W - M - px
    p1y, p1h = 100, 138
    p2y, p2h = 288, 138

    s.rect(px, p1y, pw, p1h, fill=BLUEL, stroke=BLUE, sw=1.6)
    s.text(px + 16, p1y + 28, "PAPER 1", size=11.5, weight="bold", fill=BLUE,
           spacing=1.2)
    s.text(px + 16, p1y + 52, "The argument", size=15, weight="bold", fill=INK)
    s.para(px + 16, p1y + 74,
           "JAMA Viewpoint, 1200 words, 7 references, 4 authors, 1 display item. "
           "No new data. No presubmission inquiry. Cites Paper 2.",
           size=11, width=76, lh=14, fill=MID)
    s.text(px + 16, p1y + 122, "Ships first. Time-limited by the policy window.",
           size=10.8, fill=BLUE, weight="bold")

    s.rect(px, p2y, pw, p2h, fill="#fff", stroke=INK, sw=1.6)
    s.text(px + 16, p2y + 28, "PAPER 2", size=11.5, weight="bold", fill=MID,
           spacing=1.2)
    s.text(px + 16, p2y + 52, "The evidence", size=15, weight="bold", fill=INK)
    s.para(px + 16, p2y + 74,
           "Systematic review of policy evaluations plus meta-analysis of the "
           "risk-factor evidence. PROSPERO registered, PRISMA reported.",
           size=11, width=76, lh=14, fill=MID)
    s.text(px + 16, p2y + 122,
           "Slower. Preprint it so Paper 1 has something citable.",
           size=10.8, fill=INK, weight="bold")

    s.arrow(bx + bw + 6, p1y + p1h / 2, px - 6, p1y + p1h / 2)
    s.arrow(bx + bw + 6, p2y + p2h / 2, px - 6, p2y + p2h / 2)

    # cross-citation, drawn in the gap between the two paper boxes so it
    # cannot be mistaken for a third input arrow
    ccx = px + pw / 2
    s.line(ccx, p2y - 6, ccx, p1y + p1h + 6, stroke=BLUE, sw=1.3, dash="5 4")
    s.add(f'<path d="M {ccx:.1f} {p1y + p1h + 2:.1f} L {ccx-5:.1f} '
          f'{p1y + p1h + 12:.1f} L {ccx+5:.1f} {p1y + p1h + 12:.1f} Z" '
          f'fill="{BLUE}"/>')
    s.text(ccx + 10, (p1y + p1h + p2y) / 2 + 4, "cites", size=11, fill=BLUE,
           anchor="start", style="italic")

    # firewall. Height follows the wrapped text so editing the copy cannot
    # clip the last line, per the redbook figure rule.
    FW_TEXT = (
        "Paper 1 reports no pooled estimate, no PRISMA count, and no new "
        "appraisal. It argues from evidence published elsewhere, including "
        "Paper 2. Paper 2 makes no policy recommendation beyond what its own "
        "data support. Disclose each submission to the other journal's editor "
        "and cross-cite. This is the difference between a companion pair and a "
        "salami slice, and editors check.")
    fy = 452
    n_lines = len(wrap(FW_TEXT, 118))
    fh = 50 + n_lines * 15 + 12
    s.rect(M, fy, W - 2 * M, fh, fill=REDL, stroke=RED, sw=1.4)
    s.text(M + 16, fy + 26, "THE FIREWALL", size=11.5, weight="bold", fill=RED,
           spacing=1.2)
    s.para(M + 16, fy + 50, FW_TEXT, size=11.2, width=118, lh=15, fill=INK)
    s.h = int(fy + fh + 24)
    return s.render()


# ---------------------------------------------------------------- content
EMAIL = """Subject: Presubmission inquiry: Special Communication on the evidence base for youth screen time and social media policy

Dear Dr Walter,

I am writing to inquire whether JAMA would be interested in a Special Communication assessing how much of the current youth screen time and social media policy landscape rests on evidence that the interventions work, as distinct from evidence that the exposure is associated with harm.

Governments in at least {n_jurisdictions} jurisdictions have restricted children's access to social media, smartphones, or online games since 2018, and the pace has accelerated since the 2023 Surgeon General's advisory. We assembled an inventory of {n_policies} enacted or announced measures and systematically searched PubMed and Europe PMC for evaluations of them, alongside the risk-factor literature the measures are justified by.

Three findings motivate the piece. Of {n_policies} policies, {n_prespecified} was enacted with a prespecified evaluation and {n_never_evaluated} have never been evaluated at all, including France's school phone ban, in force since 2018. Of the {n_evals} published evaluations we identified, none reported suicide or self-harm, which are the outcomes invoked most often in advocacy for these laws. Where evaluation has occurred the effects are small or absent: South Korea's decade-long gaming curfew reduced adolescent internet use by 3.6 minutes per day in its first year, decaying to zero by the fourth, and was repealed in 2021; three months after Australia's minimum-age law took effect, more than 85% of adolescents younger than 16 were still using restricted platforms.

The argument is not that screen time is harmless or that policymakers should have waited for perfect evidence. It is that population-level restrictions affecting tens of millions of children have been exempted from the evaluation standard applied to any drug or clinical intervention, and that the exemption is not defensible at this scale. We propose that new restrictions carry prespecified evaluation, that the staggered adoption of school phone restrictions across more than 30 US states be exploited as a natural experiment before it saturates, and that the substitution hypothesis, which only Sweden is currently testing, be evaluated directly.

The manuscript is drafted at 3000 words with three tables and one figure, within the Special Communication limits. The policy inventory, the exact search strings, the screening decisions, and the code that generates every table and figure are openly available. I am happy to send the full draft.

I am a [TITLE] in the Department of Population Health Sciences at Weill Cornell Medicine, where my research concerns youth mental health, suicide prevention, and the social determinants of health. [ONE SENTENCE ON YOUR PUBLICATION RECORD IN THIS AREA, WHICH JAMA ASKS FOR.]

Thank you for considering this.

Sincerely,
Yunyu Xiao, PhD
Department of Population Health Sciences
Weill Cornell Medicine
yux4008@med.cornell.edu
ORCID 0000-0002-0479-1781""".format(
    n_jurisdictions=C["n_jurisdictions"], n_policies=C["n_policies"],
    n_prespecified=C["n_prespecified"], n_never_evaluated=C["n_never_evaluated"],
    evals=None, n_evals=C["n_evaluations_table2"])


def table(headers, rows, cls=""):
    h = "<tr>" + "".join(f"<th>{c}</th>" for c in headers) + "</tr>"
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead>{h}</thead><tbody>{b}</tbody></table></div>'


SEPARATION = [
    ("What it is",
     "Infrastructure. A database that outlives any single paper and that other "
     "people will query.",
     "An argument. A time-limited intervention in a live policy debate."),
    ("Success looks like",
     "The database is cited, reused, and versioned. A v2.0 exists in two years.",
     "The papers land while the policy window is open. Nobody reuses the corpus."),
    ("Clock",
     "None. Quality dominates. A delay costs nothing.",
     "Real. Australia's law took effect in December 2025 and the evaluations are "
     "arriving now. Late is worthless."),
    ("Corpus",
     "103,528 records, 1989 to 2026, grows with each harvest.",
     f"{TOTAL_RETRIEVED:,} retrieved, screened down to hundreds. Frozen at "
     f"submission and never touched again."),
    ("Where the work is",
     "Recall and classification. Getting the corpus complete and the labels right.",
     "Appraisal and argument. The corpus is a means, not the product."),
    ("People",
     "Two coders plus an adjudicator on 300 records, then ongoing maintenance. "
     "This is a standing role.",
     "One or two people in a sprint. Do not staff it like a database project."),
    ("Repository",
     "<code>suicide-research-evidence-database</code>, public, tagged releases "
     "with Zenodo DOIs.",
     "<code>screen-time-evidence-policy</code>, not yet created. One release at "
     "submission, then archived."),
    ("Biggest risk",
     "Silent incompleteness. Web of Science just showed 37% of 2024 records "
     "missing, including in the specialty journals.",
     "Scope creep. Every new policy is tempting and none of them change the "
     "finding."),
    ("Data licensing",
     "Open sources only in the public release. Web of Science records are used "
     "for coverage comparison and excluded from redistribution.",
     "Open sources only. No licensing constraint."),
]


def main() -> int:
    css = f"""
:root {{ --ink:{INK}; --mid:{MID}; --light:{LIGHT}; --rule:{RULE}; --red:{RED};
  --redl:{REDL}; --blue:{BLUE}; --bluel:{BLUEL}; --panel:{PANEL}; --green:{GREEN}; }}
*{{box-sizing:border-box}}
body{{font-family:{FONT};color:var(--ink);margin:0;background:#fff;
  line-height:1.62;font-size:15px}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 28px 80px}}
header.top{{border-bottom:3px solid var(--blue);margin-bottom:30px;padding:44px 0 24px}}
header.top .kicker{{color:var(--blue);font-weight:bold;font-size:12px;
  letter-spacing:2px;margin-bottom:10px}}
h1{{font-size:32px;line-height:1.2;margin:0 0 12px}}
header.top p{{color:var(--mid);font-size:16px;margin:0;max-width:840px}}
h2{{font-size:23px;margin:48px 0 6px;padding-bottom:8px;border-bottom:2px solid var(--rule)}}
h3{{font-size:17px;margin:26px 0 8px}}
h4{{font-size:14px;margin:18px 0 6px;color:var(--mid);letter-spacing:.6px}}
p,li{{margin:9px 0}} ul,ol{{padding-left:22px}}
a{{color:var(--blue);text-decoration:none;border-bottom:1px solid #cfe0ee}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;
  background:#f2f2f2;padding:1px 5px;border-radius:3px}}
pre{{background:#fbfbfb;border:1px solid var(--rule);padding:18px 20px;
  border-radius:5px;overflow-x:auto;font-size:13px;line-height:1.65;
  white-space:pre-wrap;font-family:{FONT}}}
.diagram{{border:1px solid var(--rule);border-radius:5px;padding:8px;margin:20px 0 8px}}
.cap{{font-size:12.5px;color:var(--mid);margin:0 0 26px}}
.tw{{overflow-x:auto;margin:14px 0 22px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{background:#eee;text-align:left;padding:9px 11px;font-size:12px;
  border:1px solid var(--rule);vertical-align:top}}
td{{padding:9px 11px;border:1px solid var(--rule);vertical-align:top}}
tbody tr:nth-child(even){{background:#fbfbfb}}
table.sep td:first-child{{width:14%;font-weight:bold}}
table.sep td:nth-child(2){{width:43%}}
.warn{{background:var(--redl);border-left:3px solid var(--red);padding:12px 16px;
  border-radius:0 4px 4px 0;margin:16px 0}}
.note{{background:var(--bluel);border-left:3px solid var(--blue);padding:12px 16px;
  border-radius:0 4px 4px 0;margin:16px 0}}
.ok{{background:#eef6f1;border-left:3px solid var(--green);padding:12px 16px;
  border-radius:0 4px 4px 0;margin:16px 0}}
.decision{{border:1.5px solid var(--ink);border-radius:5px;padding:2px 20px 14px;
  margin:20px 0}}
.decision .lbl{{display:inline-block;background:var(--ink);color:#fff;font-size:11px;
  font-weight:bold;letter-spacing:1.2px;padding:3px 10px;border-radius:0 0 4px 4px}}
.toc{{background:var(--panel);border:1px solid var(--rule);border-radius:5px;
  padding:18px 24px;margin:24px 0}}
.toc h3{{margin:0 0 8px;font-size:12px;letter-spacing:1.6px;color:var(--mid)}}
.toc ol{{columns:2;column-gap:40px;margin:0;padding-left:20px;font-size:14px}}
footer{{margin-top:56px;padding-top:20px;border-top:1px solid var(--rule);
  font-size:12.5px;color:var(--light)}}
@media print{{.decision,.tw{{break-inside:avoid}} a{{border:none}}}}
"""

    sep_rows = [(a, b, c) for a, b, c in SEPARATION]

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STEP: two-paper plan</title><style>{css}</style></head><body><div class="wrap">

<header class="top">
<div class="kicker">STEP &nbsp;|&nbsp; REVISION PLAN</div>
<h1>Two papers from one evidence base</h1>
<p>How to split the screen time and youth mental health work into a JAMA
argument piece and a systematic review, what each one needs before it can go
out, and how to keep STEP from colliding with SRED.</p>
</header>

<div class="toc"><h3>CONTENTS</h3><ol>
<li><a href="#status">Where things actually stand</a></li>
<li><a href="#recall">What the Undermind reports changed</a></li>
<li><a href="#arch">The two-paper architecture</a></li>
<li><a href="#p1">Paper 1: the argument</a></li>
<li><a href="#p2">Paper 2: the systematic review</a></li>
<li><a href="#meta">Can we meta-analyse? The honest answer</a></li>
<li><a href="#email">Presubmission inquiry email</a></li>
<li><a href="#seq">Sequencing and timeline</a></li>
<li><a href="#sep">Separating SRED and STEP</a></li>
</ol></div>

<h2 id="status">Where things actually stand</h2>
<p>The systematic search finished while this plan was being written. All four
source-arm combinations are complete for every publication year from 2010 to
2026.</p>
{table(["Component", "State", "What is missing"], [
  ("Systematic search",
   f"<b>Complete.</b> {TOTAL_RETRIEVED:,} records across both arms, 17 of 17 years each.",
   "Nothing. Ready to screen."),
  ("Policy inventory",
   f"{C['n_policies']} policies, {C['n_jurisdictions']} jurisdictions, projected into Table 1 from config.",
   "<b>Every entry is <code>verified: false</code>.</b> Details come from secondary coverage, not primary legislative sources."),
  ("Evidence appraisal",
   f"{C['n_evaluations_table2']} evaluations appraised, 5 of them verified against PubMed abstracts.",
   "The full screening pass over the retrieved corpus has not been run."),
  ("Manuscript",
   "Drafted at 2142 words, 348-word abstract, 3 tables, 1 figure, 11 references.",
   "References 12 to 50, author list, and the Undermind recall figure."),
  ("Undermind reports",
   "<b>In your Dropbox STEP folder. I cannot reach them.</b>",
   "This session is bound to a different Mac than the one the folder is connected on, so the bridge tools are unavailable."),
])}
<div class="warn"><b>The one thing blocking substantive revision.</b> I could
not read the Undermind deep-search reports or references, so nothing in this
plan reflects them. The fastest fix is to attach the report files and the
reference export directly to the chat. If you would rather I work from the
folder, the task has to be started again on your computer using the
&ldquo;Run this task&rdquo; picker at the top right of a new Cowork task,
because a session started in the cloud cannot be moved to a different
machine mid-run.</div>

<h2 id="recall">What the Undermind reports changed</h2>
<p>The nine reports and the 147-reference collection have been read and the
recall check has been run. Three things came out of it, one of them serious.</p>

<h3>1. Our systematic search had 45.6% recall, and the reason is instructive</h3>
{table(["", "n", "What it means"], [
  ("Undermind references", "147", "The recursive reference collection."),
  ("Already in our corpus", "67", "Matched by DOI or fuzzy title."),
  ("<b>Missed</b>", "<b>80</b>", "<b>Recall 45.6%.</b> Not all are in scope, but the pattern is diagnostic."),
  ("&nbsp;&nbsp;of which: not in PubMed at all", "51",
   "A <b>database coverage gap</b>. Economics, education, communications, and law journals: <i>Labour Economics</i>, <i>Economics of Education Review</i>, <i>Journal of Health Economics</i>, <i>Marketing Science</i>. Our two sources are biomedical; a large part of the policy-evaluation literature is not."),
  ("&nbsp;&nbsp;of which: in PubMed but not retrieved", "24",
   "<b>Our query was too narrow.</b> This is the fixable half, and it includes a citation we depend on."),
  ("&nbsp;&nbsp;could not be checked", "5", "No DOI in the export."),
])}

<div class="warn"><b>The serious one. Our own reference 7 fails our own
systematic search.</b> Barnes et al. (<i>BMJ</i> 2026), the Australian
regression discontinuity that the manuscript leans on, is indexed in PubMed and
matches our intervention clause. It fails on one clause only: the requirement
that a mental health or suicide term appear in the title or abstract. The study
measured platform use, not symptoms.
<br><br>
That is not a typo. It is the same mistake the paper accuses the field of
making. We already knew not to require <i>design</i> terms, because the
proportion evaluated is what we are measuring. We then required <i>outcome</i>
terms, which excluded every evaluation whose only outcome was behavioural,
which is most of them, and which is the paper's central finding. A query that
presupposes the outcome cannot count which outcomes were chosen.</div>

<div class="ok"><b>Fixed.</b> Arm A no longer requires an outcome term.
Outcome class is coded at appraisal, exactly as design already was. PubMed Arm A
goes from 4,995 to <b>13,132</b> records, and the corrected query retrieves
Barnes et al. The re-harvest is running. This correction belongs in the
Methods section as a stated design decision, not buried.</div>

<div class="note"><b>The other half needs Web of Science, which you now have.</b>
51 of the 80 misses are not in PubMed or Europe PMC at all. WoS indexes
<i>Labour Economics</i>, <i>Economics of Education Review</i>, <i>Journal of
Health Economics</i>, and <i>Marketing Science</i>, where several of the best
policy evaluations live. The Starter API returns no abstracts, so it cannot be
a primary source, but it can identify the records by DOI so their abstracts can
be recovered from Crossref or Europe PMC. Adding it closes the coverage gap the
recall check just exposed.</div>

<h3>2. Undermind surfaced evidence that strengthens the argument</h3>
<p>Several of these are better than what the draft currently uses.</p>
{table(["Finding", "Why it matters"], [
  ("<b>The experimental evidence is from adults.</b> Lopes et al. (2026) pooled 35 randomized studies of social media constraints, 7,160 participants, <b>mean age 27.3 years</b>. Burnell et al. (2025) pooled 32 trials, 5,544 participants, all college students or adults, mean age about 23.",
   "This is the strongest single addition available. The trials cited to justify restricting <i>children</i> were run on <i>adults</i>. It converts the argument from &ldquo;the remedy is untested&rdquo; to the sharper and more defensible &ldquo;the remedy was tested on the wrong population.&rdquo;"),
  ("<b>Restriction can reverse in heavy users.</b> Jo et al. (2020) used Korean game-log data: the shutdown law reduced play among lighter users, the effect diminished as prior use rose, and became <i>positive</i> among the heaviest. Spending did not fall.",
   "Far stronger than survey self-report, and it shows the policy failed most clearly in exactly the group it targeted."),
  ("<b>Compliance without benefit.</b> Zhou et al. (2024): 84.7% of heavy gamers reported complying with China's restriction, but 59% shifted to short videos, 51% to television or anime, 23% to other games.",
   "Direct evidence for the substitution mechanism the manuscript argues is untested. Compliance and benefit are separable, and here they separate."),
  ("<b>School phone bans have no randomized evidence.</b> Campbell et al. (2024): scoping review, 22 studies, 12 countries, no randomized trials, only 5 difference-in-differences. King et al. (2024): controlled South Australian natural experiment, no effect on problematic use, bullying, or belonging.",
   "Replaces the single SMART Schools citation with a body of evidence, and covers more than 30 US states are about to adopt."),
  ("<b>Severe outcomes do exist, from broadband natural experiments.</b> Arenas-Arroyo et al. (2025) and Donati et al. (2025) use fiber and broadband rollout with hospital records and find increases in self-harm and, in Spain, suicide mortality among girls.",
   "The current draft says suicide outcomes are absent. That is true of <i>policy evaluations</i> and false of the wider literature. The claim must be narrowed to stay accurate."),
  ("<b>A meta-analysis of screen activity and self-harm already exists.</b> Chen et al. (2024), <i>Psychiatry Research</i>, longitudinal studies.",
   "Changes what Paper 2 can claim as novel. It must be cited and positioned against, not ignored."),
])}

<div class="warn"><b>A citation error the reports exposed.</b> Reference 6
conflated two different papers: Lee, Kim and Hong (<i>Telematics and
Informatics</i>, 2017) and Choi et al. (<i>J Adolesc Health</i>, 2018, PMID
29434003). The manuscript carried the 2017 authors and title with the 2018
journal and PMID. Now corrected to Choi et al. Reference 7 has its full author
list. This is what the <code>[Verify ...]</code> flags were for.</div>

<h3>3. Undermind independently reached your argument</h3>
<p>Its proposed title is <i>Before Recommending Restriction: Test the Policy,
Not Just the Problem</i>, and its four claims are close to the manuscript's.
Treat that as convergent validation of the thesis rather than as drafting to
reuse. It also independently concluded that a single pooled estimate across
national laws, school rules, and short-term student experiments would be
<i>&ldquo;statistically impressive but scientifically uninterpretable&rdquo;</i>,
which is the same judgment reached below on independent grounds.</p>

<h2 id="arch">The two-paper architecture</h2>
<div class="diagram">{diagram()}</div>
<p class="cap"><b>Figure.</b> The shared evidence base feeds both papers, but
each carries a different kind of claim. The firewall at the bottom is the part
that has to survive editorial scrutiny at two journals at once.</p>

<h2 id="p1">Paper 1: the argument</h2>
<p>The current draft is a 3000-word Special Communication. You asked about a
Viewpoint. These are genuinely different papers and the choice determines
roughly two weeks of work.</p>

<div class="decision"><span class="lbl">DECISION 1</span>
<h3>Viewpoint or Special Communication?</h3>
{table(["", "Viewpoint", "Special Communication"], [
  ("Budget", "1200 words, 7 references, 1 display item, 4 authors",
   "3000 words, 50 references, 4 display items, no author cap"),
  ("Presubmission inquiry", "<b>Not required.</b> Submit directly.",
   "<b>Required at JAMA.</b> Not required at JAMA Network Open or JAMA Pediatrics."),
  ("What survives the cut",
   "Korea, Australia, the never-evaluated count, the zero-suicide-outcomes finding, one figure.",
   "All three tables, the full inventory, the research agenda, the limitations."),
  ("What you lose", "The inventory table. Table 1 is the paper's evidence and it will not fit.",
   "Nothing, but you wait for an editor's reply before submitting."),
  ("Time to decision", "Fast. Days to weeks.", "Add two to six weeks for the inquiry."),
])}
<p><b>Recommendation: Special Communication, with the Viewpoint held in
reserve.</b> The reason is Table 1. The argument rests on a systematic
inventory showing that {C['n_never_evaluated']} of {C['n_policies']} policies
were never evaluated, and a Viewpoint's single display item cannot carry that
table and the figure. Without the table the piece becomes opinion, which is a
weaker version of the same claim and easier for the professional bodies to
dismiss. Send the presubmission inquiry, and if JAMA declines, the same
manuscript goes to JAMA Network Open or JAMA Pediatrics unchanged, since both
take Special Communications at the identical 3000-word and four-item budget
with no inquiry required.</p>
</div>

<h4>REVISION TASKS, PAPER 1</h4>
<ol>
<li><b>Verify the policy inventory against primary sources.</b> This is the
highest-value remaining work and the biggest reviewer risk. All
{C['n_policies']} entries are currently unverified. Each needs the legal
instrument itself, not press coverage: the Australian Act, the Kagawa ordinance
and the 2022 Takamatsu judgment, the Korean statute and its 2021 repeal, the
NPPA notice, Brazil's Law 15.100/2025, France's Loi 2018-698, the UK Online
Safety Act, the Danish announcement, and the two Swedish measures. Undermind's
Query 2 was written for exactly this.</li>
<li><b>Fold in the Undermind recall figure.</b> One sentence in Methods
reporting what an independent search found that ours did not. An independent
search finding nothing new is the strongest defence available at review.</li>
<li><b>Write references 12 to 50.</b> Mostly the primary legislative sources
from task 1, plus the specification-curve literature and the experimental
reduction trials.</li>
<li><b>Resolve every <code>[Verify ...]</code> flag.</b> Author lists on
references 6 to 9 and 11 are still unconfirmed.</li>
<li><b>Name the coauthors.</b> Three affiliation placeholders remain, and the
CRediT statement cannot be written until they are filled.</li>
</ol>

<h2 id="p2">Paper 2: the systematic review</h2>
<p>This is the paper that makes Paper 1 citable rather than merely assertive.
It is also the one with real methodological requirements.</p>

<div class="warn"><b>Register with PROSPERO before screening, and disclose the
timing.</b> The searches have already run, but no screening decisions have been
made, so registration now is still legitimate. What is not legitimate is
implying the registration preceded the search. State plainly in the manuscript
that the protocol was registered after the searches were executed and before
any record was screened. Reviewers can see the dates, and volunteering the
sequence costs nothing while being caught omitting it is fatal.</div>

<h4>WHAT PAPER 2 CONTAINS</h4>
<ol>
<li><b>A PRISMA 2020 flow diagram</b> from {TOTAL_RETRIEVED:,} retrieved
records through deduplication, screening, and full-text assessment to the
included set. The query strings are already written to
<code>data/interim/queries/</code>, so PRISMA-S reporting is achievable.</li>
<li><b>Risk-of-bias assessment.</b> ROBINS-I for the policy evaluations, which
are all non-randomised, and RoB 2 for any trial in Arm B. Two independent
assessors with a kappa.</li>
<li><b>A narrative synthesis of the policy evaluations</b>, because they cannot
be pooled. See the next section.</li>
<li><b>A meta-analysis of the risk-factor evidence</b>, where the estimates are
poolable.</li>
<li><b>GRADE certainty ratings</b> for each body of evidence. Applying GRADE to
the policy evidence and reporting what it yields is itself a finding, given how
rarely the policy documents apply it to their own basis.</li>
</ol>

<h4>WHERE IT GOES</h4>
{table(["Journal", "Fit", "Constraint"], [
  ("<b>JAMA Pediatrics</b>", "First choice. Right audience, Q1 rank 1 in pediatrics, and the topic is squarely theirs.",
   "Presubmission inquiry required only for a systematic review <i>without</i> meta-analysis. Including the Arm B meta-analysis removes that requirement."),
  ("JAMA Network Open", "Strong fallback. Same 3000-word budget, open access, no inquiry.",
   "APC applies."),
  ("Lancet Child &amp; Adolescent Health", "High visibility, policy-facing readership.",
   "Different format conventions; would need reformatting from the JAMA draft."),
  ("Pediatrics", "Good reach into the AAP audience, which is one of the bodies the argument addresses.",
   "Publishing the critique in the AAP's own journal is either the strongest possible venue or a conflict. Worth a conversation."),
])}

<h2 id="meta">Can we meta-analyse? The honest answer</h2>
<p>Partly, and the asymmetry is the most interesting thing in the whole
project.</p>

<p>Undermind reached the same conclusion independently and named the design:
<b>component meta-analyses</b>, one per comparable intervention-outcome pair,
never one omnibus pool. Specifically: randomized social media restriction and
depressive symptoms; the same and anxiety or distress; randomized smartphone
reduction and wellbeing; the same and sleep; policy interventions and targeted
device use. Everything else gets structured narrative synthesis with GRADE.</p>
<div class="ok"><b>Arm B, the risk-factor evidence: yes.</b> Longitudinal
studies of screen or social media exposure and adolescent mental health report
a common estimand often enough that pooling is defensible. Expect
heterogeneity, so use random effects, prespecify subgroups by age band, sex,
and exposure metric, and run a specification-curve or influence analysis given
the known sensitivity of this literature to analytic choices.</div>

<div class="warn"><b>Arm A, the policy evaluations: no, and that is the
finding.</b> There are {C['n_evaluations_table2']} of them. They use
difference-in-differences, sharp regression discontinuity, a cross-sectional
school comparison, and an uncontrolled cohort. Their outcomes are minutes of
internet use per day, the proportion still holding accounts, and a wellbeing
scale. There is no common estimand. Pooling them would produce a number with no
interpretation, and any competent reviewer would say so.</div>

<p><b>Make the asymmetry the headline.</b> Paper 2's central result is not a
pooled effect size. It is this: <i>the evidence for the premise can be
meta-analysed and the evidence for the remedy cannot, because there is not
enough of it and what exists shares no common measure.</i> That is a
quantitative demonstration of Paper 1's argument rather than a restatement of
it, and it is a genuinely novel structure for a review in this area. Report the
pooled estimate for the exposure-outcome link, then report the
non-poolability of the policy evidence as a formal result with the reasons
enumerated.</p>

<h2 id="email">Presubmission inquiry email</h2>
<p>JAMA's instructions specify email to the editorial office, addressed to
Kristin Walter, MD, at <code>kristin.walter@jamanetwork.com</code>. Confirm
that address on the
<a href="https://jamanetwork.com/journals/jama/pages/instructions-for-authors">Instructions
for Authors</a> page before sending, since editorial contacts change. They ask
for a detailed outline, a summary of the supporting literature, and a summary
of your publication record in the field; a completed draft may be sent
instead of an outline.</p>
<p>Two placeholders are marked in capitals. I have not sent this and will not
send anything on your behalf.</p>
<pre>{escape(EMAIL)}</pre>

<h2 id="seq">Sequencing and timeline</h2>
<p>The tension is that Paper 1 is time-sensitive and Paper 2 is not, but Paper
1 is stronger if it can cite Paper 2.</p>
<div class="note"><b>Resolve it with a preprint.</b> Post Paper 2 to medRxiv
when the systematic review is drafted. Paper 1 then cites a citable, dated,
DOI-bearing object rather than &ldquo;manuscript in preparation&rdquo;, which
carries no weight with reviewers. medRxiv posting does not compromise
subsequent journal submission at any of the target journals.</div>
{table(["Order", "Step", "Blocks what"], [
  ("1", "Attach the Undermind reports and references so the recall check can run.", "Everything downstream in Methods."),
  ("2", "Register the protocol with PROSPERO.", "Paper 2 screening. Must precede it."),
  ("3", "Verify the 13 policy inventory entries against primary sources.", "Both papers. Table 1 is not citable until this is done."),
  ("4", "Send the presubmission inquiry.", "Paper 1 submission. Runs in parallel with 3."),
  ("5", "Screen and appraise the retrieved corpus; build the PRISMA diagram.", "Paper 2."),
  ("6", "Draft Paper 2; post to medRxiv.", "Paper 1's strongest citation."),
  ("7", "Finalise Paper 1 against whichever venue replied; submit.", "Nothing."),
])}

<h2 id="sep">Separating SRED and STEP</h2>
<p>These two projects look similar because STEP borrowed SRED's pipeline. They
are not similar, and treating them the same way will hurt both. SRED is
infrastructure; STEP is an intervention in a debate.</p>
{table(["Dimension", "SRED", "STEP"], sep_rows, cls="sep")}

<h3>The code question</h3>
<p>STEP currently duplicates SRED's harvest layer. There are two defensible
answers and one bad one.</p>
<ul>
<li><b>Extract a shared harvest package.</b> <code>http.py</code>,
<code>schema.py</code>, and <code>sources/</code> are roughly 600 lines and
they are where the expensive bug fixes live: per-host rate limits, soft-error
detection inside HTTP 200 bodies, recursive batch halving on 413, the
resumable shard markers. Those fixes should exist once. <b>This is the
recommendation</b>, because the redbook implies there will be a third project
and fixing the same bug twice is already happening.</li>
<li><b>Keep them fully separate</b> and accept the drift. Defensible if STEP is
genuinely the last one.</li>
<li><b>Do not</b> merge the projects into one repository. Their release
cadences, licences, and audiences differ, and a reviewer following the STEP
data availability statement should not land in a 300 MB suicide research
database.</li>
</ul>
<p>Keep <code>classify/</code> and <code>analysis/</code> project-specific.
SRED classifies communication type and methodology; STEP appraises study design
and outcome class. Those should never share code.</p>

<h3>Practical separation rules</h3>
<ul>
<li><b>Separate repositories, separate DOIs, separate release cadence.</b> SRED
gets versioned releases indefinitely. STEP gets one release at submission and
is then archived.</li>
<li><b>Separate RAs.</b> SRED coding is a standing role with calibration and
adjudication. STEP appraisal is a sprint. A person doing both will apply SRED's
codebook habits to STEP's appraisal schema, and the two are not compatible.</li>
<li><b>Separate meetings.</b> A joint meeting will always be spent on whichever
is on fire, which will always be STEP, and SRED will quietly stall.</li>
<li><b>One shared rule.</b> Both follow the redbook: no number typed by hand,
verification re-derives every claim, and the build fails on an unresolved
placeholder. That is what makes the two projects feel like one lab rather than
two hobbies.</li>
</ul>

<footer>
STEP revision plan. Counts render from
<code>data/processed/table_counts.json</code> and
<code>search_yield.json</code>, so this document cannot drift from the
database. Nothing here reflects the Undermind reports, which were not
reachable from this session.
</footer>

</div></body></html>"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} ({len(doc)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
