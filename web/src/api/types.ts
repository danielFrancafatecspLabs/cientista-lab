// Contrato entre o app e o backend (metaexp/api.py). Mantenha em sincronia com
// Sessao.snapshot(), Sessao.resumo() e os eventos SSE dos agentes.

export type PapelId = "solicitante" | "desenvolvedor" | "lab" | "sponsor";
export type PapelConversa = "solicitante" | "desenvolvedor";
export type Status =
  | "conversa" | "em_revisao" | "devolvido" | "aprovado" | "em_execucao" | "parecer" | "decidido" | "encerrado";

export interface Preferencia { id: string; pergunta: string; opcoes: [string, string][]; padrao: string }
export interface Jornada {
  papel: PapelId; nome: string; chamada: string; descricao: string; promessa: string;
  tipo: "conversa" | "painel"; etapas: string[]; destinos: string[]; preferencias: Preferencia[];
}
export interface Dimensao { id: string; nome: string; busca: string; peso: number; minimo: number }
export interface Papeis {
  jornadas: Jornada[];
  etapas_ciclo: string[];
  dimensoes: Dimensao[];
  tecnicas: Record<string, { nome: string; como: string }>;
}

export interface Metrica { nome: string; descricao: string; criterio_aceite: string; obrigatoria: boolean }
export interface Abordagem {
  nome: string; descricao: string; pros: string[]; contras: string[]; custo: string; latencia: string;
  complexidade: "baixa" | "media" | "alta"; recomendada: boolean;
}
export interface MetricaTecnica { nome: string; alvo: string; baseline?: string | null; liga_a?: string | null }
export interface Protocolo {
  conjunto: string; tamanho?: number | null; divisao?: string | null; metricas: MetricaTecnica[]; gate_regressao?: string | null;
}
export interface Desenho {
  stack?: string; fontes_dados?: string; restricoes?: string[]; baseline?: string; abordagens?: Abordagem[];
  abordagem_escolhida?: string; avaliacao?: Protocolo | null; arquitetura?: string[]; riscos_tecnicos?: string[];
}
export interface Ficha {
  id?: string; titulo?: string; dominio?: string; problema?: string; publico_afetado?: string; objetivo?: string;
  hipotese?: string; metodologia?: string; tecnologia?: string; tecnica?: string; justificativa_tecnica?: string;
  golden_path?: string; metricas?: Metrica[]; dados?: string; amostra?: string; bo?: string; sponsor?: string;
  skills?: string[]; execucao?: string; riscos?: string[]; detalhes_tecnicos?: Desenho;
}

export interface DimensaoEstado extends Dimensao { entendimento: string | null; profundidade: number; evidencia: string | null }
export interface Porque { dimensao: string; tecnica: string; por_que: string; tecnica_nome?: string; dimensao_nome?: string }
export interface Mapa {
  cobertura: number; pronto: boolean; sintese: string | null; sintese_confirmada: boolean;
  pergunta_atual: Porque | null; dimensoes: DimensaoEstado[];
}

export interface NotaRubrica { criterio: string; nota: number; justificativa: string }
export interface PreRevisao {
  resumo: string; notas: NotaRubrica[]; pontos_fortes: string[]; riscos: string[]; ajustes_sugeridos: string[];
  recomendacao: "aprovar" | "aprovar_com_ajustes" | "devolver";
}
export interface Revisao { decisao: "aprovar" | "devolver"; comentario: string; revisor: string; versao_ficha: number; em: string }
export interface DecisaoSponsor { decisao: "escalar" | "iterar" | "encerrar"; comentario: string; em: string }

export interface Bancada {
  iniciada: boolean; etapa: number; status: Record<string, string>; aguardando: string | null;
  artefatos: Record<string, any>; rodadas: Rodada[]; decisao_final: string | null;
}
export interface Rodada { k: number; q: number; aderencia: number; feedback: string[]; criterios: { criterio: string; atendido: boolean; evidencia: string }[] }

export interface Estado {
  id: string; nome: string; papel: PapelConversa; preferencias: Record<string, string>; status: Status;
  ficha: Ficha; faltantes: string[]; pendencias: string[]; ficha_gerada: boolean; ficha_versao: number;
  mapa: Mapa; desenho_pendencias: string[] | null; encaminhamento: string | null;
  pre_revisao: PreRevisao | null; revisoes: Revisao[]; feedback_lab: Revisao | null; decisao: DecisaoSponsor | null;
  eventos: { em: string; tipo: string; detalhe: string }[]; bancada: Bancada; arquivos: any[]; similares: string[];
  transcricao?: { de: "pessoa" | "cientista"; texto: string }[];
}

export interface Resumo {
  id: string; titulo: string; papel: PapelConversa; nome: string; status: Status; dominio?: string | null;
  hipotese?: string | null; bo?: string | null; sponsor?: string | null; criada_em: string; atualizada_em: string;
  versao: number; encaminhamento: string | null; lead_time_horas: number | null; revisoes: number;
  recomendacao: PreRevisao["recomendacao"] | null; veredito: string | null; decisao: string | null; cobertura: number;
}
export interface Detalhe extends Estado {
  resumo: Resumo; transcricao: { de: "pessoa" | "cientista"; texto: string }[]; markdown: string;
}
export interface Portfolio {
  kpis: {
    experimentos: number; em_revisao: number; aprovacao_primeira_revisao: number | null;
    lead_time_mediano_horas: number | null; cobertura_media_mapa: number | null; decisoes_pendentes: number;
  };
  por_status: Partial<Record<Status, number>>;
  vereditos: Record<string, number>;
  historico: { total: number; vereditos: Record<string, number> };
}
export interface Kit { pasta: string; arquivos: Record<string, string> }

// ---------------------------------------------------------------- eventos ----

export type CardKind =
  | "sintese" | "similares" | "amostra" | "abordagens" | "avaliacao" | "desenho" | "tecnologia" | "skills"
  | "ficha_gerada" | "ficha" | "plano" | "rodada" | "parecer";

export type Evento =
  | { type: "text"; delta: string }
  | { type: "mapa"; mapa: Mapa }
  | ({ type: "porque" } & Porque)
  | { type: "ficha"; ficha: Ficha; changed: string[]; pendencias: string[]; gerada: boolean }
  | { type: "card"; kind: CardKind; data: any }
  | { type: "chips"; options: string[] }
  | { type: "upload"; descricao: string; formatos: string[] }
  | { type: "handoff"; destino: string; resumo: string; status: Status; ficha: Ficha; markdown: string; kit?: string[] }
  | { type: "auto_ingestao" }
  | { type: "retry" }
  | { type: "etapa"; etapa: string; status: string }
  | { type: "mensagem"; agente: string; texto: string }
  | { type: "aprovacao"; etapa: string; opcoes: { id: string; rotulo: string }[] }
  | { type: "aguardando"; motivo: string; status: Status; message: string }
  | { type: "error"; message: string }
  | { type: "done"; state: Estado };

export type OnEvento = (e: Evento) => void;

export interface Backend {
  modo: "ao_vivo" | "demo";
  papeis(): Promise<Papeis>;
  criarSessao(body: { nome?: string; papel: PapelConversa; preferencias: Record<string, string> }): Promise<Estado>;
  sessao(id: string): Promise<Estado>;
  iniciar(id: string, on: OnEvento): Promise<void>;
  mensagem(id: string, texto: string, on: OnEvento): Promise<void>;
  arquivo(id: string, file: File, on: OnEvento): Promise<void>;
  retomar(id: string, on: OnEvento): Promise<void>;
  bancada(id: string, body: { decisao?: string; comentario?: string }, on: OnEvento): Promise<void>;
  kit(id: string): Promise<Kit>;
  kitUrl(id: string): string | null;
  experimentos(status?: Status[]): Promise<Resumo[]>;
  experimento(id: string): Promise<Detalhe>;
  preRevisao(id: string): Promise<PreRevisao>;
  revisao(id: string, body: { decisao: "aprovar" | "devolver"; comentario: string; revisor: string }): Promise<Estado>;
  decisao(id: string, body: { decisao: "escalar" | "iterar" | "encerrar"; comentario: string }): Promise<Estado>;
  portfolio(): Promise<Portfolio>;
}
