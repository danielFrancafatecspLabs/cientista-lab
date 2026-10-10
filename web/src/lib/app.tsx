// Estado global do app: backend (ao vivo ou demonstração), rota por hash e perfil da pessoa.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Backend, Papeis, PapelId } from "../api/types";

export type Rota =
  | { tela: "entrada"; papel?: PapelId }
  | { tela: "estudio"; sid: string }
  | { tela: "bancada"; sid: string }
  | { tela: "lab"; id?: string }
  | { tela: "sponsor"; id?: string };

export function lerRota(hash = window.location.hash): Rota {
  const [, tela, arg] = hash.replace(/^#\/?/, "/").split("/");
  if (tela === "estudio" && arg) return { tela: "estudio", sid: arg };
  if (tela === "bancada" && arg) return { tela: "bancada", sid: arg };
  if (tela === "lab") return { tela: "lab", id: arg || undefined };
  if (tela === "sponsor") return { tela: "sponsor", id: arg || undefined };
  if (tela === "entrada" && arg) return { tela: "entrada", papel: arg as PapelId };
  return { tela: "entrada" };
}

export function hrefDe(r: Rota): string {
  switch (r.tela) {
    case "estudio": return `#/estudio/${r.sid}`;
    case "bancada": return `#/bancada/${r.sid}`;
    case "lab": return r.id ? `#/lab/${r.id}` : "#/lab";
    case "sponsor": return r.id ? `#/sponsor/${r.id}` : "#/sponsor";
    default: return r.papel ? `#/entrada/${r.papel}` : "#/";
  }
}

interface Perfil { nome: string; papel: PapelId | null; sessoes: Partial<Record<PapelId, string>> }

const LS = "metaexp.perfil.v3";
function lerPerfil(): Perfil {
  try { return { nome: "", papel: null, sessoes: {}, ...JSON.parse(localStorage.getItem(LS) || "{}") }; } catch { return { nome: "", papel: null, sessoes: {} }; }
}

interface Ctx {
  api: Backend;
  papeis: Papeis | null;
  rota: Rota;
  ir: (r: Rota) => void;
  perfil: Perfil;
  setPerfil: (p: Partial<Perfil>) => void;
  tema: "light" | "dark" | "auto";
  setTema: (t: "light" | "dark" | "auto") => void;
}

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ api, children }: { api: Backend; children: ReactNode }) {
  const [rota, setRota] = useState<Rota>(() => lerRota());
  const [papeis, setPapeis] = useState<Papeis | null>(null);
  const [perfil, setPerfilState] = useState<Perfil>(lerPerfil);
  const [tema, setTemaState] = useState<"light" | "dark" | "auto">(() => (localStorage.getItem("metaexp.tema") as never) || "auto");

  useEffect(() => { api.papeis().then(setPapeis).catch(() => setPapeis(null)); }, [api]);
  useEffect(() => {
    const on = () => setRota(lerRota());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    if (tema === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", tema);
    try { localStorage.setItem("metaexp.tema", tema); } catch { /* sem armazenamento */ }
  }, [tema]);

  const ir = useCallback((r: Rota) => {
    const h = hrefDe(r);
    if (window.location.hash !== h) window.location.hash = h;
    setRota(r);
    window.scrollTo({ top: 0 });
  }, []);
  const setPerfil = useCallback((p: Partial<Perfil>) => {
    setPerfilState((cur) => {
      const novo = { ...cur, ...p, sessoes: { ...cur.sessoes, ...p.sessoes } };
      try { localStorage.setItem(LS, JSON.stringify(novo)); } catch { /* sem armazenamento */ }
      return novo;
    });
  }, []);

  const value = useMemo(() => ({ api, papeis, rota, ir, perfil, setPerfil, tema, setTema: setTemaState }),
    [api, papeis, rota, ir, perfil, setPerfil, tema]);
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp(): Ctx {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp fora do AppProvider");
  return c;
}
