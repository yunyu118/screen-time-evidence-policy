#!/usr/bin/env python3
"""Build Tables 1-3 and the counts the manuscript asserts, from config.

Nothing in the manuscript's tables is typed by hand. Table 1 is a projection of
``config/policy_inventory.yml``; Table 2 and Table 3 are projections of
``config/evaluations.yml``. The counts quoted in the abstract and the
Observations section (13 policies, 10 jurisdictions, 1 prespecified, 6 never
evaluated, 11 of 13 on correlational evidence alone) are recomputed here and
written to ``data/processed/table_counts.json`` so that ``05_verify.py`` can
fail the build if the prose and the config drift apart.

Outputs
-------
    manuscript/tables.md          Markdown, for the manuscript build
    data/processed/table1.csv     Machine-readable, for the repository
    data/processed/table2.csv
    data/processed/table3.csv
    data/processed/table_counts.json
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
OUT = ROOT / "data" / "processed"
MS = ROOT / "manuscript"

(ROOT / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(ROOT / "logs" / "tables.log")])
log = logging.getLogger("tables")

# Rendering maps. Kept explicit rather than derived by string munging so that a
# typo in the config produces a KeyError instead of a plausible-looking cell.
EVAL_STATUS = {
    "evaluated_early": "Early evaluation published",
    "evaluated_after": "Evaluated after the fact",
    "evaluated_partial": "Partial, behaviour only",
    "not_evaluated": "None published",
    "largely_not_evaluated": "Largely none published",
    "not_applicable_advisory": "Not applicable (advisory)",
    "not_yet_in_force": "Not yet in force",
}
EVIDENCE = {
    "correlational_only": "Correlational only",
    "theory_and_correlational": "Theory plus correlational",
    "correlational_and_case_evidence": "Correlational plus case evidence",
}
POLICY_TYPE = {
    "age_restriction": "Minimum age",
    "time_limit": "Daily time limit",
    "curfew": "Time-of-day curfew",
    "school_restriction": "School-hours restriction",
    "platform_duty": "Platform safety duty",
    "guidance": "Guidance",
    "substitution_environment": "Offline substitution",
    "advisory": "Advisory",
}
PRESPEC = {True: "Yes", False: "No", "unknown": "Unknown", None: "Unknown"}

# Which statuses count as "no published evaluation of any outcome". An advisory
# is not an intervention and a policy not yet in force cannot have been
# evaluated, so neither is counted as a failure to evaluate.
NEVER_EVALUATED = {"not_evaluated"}
NOT_ELIGIBLE = {"not_applicable_advisory", "not_yet_in_force"}


def load(name: str) -> dict:
    with open(CONFIG / name) as fh:
        return yaml.safe_load(fh)


def esc(s: str | None) -> str:
    """Collapse whitespace and neutralise pipes so a cell cannot break a row."""
    if s is None:
        return ""
    return " ".join(str(s).split()).replace("|", "/")


def build_table1(policies: list[dict]) -> tuple[str, list[dict]]:
    rows = []
    for p in policies:
        eff = p.get("effective") or p.get("enacted") or ""
        rows.append({
            "Jurisdiction": esc(p["jurisdiction"]),
            "Policy": esc(p["name"]),
            "Type": POLICY_TYPE[p["type"]],
            "In force": esc(eff) + (f" to {p['repealed']}" if p.get("repealed") else ""),
            "Evaluation prespecified": PRESPEC[p.get("evaluation_prespecified")],
            "Evaluation published": EVAL_STATUS[p["evaluation_status"]],
            "Evidence for this intervention at enactment": EVIDENCE[p["evidence_at_enactment"]],
        })
    return md_table(rows), rows


def build_table2(evals: list[dict]) -> tuple[str, list[dict]]:
    rows = []
    for e in evals:
        n = e.get("n_analysed")
        n_txt = ""
        if n:
            n_txt = f"{n:,}" if not e.get("n_note") == "approx" else f"~{n:,}"
        if e.get("n_note") and e["n_note"] not in ("approx",):
            n_txt = (n_txt + f" ({e['n_note']})").strip()
        if not n_txt:
            n_txt = "Not reported"
        measured = ", ".join(o.replace("_", " ") for o in e["outcomes_measured"])
        rows.append({
            "Jurisdiction": esc(e["jurisdiction"]),
            "Policy evaluated": esc(e["policy_short"]),
            "Design": esc(e["design_label"]),
            "N": n_txt,
            "Primary outcome": esc(e["outcome_primary"]),
            "Effect estimate": esc(e["effect_text"]),
            "Mental health or suicide outcome reported":
                "Yes" if any(o in ("mental_health_symptoms", "self_harm",
                                   "suicide_attempt", "suicide_death")
                             for o in e["outcomes_measured"]) else "No",
        })
        _ = measured
    return md_table(rows), rows


def build_table3(priorities: list[dict]) -> tuple[str, list[dict]]:
    rows = []
    for p in sorted(priorities, key=lambda r: r["rank"]):
        rows.append({
            "Priority": str(p["rank"]),
            "Question": esc(p["question"]),
            "Design": esc(p["design"]),
            "Data source": esc(p["data"]),
            "Outcomes": esc(p["outcomes"]),
            "Feasibility": esc(p["feasibility"]),
            "Cost": esc(p["cost"]),
            "Time to result": esc(p["timeline"]),
        })
    return md_table(rows), rows


def md_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r[c] for c in cols) + " |")
    return "\n".join(out)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def counts(policies: list[dict], evals: list[dict], anchor: list[dict]) -> dict:
    status = Counter(p["evaluation_status"] for p in policies)
    prespec = Counter(str(p.get("evaluation_prespecified")) for p in policies)
    evidence = Counter(p["evidence_at_enactment"] for p in policies)
    juris = {p["jurisdiction"].split(" (")[0] for p in policies}

    eligible = [p for p in policies if p["evaluation_status"] not in NOT_ELIGIBLE]
    any_eval = [p for p in eligible
                if p["evaluation_status"] not in NEVER_EVALUATED
                and p["evaluation_status"] != "largely_not_evaluated"]

    mh_reported = sum(
        1 for e in evals
        if any(o in ("mental_health_symptoms", "self_harm", "suicide_attempt",
                     "suicide_death") for o in e["outcomes_measured"]))
    suicide_reported = sum(
        1 for e in evals
        if any(o in ("self_harm", "suicide_attempt", "suicide_death")
               for o in e["outcomes_measured"]))

    c = {
        "n_policies": len(policies),
        "n_jurisdictions": len(juris),
        "jurisdictions": sorted(juris),
        "n_prespecified": prespec.get("True", 0),
        "n_not_prespecified": prespec.get("False", 0),
        "n_prespecified_unknown": prespec.get("unknown", 0) + prespec.get("None", 0),
        "n_never_evaluated": sum(status[s] for s in NEVER_EVALUATED),
        "n_not_eligible_for_evaluation": sum(status[s] for s in NOT_ELIGIBLE),
        "n_with_any_evaluation": len(any_eval),
        "n_correlational_only": evidence["correlational_only"],
        "n_evaluations_table2": len(evals),
        "n_evaluations_reporting_mental_health": mh_reported,
        "n_evaluations_reporting_suicide_or_self_harm": suicide_reported,
        "n_riskfactor_anchor": len(anchor),
        "evaluation_status_counts": dict(status),
        "evidence_at_enactment_counts": dict(evidence),
        "n_verified_policy_entries": sum(1 for p in policies if p.get("verified")),
    }
    return c


def main() -> int:
    inv = load("policy_inventory.yml")
    ev = load("evaluations.yml")
    policies = inv["policies"]
    evals = ev["evaluations"]

    t1_md, t1_rows = build_table1(policies)
    t2_md, t2_rows = build_table2(evals)
    t3_md, t3_rows = build_table3(ev["priorities"])

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "table1.csv", t1_rows)
    write_csv(OUT / "table2.csv", t2_rows)
    write_csv(OUT / "table3.csv", t3_rows)

    c = counts(policies, evals, ev["riskfactor_anchor"])
    (OUT / "table_counts.json").write_text(json.dumps(c, indent=2))
    log.info("counts: %s policies, %s jurisdictions, %s prespecified, "
             "%s never evaluated, %s correlational only",
             c["n_policies"], c["n_jurisdictions"], c["n_prespecified"],
             c["n_never_evaluated"], c["n_correlational_only"])

    body = [
        "## Tables",
        "",
        f"**Table 1.** Enacted and announced policies restricting young people's "
        f"screen, social media, or online gaming access, by evaluation status and "
        f"evidence available at enactment (N = {c['n_policies']} policies, "
        f"{c['n_jurisdictions']} jurisdictions).",
        "",
        t1_md,
        "",
        "Abbreviation: Evidence at enactment refers to the strongest evidence "
        "available for this specific intervention, in this population, at the "
        "time the measure took effect. Correlational evidence that exposure is "
        "associated with poorer mental health is not evidence that restricting "
        "exposure improves it.",
        "",
        "---",
        "",
        "**Table 2.** Published evaluations of youth screen and social media "
        "policies: design, sample, outcomes assessed, and effect estimates.",
        "",
        t2_md,
        "",
        "Abbreviation: CI, confidence interval. Effect estimates are reproduced "
        "as reported in the source. The final column distinguishes evaluations "
        "that measured a mental health or suicide outcome from those that "
        "measured only whether device use changed.",
        "",
        "---",
        "",
        "**Table 3.** Priority research questions, matched study designs, data "
        "sources, and feasibility.",
        "",
        t3_md,
        "",
    ]
    MS.mkdir(parents=True, exist_ok=True)
    (MS / "tables.md").write_text("\n".join(body))
    log.info("wrote %s", MS / "tables.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
