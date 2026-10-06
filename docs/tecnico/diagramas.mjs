// Diagramas do documento técnico (SVG). Cores fixas: o documento é impresso em fundo claro.

const C = {
  ink: "#1d1b18", mute: "#6d675e", line: "#cfc9bf", red: "#da291c", redSoft: "#fdecea",
  paper: "#ffffff", soft: "#f6f4f0",
  cientista: "#ffd3cf", dados: "#cfe6ff", dev: "#e4d9ff", qa: "#d4f2d0", analista: "#ffe0b8", neutro: "#efece6",
};
const F = "Figtree, 'Liberation Sans', sans-serif";
const FM = "'JetBrains Mono', 'DejaVu Sans Mono', monospace";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function box(x, y, w, h, { title, lines = [], fill = C.paper, stroke = C.line, r = 10, tsize = 15, lsize = 12, dash, bold = true, align = "middle", color = C.ink } = {}) {
  const tx = align === "middle" ? x + w / 2 : x + 14;
  const n = (title ? 1 : 0) + lines.length;
  const lh = lsize * 1.35;
  let ty = y + h / 2 - ((n - 1) * lh) / 2 + 5;
  let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="1.4"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`;
  if (title) { s += `<text x="${tx}" y="${ty}" text-anchor="${align === "middle" ? "middle" : "start"}" font-family="${F}" font-size="${tsize}" font-weight="${bold ? 700 : 500}" fill="${color}">${esc(title)}</text>`; ty += lh + 1; }
  for (const l of lines) { s += `<text x="${tx}" y="${ty}" text-anchor="${align === "middle" ? "middle" : "start"}" font-family="${F}" font-size="${lsize}" fill="${C.mute}">${esc(l)}</text>`; ty += lh; }
  return s;
}
function arrow(x1, y1, x2, y2, { label, color = C.mute, dash, lx, ly, curve } = {}) {
  const d = curve ? `M${x1},${y1} Q${curve[0]},${curve[1]} ${x2},${y2}` : `M${x1},${y1} L${x2},${y2}`;
  let s = `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" marker-end="url(#ah)"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`;
  if (label) s += `<text x="${lx ?? (x1 + x2) / 2}" y="${ly ?? (y1 + y2) / 2 - 6}" text-anchor="middle" font-family="${F}" font-size="11.5" fill="${color}">${esc(label)}</text>`;
  return s;
}
function pill(x, y, text, { fill = C.soft, stroke = C.line, color = C.ink, size = 11.5, w } = {}) {
  const ww = w ?? text.length * size * 0.56 + 18;
  return { w: ww, s: `<rect x="${x}" y="${y}" width="${ww}" height="22" rx="11" fill="${fill}" stroke="${stroke}"/><text x="${x + ww / 2}" y="${y + 15}" text-anchor="middle" font-family="${F}" font-size="${size}" fill="${color}">${esc(text)}</text>` };
}
function gate(x, y, label) {
  return `<g><polygon points="${x},${y - 15} ${x + 15},${y} ${x},${y + 15} ${x - 15},${y}" fill="${C.red}"/><text x="${x}" y="${y + 4}" text-anchor="middle" font-family="${FM}" font-size="10" font-weight="600" fill="#fff">${label}</text></g>`;
}
function svg(w, h, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}"><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${C.mute}"/></marker></defs><rect width="${w}" height="${h}" fill="#fff"/>${body}</svg>`;
}
const label = (x, y, t, { size = 12, color = C.mute, weight = 600, anchor = "start", mono = false } = {}) =>
  `<text x="${x}" y="${y}" text-anchor="${anchor}" font-family="${mono ? FM : F}" font-size="${size}" font-weight="${weight}" fill="${color}" letter-spacing="${mono ? 0.5 : 0}">${esc(t)}</text>`;

// 1. Ciclo do método com gates ------------------------------------------------
export function ciclo() {
  let b = "";
  const y = 120, h = 96, w = 150;
  const xs = [30, 230, 430, 630, 830];
  const ag = [
    ["Cientista", ["Ficha do experimento"], C.cientista],
    ["Analista de Dados", ["Amostra validada"], C.dados],
    ["Desenvolvedor", ["Solução e resultados"], C.dev],
    ["QA", ["Avaliação Qk"], C.qa],
    ["Analista", ["Parecer e veredito"], C.analista],
  ];
  b += `<rect x="16" y="78" width="178" height="226" rx="14" fill="${C.redSoft}" stroke="${C.red}" stroke-dasharray="5 4"/>`;
  b += label(30, 98, "FASE 1", { mono: true, color: C.red, size: 11 });
  b += label(500, 40, "Ciclo do Método Experimento: cinco agentes, quatro gates humanos", { anchor: "middle", size: 15, color: C.ink, weight: 700 });
  ag.forEach(([t, l, f], i) => { b += box(xs[i], y, w, h, { title: t, lines: l, fill: f, stroke: "#00000022" }); });
  const gates = [["G0", 205], ["G1", 405], ["G3", 1005 - 20]];
  b += arrow(180, y + 48, 222, y + 48); b += gate(205, y + 48, "G0");
  b += arrow(380, y + 48, 422, y + 48); b += gate(405, y + 48, "G1");
  b += arrow(580, y + 38, 628, y + 38);
  b += arrow(630, y + 62, 582, y + 62);
  b += gate(605, y + 96 + 28, "G2");
  b += label(605, y + 96 + 62, "Ralph Loop: Qk ≥ 0,85", { anchor: "middle", size: 11.5 });
  b += label(605, y + 96 + 78, "no máximo 5 iterações", { anchor: "middle", size: 11.5, weight: 500 });
  b += arrow(780, y + 48, 828, y + 48); b += gate(805, y + 48, "G2");
  b += gate(905, y + 96 + 28, "G3");
  b += label(905, y + 96 + 62, "Sponsor decide", { anchor: "middle", size: 11.5 });
  b += label(905, y + 96 + 78, "piloto ou escala", { anchor: "middle", size: 11.5, weight: 500 });
  const hum = ["Solicitante aprova a ficha", "Lab confirma os dados", "", "Especialista se Kmax", "Solicitante aceita o parecer"];
  hum.forEach((t, i) => { if (t) b += label(xs[i] + w / 2, y + h + 104, t, { anchor: "middle", size: 11, weight: 500 }); });
  b += label(30, 335, "◆ gate com decisão humana registrada", { size: 11.5, color: C.red });
  return svg(1000, 350, b);
}

// 2. Arquitetura em camadas ---------------------------------------------------
export function camadas() {
  let b = "";
  const X = 150, W = 830;
  const rows = [
    ["Canais", 50, C.soft],
    ["Orquestração", 118, C.soft],
    ["Agentes", 186, C.soft],
    ["Skills", 268, C.soft],
    ["Conhecimento", 350, C.soft],
    ["Dados", 418, C.soft],
    ["Plataforma", 486, C.soft],
  ];
  b += label(20, 30, "Arquitetura-alvo do METAEXP em camadas", { size: 15, color: C.ink, weight: 700 });
  for (const [t, y] of rows) b += label(20, y + 32, t.toUpperCase(), { mono: true, size: 11, color: C.mute });
  const put = (y, items, h = 52, fills) => {
    const gap = 10, w = (W - gap * (items.length - 1)) / items.length;
    items.forEach((it, i) => { b += box(X + i * (w + gap), y, w, h, { title: it[0], lines: it[1] ? [it[1]] : [], fill: (fills && fills[i]) || C.paper, tsize: 13.5, lsize: 11 }); });
  };
  put(50, [["Chat do Solicitante", "jornada de negócio"], ["Chat do Desenvolvedor", "jornada técnica"], ["Painel do Lab", "gates, revisão, métricas"], ["API e integrações", "Teams, Jira, esteira"]]);
  put(118, [["Máquina de estados do experimento", "G0 → G1 → G2 → G3, com aprovações humanas e trilha de auditoria"]]);
  put(186, [["Cientista", "ficha · G0"], ["Analista de Dados", "amostra · G1"], ["Desenvolvedor", "construção"], ["QA", "Ralph Loop · G2"], ["Analista", "parecer · G3"]], 70, [C.cientista, C.dados, C.dev, C.qa, C.analista]);
  put(268, [["entrevista do método", "auto-ingestão · ficha"], ["perfil e cálculo amostral", "PII · data card"], ["plano e código", "golden paths · sandbox"], ["testes da ficha", "e · o · d · S"], ["estatística e veredito", "relatório executivo"]], 70);
  put(350, [["Método oficial", "regras e checklist"], ["Golden paths", "padrões por técnica"], ["Corpus de experimentos", "real + sintético"], ["Playbooks", "lições por domínio"]]);
  put(418, [["Documentos brutos", "object storage"], ["Banco relacional + vetorial", "Postgres + pgvector"], ["Artefatos de execução", "código, logs, outputs"], ["Telemetria", "tokens, custo, lead time"]]);
  put(486, [["Gateway de modelos", "Claude + open source"], ["Sandbox de execução", "containers isolados"], ["Observabilidade", "traces e avaliação"], ["Segurança", "SSO, RBAC, LGPD"]]);
  return svg(1000, 556, b);
}

// 3. Pipeline de dados do histórico --------------------------------------------
export function pipeline() {
  let b = label(20, 30, "Do histórico bruto ao corpus que o Cientista consulta", { size: 15, color: C.ink, weight: 700 });
  const w = 200, h = 82;
  const r1 = [
    ["1 · Fontes", ["Drive, SharePoint,", "Confluence, e-mail"]],
    ["2 · Coleta", ["uma pasta por experimento,", "nomes padronizados"]],
    ["3 · Anonimização", ["PII de clientes e", "colaboradores mascarada"]],
    ["4 · Extração", ["PDF/DOCX → texto →", "registro Experimento"]],
  ];
  const r2 = [
    ["8 · Usos", ["RAG, few-shot, avaliação,", "sintético, ajuste fino"]],
    ["7 · Indexação", ["busca híbrida:", "BM25 + vetores + reranker"]],
    ["6 · Corpus versionado", ["data card, versão,", "origem real/sintético"]],
    ["5 · Validação", ["esquema + regras do método;", "revisão humana (ouro)"]],
  ];
  r1.forEach(([t, l], i) => { b += box(20 + i * 245, 60, w, h, { title: t, lines: l, fill: i === 2 ? C.redSoft : C.paper, tsize: 14, lsize: 11.5 }); if (i < 3) b += arrow(20 + i * 245 + w, 101, 20 + (i + 1) * 245 - 4, 101); });
  r2.forEach(([t, l], i) => { b += box(20 + i * 245, 200, w, h, { title: t, lines: l, fill: i === 0 ? C.cientista : C.paper, tsize: 14, lsize: 11.5 }); if (i < 3) b += arrow(20 + (i + 1) * 245, 241, 20 + i * 245 + w + 4, 241); });
  b += arrow(855, 142, 855, 196);
  b += box(20, 312, 935, 46, { title: "Registros ouro (20 → 50): curadoria campo a campo pelo Lab. São o gabarito da avaliação e a âncora do sintético; nunca entram no treino.", fill: C.soft, tsize: 12.5, bold: false });
  return svg(975, 372, b);
}

// 4. Arquitetura do Cientista (fase 1) -------------------------------------------
export function cientista() {
  let b = label(20, 30, "Cientista do beOn Labs: como o contexto é montado a cada turno", { size: 15, color: C.ink, weight: 700 });
  const layers = [
    ["1 · Método oficial e regras", "estático, em cache", C.neutro],
    ["2 · Jornada do papel", "solicitante ou desenvolvedor", C.neutro],
    ["3 · Playbook do domínio", "quando o domínio é detectado", C.analista],
    ["4 · Casos semelhantes", "top-k do histórico, resumidos", C.dados],
    ["5 · Estado da ficha", "campos, pendências do checklist", C.qa],
    ["6 · Conversa", "histórico do chat (só cresce)", C.paper],
  ];
  layers.forEach(([t, s, f], i) => { b += box(20, 56 + i * 54, 270, 46, { title: t, lines: [s], fill: f, tsize: 13, lsize: 11, align: "start" }); });
  b += arrow(292, 215, 352, 215);
  b += box(356, 150, 230, 130, { title: "Agente Cientista", lines: ["Claude via gateway", "pensamento adaptativo", "esforço por papel", "saída com ferramentas"], fill: C.cientista, tsize: 16 });
  const tools = ["atualizar_ficha", "gerar_ficha", "buscar_experimentos_similares", "classificar_experimento", "calcular_tamanho_amostra", "solicitar_dados", "sugerir_respostas", "propor_abordagens", "encaminhar"];
  b += label(650, 66, "FERRAMENTAS", { mono: true, size: 11 });
  tools.forEach((t, i) => { const p = pill(650, 76 + i * 28, t, { size: 11, w: 300 }); b += p.s; });
  b += arrow(588, 215, 646, 215);
  b += box(356, 330, 230, 64, { title: "Serviços de conhecimento", lines: ["busca híbrida · playbooks · golden paths"], tsize: 13, lsize: 11 });
  b += arrow(471, 282, 471, 326);
  b += box(650, 340, 300, 54, { title: "Corpus + índices", lines: ["Postgres + pgvector · BM25"], tsize: 13, lsize: 11 });
  b += arrow(588, 362, 646, 366);
  b += box(20, 400, 560, 50, { title: "Fora do caminho do usuário: avaliação contínua (solicitante simulado + juiz + revisão cega) a cada mudança de prompt, ferramenta ou modelo", fill: C.soft, tsize: 11.5, bold: false, dash: "5 4" });
  return svg(975, 466, b);
}

// 5. Implantação ------------------------------------------------------------------
export function implantacao() {
  let b = label(20, 30, "Implantação de referência (rede corporativa)", { size: 15, color: C.ink, weight: 700 });
  b += box(20, 60, 160, 60, { title: "Usuários", lines: ["SSO corporativo"], tsize: 14 });
  b += arrow(182, 90, 226, 90);
  b += box(230, 60, 170, 60, { title: "Front web", lines: ["chat + ficha + painel"], tsize: 14 });
  b += arrow(402, 90, 446, 90);
  b += box(450, 60, 200, 60, { title: "API (FastAPI)", lines: ["sessões, SSE, RBAC"], tsize: 14 });
  b += arrow(550, 122, 550, 166);
  b += box(450, 170, 200, 60, { title: "Orquestrador", lines: ["fila + máquina de estados"], tsize: 14 });
  b += arrow(652, 200, 716, 200);
  b += box(720, 170, 240, 60, { title: "Gateway de modelos", lines: ["roteamento, cota, logs"], tsize: 14, fill: C.redSoft });
  b += arrow(780, 232, 700, 296); b += arrow(900, 232, 900, 296);
  b += box(590, 300, 200, 64, { title: "Claude (API)", lines: ["Cientista, Analista, juiz"], tsize: 13.5, fill: C.cientista });
  b += box(810, 300, 150, 64, { title: "Pool de GPU", lines: ["vLLM · open source"], tsize: 13.5, fill: C.dev });
  b += arrow(448, 200, 380, 200);
  b += box(230, 170, 150, 60, { title: "Sandbox", lines: ["jobs isolados"], tsize: 14, fill: C.qa });
  b += arrow(500, 232, 330, 296); b += arrow(550, 232, 520, 296);
  b += box(20, 300, 220, 64, { title: "Postgres + pgvector", lines: ["sessões, corpus, vetores"], tsize: 13.5, fill: C.dados });
  b += box(260, 300, 160, 64, { title: "Object storage", lines: ["documentos, artefatos"], tsize: 13.5, fill: C.dados });
  b += box(440, 300, 130, 64, { title: "Observabilidade", lines: ["traces, custo"], tsize: 13, fill: C.neutro });
  b += box(20, 170, 190, 60, { title: "Ingestão do histórico", lines: ["batch, sob demanda"], tsize: 13 });
  b += arrow(115, 232, 115, 296);
  return svg(980, 380, b);
}

export const DIAGRAMAS = { ciclo, camadas, pipeline, cientista, implantacao };
