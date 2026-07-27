#!/usr/bin/env python3
"""Figure 1: the inferential chain from exposure to policy benefit.

The figure exists to make one point visually that the text makes in a
paragraph: the association between screen use and adolescent distress sits
*before* the chain that a restriction policy depends on, and each of the three
links in that chain carries a different and weaker grade of evidence than the
premise does.

Layout is computed rather than hard-coded, so that editing the text of a panel
grows the panel instead of overflowing it. Rendered as SVG (the source of
record, vector, editable) plus a 3x PNG and a PDF for submission.

Usage
-----
    python scripts/04_make_figure.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"

(ROOT / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("figure")

FONT = "Arial, Helvetica, sans-serif"

INK = "#111111"
MID = "#555555"
LIGHT = "#8c8c8c"
RULE = "#c9c9c9"
FILL_PREMISE = "#ebebeb"
FILL_PANEL = "#fafafa"

MARGIN = 36
PREMISE_W = 262
IMPLY_GAP = 116
NODE_W = 190
NODE_H = 104
NODE_GAP = 66
PANEL_W = 244
PANEL_PAD = 15

W = MARGIN * 2 + PREMISE_W + IMPLY_GAP + NODE_W * 4 + NODE_GAP * 3

# Evidence grades. Three levels only; finer gradations would imply a precision
# the underlying literature does not support.
GRADE = {
    "tested_null": ("Tested. Effect near zero.", 3),
    "untested_causal": ("Association only. Not tested at policy scale.", 1),
    "not_addressed": ("Not addressed.", 0),
}

LINKS = [
    ("LINK 1", "Does the policy reduce use?", "tested_null",
     "Korea, difference-in-differences, n ≈ 244 000: −3.6 min/d in "
     "year 1, decaying to zero by year 3, with no change in internet "
     "addiction or sleep. Australia, regression discontinuity: >85% of "
     "under-16s still using restricted platforms at 3 months. England, 30 "
     "schools: lower use during school hours, no difference in total use."),
    ("LINK 2", "Does reduced use improve mental health?", "untested_causal",
     "Prospective cohorts establish the association and its age gradient. "
     "Experimental reduction trials are short, small, and largely in older "
     "samples. No policy evaluation to date has reported a mental health "
     "effect."),
    ("LINK 3", "Is the achievable reduction large enough to matter?",
     "not_addressed",
     "The exposure contrast in the cohort evidence is hours per day. The "
     "largest reduction any evaluated policy has produced is minutes per "
     "day. Whether that magnitude could move a symptom scale has, to our "
     "knowledge, never been formally addressed."),
]

NODES = [
    "Restriction policy is enacted",
    "Young people's actual use falls",
    "Falling use improves mental health",
    "Population benefit: fewer depressive episodes, less self-harm, fewer suicides",
]


def wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def chars_for(px: float, size: float) -> int:
    """Rough character budget for a box of ``px`` at Arial ``size``.

    Arial's average lowercase advance is close to 0.50 em for running prose.
    Using 0.52 leaves a little slack so a line of wide characters does not
    escape the box.
    """
    return max(8, int(px / (size * 0.52)))


class SVG:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.parts = w, h, []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, size=13, weight="normal", fill=INK,
             anchor="start", style="normal", spacing=0):
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
            f'fill="{fill}" text-anchor="{anchor}"'
            + (f' letter-spacing="{spacing}"' if spacing else "")
            + f'>{escape(s)}</text>')

    def para(self, x, y, s, size=12, width=44, lh=15, fill=MID,
             weight="normal", anchor="start"):
        lines = wrap(s, width)
        for i, line in enumerate(lines):
            self.text(x, y + i * lh, line, size=size, fill=fill,
                      weight=weight, anchor=anchor)
        return y + (len(lines) - 1) * lh

    def rect(self, x, y, w, h, fill="#ffffff", stroke=INK, sw=1.4, rx=3):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                 f'height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
                 f'y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y, x2, stroke=INK, sw=1.7):
        self.line(x1, y, x2 - 9, y, stroke=stroke, sw=sw)
        self.add(f'<path d="M {x2:.1f} {y:.1f} L {x2 - 10:.1f} {y - 5.5:.1f} '
                 f'L {x2 - 10:.1f} {y + 5.5:.1f} Z" fill="{stroke}"/>')

    def render(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>'
                + "".join(self.parts) + "</svg>")


def grade_marks(s: SVG, x: float, y: float, filled: int, total: int = 3) -> None:
    """Three squares, n filled. A grade that survives grayscale printing."""
    for i in range(total):
        s.rect(x + i * 16, y, 11, 11,
               fill=(INK if i < filled else "#ffffff"),
               stroke=(INK if i < filled else "#9a9a9a"), sw=1.1, rx=1.5)


def panel_height() -> float:
    """Tallest panel wins, so all three align.

    The arithmetic below mirrors the drawing sequence in :func:`build` step for
    step. Keeping them in sync by hand is fragile, but the alternative is a
    two-pass layout engine for three boxes, which is worse.
    """
    inner = PANEL_W - 2 * PANEL_PAD
    q_chars = chars_for(inner, 12.5)
    g_chars = chars_for(inner, 11.2)
    b_chars = chars_for(inner, 10.8)
    tallest = 0.0
    for _, q, grade, ev in LINKS:
        nq = len(wrap(q, q_chars))
        nl = len(wrap(GRADE[grade][0], g_chars))
        nb = len(wrap(ev, b_chars))
        h = (24 + (nq - 1) * 16          # question block
             + 16 + 11 + 16              # gap, grade marks, gap
             + 4 + (nl - 1) * 14         # grade label
             + 12 + 18 + (nb - 1) * 13   # rule, gap, body
             + 20)                       # descender plus bottom padding
        tallest = max(tallest, h)
    return tallest


def build() -> tuple[str, int]:
    ph = panel_height()
    head_h = 76
    chain_y = head_h + 34
    panel_y = chain_y + NODE_H + 62
    foot_y = panel_y + ph + 34
    h = int(foot_y + 76)

    s = SVG(W, h)

    s.text(MARGIN, 34, "The inferential chain from exposure to policy benefit",
           size=17.5, weight="bold")
    s.text(MARGIN, 57, "Each link carries a different grade of evidence. Only "
                       "the premise, at left, is well supported.",
           size=13, fill=MID)
    s.line(MARGIN, head_h, W - MARGIN, head_h, stroke=RULE, sw=1)

    # ---------------------------------------------------------------- premise
    prem_h = NODE_H + 56
    py = chain_y - 26
    s.rect(MARGIN, py, PREMISE_W, prem_h, fill=FILL_PREMISE, stroke=INK, sw=1.4)
    inner = PREMISE_W - 30
    s.text(MARGIN + 15, py + 27, "PREMISE", size=11, weight="bold", fill=MID,
           spacing=1.4)
    s.para(MARGIN + 15, py + 51,
           "Heavier social media use is prospectively associated with more "
           "depressive symptoms in adolescents.",
           size=12.5, width=chars_for(inner, 12.5), lh=16, fill=INK)
    s.line(MARGIN + 15, py + prem_h - 60, MARGIN + PREMISE_W - 15,
           py + prem_h - 60, stroke=LIGHT, sw=0.9)
    s.para(MARGIN + 15, py + prem_h - 42,
           "Cohort, ages 12-19 y. Risk difference, 6.3 per 100 (95% CI, "
           "2.7-9.9) for >2 h vs <1 h daily use.",
           size=11.2, width=chars_for(inner, 11.2), lh=14, fill=MID)

    # "does not imply" break in the chain
    bx0 = MARGIN + PREMISE_W
    bcx = bx0 + IMPLY_GAP / 2
    bcy = chain_y + NODE_H / 2
    s.line(bx0 + 10, bcy, bx0 + IMPLY_GAP - 10, bcy, stroke=LIGHT, sw=1.4,
           dash="5 4")
    s.add(f'<path d="M {bcx - 9:.1f} {bcy - 9:.1f} L {bcx + 9:.1f} '
          f'{bcy + 9:.1f}" stroke="{INK}" stroke-width="2"/>')
    s.add(f'<path d="M {bcx + 9:.1f} {bcy - 9:.1f} L {bcx - 9:.1f} '
          f'{bcy + 9:.1f}" stroke="{INK}" stroke-width="2"/>')
    s.text(bcx, bcy - 20, "does not imply", size=11.5, fill=MID,
           anchor="middle", style="italic")

    # ------------------------------------------------------------ chain nodes
    x0 = MARGIN + PREMISE_W + IMPLY_GAP
    xs = [x0 + i * (NODE_W + NODE_GAP) for i in range(4)]
    n_chars = chars_for(NODE_W - 24, 12.5)
    for nx, label in zip(xs, NODES):
        s.rect(nx, chain_y, NODE_W, NODE_H, fill="#ffffff", stroke=INK, sw=1.5)
        lines = wrap(label, n_chars)
        ty = chain_y + NODE_H / 2 - (len(lines) - 1) * 8 + 5
        for j, ln in enumerate(lines):
            s.text(nx + NODE_W / 2, ty + j * 16, ln, size=12.5,
                   anchor="middle", fill=INK)

    # A note in the space left of the evidence panels, which would otherwise be
    # blank, stating the distinction the figure is built around.
    note_w = PREMISE_W + IMPLY_GAP - 20
    s.text(MARGIN, panel_y + 24, "WHY THE DISTINCTION MATTERS", size=11,
           weight="bold", fill=MID, spacing=1.4)
    ny2 = s.para(MARGIN, panel_y + 50,
                 "The premise concerns an exposure contrast of hours per day, "
                 "estimated observationally. The chain concerns what a law "
                 "achieves. Policy debate has largely treated these as one "
                 "claim.",
                 size=11.8, width=chars_for(note_w, 11.8), lh=15.5, fill=INK)
    s.para(MARGIN, ny2 + 26,
           "A policy can be no better evidenced than the weakest link it "
           "depends on. Here that link has never been examined.",
           size=11.2, width=chars_for(note_w, 11.2), lh=14.5, fill=MID)

    # ---------------------------------------------------- links and evidence
    ay = chain_y + NODE_H / 2
    pin = PANEL_W - 2 * PANEL_PAD
    for i, (tag, q, grade, ev) in enumerate(LINKS):
        ax1, ax2 = xs[i] + NODE_W, xs[i + 1]
        cx = (ax1 + ax2) / 2
        s.arrow(ax1 + 7, ay, ax2 - 7)
        s.text(cx, ay - 15, tag, size=10.5, weight="bold", anchor="middle",
               fill=MID, spacing=1.1)

        bx = cx - PANEL_W / 2
        s.line(cx, ay + 14, cx, panel_y - 8, stroke=RULE, sw=1, dash="3 4")
        s.rect(bx, panel_y, PANEL_W, ph, fill=FILL_PANEL, stroke=RULE, sw=1)

        y = panel_y + 24
        y = s.para(bx + PANEL_PAD, y, q, size=12.5,
                   width=chars_for(pin, 12.5), lh=16, fill=INK, weight="bold")
        y += 16
        grade_marks(s, bx + PANEL_PAD, y, GRADE[grade][1])
        y += 11 + 16
        y = s.para(bx + PANEL_PAD, y + 4, GRADE[grade][0], size=11.2,
                   width=chars_for(pin, 11.2), lh=14, fill=INK, weight="bold")
        y += 12
        s.line(bx + PANEL_PAD, y, bx + PANEL_W - PANEL_PAD, y, stroke=RULE,
               sw=0.9)
        s.para(bx + PANEL_PAD, y + 18, ev, size=10.8,
               width=chars_for(pin, 10.8), lh=13, fill=MID)

    # ------------------------------------------------------------------ foot
    s.line(MARGIN, foot_y, W - MARGIN, foot_y, stroke=RULE, sw=1)
    s.text(MARGIN, foot_y + 25,
           "Of 13 policies inventoried, 1 was enacted with a prespecified "
           "evaluation. Of 5 published evaluations, none reported a suicide "
           "or self-harm outcome.", size=12.5, weight="bold", fill=INK)
    s.text(MARGIN, foot_y + 46,
           "Filled squares indicate the evidence available for that link: "
           "3 of 3, tested with an informative result; 1 of 3, association "
           "only; 0 of 3, not addressed.", size=11, fill=LIGHT)
    return s.render(), h


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    svg, h = build()
    (FIG / "figure1.svg").write_text(svg)
    log.info("wrote %s (%d x %d)", FIG / "figure1.svg", W, h)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode(),
                         write_to=str(FIG / "figure1.png"),
                         output_width=W * 3, output_height=h * 3)
        cairosvg.svg2pdf(bytestring=svg.encode(),
                         write_to=str(FIG / "figure1.pdf"))
        log.info("wrote figure1.png (3x) and figure1.pdf")
    except Exception as exc:  # pragma: no cover
        log.warning("raster/pdf conversion unavailable: %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
