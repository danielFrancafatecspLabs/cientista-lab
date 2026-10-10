// Dados e regras espelhados do backend para o modo demonstração (sem API).
// Fonte de verdade: metaexp/core/descoberta.py, metaexp/core/papeis.py e metaexp/core/metodo.py.
import type { Dimensao, Estado, Ficha, Mapa, Papeis, PapelConversa } from "../types";

export const DIMENSOES: Dimensao[] = [
  { id: "sintoma", nome: "O que acontece", busca: "o que se observa hoje, descrito em fatos e não em soluções", peso: 3, minimo: 2 },
  { id: "quem_sofre", nome: "Quem sente", busca: "quem é afetado, quantas pessoas e em que momento do trabalho", peso: 3, minimo: 2 },
  { id: "tamanho", nome: "Tamanho do problema", busca: "frequência, volume e custo em números, mesmo que aproximados", peso: 3, minimo: 2 },
  { id: "caso_concreto", nome: "Um caso real", busca: "o último exemplo real, com o que aconteceu passo a passo", peso: 2, minimo: 1 },
  { id: "causas", nome: "Por que acontece", busca: "as causas prováveis, separando sintoma de causa raiz", peso: 2, minimo: 1 },
  { id: "solucao_atual", nome: "Como se resolve hoje", busca: "o contorno atual e por que ele não basta", peso: 2, minimo: 1 },
  { id: "decisao", nome: "Decisão em jogo", busca: "que decisão o resultado vai destravar e quem a toma", peso: 3, minimo: 2 },
  { id: "sucesso", nome: "Como saberemos", busca: "o sinal observável de sucesso, que vira métrica e critério", peso: 3, minimo: 2 },
  { id: "restricoes", nome: "Restrições", busca: "prazo, regras, dados disponíveis, orçamento e riscos que limitam a solução", peso: 1, minimo: 0 },
  { id: "premissa_critica", nome: "Premissa mais arriscada", busca: "o que precisa ser verdade para valer a pena, e ainda não sabemos", peso: 2, minimo: 1 },
];

export const TECNICAS: Record<string, { nome: string; como: string }> = {
  caso_concreto: { nome: "Um caso real", como: "Peça o último caso concreto, com quem, quando e o que aconteceu." },
  espelhar: { nome: "Confirmar entendimento", como: "Resuma com as palavras da pessoa e pergunte o que ficou errado." },
  quem_mais: { nome: "Quem mais sente", como: "Pergunte quem mais sofre com isso e em que momento." },
  quantificar: { nome: "Ordem de grandeza", como: "Peça números aproximados; ofereça faixas." },
  custo_da_inacao: { nome: "Custo de não fazer nada", como: "O que acontece se nada mudar em seis meses?" },
  cinco_porques: { nome: "Por que, de novo", como: "Pergunte por que até chegar a algo que dá para mudar." },
  ja_tentaram: { nome: "O que já tentaram", como: "O que foi tentado e por que não resolveu?" },
  decisao: { nome: "Decisão destravada", como: "Que decisão muda se der certo, e quem decide?" },
  contrafactual: { nome: "Se já estivesse resolvido", como: "O que seria visivelmente diferente no dia a dia?" },
  criterio_de_parada: { nome: "Quando desistir", como: "Que resultado faria a área desistir da ideia?" },
  premissa: { nome: "Premissa arriscada", como: "O que precisa ser verdade, e qual é a menos certa?" },
  restricao: { nome: "Limites do jogo", como: "Prazos, regras, sistemas e dados que limitam a solução." },
};

const AREAS: [string, string][] = [["atendimento", "Atendimento"], ["rede", "Rede"], ["digital", "Digital"], ["financeiro", "Financeiro"],
  ["suprimentos", "Suprimentos"], ["juridico", "Jurídico"], ["rh", "RH"], ["marketing", "Marketing"], ["operacoes", "Operações"], ["outro", "Outra"]];

export const PAPEIS: Papeis = {
  jornadas: [
    { papel: "solicitante", nome: "Solicitante", tipo: "conversa", chamada: "Tenho um desafio de negócio",
      descricao: "Você trouxe um desafio para o beOn Labs resolver com tecnologia.",
      promessa: "Você fala do seu negócio. O Cientista transforma isso em um experimento e o laboratório executa.",
      etapas: ["Desafio", "Entendimento", "Hipótese", "Sucesso", "Dados", "Responsáveis", "Ficha", "Revisão do Lab", "Bancada"],
      destinos: ["workflow"],
      preferencias: [{ id: "area", pergunta: "Área:", opcoes: AREAS, padrao: "atendimento" },
        { id: "ritmo", pergunta: "Ritmo:", opcoes: [["direto", "Direto ao ponto"], ["guiado", "Guiado, com exemplos"]], padrao: "guiado" }] },
    { papel: "desenvolvedor", nome: "Desenvolvedor", tipo: "conversa", chamada: "Quero construir algo",
      descricao: "Você quer construir uma solução e precisa provar que ela funciona.",
      promessa: "Desenho técnico com baseline, trade-offs e protocolo de avaliação, e um kit pronto para rodar com CI.",
      etapas: ["Problema", "Contexto técnico", "Baseline", "Hipótese", "Abordagens", "Avaliação", "Dados", "Ficha", "Kit"],
      destinos: ["desenvolvedor", "workflow"],
      preferencias: [
        { id: "stack", pergunta: "Stack:", opcoes: [["python", "Python"], ["typescript", "TypeScript / Node"], ["java", "Java / Kotlin"], ["sql", "SQL e dados"]], padrao: "python" },
        { id: "ia", pergunta: "Experiência com IA:", opcoes: [["iniciante", "Começando"], ["intermediario", "Já usei LLMs"], ["avancado", "Especialista em ML"]], padrao: "intermediario" },
        { id: "ambiente", pergunta: "Onde vai rodar:", opcoes: [["sandbox", "Sandbox do Lab"], ["propria", "Minha infraestrutura"]], padrao: "sandbox" }] },
    { papel: "lab", nome: "Lab", tipo: "painel", chamada: "Reviso e aprovo experimentos",
      descricao: "Você garante o rigor do método antes de qualquer execução.",
      promessa: "Fila de revisão com pré-análise do Agente Revisor, evidências da conversa e decisão em um clique.",
      etapas: ["Fila", "Pré-revisão", "Evidências", "Decisão"], destinos: [], preferencias: [] },
    { papel: "sponsor", nome: "Sponsor", tipo: "painel", chamada: "Acompanho o portfólio",
      descricao: "Você patrocina experimentos e decide o que escala.",
      promessa: "Portfólio por etapa, indicadores do metaexperimento e as decisões que dependem de você.",
      etapas: ["Portfólio", "Indicadores", "Decisões"], destinos: [], preferencias: [] },
  ],
  etapas_ciclo: ["Ficha", "Revisão (G0)", "Amostra (G1)", "Construção", "Qualidade (G2)", "Parecer (G3)", "Decisão"],
  dimensoes: DIMENSOES,
  tecnicas: TECNICAS,
};

export function mapaVazio(): Mapa {
  return { cobertura: 0, pronto: false, sintese: null, sintese_confirmada: false, pergunta_atual: null,
    dimensoes: DIMENSOES.map((d) => ({ ...d, entendimento: null, profundidade: 0, evidencia: null })) };
}

export function recalcular(m: Mapa): Mapa {
  const total = DIMENSOES.reduce((a, d) => a + d.peso * 3, 0);
  const soma = m.dimensoes.reduce((a, d) => a + d.peso * d.profundidade, 0);
  const cobertura = Math.round((soma / total) * 1000) / 1000;
  const pronto = m.dimensoes.every((d) => d.profundidade >= d.minimo) && cobertura >= 0.6;
  return { ...m, cobertura, pronto };
}

export function setDim(m: Mapa, id: string, entendimento: string, profundidade: number, evidencia?: string): Mapa {
  const dimensoes = m.dimensoes.map((d) => d.id === id
    ? { ...d, entendimento, profundidade: Math.max(d.profundidade, profundidade), evidencia: evidencia ?? d.evidencia }
    : d);
  return recalcular({ ...m, dimensoes });
}

const CHECK: [keyof Ficha, string][] = [["problema", "Problema identificado"], ["publico_afetado", "Impacto"],
  ["objetivo", "Objetivo definido"], ["hipotese", "Hipótese mensurável"], ["metodologia", "Metodologia compreensível"],
  ["amostra", "Amostra definida"], ["metricas", "Métricas e critérios com valores numéricos"], ["bo", "Responsável pelo experimento (BO)"],
  ["sponsor", "Patrocinador (SPONSOR)"], ["titulo", "Nome do experimento"]];

export function pendencias(f: Ficha): string[] {
  const out: string[] = [];
  for (const [campo, rotulo] of CHECK) {
    const v = f[campo];
    if (!v || (Array.isArray(v) && !v.length)) out.push(`${rotulo}: ausente`);
  }
  if (f.hipotese && !f.hipotese.toLowerCase().startsWith("acreditamos que")) out.push("a hipótese deve começar com 'Acreditamos que...'");
  if (f.titulo && f.titulo.split(/\s+/).length > 3) out.push("o nome do experimento deve ter no máximo 3 palavras");
  return out;
}

export function novoEstado(id: string, nome: string, papel: PapelConversa, preferencias: Record<string, string>): Estado {
  return {
    id, nome, papel, preferencias, status: "conversa", ficha: { id: `EXP-${id.slice(0, 6).toUpperCase()}`, metricas: [] },
    faltantes: [], pendencias: pendencias({}), ficha_gerada: false, ficha_versao: 0, mapa: mapaVazio(),
    desenho_pendencias: papel === "desenvolvedor" ? ["stack", "baseline", "abordagem escolhida", "protocolo de avaliação com métricas técnicas", "arquitetura"] : null,
    encaminhamento: null, pre_revisao: null, revisoes: [], feedback_lab: null, decisao: null,
    eventos: [{ em: new Date().toISOString(), tipo: "criada", detalhe: papel }],
    bancada: { iniciada: false, etapa: 0, status: {}, aguardando: null, artefatos: {}, rodadas: [], decisao_final: null },
    arquivos: [], similares: [],
  };
}

export const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));
