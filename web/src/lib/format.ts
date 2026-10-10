import type { Status } from "../api/types";

export const STATUS: Record<Status, { rotulo: string; tom: "" | "ok" | "warn" | "info" | "accent" }> = {
  conversa: { rotulo: "Em conversa", tom: "" },
  em_revisao: { rotulo: "Revisão do Lab", tom: "warn" },
  devolvido: { rotulo: "Ajustes pedidos", tom: "accent" },
  aprovado: { rotulo: "Aprovado (G0)", tom: "ok" },
  em_execucao: { rotulo: "Na bancada", tom: "info" },
  parecer: { rotulo: "Parecer pronto", tom: "ok" },
  decidido: { rotulo: "Decidido", tom: "" },
  encerrado: { rotulo: "Encerrado", tom: "" },
};

export const VEREDITO: Record<string, { rotulo: string; tom: "ok" | "warn" | "accent" | "" }> = {
  validada: { rotulo: "Validada", tom: "ok" },
  parcialmente_comprovada: { rotulo: "Parcial", tom: "warn" },
  invalidada: { rotulo: "Invalidada", tom: "accent" },
  inconclusiva: { rotulo: "Inconclusiva", tom: "" },
};

export const RECOMENDACAO: Record<string, { rotulo: string; tom: "ok" | "warn" | "accent" }> = {
  aprovar: { rotulo: "Aprovar", tom: "ok" },
  aprovar_com_ajustes: { rotulo: "Aprovar com ajustes", tom: "warn" },
  devolver: { rotulo: "Devolver", tom: "accent" },
};

export const DOMINIO: Record<string, string> = {
  atendimento: "Atendimento", rede: "Rede", digital: "Digital", financeiro: "Financeiro", suprimentos: "Suprimentos",
  juridico: "Jurídico", rh: "RH", marketing: "Marketing", operacoes: "Operações", outro: "Outra",
};

export function pct(x: number | null | undefined, casas = 0): string {
  if (x == null) return "—";
  return `${(x * 100).toFixed(casas).replace(".", ",")}%`;
}

export function horas(h: number | null | undefined): string {
  if (h == null) return "—";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `${h.toFixed(1).replace(".", ",")} h`;
  return `${Math.round(h / 24)} dias`;
}

export function haQuanto(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "agora";
  if (s < 3600) return `há ${Math.round(s / 60)} min`;
  if (s < 86400) return `há ${Math.round(s / 3600)} h`;
  return `há ${Math.round(s / 86400)} d`;
}

export function iniciais(nome: string): string {
  return nome.split(/[\s·]+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("") || "?";
}
