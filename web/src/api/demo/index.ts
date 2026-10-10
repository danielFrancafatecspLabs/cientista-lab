// Backend de demonstração: mesmo contrato do real, em memória e com roteiros.
// Permite percorrer o ciclo inteiro trocando de papel: Solicitante → Lab → Bancada → Sponsor.
import type { Backend, Detalhe, Estado, Evento, Kit, OnEvento, PreRevisao, Resumo, Status } from "../types";
import { PAPEIS, TECNICAS, DIMENSOES, espera, novoEstado, pendencias, setDim } from "./base";
import { roteiroDesenvolvedor, roteiroSolicitante, type Passo } from "./roteiros";
import { sementes } from "./sementes";

interface Registro { estado: Estado; passo: number; transcricao: { de: "pessoa" | "cientista"; texto: string }[] }

const db = new Map<string, Registro>();
for (const s of sementes()) db.set(s.estado.id, s);

const uid = () => Math.random().toString(16).slice(2, 14);
const agora = () => new Date().toISOString();

function registrar(e: Estado, tipo: string, detalhe = "") { e.eventos = [...e.eventos, { em: agora(), tipo, detalhe }]; }
function mudar(e: Estado, s: Status, detalhe = "") { e.status = s; registrar(e, `status:${s}`, detalhe); }
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));

async function falar(texto: string, on: OnEvento) {
  const partes = texto.split(/(\s+)/);
  for (let i = 0; i < partes.length; i += 3) {
    on({ type: "text", delta: partes.slice(i, i + 3).join("") });
    await espera(22);
  }
}

function aplicar(r: Registro, p: Passo, on: OnEvento) {
  const e = r.estado;
  if (p.mapa) {
    for (const [d, ent, prof, ev] of p.mapa) e.mapa = setDim(e.mapa, d, ent, prof, ev);
  }
  if (p.porque) {
    const [dimensao, tecnica, por_que] = p.porque;
    e.mapa = { ...e.mapa, pergunta_atual: { dimensao, tecnica, por_que } };
  }
  if (p.sintese) e.mapa = { ...e.mapa, sintese: p.sintese, sintese_confirmada: false };
  if (p.confirma) e.mapa = { ...e.mapa, sintese_confirmada: true };
  if (p.mapa || p.porque || p.sintese || p.confirma) on({ type: "mapa", mapa: clone(e.mapa) });
  if (p.ficha || p.desenho) {
    e.ficha = { ...e.ficha, ...p.ficha };
    if (p.desenho) {
      e.ficha.detalhes_tecnicos = { ...e.ficha.detalhes_tecnicos, ...p.desenho };
      const d = e.ficha.detalhes_tecnicos;
      e.desenho_pendencias = [
        !d.stack && "stack", !d.baseline && "baseline", !d.abordagem_escolhida && "abordagem escolhida",
        !d.avaliacao?.metricas?.length && "protocolo de avaliação com métricas técnicas", !d.arquitetura?.length && "arquitetura",
      ].filter(Boolean) as string[];
    }
    if (e.ficha_gerada) e.ficha_gerada = false;
    e.pendencias = pendencias(e.ficha);
    on({ type: "ficha", ficha: clone(e.ficha), changed: Object.keys({ ...p.ficha, ...(p.desenho ? { detalhes_tecnicos: 1 } : {}) }), pendencias: e.pendencias, gerada: false });
  }
}

async function executarPasso(r: Registro, on: OnEvento) {
  const roteiro = r.estado.papel === "desenvolvedor" ? roteiroDesenvolvedor(r.estado.nome) : roteiroSolicitante(r.estado.nome);
  const p = roteiro[Math.min(r.passo, roteiro.length - 1)];
  r.passo += 1;
  const e = r.estado;
  await espera(450);
  aplicar(r, p, on);
  await falar(p.texto, on);
  r.transcricao.push({ de: "cientista", texto: p.texto });
  if (p.porque) {
    const [dimensao, tecnica, por_que] = p.porque;
    on({ type: "porque", dimensao, tecnica, por_que, tecnica_nome: TECNICAS[tecnica]?.nome, dimensao_nome: DIMENSOES.find((d) => d.id === dimensao)?.nome });
  }
  if (p.sintese) on({ type: "card", kind: "sintese", data: { texto: p.sintese } });
  for (const c of p.cards ?? []) { await espera(180); on({ type: "card", kind: c.kind, data: c.data }); }
  if (p.gerar) {
    e.ficha_gerada = true; e.ficha_versao += 1; e.pendencias = pendencias(e.ficha);
    registrar(e, "ficha_gerada", `versão ${e.ficha_versao}`);
    on({ type: "ficha", ficha: clone(e.ficha), changed: [], pendencias: e.pendencias, gerada: true });
    on({ type: "card", kind: "ficha_gerada", data: { ficha: clone(e.ficha), versao: e.ficha_versao, markdown: markdown(e) } });
  }
  if (p.encaminhar) {
    e.encaminhamento = p.encaminhar;
    e.ficha.execucao = p.encaminhar === "workflow" ? "laboratorio" : "solicitante";
    mudar(e, "em_revisao", "encaminhada");
    on({ type: "handoff", destino: p.encaminhar, resumo: e.ficha.titulo ?? "", status: e.status, ficha: clone(e.ficha), markdown: markdown(e),
      kit: p.encaminhar === "desenvolvedor" ? Object.keys(kitArquivos(e)).sort() : undefined });
  }
  if (p.upload) on({ type: "upload", descricao: p.upload.descricao, formatos: p.upload.formatos });
  if (p.chips) on({ type: "chips", options: p.chips });
  on({ type: "done", state: clone(e) });
}

function markdown(e: Estado): string {
  const f = e.ficha;
  const m = (f.metricas ?? []).map((x) => `| ${x.nome} | ${x.descricao} | ${x.criterio_aceite} | ${x.obrigatoria ? "sim" : "não"} |`).join("\n");
  return `# ${f.titulo ?? "Experimento"}\n\`${f.id}\` · versão ${Math.max(1, e.ficha_versao)}\n\n**BO:** ${f.bo ?? "—"} · **Sponsor:** ${f.sponsor ?? "—"}\n\n## Problema\n${f.problema ?? "—"}\n\n## Impacto\n${f.publico_afetado ?? "—"}\n\n## Objetivo\n${f.objetivo ?? "—"}\n\n## Hipótese\n${f.hipotese ?? "—"}\n\n## Metodologia\n${f.metodologia ?? "—"}\n\n## Amostra\n${f.amostra ?? "—"}\n\n## Métricas e critérios\n| Métrica | Descrição | Critério | Obrigatória |\n|---|---|---|---|\n${m}\n`;
}

function kitArquivos(e: Estado): Record<string, string> {
  const f = e.ficha, d = f.detalhes_tecnicos, a = d?.avaliacao;
  const metas = JSON.stringify({ metricas: (a?.metricas ?? []).map((x) => ({ nome: x.nome, alvo: x.alvo, baseline: x.baseline })), gate_regressao: a?.gate_regressao }, null, 2);
  return {
    "experimento.yaml": `id: ${f.id}\ntitulo: "${f.titulo}"\nhipotese: "${f.hipotese}"\ngolden_path: ${f.golden_path}\navaliacao:\n  conjunto: "${a?.conjunto}"\n  tamanho: ${a?.tamanho}\n  gate_regressao: "${a?.gate_regressao}"\n  metricas:\n${(a?.metricas ?? []).map((x) => `    - nome: ${x.nome}\n      alvo: "${x.alvo}"\n      baseline: "${x.baseline ?? ""}"`).join("\n")}\n`,
    "README.md": `# ${f.titulo}\n\n> ${f.hipotese}\n\n**Baseline:** ${d?.baseline}\n\n**Abordagem:** ${d?.abordagem_escolhida}\n\n## Como rodar\n\n1. Monte \`eval/casos.jsonl\`.\n2. Grave as saídas da solução em \`eval/predicoes.jsonl\`.\n3. \`python eval/avaliar.py\` (no CI: \`--ci\`).\n`,
    "eval/metas.json": metas + "\n",
    "eval/avaliar.py": `"""Avaliador do experimento (gerado pelo METAEXP). Sem dependências externas."""\n# Calcula as métricas, compara com eval/metas.json e com o baseline congelado,\n# grava eval/historico.csv e sai com erro no CI se houver falha ou regressão.\n...\n`,
    "eval/casos.exemplo.jsonl": `{"id": "c1", "entrada": "...", "esperado": "cobranca"}\n`,
    "eval/predicoes.exemplo.jsonl": `{"id": "c1", "previsto": "cobranca", "latencia_ms": 42}\n`,
    ".github/workflows/experimento.yml": `name: experimento\non: [push, pull_request]\njobs:\n  avaliar:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n      - run: python eval/avaliar.py --ci\n`,
    "RESULTADOS.md": `# Resultados · ${f.titulo}\n\n| Critério | Meta | Resultado | Atendido? |\n|---|---|---|---|\n${(f.metricas ?? []).map((x) => `| ${x.nome} | ${x.criterio_aceite} | | |`).join("\n")}\n`,
    "docs/ficha.md": markdown(e),
  };
}

function resumo(r: Registro): Resumo {
  const e = r.estado;
  const lt = e.eventos.find((x) => x.tipo === "status:em_revisao");
  return {
    id: e.id, titulo: e.ficha.titulo ?? "Sem título", papel: e.papel, nome: e.nome, status: e.status, dominio: e.ficha.dominio,
    hipotese: e.ficha.hipotese, bo: e.ficha.bo, sponsor: e.ficha.sponsor, criada_em: e.eventos[0]?.em ?? agora(),
    atualizada_em: e.eventos[e.eventos.length - 1]?.em ?? agora(), versao: e.ficha_versao, encaminhamento: e.encaminhamento,
    lead_time_horas: lt ? Math.max(0.05, (new Date(lt.em).getTime() - new Date(e.eventos[0].em).getTime()) / 3.6e6) : null,
    revisoes: e.revisoes.length, recomendacao: e.pre_revisao?.recomendacao ?? null, veredito: e.bancada.artefatos.parecer?.veredito ?? null,
    decisao: e.decisao?.decisao ?? null, cobertura: e.mapa.cobertura,
  };
}

function preRevisaoDe(e: Estado): PreRevisao {
  const m = e.mapa, f = e.ficha;
  const nota = (x: number) => Math.max(1, Math.min(5, Math.round(x)));
  const dim = (id: string) => m.dimensoes.find((d) => d.id === id)?.profundidade ?? 0;
  const notas = [
    { criterio: "problema", nota: nota(1 + (dim("sintoma") + dim("tamanho") + dim("decisao")) / 2.2), justificativa: `“${f.problema ?? "—"}”` },
    { criterio: "hipotese", nota: f.hipotese?.startsWith("Acreditamos que") && /\d/.test(f.hipotese) ? 5 : 2, justificativa: "No formato oficial, mensurável e ligada às métricas." },
    { criterio: "criterios", nota: (f.metricas ?? []).length >= 2 ? 4 : 3, justificativa: (f.metricas ?? []).map((x) => x.criterio_aceite).join(" · ") || "sem critérios" },
    { criterio: "dados", nota: /meta de 400|indicativo/.test(f.amostra ?? "") ? 3 : 4, justificativa: f.amostra ?? "amostra não definida" },
    { criterio: "viabilidade", nota: f.bo && f.sponsor ? 4 : 2, justificativa: `BO: ${f.bo ?? "—"} · Sponsor: ${f.sponsor ?? "—"}` },
  ];
  const min = Math.min(...notas.map((n) => n.nota));
  return {
    resumo: `${f.objetivo ?? "O experimento"} O problema e a decisão em jogo estão claros e os critérios são numéricos. ${min >= 4 ? "Pronta para executar." : min >= 3 ? "Pronta para executar, com ajustes pequenos." : "Precisa de ajustes antes de executar."}`,
    notas, pontos_fortes: ["Problema descrito com caso real e números", "Decisão de negócio explícita", "Critérios ancorados em caso do Lab"],
    riscos: /meta de 400/.test(f.amostra ?? "") ? ["Amostra abaixo de 400: resultado pode ser só indicativo"] : ["Rótulos históricos podem ter ruído"],
    ajustes_sugeridos: ["Registrar o baseline atual de tempo de busca antes do teste", "Definir quem valida o acerto das respostas"],
    recomendacao: min >= 4 ? "aprovar" : min >= 3 ? "aprovar_com_ajustes" : "devolver",
  };
}

async function bancadaDemo(r: Registro, body: { decisao?: string }, on: OnEvento) {
  const e = r.estado, b = e.bancada;
  const etapa = async (nome: string, status: string) => { b.status = { ...b.status, [nome]: status }; on({ type: "etapa", etapa: nome, status }); await espera(500); };
  const msg = async (agente: string, texto: string) => { on({ type: "mensagem", agente, texto }); await espera(650); };
  if (!b.iniciada) {
    if (e.status !== "aprovado") {
      on({ type: "aguardando", motivo: "revisao_lab", status: e.status, message: "A ficha ainda está com o Lab para revisão (G0)." });
      on({ type: "done", state: clone(e) }); return;
    }
    b.iniciada = true; mudar(e, "em_execucao");
    const rev = e.revisoes[e.revisoes.length - 1];
    await msg("cientista", `A ficha foi aprovada pelo Lab. Vamos começar, ${e.nome}.${rev?.comentario ? ` Comentário do Lab: ${rev.comentario}` : ""}`);
    await etapa("ficha", "ok");
    await etapa("amostra", "run");
    const analise = { resumo: "230 perguntas reais, sem duplicatas relevantes e com respostas na FAQ para 92% delas.", registros_validos: 230, tamanho_minimo: 400, suficiente: false,
      qualidade: "boa", achados: ["92% das perguntas têm resposta na FAQ", "Perguntas de portabilidade são 31% do total"], alertas: ["Abaixo de 400: resultado indicativo até completar a amostra"], decisao_g1: "aprovado_com_ressalva" };
    b.artefatos.amostra = analise;
    await msg("dados", `Conferi a amostra. ${analise.resumo} Por enquanto está ok. Posso dar o próximo passo?`);
    on({ type: "card", kind: "amostra", data: analise });
    b.aguardando = "amostra"; b.status = { ...b.status, amostra: "wait" };
    on({ type: "etapa", etapa: "amostra", status: "wait" });
    on({ type: "aprovacao", etapa: "amostra", opcoes: [{ id: "seguir", rotulo: "Pode seguir" }] });
    on({ type: "done", state: clone(e) }); return;
  }
  if (b.aguardando === "amostra" && body.decisao) {
    b.aguardando = null; await etapa("amostra", "ok");
    await etapa("construcao", "run");
    const plano = { abordagem: "Busca híbrida (palavra-chave + semântica) com resposta citando a fonte da FAQ", etapas: ["Indexar FAQ", "Buscar top-5", "Responder com fonte", "Medir tempo e acerto"],
      componentes: ["indexador", "buscador híbrido", "gerador com citação", "avaliador"], criterios_atendidos: ["tempo_de_busca", "respostas_corretas"], riscos_tecnicos: ["FAQ desatualizada"] };
    b.artefatos.plano = plano;
    await msg("dev", `Plano da solução pronto: ${plano.abordagem}.`);
    on({ type: "card", kind: "plano", data: plano });
    await etapa("construcao", "ok");
    await etapa("qualidade", "run");
    const qs = [0.62, 0.78, 0.91];
    const fb = [["Citar a fonte em todas as respostas", "Tratar perguntas fora da FAQ"], ["Ajustar o corte de relevância"], []];
    for (let i = 0; i < qs.length; i++) {
      const rodada = { k: i + 1, q: qs[i], aderencia: qs[i], feedback: fb[i], criterios: [] };
      b.rodadas = [...b.rodadas, rodada];
      on({ type: "card", kind: "rodada", data: rodada });
      await espera(700);
      if (i < qs.length - 1) await msg("dev", `Rodada ${i + 1}: corrigi ${fb[i].length} pontos apontados pelo QA.`);
    }
    await msg("qa", "Aprovado na rodada 3: qualidade 91%, acima da meta de 85%.");
    await etapa("qualidade", "ok");
    await etapa("resultado", "run");
    const parecer = { veredito: "validada", titulo: "A busca reduziu o tempo de busca em 26% sem perder acerto",
      resumo: "Com 230 perguntas reais (resultado indicativo), o tempo médio caiu de 6,1 para 4,5 minutos e o acerto ficou em 88%. Resultados simulados nesta demonstração.",
      evidencias: ["Tempo de busca: −26% (meta −20%)", "Acerto: 88% (meta 85%)"], riscos: ["Amostra abaixo de 400"],
      proximos_passos: ["Completar 400 perguntas", "Piloto com 10 analistas novos"], oportunidades: ["Levar ao 2º nível"],
      resultados: { simulado: true, metricas: [{ metrica: "tempo_de_busca", meta: "−20%", resultado: "−26%", atendida: true }, { metrica: "respostas_corretas", meta: "≥ 85%", resultado: "88%", atendida: true }], observacoes: [] } };
    b.artefatos.parecer = parecer;
    await msg("analista", `Terminei a análise. ${parecer.titulo}.`);
    on({ type: "card", kind: "parecer", data: parecer });
    await etapa("resultado", "ok");
    mudar(e, "parecer", "validada");
    on({ type: "done", state: clone(e) }); return;
  }
  on({ type: "error", message: "Nada a fazer: a bancada não espera uma decisão agora." });
  on({ type: "done", state: clone(e) });
}

function get(id: string): Registro {
  const r = db.get(id);
  if (!r) throw new Error("experimento não encontrado");
  return r;
}

async function streamDe(fn: () => Promise<void>, on: OnEvento) {
  try { await fn(); } catch (err) { on({ type: "error", message: String((err as Error).message) } as Evento); }
}

export const demo: Backend = {
  modo: "demo",
  papeis: async () => PAPEIS,
  criarSessao: async ({ nome, papel, preferencias }) => {
    const id = uid();
    const j = PAPEIS.jornadas.find((x) => x.papel === papel)!;
    const prefs = Object.fromEntries(j.preferencias.map((p) => [p.id, preferencias[p.id] ?? p.padrao]));
    const estado = novoEstado(id, nome?.trim() || "você", papel, prefs);
    db.set(id, { estado, passo: 0, transcricao: [] });
    return clone(estado);
  },
  sessao: async (id) => ({ ...clone(get(id).estado), transcricao: clone(get(id).transcricao) }),
  iniciar: (id, on) => streamDe(async () => {
    const r = get(id);
    if (r.passo > 0) { on({ type: "done", state: clone(r.estado) }); return; }
    await executarPasso(r, on);
  }, on),
  mensagem: (id, texto, on) => streamDe(async () => {
    const r = get(id);
    if (r.estado.status !== "conversa") throw new Error(`a conversa está fechada (status: ${r.estado.status})`);
    r.transcricao.push({ de: "pessoa", texto });
    if (texto.length > 400) on({ type: "auto_ingestao" });
    await executarPasso(r, on);
  }, on),
  arquivo: (id, file, on) => streamDe(async () => {
    const r = get(id);
    let registros = 230;
    if (/\.(csv|txt|jsonl)$/i.test(file.name)) registros = Math.max(1, (await file.text()).split(/\r?\n/).filter(Boolean).length - 1);
    const perfil = { nome: file.name, formato: file.name.split(".").pop(), registros, colunas: ["pergunta", "resposta", "categoria"], completude: 0.97, duplicadas: 3,
      total_registros: registros, minimo: 400, arquivos: r.estado.arquivos.length + 1, observacoes: [] };
    r.estado.arquivos = [...r.estado.arquivos, perfil];
    on({ type: "card", kind: "amostra", data: perfil });
    r.transcricao.push({ de: "pessoa", texto: `📎 Anexei o arquivo ${file.name}.` });
    await executarPasso(r, on);
  }, on),
  retomar: (id, on) => streamDe(async () => {
    const r = get(id), e = r.estado;
    const rev = e.feedback_lab;
    e.feedback_lab = null; e.ficha_gerada = false; mudar(e, "conversa", "retomada");
    await espera(400);
    const texto = `O Lab pediu um ajuste: “${rev?.comentario ?? ""}”. Vamos resolver isso rapidinho e reenviar.\n\n**Você consegue registrar o tempo médio de busca de hoje, numa amostra de 20 atendimentos?**`;
    await falar(texto, on);
    r.transcricao.push({ de: "cientista", texto });
    r.passo = (e.papel === "desenvolvedor" ? roteiroDesenvolvedor(e.nome) : roteiroSolicitante(e.nome)).length - 1;
    on({ type: "chips", options: ["Sim, registro esta semana", "Já temos: 6,1 minutos"] });
    on({ type: "done", state: clone(e) });
  }, on),
  bancada: (id, body, on) => streamDe(() => bancadaDemo(get(id), body, on), on),
  kit: async (id): Promise<Kit> => {
    const e = get(id).estado;
    return { pasta: (e.ficha.titulo ?? "experimento").toLowerCase().replace(/[^a-z0-9]+/g, "-"), arquivos: kitArquivos(e) };
  },
  kitUrl: () => null,
  experimentos: async (status) => [...db.values()].filter((r) => r.estado.ficha_versao > 0 && (!status?.length || status.includes(r.estado.status)))
    .map(resumo).sort((a, b) => b.atualizada_em.localeCompare(a.atualizada_em)),
  experimento: async (id): Promise<Detalhe> => {
    const r = get(id);
    return { ...clone(r.estado), resumo: resumo(r), transcricao: clone(r.transcricao), markdown: markdown(r.estado) };
  },
  preRevisao: async (id) => {
    await espera(1400);
    const e = get(id).estado;
    e.pre_revisao = preRevisaoDe(e);
    registrar(e, "pre_revisao", e.pre_revisao.recomendacao);
    return clone(e.pre_revisao);
  },
  revisao: async (id, { decisao, comentario, revisor }) => {
    const e = get(id).estado;
    if (e.status !== "em_revisao") throw new Error(`o experimento não está em revisão (status: ${e.status})`);
    if (decisao === "devolver" && !comentario.trim()) throw new Error("explique o que precisa mudar para devolver a ficha");
    const rev = { decisao, comentario: comentario.trim(), revisor, versao_ficha: e.ficha_versao, em: agora() };
    e.revisoes = [...e.revisoes, rev];
    e.feedback_lab = decisao === "devolver" ? rev : null;
    mudar(e, decisao === "aprovar" ? "aprovado" : "devolvido", comentario);
    return clone(e);
  },
  decisao: async (id, { decisao, comentario }) => {
    const e = get(id).estado;
    e.decisao = { decisao, comentario, em: agora() };
    mudar(e, "decidido", decisao);
    return clone(e);
  },
  portfolio: async () => {
    const rs = [...db.values()].filter((r) => r.estado.ficha_versao > 0).map(resumo);
    const revisadas = [...db.values()].filter((r) => r.estado.revisoes.length);
    const primeira = revisadas.filter((r) => r.estado.revisoes[0].decisao === "aprovar");
    const leads = rs.map((r) => r.lead_time_horas).filter((x): x is number => x != null).sort((a, b) => a - b);
    const por_status: Record<string, number> = {};
    const vereditos: Record<string, number> = {};
    for (const r of rs) { por_status[r.status] = (por_status[r.status] ?? 0) + 1; if (r.veredito) vereditos[r.veredito] = (vereditos[r.veredito] ?? 0) + 1; }
    return {
      kpis: { experimentos: rs.length, em_revisao: por_status.em_revisao ?? 0,
        aprovacao_primeira_revisao: revisadas.length ? primeira.length / revisadas.length : null,
        lead_time_mediano_horas: leads.length ? leads[Math.floor(leads.length / 2)] : null,
        cobertura_media_mapa: rs.length ? rs.reduce((a, r) => a + r.cobertura, 0) / rs.length : null, decisoes_pendentes: por_status.parecer ?? 0 },
      por_status, vereditos, historico: { total: 7, vereditos: { validada: 4, parcialmente_comprovada: 2, invalidada: 1 } },
    };
  },
};

