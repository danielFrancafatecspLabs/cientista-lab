// Backend real: REST + SSE sobre POST (fetch com leitura incremental do corpo).
import type { Backend, Estado, OnEvento, Status } from "./types";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${r.status}`);
  }
  return r.json();
}

async function sse(url: string, body: unknown, on: OnEvento): Promise<void> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
  if (!r.ok || !r.body) {
    const detail = await r.json().then((b) => b.detail).catch(() => null);
    on({ type: "error", message: detail || `Erro ${r.status}` });
    return;
  }
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const bloco = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const data = bloco.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("\n");
      if (data) on(JSON.parse(data));
    }
  }
}

function b64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => res(String(fr.result).split(",")[1] ?? "");
    fr.onerror = rej;
    fr.readAsDataURL(file);
  });
}

export const live: Backend = {
  modo: "ao_vivo",
  papeis: () => json("/api/papeis"),
  criarSessao: (body) => json<Estado>("/api/sessoes", { method: "POST", body: JSON.stringify(body) }),
  sessao: (id) => json(`/api/sessoes/${id}`),
  iniciar: (id, on) => sse(`/api/sessoes/${id}/iniciar`, {}, on),
  mensagem: (id, texto, on) => sse(`/api/sessoes/${id}/mensagens`, { texto }, on),
  arquivo: async (id, file, on) => sse(`/api/sessoes/${id}/arquivos`, { nome: file.name, conteudo_base64: await b64(file) }, on),
  retomar: (id, on) => sse(`/api/sessoes/${id}/retomar`, {}, on),
  bancada: (id, body, on) => sse(`/api/sessoes/${id}/bancada`, body, on),
  kit: (id) => json(`/api/sessoes/${id}/kit`),
  kitUrl: (id) => `/api/sessoes/${id}/kit.zip`,
  experimentos: (status?: Status[]) => json(`/api/experimentos${status?.length ? `?status=${status.join(",")}` : ""}`),
  experimento: (id) => json(`/api/experimentos/${id}`),
  preRevisao: (id) => json(`/api/experimentos/${id}/pre-revisao`, { method: "POST" }),
  revisao: (id, body) => json(`/api/experimentos/${id}/revisao`, { method: "POST", body: JSON.stringify(body) }),
  decisao: (id, body) => json(`/api/experimentos/${id}/decisao`, { method: "POST", body: JSON.stringify(body) }),
  portfolio: () => json("/api/portfolio"),
};

export async function backendDisponivel(): Promise<boolean> {
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 1500);
    const r = await fetch("/api/health", { signal: ctl.signal });
    clearTimeout(t);
    return r.ok && (await r.json()).ok === true;
  } catch {
    return false;
  }
}
