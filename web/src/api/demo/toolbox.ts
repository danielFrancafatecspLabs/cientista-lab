// Caixa de ferramentas no modo demonstração: o catálogo é o mesmo do backend
// (metaexp/catalogo/toolbox.json); pedidos e benchmarks ficam em memória.
import catalogo from "../../../../metaexp/catalogo/toolbox.json";
import type { BenchmarkLab, Credencial, NovoBenchmark, NovoPedido, Pedido, StatusPedido, Toolbox } from "../types";

export const TOOLBOX = catalogo as unknown as Toolbox;

const uid = () => Math.random().toString(16).slice(2, 12);
const agora = () => new Date().toISOString();
const horasAtras = (h: number) => new Date(Date.now() - h * 3.6e6).toISOString();
const emDias = (d: number) => new Date(Date.now() + d * 864e5).toISOString();
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));
const segredo = (n = 32) => Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"[b % 56]).join("");
const BASE = "https://llm.lab.interno/v1";

function exemploLlm(modelo: string) {
  return `# pip install openai\nimport os\nfrom openai import OpenAI\n\nclient = OpenAI(base_url="${BASE}", api_key=os.environ["LAB_LLM_KEY"])\nresp = client.chat.completions.create(\n    model="${modelo}",\n    messages=[{"role": "user", "content": "Olá!"}],\n)\nprint(resp.choices[0].message.content)\n`;
}

function credencialDe(p: Pedido): Credencial {
  const d = p.detalhes;
  if (p.tipo === "llm_key") {
    const modelos: string[] = d.modelos?.length ? d.modelos : ["deepseek-v4-flash"];
    return { resumo: `Chave do gateway LiteLLM para ${modelos.join(", ")}`, segredo: `sk-lab-${segredo()}`, simulada: true,
      campos: { base_url: BASE, modelos: modelos.join(", "), orcamento_mensal: `US$ ${d.orcamento ?? "50"}` },
      exemplo: exemploLlm(modelos[0]), expira_em: emDias(parseInt(d.validade ?? "30", 10)) };
  }
  if (p.tipo === "servidor") {
    const nome = `lab-${d.perfil ?? "cpu-p"}-${p.id.slice(0, 6)}`;
    const usuario = p.solicitante.toLowerCase().normalize("NFD").replace(/[^a-z]/g, "").slice(0, 16) || "dev";
    return { resumo: `Servidor ${nome} (${d.perfil})`, segredo: segredo(18), simulada: true,
      campos: { host: `${nome}.lab.interno`, usuario, perfil: d.perfil, uso: d.uso },
      exemplo: `ssh ${usuario}@${nome}.lab.interno\n# troque a senha no primeiro acesso: passwd`, expira_em: emDias(parseInt(d.duracao ?? "30", 10)) };
  }
  const repo = d.repositorio || (p.experimento ?? "experimento").toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return { resumo: `Acesso à organização beonlabs e ao repositório ${repo}`, simulada: true,
    campos: { organizacao: "beonlabs", repositorio: `beonlabs/${repo}`, usuario: d.usuario, permissao: d.permissao },
    exemplo: `# aceite o convite em https://github.com/orgs/beonlabs/invitation\ngit clone git@github.com:beonlabs/${repo}.git\n# descompacte o kit do METAEXP na raiz e faça o primeiro push: o CI de avaliação já vem pronto` };
}

const pedidos = new Map<string, Pedido>();
const semear = (p: Omit<Pedido, "id">) => { const id = uid(); const x = { ...p, id }; if (x.status === "aprovado") x.credencial = credencialDe(x); pedidos.set(id, x); };
semear({ tipo: "servidor", solicitante: "Marina Costa", justificativa: "Subir o n8n do experimento e o agente LangGraph para o teste com 10 analistas.",
  detalhes: { perfil: "cpu-m", duracao: "30d", uso: "piloto" }, experimento: "Triagem de Chamados", status: "pendente", criado_em: horasAtras(3) });
semear({ tipo: "llm_key", solicitante: "Marina Costa", justificativa: "Comparar V4 Flash e GPT-OSS 120B no protocolo de avaliação da triagem.",
  detalhes: { modelos: ["deepseek-v4-flash", "gpt-oss-120b"], validade: "30d", orcamento: "50" }, experimento: "Triagem de Chamados",
  status: "aprovado", criado_em: horasAtras(28), decidido_em: horasAtras(26), decidido_por: "Lia (Lab)" });
semear({ tipo: "github", solicitante: "Caio Mendes", justificativa: "Repositório do experimento de extração de notas fiscais.",
  detalhes: { usuario: "caiomendes", repositorio: "extracao-nf", permissao: "write" }, status: "pendente", criado_em: horasAtras(1) });

const benchmarks: BenchmarkLab[] = [
  { id: uid(), modelo: "DeepSeek V4 Flash", tarefa: "RAG sobre a FAQ de atendimento (230 perguntas)", metrica: "acerto", valor: "88%", conjunto: "Busca FAQ",
    observacoes: "non-think; top-5 híbrido", responsavel: "Lab", em: horasAtras(240), ilustrativo: true },
  { id: uid(), modelo: "GPT-OSS 120B", tarefa: "RAG sobre a FAQ de atendimento (230 perguntas)", metrica: "acerto", valor: "84%", conjunto: "Busca FAQ",
    observacoes: "reasoning medium", responsavel: "Lab", em: horasAtras(239), ilustrativo: true },
  { id: uid(), modelo: "DeepSeek V4 Flash", tarefa: "Triagem de chamados em 12 categorias", metrica: "F1 macro", valor: "0,81", conjunto: "Triagem",
    responsavel: "Lab", em: horasAtras(120), ilustrativo: true },
  { id: uid(), modelo: "Qwen 3.5 35B-A3B", tarefa: "Triagem de chamados em 12 categorias", metrica: "latência p95", valor: "620 ms", conjunto: "Triagem",
    observacoes: "hub, 1×GPU 80 GB", responsavel: "Lab", em: horasAtras(119), ilustrativo: true },
];

const publico = (p: Pedido): Pedido => {
  const x = clone(p);
  if (x.credencial?.segredo) { x.credencial.segredo_final = x.credencial.segredo.slice(-4); x.credencial.segredo = null; }
  return x;
};
const pegar = (id: string) => { const p = pedidos.get(id); if (!p) throw new Error("pedido não encontrado"); return p; };

export const toolboxDemo = {
  toolbox: async () => clone(TOOLBOX),
  pedidos: async (f: { status?: StatusPedido[]; solicitante?: string } = {}) => [...pedidos.values()]
    .filter((p) => (!f.status?.length || f.status.includes(p.status)) && (!f.solicitante || p.solicitante.toLowerCase() === f.solicitante.trim().toLowerCase()))
    .sort((a, b) => b.criado_em.localeCompare(a.criado_em)).map(publico),
  pedir: async (body: NovoPedido, experimento?: string | null) => {
    if (!body.justificativa.trim()) throw new Error("conte para que você precisa do recurso");
    if (body.tipo === "github" && !body.detalhes.usuario) throw new Error("informe seu usuário no GitHub");
    const p: Pedido = { id: uid(), ...body, solicitante: body.solicitante.trim() || "você", experimento: experimento ?? null, status: "pendente", criado_em: agora() };
    pedidos.set(p.id, p);
    return publico(p);
  },
  decidirPedido: async (id: string, b: { decisao: "aprovar" | "negar"; comentario: string; revisor: string }) => {
    const p = pegar(id);
    if (p.status !== "pendente") throw new Error(`o pedido já foi decidido (status: ${p.status})`);
    if (b.decisao === "negar" && !b.comentario.trim()) throw new Error("explique o motivo para negar o pedido");
    if (b.decisao === "aprovar") p.credencial = credencialDe(p);
    Object.assign(p, { status: b.decisao === "aprovar" ? "aprovado" : "negado", decidido_em: agora(), decidido_por: b.revisor, comentario: b.comentario.trim() || null });
    return publico(p);
  },
  revogarPedido: async (id: string, b: { revisor: string; comentario?: string }) => {
    const p = pegar(id);
    if (p.status !== "aprovado") throw new Error("só dá para revogar um pedido aprovado");
    Object.assign(p, { status: "revogado", decidido_em: agora(), decidido_por: b.revisor, comentario: b.comentario?.trim() || p.comentario });
    return publico(p);
  },
  credencial: async (id: string) => {
    const p = pegar(id);
    if (p.status !== "aprovado" || !p.credencial) throw new Error("a credencial só existe para pedidos aprovados");
    return clone(p.credencial);
  },
  benchmarksLab: async () => clone(benchmarks),
  registrarBenchmark: async (b: NovoBenchmark) => { const x = { ...b, id: uid(), em: agora() }; benchmarks.unshift(x); return clone(x); },
  removerBenchmark: async (id: string) => { const i = benchmarks.findIndex((x) => x.id === id); if (i >= 0) benchmarks.splice(i, 1); },
};
