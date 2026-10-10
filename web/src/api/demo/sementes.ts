// Experimentos de exemplo para o modo demonstração: povoam a fila do Lab e o portfólio do Sponsor.
import type { Estado, Ficha, PapelConversa, Status } from "../types";
import { novoEstado, pendencias, setDim } from "./base";

interface Semente {
  id: string; nome: string; papel: PapelConversa; status: Status; horasAtras: number; leadHoras: number;
  ficha: Ficha; mapa: [string, string, number, string?][]; transcricao: { de: "pessoa" | "cientista"; texto: string }[];
  parecer?: Record<string, unknown>; decisao?: "escalar" | "iterar" | "encerrar";
}

const ISO = (horas: number) => new Date(Date.now() - horas * 3.6e6).toISOString();

const SEMENTES: Semente[] = [
  {
    id: "a1f09c2e7b31", nome: "Carlos · Financeiro", papel: "solicitante", status: "em_revisao", horasAtras: 30, leadHoras: 1.4,
    ficha: { titulo: "Conciliação de faturas", dominio: "financeiro", problema: "Analistas conferem à mão 1.200 faturas de fornecedores por mês contra pedidos de compra.",
      publico_afetado: "6 analistas do contas a pagar; 3 dias de fechamento por mês.", objetivo: "Testar extração automática de campos das faturas e conferência com o pedido.",
      hipotese: "Acreditamos que a extração automática irá reduzir em 50% o tempo de conferência no fechamento mensal.",
      metodologia: "Rodar a extração em 300 faturas já conferidas e comparar campos e tempo.", tecnologia: "ia_generativa", tecnica: "Automação documental", golden_path: "automacao-documental",
      metricas: [{ nome: "extracao_correta", descricao: "Campos extraídos corretamente", criterio_aceite: "≥ 95%", obrigatoria: true },
        { nome: "tempo_conferencia", descricao: "Tempo por fatura", criterio_aceite: "Redução ≥ 50%", obrigatoria: true }],
      dados: "PDFs de faturas e pedidos no ERP", amostra: "300 faturas já conferidas", bo: "Coordenação de contas a pagar", sponsor: "Diretoria financeira" },
    mapa: [["sintoma", "Conferência manual de 1.200 faturas/mês.", 3, "conferimos uma por uma"], ["quem_sofre", "6 analistas do contas a pagar.", 2], ["tamanho", "3 dias de fechamento por mês.", 2],
      ["caso_concreto", "Fatura com CNPJ divergente passou e gerou pagamento duplicado.", 2], ["decisao", "Antecipar o fechamento em 2 dias.", 2], ["sucesso", "Fechamento em 1 dia.", 2],
      ["solucao_atual", "Planilha de conferência.", 1], ["causas", "Fornecedores mandam layouts diferentes.", 1], ["premissa_critica", "Os PDFs têm texto, não são imagens.", 1]],
    transcricao: [{ de: "cientista", texto: "**O que está acontecendo hoje que fez você procurar o Lab?**" }, { de: "pessoa", texto: "A gente confere uma por uma, são 1.200 faturas por mês." },
      { de: "cientista", texto: "**Pense na última fatura que deu problema: o que aconteceu?**" }, { de: "pessoa", texto: "Uma com CNPJ divergente passou e pagamos duas vezes." }],
  },
  {
    id: "b7c41d08e2aa", nome: "Juliana · Suprimentos", papel: "solicitante", status: "parecer", horasAtras: 120, leadHoras: 2.1,
    ficha: { titulo: "Previsão de estoque", dominio: "suprimentos", problema: "Ruptura de 9% nos itens de reparo de rede nas regionais.", publico_afetado: "Técnicos de campo e 4 centros de distribuição.",
      objetivo: "Testar previsão semanal de demanda por item e regional.", hipotese: "Acreditamos que a previsão semanal irá reduzir de 9% para 4% a ruptura de itens críticos nas regionais.",
      metodologia: "Backtest com 24 meses e piloto em uma regional.", tecnologia: "estatistica", tecnica: "Séries temporais", golden_path: "previsao-demanda",
      metricas: [{ nome: "ruptura", descricao: "Itens críticos em falta", criterio_aceite: "≤ 4%", obrigatoria: true }, { nome: "mape", descricao: "Erro da previsão", criterio_aceite: "MAPE ≤ 15%", obrigatoria: true }],
      dados: "ERP de suprimentos, 24 meses", amostra: "24 meses × 180 itens", bo: "Gerência de suprimentos", sponsor: "VP de Operações" },
    mapa: [["sintoma", "Ruptura de itens de reparo.", 3], ["quem_sofre", "Técnicos de campo.", 2], ["tamanho", "9% de ruptura.", 3], ["caso_concreto", "Falta de conectores na regional Sul.", 2],
      ["decisao", "Mudar a política de reposição.", 3], ["sucesso", "Ruptura ≤ 4%.", 3], ["solucao_atual", "Reposição por média móvel.", 2], ["causas", "Sazonalidade de chuvas.", 2], ["premissa_critica", "Histórico confiável.", 2]],
    transcricao: [{ de: "pessoa", texto: "Falta conector na regional Sul toda época de chuva." }],
    parecer: { veredito: "validada", titulo: "A previsão reduziu a ruptura para 3,6% no backtest", resumo: "MAPE de 12% e ruptura simulada de 3,6% contra 9% hoje.",
      evidencias: ["Ruptura: 3,6% (meta ≤ 4%)", "MAPE: 12% (meta ≤ 15%)"], riscos: ["Backtest não captura mudanças de fornecedor"], proximos_passos: ["Piloto na regional Sul"], oportunidades: ["Estender a 600 itens"] },
  },
  {
    id: "c3e88f1a90d4", nome: "Pedro · Rede", papel: "desenvolvedor", status: "em_execucao", horasAtras: 72, leadHoras: 0.9,
    ficha: { titulo: "Inspeção de postes", dominio: "rede", problema: "Inspeção visual de postes depende de visita de técnico.", publico_afetado: "Equipes de manutenção preventiva.",
      objetivo: "Testar detecção de avarias em fotos de drone.", hipotese: "Acreditamos que a detecção em fotos irá identificar 90% das avarias graves antes da visita técnica.",
      metodologia: "Avaliar com 1.000 fotos rotuladas.", tecnologia: "visao_computacional", tecnica: "Detecção de objetos", golden_path: "visao-computacional",
      metricas: [{ nome: "recall_avarias", descricao: "Avarias graves detectadas", criterio_aceite: "≥ 90%", obrigatoria: true }],
      dados: "Fotos de drone", amostra: "1.000 fotos rotuladas", bo: "Engenharia de rede", sponsor: "Diretoria de rede" },
    mapa: [["sintoma", "Inspeção depende de visita.", 2], ["quem_sofre", "Manutenção preventiva.", 2], ["tamanho", "4 mil postes por mês.", 2], ["decisao", "Priorizar visitas.", 2], ["sucesso", "90% das avarias graves.", 2],
      ["caso_concreto", "Poste com trinca não visto.", 1], ["causas", "Baixa frequência de inspeção.", 1], ["solucao_atual", "Rondas trimestrais.", 1], ["premissa_critica", "Fotos com resolução suficiente.", 1]],
    transcricao: [{ de: "pessoa", texto: "Queremos usar as fotos de drone que já temos." }],
  },
  {
    id: "d92a5b6c1f07", nome: "Marta · Atendimento", papel: "solicitante", status: "decidido", horasAtras: 400, leadHoras: 1.8,
    ficha: { titulo: "Voz do cliente", dominio: "atendimento", problema: "Reclamações livres não são categorizadas.", publico_afetado: "Qualidade e produto.",
      objetivo: "Classificar reclamações por motivo.", hipotese: "Acreditamos que a classificação automática irá concordar em 85% com especialistas para o time de qualidade.",
      metodologia: "Comparar com 500 rótulos de especialistas.", tecnologia: "ia_generativa", tecnica: "Classificação de texto", golden_path: "texto-livre-voc",
      metricas: [{ nome: "concordancia", descricao: "Concordância com especialistas", criterio_aceite: "≥ 85%", obrigatoria: true }],
      dados: "Reclamações do último trimestre", amostra: "500 reclamações rotuladas", bo: "Qualidade", sponsor: "Diretoria de atendimento" },
    mapa: [["sintoma", "Reclamações sem categoria.", 2], ["quem_sofre", "Time de qualidade.", 2], ["tamanho", "20 mil por mês.", 2], ["decisao", "Priorizar melhorias de produto.", 2], ["sucesso", "85% de concordância.", 2],
      ["caso_concreto", "Pico de reclamações de fatura não percebido.", 2], ["causas", "Texto livre.", 1], ["solucao_atual", "Amostragem manual.", 1], ["premissa_critica", "Especialistas concordam entre si.", 1]],
    transcricao: [{ de: "pessoa", texto: "Ninguém lê as reclamações abertas." }],
    parecer: { veredito: "validada", titulo: "Concordância de 88% com os especialistas", resumo: "Validada; recomendado escalar.", evidencias: [], riscos: [], proximos_passos: [], oportunidades: [] },
    decisao: "escalar",
  },
];

export function sementes(): { estado: Estado; passo: number; transcricao: Semente["transcricao"] }[] {
  return SEMENTES.map((s) => {
    const e = novoEstado(s.id, s.nome, s.papel, {});
    e.eventos = [{ em: ISO(s.horasAtras), tipo: "criada", detalhe: s.papel }, { em: ISO(s.horasAtras - s.leadHoras), tipo: "status:em_revisao", detalhe: "encaminhada" }];
    e.ficha = { id: `EXP-${s.id.slice(0, 6).toUpperCase()}`, ...s.ficha };
    e.pendencias = pendencias(e.ficha);
    e.ficha_gerada = true; e.ficha_versao = 1; e.status = s.status;
    e.encaminhamento = s.papel === "desenvolvedor" ? "desenvolvedor" : "workflow";
    for (const [d, ent, p, ev] of s.mapa) e.mapa = setDim(e.mapa, d, ent, p, ev);
    e.mapa.sintese_confirmada = true;
    if (s.status !== "em_revisao") {
      e.revisoes = [{ decisao: "aprovar", comentario: "Pronta para executar.", revisor: "Marina (Lab)", versao_ficha: 1, em: ISO(s.horasAtras - 6) }];
      e.eventos.push({ em: ISO(s.horasAtras - 6), tipo: "status:aprovado", detalhe: "" });
    }
    if (s.parecer) {
      e.bancada = { ...e.bancada, iniciada: true, artefatos: { parecer: s.parecer },
        status: { ficha: "ok", amostra: "ok", construcao: "ok", qualidade: "ok", resultado: "ok" } };
      e.eventos.push({ em: ISO(s.horasAtras - 40), tipo: "status:parecer", detalhe: String(s.parecer.veredito) });
    }
    if (s.decisao) {
      e.decisao = { decisao: s.decisao, comentario: "Piloto em duas regionais.", em: ISO(s.horasAtras - 60) };
      e.eventos.push({ em: ISO(s.horasAtras - 60), tipo: "status:decidido", detalhe: s.decisao });
    }
    return { estado: e, passo: 99, transcricao: s.transcricao };
  });
}
