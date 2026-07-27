// Build the submission copy of the STEP manuscript from manuscript_built.md.
//
// docx-js rather than pandoc, for the same reason as in SRED: JAMA's portal
// wants specific mechanics a generic converter does not produce. Arial, US
// Letter, double-spaced body, continuous line numbers, tables that fit.
//
// The one structural addition over the SRED builder is section handling.
// Tables 1 and 3 are seven and eight columns wide, which is unreadable at 6.5
// inches, so the document breaks into three sections: portrait for the text and
// references, landscape for the tables, portrait again for the figure. Line
// numbering restarts continuously across all three.

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, LineRuleType, PageNumber, Header, Footer, PageOrientation,
} = require("docx");

const DIR = __dirname;
const ROOT = path.resolve(DIR, "..");
const SRC = path.join(DIR, "manuscript_built.md");
const OUT = path.join(DIR, "STEP_manuscript.docx");

const FONT = "Arial";
const BODY_SIZE = 22;                              // half-points => 11 pt
const LETTER = { width: 12240, height: 15840 };    // DXA
const MARGIN = { top: 1440, right: 1440, bottom: 1440, left: 1440 };
const MARGIN_LS = { top: 1080, right: 1080, bottom: 1080, left: 1080 };

const TEXT_WIDTH = 9360;                           // 6.5 in portrait
const TEXT_WIDTH_LS = 13680;                       // 9.5 in landscape, matching MARGIN_LS

const DOUBLE = { line: 480, lineRule: LineRuleType.AUTO, after: 0 };
const SINGLE = { line: 240, lineRule: LineRuleType.AUTO, after: 120 };

// --- inline markdown -> TextRun[] -------------------------------------------
function runs(text, { bold = false, italics = false, size = BODY_SIZE } = {}) {
  const out = [];
  const parts = text.split(/(\*\*[^*]+\*\*|(?<!\*)\*[^*]+\*(?!\*)|`[^`]+`)/g);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("**") && part.endsWith("**")) {
      out.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size }));
    } else if (part.startsWith("`") && part.endsWith("`")) {
      out.push(new TextRun({ text: part.slice(1, -1), font: "Courier New", size: size - 2 }));
    } else if (part.startsWith("*") && part.endsWith("*")) {
      out.push(new TextRun({ text: part.slice(1, -1), italics: true, font: FONT, size }));
    } else {
      out.push(new TextRun({ text: part, bold, italics, font: FONT, size }));
    }
  }
  return out.length ? out : [new TextRun({ text: "", font: FONT, size })];
}

function heading(text, level) {
  const size = level === 1 ? 28 : level === 2 ? 26 : 24;
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1
      : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: 300, after: 160 },
    children: runs(text.replace(/^#+\s*/, ""), { bold: true, size }),
  });
}

// --- markdown table -> docx Table -------------------------------------------
// Column widths are proportional to the longest cell in each column rather than
// uniform. With a "Jurisdiction" column and an "Effect estimate" column in the
// same table, equal widths waste half the page.
function mdTable(rows, total) {
  const cols = rows[0].length;
  const weight = Array(cols).fill(0);
  for (const r of rows) {
    r.forEach((c, i) => {
      const len = Math.min(c.length, 140);            // cap runaway cells
      weight[i] = Math.max(weight[i], Math.sqrt(len + 6));
    });
  }
  const sum = weight.reduce((a, b) => a + b, 0);
  let widths = weight.map(w => Math.floor((w / sum) * total));

  // A column whose cells are all short still has to fit its own header word.
  // Without a floor, "Priority" over a column of single digits breaks across
  // two lines as "Priorit / y".
  const MIN = 850;                                   // ~0.59 in
  const short = widths.map((w, i) => (w < MIN ? MIN - w : 0));
  const deficit = short.reduce((a, b) => a + b, 0);
  if (deficit > 0) {
    const donors = widths.map((w, i) => (short[i] ? 0 : w - MIN)).map(v => Math.max(v, 0));
    const pool = donors.reduce((a, b) => a + b, 0);
    widths = widths.map((w, i) =>
      short[i] ? MIN : w - (pool ? Math.floor((donors[i] / pool) * deficit) : 0));
  }
  widths[cols - 1] = total - widths.slice(0, -1).reduce((a, b) => a + b, 0);

  return new Table({
    columnWidths: widths,
    width: { size: total, type: WidthType.DXA },
    rows: rows.map((cells, ri) => new TableRow({
      tableHeader: ri === 0,
      children: cells.map((c, ci) => new TableCell({
        width: { size: widths[ci], type: WidthType.DXA },
        shading: ri === 0
          ? { type: ShadingType.CLEAR, fill: "E8E8E8", color: "auto" }
          : undefined,
        margins: { top: 60, bottom: 60, left: 90, right: 90 },
        children: [new Paragraph({
          spacing: { line: 240, lineRule: LineRuleType.AUTO, after: 0 },
          children: runs(c, { bold: ri === 0, size: 17 }),
        })],
      })),
    })),
  });
}

// --- parse ------------------------------------------------------------------
// Three buckets, switched by the "## Tables" and "## Figure" headings.
const bucket = { body: [], tables: [], figure: [] };
let current = "body";
let tableBuf = [];

function target() { return bucket[current]; }
function tableWidth() { return current === "tables" ? TEXT_WIDTH_LS : TEXT_WIDTH; }

function flushTable() {
  if (!tableBuf.length) return;
  const rows = tableBuf
    .filter(r => !/^\|[\s:|-]+\|$/.test(r.trim()))
    .map(r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim()));
  if (rows.length) {
    target().push(mdTable(rows, tableWidth()));
    target().push(new Paragraph({ text: "", spacing: { after: 200 } }));
  }
  tableBuf = [];
}

const md = fs.readFileSync(SRC, "utf8");
const lines = md.split("\n");

for (const raw of lines) {
  const line = raw.trimEnd();

  if (line.trim().startsWith("|")) { tableBuf.push(line); continue; }
  flushTable();
  if (!line.trim()) continue;

  const h = line.match(/^(#{1,4})\s+(.*)$/);
  if (h) {
    const title = h[2].trim();
    if (/^Tables$/i.test(title)) { current = "tables"; }
    else if (/^Figure$/i.test(title)) { current = "figure"; }
    target().push(heading(title, h[1].length));
    continue;
  }

  // Horizontal rules are section furniture in the markdown; in the rendered
  // document they only add noise inside the tables and figure sections.
  if (/^---+$/.test(line.trim())) {
    if (current !== "body") continue;
    target().push(new Paragraph({
      children: [new TextRun({ text: "", font: FONT, size: BODY_SIZE })],
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "BBBBBB", space: 6 } },
      spacing: { before: 160, after: 200 },
    }));
    continue;
  }

  const li = line.match(/^\s*[-*]\s+(.*)$/);
  if (li) {
    target().push(new Paragraph({
      children: runs(li[1]), bullet: { level: 0 }, spacing: SINGLE,
    }));
    continue;
  }

  // Numbered reference entries: hanging indent, single spaced.
  const nli = line.match(/^\s*(\d+)\.\s+(.*)$/);
  if (nli) {
    target().push(new Paragraph({
      children: runs(`${nli[1]}. ${nli[2]}`),
      spacing: SINGLE,
      indent: { left: 720, hanging: 720 },
    }));
    continue;
  }

  // Each table starts a fresh landscape page, so a wide table is never split
  // across a page boundary if it does not have to be.
  if (current === "tables" && /^\*\*Table /.test(line.trim())) {
    if (target().some(b => b instanceof Table)) {
      target().push(new Paragraph({ children: [new PageBreak()] }));
    }
  }

  const isNote = /^\*\[/.test(line.trim()) || /^Abbreviation/.test(line.trim())
    || /^\*Figure legend/.test(line.trim());
  target().push(new Paragraph({
    children: runs(line.trim(), isNote ? { size: 20 } : {}),
    spacing: current === "body" && !isNote ? DOUBLE : SINGLE,
  }));
}
flushTable();

// --- figure image -----------------------------------------------------------
const figPath = path.join(ROOT, "figures", "figure1.png");
if (fs.existsSync(figPath)) {
  // The SVG is 1408 x 624; preserve that ratio at 6.9 in wide.
  bucket.figure.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 120 },
    children: [new ImageRun({
      type: "png",
      data: fs.readFileSync(figPath),
      transformation: { width: 660, height: 292 },
    })],
  }));
  bucket.figure.push(new Paragraph({
    spacing: SINGLE,
    children: runs("Vector versions (SVG, PDF) are provided in the repository "
      + "and will be supplied at submission.", { size: 18 }),
  }));
}

// --- document ---------------------------------------------------------------
const RUNNING_HEAD = "Recommending Without Testing";

function footer() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })],
    })],
  });
}
function header() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: runs(RUNNING_HEAD, { size: 18 }),
    })],
  });
}

function section(children, landscape) {
  return {
    properties: {
      page: {
        // docx-js normalises width/height itself when an orientation is given,
        // so the portrait dimensions are passed in both cases and the library
        // performs the swap. Passing pre-swapped values yields a portrait page
        // carrying a landscape flag, which Word and LibreOffice both render
        // portrait.
        size: landscape
          ? { ...LETTER, orientation: PageOrientation.LANDSCAPE }
          : LETTER,
        margin: landscape ? MARGIN_LS : MARGIN,
      },
      lineNumbers: { countBy: 1, restart: "continuous" },
    },
    headers: { default: header() },
    footers: { default: footer() },
    children,
  };
}

const doc = new Document({
  creator: "Yunyu Xiao",
  title: "Recommending Without Testing: The Evidence Gap in Youth Screen Time and Social Media Policy",
  description: "JAMA Special Communication. Policy inventory and evidence appraisal, STEP project.",
  styles: {
    default: {
      document: { run: { font: FONT, size: BODY_SIZE } },
      heading1: { run: { font: FONT, size: 28, bold: true, color: "000000" } },
      heading2: { run: { font: FONT, size: 26, bold: true, color: "000000" } },
      heading3: { run: { font: FONT, size: 24, bold: true, color: "000000" } },
    },
  },
  sections: [
    section(bucket.body, false),
    section(bucket.tables, true),
    section(bucket.figure, false),
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  const n = bucket.body.length + bucket.tables.length + bucket.figure.length;
  console.log(`wrote ${OUT} (${(buf.length / 1024).toFixed(0)} KB, ${n} blocks, `
    + `${bucket.body.length} body / ${bucket.tables.length} tables / ${bucket.figure.length} figure)`);
});
