// Gera o documento técnico em PDF (estilizado, via Chromium) e em Word (.docx) a partir de conteudo.mjs.
// Uso: node docs/tecnico/build.mjs   (precisa de playwright e docx disponíveis no Node)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { META, BLOCOS } from "./conteudo.mjs";
import { DIAGRAMAS } from "./diagramas.mjs";

const require = createRequire(import.meta.url);
const DIR = path.dirname(fileURLToPath(import.meta.url));
const OUT = DIR;
const NOME = "cientista-beon-labs-visao-tecnica";
const PW = process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright/index.mjs";
const { chromium } = await import(pathToFileURL(PW).href);
const docx = require(process.env.DOCX_MODULE || "docx");

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>");

// ------------------------------------------------------------------ HTML ----
function fontFaces() {
  const dir = path.join(process.env.HOME || "/root", ".fonts/gf");
  if (!fs.existsSync(dir)) return "";
  return fs.readdirSync(dir).filter((f) => f.endsWith(".ttf")).map((f) => {
    const [fam, w, st] = f.replace(".ttf", "").split("-");
    const family = { Figtree: "Figtree", BricolageGrotesque: "Bricolage Grotesque", JetBrainsMono: "JetBrains Mono" }[fam] || fam;
    return `@font-face{font-family:"${family}";font-weight:${w};font-style:${st};src:url("${pathToFileURL(path.join(dir, f)).href}")}`;
  }).join("\n");
}

function toc() {
  const caps = BLOCOS.filter((b) => b.h1 && b.n !== "");
  let h = `<section class="toc"><div class="eyebrow">Conteúdo</div><h2 class="toct">Sumário</h2><ol>`;
  let cur = null;
  for (const b of BLOCOS) {
    if (b.h1) { if (cur) h += `</ul></li>`; cur = b; h += `<li><span class="tn">${esc(b.n || "·")}</span><span class="tt">${esc(b.h1)}</span><ul>`; }
    else if (b.h2 && cur) h += `<li>${esc(b.h2)}</li>`;
  }
  if (cur) h += `</ul></li>`;
  void caps;
  return h + `</ol></section>`;
}

function blockHtml(b) {
  if (b.h1) return `<section class="chap"><div class="chapn">${b.n ? (/^\d/.test(b.n) ? String(b.n).padStart(2, "0") : b.n) : "00"}</div><h1>${esc(b.h1)}</h1></section>`;
  if (b.h2) return `<h2>${esc(b.h2)}</h2>`;
  if (b.h3) return `<h3>${esc(b.h3)}</h3>`;
  if (b.p) return `<p>${inline(b.p)}</p>`;
  if (b.quote) return `<blockquote>${inline(b.quote)}</blockquote>`;
  if (b.ul) return `<ul>${b.ul.map((i) => `<li>${inline(i)}</li>`).join("")}</ul>`;
  if (b.ol) return `<ol class="num">${b.ol.map((i) => `<li>${inline(i)}</li>`).join("")}</ol>`;
  if (b.kpis) return `<div class="kpis">${b.kpis.map(([v, l]) => `<div class="kpi"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join("")}</div>`;
  if (b.callout) return `<div class="callout"><div class="ct">${esc(b.callout.titulo)}</div><div>${inline(b.callout.texto)}</div></div>`;
  if (b.fig) return `<figure>${DIAGRAMAS[b.fig]().replace(/width="\d+" height="\d+"/, 'width="100%"')}<figcaption>${esc(b.caption)}</figcaption></figure>`;
  if (b.table) {
    const t = b.table;
    return `<table><colgroup>${t.widths.map((w) => `<col style="width:${w}%">`).join("")}</colgroup><thead><tr>${t.cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${t.rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }
  if (b.pagebreak) return `<div style="break-after:page"></div>`;
  return "";
}

function html() {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${esc(META.titulo)}</title><style>
${fontFaces()}
@page{size:A4;margin:22mm 18mm 20mm 18mm}
:root{--red:#da291c;--ink:#1d1b18;--mute:#6d675e;--line:#e3dfd7;--soft:#f6f4f0;--redsoft:#fdecea}
*{box-sizing:border-box}
body{margin:0;font:10pt/1.55 Figtree,"Liberation Sans",sans-serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1,h2,h3,.toct{font-family:"Bricolage Grotesque",Figtree,sans-serif;letter-spacing:-.01em;color:var(--ink)}
code{font:8.6pt "JetBrains Mono",monospace;background:var(--soft);border:1px solid var(--line);border-radius:3px;padding:0 3px}
strong{font-weight:700}
.cover{height:297mm;width:210mm;position:relative;overflow:hidden;background:#fff;break-after:page;padding:26mm 22mm}
.cover .band{position:absolute;left:0;top:0;bottom:0;width:9mm;background:var(--red)}
.cover .dots{position:absolute;right:-30mm;top:-20mm;width:150mm;height:150mm;background-image:radial-gradient(#e7e2d9 1.4px,transparent 1.4px);background-size:7mm 7mm;border-radius:50%}
.cover .mark{display:flex;align-items:center;gap:10px;font-weight:700;font-size:11pt;position:relative}
.cover .logo{width:34px;height:34px;border-radius:9px;background:var(--red);color:#fff;display:grid;place-items:center;font:800 17px "Bricolage Grotesque"}
.cover .eyebrow{margin-top:70mm;position:relative}
.cover h1{font-size:42pt;line-height:1.02;margin:6mm 0 6mm;font-weight:800;position:relative;max-width:170mm}
.cover .sub{font-size:15pt;line-height:1.4;color:#3b3833;max-width:150mm;position:relative}
.cover .meta{position:absolute;left:22mm;right:22mm;bottom:24mm;display:flex;justify-content:space-between;border-top:2px solid var(--ink);padding-top:5mm;font-size:9.5pt;color:var(--mute)}
.cover .meta b{display:block;color:var(--ink);font-size:10.5pt}
.cover .phases{position:relative;margin-top:14mm;display:flex;gap:4mm}
.cover .ph{border:1.4px solid var(--line);border-radius:10px;padding:4mm 5mm;width:62mm;background:#fff}
.cover .ph.on{border-color:var(--red);background:var(--redsoft)}
.cover .ph span{font:600 8pt "JetBrains Mono";color:var(--red);letter-spacing:.06em}
.cover .ph b{display:block;font:700 12pt "Bricolage Grotesque";margin-top:1mm}
.eyebrow{font:600 8.5pt "JetBrains Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--red)}
.toc{break-after:page}
.toct{font-size:26pt;margin:1mm 0 5mm}
.toc>ol{list-style:none;padding:0;margin:0;columns:1}
.toc>ol>li{display:grid;grid-template-columns:12mm 1fr;padding:2mm 0;border-top:1px solid var(--line);break-inside:avoid}
.toc .tn{font:700 14pt "Bricolage Grotesque";color:var(--red)}
.toc .tt{font:700 11.5pt "Bricolage Grotesque"}
.toc ul{grid-column:2;list-style:none;padding:0;margin:1mm 0 0;font-size:8.3pt;line-height:1.35;color:var(--mute);columns:3;column-gap:6mm}
.toc ul li{padding:.4mm 0;break-inside:avoid}
.chap{break-before:page;padding-top:4mm;margin-bottom:6mm;border-bottom:2px solid var(--ink);padding-bottom:4mm}
.chapn{font:800 40pt/1 "Bricolage Grotesque";color:var(--red)}
.chap h1{font-size:26pt;line-height:1.1;margin:2mm 0 0;font-weight:800}
h2{font-size:15pt;margin:8mm 0 2.5mm;break-after:avoid}
h3{font-size:11.5pt;margin:5mm 0 2mm;break-after:avoid}
p{margin:0 0 3mm}
ul,ol{margin:0 0 3.5mm;padding-left:5mm}
li{margin:0 0 1.4mm;padding-left:1mm}
ul li::marker{color:var(--red)}
ol.num li::marker{color:var(--red);font-weight:700}
blockquote{margin:3mm 0 5mm;padding:4mm 6mm;border-left:4px solid var(--red);background:var(--redsoft);font:600 12.5pt/1.45 "Bricolage Grotesque";border-radius:0 8px 8px 0}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin:4mm 0 5mm}
.kpi{border:1px solid var(--line);border-top:3px solid var(--red);border-radius:6px;padding:3mm 3.5mm;background:#fff}
.kpi b{display:block;font:800 18pt/1.1 "Bricolage Grotesque"}
.kpi span{font-size:8.5pt;color:var(--mute);line-height:1.3;display:block;margin-top:1mm}
.callout{border:1px solid #f3c1bc;background:var(--redsoft);border-radius:8px;padding:3.5mm 4.5mm;margin:3mm 0 5mm;break-inside:avoid}
.callout .ct{font:700 10.5pt "Bricolage Grotesque";color:var(--red);margin-bottom:1mm}
table{width:100%;border-collapse:collapse;margin:2mm 0 5mm;font-size:8.6pt;line-height:1.4;table-layout:fixed}
thead{display:table-header-group}
th{text-align:left;background:var(--ink);color:#fff;font-weight:600;padding:2mm 2.4mm;font-size:8.2pt;letter-spacing:.01em}
th:first-child{border-top-left-radius:5px}th:last-child{border-top-right-radius:5px}
td{padding:1.9mm 2.4mm;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:nth-child(even) td{background:#faf9f6}
tr{break-inside:avoid}
figure{margin:3mm 0 6mm;break-inside:avoid;border:1px solid var(--line);border-radius:8px;padding:3mm;background:#fff}
figure svg{display:block;height:auto}
figcaption{font-size:8.5pt;color:var(--mute);margin-top:2mm;text-align:center}
</style></head><body>
<!--COVER--><section class="cover"><div class="band"></div><div class="dots"></div>
  <div class="mark"><div class="logo">M</div>METAEXP · beOn Labs</div>
  <div class="eyebrow">Documento técnico</div>
  <h1>${esc(META.titulo)}</h1>
  <div class="sub">${esc(META.subtitulo)}</div>
  <div class="phases"><div class="ph on"><span>FASE 1</span><b>Cientista inteligente com o histórico do Lab</b></div><div class="ph"><span>FASE 2</span><b>Pipeline multiagente de execução</b></div></div>
  <div class="meta"><div><b>${esc(META.area)}</b>${esc(META.status)}</div><div style="text-align:right"><b>${esc(META.versao)}</b>Uso interno</div></div>
</section>
<!--/COVER-->${toc()}
${BLOCOS.map(blockHtml).join("\n")}
</body></html>`;
}

// ---------------------------------------------------------------- render ----
const browser = await chromium.launch();
const page = await browser.newPage();
const htmlPath = path.join(OUT, `${NOME}.html`);
const full = html();
const capa = full.replace(/<!--\/COVER-->[\s\S]*<\/body>/, "</body>").replace("<!--COVER-->", "").replace("</style>", "@page{margin:0}</style>");
const corpo = full.replace(/<!--COVER-->[\s\S]*<!--\/COVER-->/, "");
const capaPdf = path.join(OUT, "_capa.pdf"), corpoPdf = path.join(OUT, "_corpo.pdf");
fs.writeFileSync(htmlPath, capa);
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
await page.pdf({ path: capaPdf, width: "210mm", height: "297mm", printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 }, pageRanges: "1" });
fs.writeFileSync(htmlPath, corpo);
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
await page.pdf({
  path: corpoPdf, format: "A4", printBackground: true, preferCSSPageSize: true,
  displayHeaderFooter: true,
  headerTemplate: `<div style="width:100%;font:7.5pt Figtree,sans-serif;color:#9a948a;padding:0 18mm;display:flex;justify-content:space-between"><span>Cientista do beOn Labs · visão técnica</span><span>METAEXP</span></div>`,
  footerTemplate: `<div style="width:100%;font:7.5pt Figtree,sans-serif;color:#9a948a;padding:0 18mm;display:flex;justify-content:space-between"><span>${esc(META.versao)}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
});
// Diagramas em PNG para o Word
const png = {};
for (const [id, fn] of Object.entries(DIAGRAMAS)) {
  const s = fn();
  const [, w, h] = s.match(/viewBox="0 0 (\d+) (\d+)"/).map(Number);
  const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  await p.setContent(`<html><head><style>${fontFaces()}body{margin:0}</style></head><body>${s}</body></html>`, { waitUntil: "networkidle" });
  png[id] = { data: await p.screenshot({ clip: { x: 0, y: 0, width: w, height: h } }), w, h };
  await p.close();
}
await browser.close();
fs.unlinkSync(htmlPath);
execFileSync("pdfunite", [capaPdf, corpoPdf, path.join(OUT, `${NOME}.pdf`)]);
fs.unlinkSync(capaPdf); fs.unlinkSync(corpoPdf);

// ------------------------------------------------------------------ DOCX ----
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  BorderStyle, ImageRun, PageBreak, LevelFormat, Footer, Header, PageNumber, TableOfContents, TableLayoutType,
} = docx;
const RED = "DA291C", INK = "1D1B18", MUTE = "6D675E", LINE = "E3DFD7", SOFT = "F6F4F0", REDSOFT = "FDECEA";
const FONT = "Figtree", HFONT = "Bricolage Grotesque";
const CW = 9638; // largura útil A4 com margens de 2 cm (DXA)

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*.+?\*\*|`.+?`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), font: "JetBrains Mono", size: (base.size || 20) - 2, ...base, ...(base.font ? {} : {}) }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, opts = {}, base = {}) => new Paragraph({ children: runs(text, base), spacing: { after: 120, line: 300 }, ...opts });

function cell(text, w, { header = false, fill, size = 17 } = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, fill: INK, color: "auto" } : fill ? { type: ShadingType.CLEAR, fill, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    borders: { top: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE } },
    children: [new Paragraph({ children: runs(text, header ? { bold: true, color: "FFFFFF", size } : { size }), spacing: { after: 0, line: 264 } })],
  });
}
function table(t) {
  const ws = t.widths.map((w) => Math.round((CW * w) / 100));
  ws[ws.length - 1] += CW - ws.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: ws, layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ tableHeader: true, children: t.cols.map((c, i) => cell(c, ws[i], { header: true })) }),
      ...t.rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, ws[i], { fill: ri % 2 ? "FAF9F6" : undefined })) })),
    ],
  });
}
function boxed(children, fill, border) {
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CW, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill, color: "auto" },
      margins: { top: 140, bottom: 140, left: 200, right: 200 },
      borders: { top: { style: BorderStyle.SINGLE, size: 4, color: border }, bottom: { style: BorderStyle.SINGLE, size: 4, color: border }, right: { style: BorderStyle.SINGLE, size: 4, color: border }, left: { style: BorderStyle.SINGLE, size: 24, color: RED } },
      children,
    })] })],
  });
}
const spacer = () => new Paragraph({ children: [], spacing: { after: 120 } });

let olInstance = 0;
const body = [];
for (const b of BLOCOS) {
  if (b.h1) {
    body.push(new Paragraph({ children: [new PageBreak()] }));
    body.push(new Paragraph({ children: [new TextRun({ text: b.n ? (/^\d/.test(b.n) ? String(b.n).padStart(2, "0") : b.n) : "00", font: HFONT, bold: true, size: 64, color: RED })], spacing: { after: 0 } }));
    body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: b.h1 })], border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: INK, space: 6 } }, spacing: { after: 240 } }));
  } else if (b.h2) body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(b.h2)] }));
  else if (b.h3) body.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(b.h3)] }));
  else if (b.p) body.push(P(b.p));
  else if (b.quote) { body.push(boxed([new Paragraph({ children: runs(b.quote, { font: HFONT, bold: true, size: 24 }), spacing: { after: 0, line: 320 } })], REDSOFT, REDSOFT)); body.push(spacer()); }
  else if (b.ul) b.ul.forEach((i) => body.push(new Paragraph({ children: runs(i), numbering: { reference: "bul", level: 0 }, spacing: { after: 80, line: 290 } })));
  else if (b.ol) { olInstance++; b.ol.forEach((i) => body.push(new Paragraph({ children: runs(i), numbering: { reference: "num", level: 0, instance: olInstance }, spacing: { after: 80, line: 290 } }))); }
  else if (b.kpis) {
    const w = Math.floor(CW / b.kpis.length);
    body.push(new Table({ width: { size: w * b.kpis.length, type: WidthType.DXA }, columnWidths: b.kpis.map(() => w), rows: [new TableRow({ children: b.kpis.map(([v, l]) => new TableCell({
      width: { size: w, type: WidthType.DXA }, margins: { top: 100, bottom: 100, left: 140, right: 140 },
      borders: { top: { style: BorderStyle.SINGLE, size: 18, color: RED }, bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE }, left: { style: BorderStyle.SINGLE, size: 4, color: "FFFFFF" }, right: { style: BorderStyle.SINGLE, size: 4, color: "FFFFFF" } },
      children: [new Paragraph({ children: [new TextRun({ text: v, font: HFONT, bold: true, size: 32 })], spacing: { after: 40 } }), new Paragraph({ children: [new TextRun({ text: l, size: 16, color: MUTE })], spacing: { after: 0 } })],
    })) })] }));
    body.push(spacer());
  } else if (b.callout) {
    body.push(boxed([new Paragraph({ children: [new TextRun({ text: b.callout.titulo, font: HFONT, bold: true, color: RED, size: 21 })], spacing: { after: 60 } }), new Paragraph({ children: runs(b.callout.texto, { size: 19 }), spacing: { after: 0, line: 290 } })], REDSOFT, "F3C1BC"));
    body.push(spacer());
  } else if (b.fig) {
    const im = png[b.fig]; const wpx = 640, hpx = Math.round((im.h / im.w) * wpx);
    body.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: im.data, transformation: { width: wpx, height: hpx } })], spacing: { before: 120, after: 60 } }));
    body.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: b.caption, size: 16, color: MUTE, italics: true })], spacing: { after: 240 } }));
  } else if (b.table) { body.push(table(b.table)); body.push(spacer()); }
}

const cover = [
  new Paragraph({ children: [new TextRun({ text: "METAEXP · beOn Labs", bold: true, size: 22, color: INK })], spacing: { after: 2400 } }),
  new Paragraph({ children: [new TextRun({ text: "DOCUMENTO TÉCNICO", font: "JetBrains Mono", size: 17, color: RED, bold: true })], spacing: { after: 200 } }),
  new Paragraph({ children: [new TextRun({ text: META.titulo, font: HFONT, bold: true, size: 84, color: INK })], spacing: { after: 300, line: 860 } }),
  new Paragraph({ children: [new TextRun({ text: META.subtitulo, size: 30, color: "3B3833" })], spacing: { after: 600, line: 400 } }),
  new Paragraph({ children: [new TextRun({ text: "FASE 1  ", font: "JetBrains Mono", size: 16, color: RED, bold: true }), new TextRun({ text: "Cientista inteligente com o histórico do Lab", font: HFONT, bold: true, size: 22 })], spacing: { after: 80 } }),
  new Paragraph({ children: [new TextRun({ text: "FASE 2  ", font: "JetBrains Mono", size: 16, color: MUTE, bold: true }), new TextRun({ text: "Pipeline multiagente de execução", font: HFONT, bold: true, size: 22, color: MUTE })], spacing: { after: 2600 } }),
  new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 16, color: INK, space: 8 } }, children: [new TextRun({ text: META.area, bold: true, size: 20 })], spacing: { after: 40 } }),
  new Paragraph({ children: [new TextRun({ text: `${META.versao} · ${META.status}`, size: 18, color: MUTE })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ children: [new TextRun({ text: "Sumário", font: HFONT, bold: true, size: 48 })], spacing: { after: 240 } }),
  new TableOfContents("Sumário", { hyperlink: true, headingStyleRange: "1-2" }),
];

const doc = new Document({
  creator: "beOn Labs", title: META.titulo, description: META.subtitulo,
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 20, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: HFONT, size: 48, bold: true, color: INK }, paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: HFONT, size: 30, bold: true, color: INK }, paragraph: { spacing: { before: 360, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: HFONT, size: 23, bold: true, color: RED }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { run: { color: RED }, paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { run: { color: RED, bold: true }, paragraph: { indent: { left: 400, hanging: 280 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } }, titlePage: true },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Cientista do beOn Labs · visão técnica", size: 15, color: "9A948A" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: `${META.versao}   ·   `, size: 15, color: "9A948A" }), new TextRun({ children: [PageNumber.CURRENT], size: 15, color: "9A948A" })] })] }) },
    children: [...cover, ...body],
  }],
});
fs.writeFileSync(path.join(OUT, `${NOME}.docx`), await Packer.toBuffer(doc));
console.log("ok:", `${NOME}.pdf`, `${NOME}.docx`);
