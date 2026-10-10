import { useEffect, useRef, useState, type ReactNode } from "react";
import type { PapelId } from "../api/types";
import { useApp } from "../lib/app";
import { Icon } from "./ui";
import "./shell.css";

const ICONE: Record<PapelId, "chat" | "code" | "shield" | "chart"> = { solicitante: "chat", desenvolvedor: "code", lab: "shield", sponsor: "chart" };

export function papelDaRota(r: ReturnType<typeof useApp>["rota"], fallback: PapelId | null): PapelId | null {
  if (r.tela === "lab") return "lab";
  if (r.tela === "sponsor") return "sponsor";
  if (r.tela === "entrada") return null;
  return fallback;
}

function TrocarPapel() {
  const { papeis, rota, ir, perfil, setPerfil } = useApp();
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const atual = papelDaRota(rota, perfil.papel);
  useEffect(() => {
    const fora = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setAberto(false); };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, []);
  if (!papeis) return null;
  const jornadaAtual = papeis.jornadas.find((j) => j.papel === atual);

  const trocar = (p: PapelId) => {
    setAberto(false);
    setPerfil({ papel: p });
    if (p === "lab") return ir({ tela: "lab" });
    if (p === "sponsor") return ir({ tela: "sponsor" });
    const sid = perfil.sessoes[p];
    ir(sid ? { tela: "estudio", sid } : { tela: "entrada", papel: p });
  };

  return (
    <div className="papel-switch" ref={ref}>
      <button className="btn sm" onClick={() => setAberto((x) => !x)} aria-haspopup="menu" aria-expanded={aberto}>
        {atual ? <Icon name={ICONE[atual]} size={15} /> : <Icon name="swap" size={15} />}
        {jornadaAtual ? jornadaAtual.nome : "Escolher papel"}
        <Icon name="chevron" size={14} style={{ transform: "rotate(90deg)" }} />
      </button>
      {aberto && (
        <div className="menu" role="menu">
          <div className="eyebrow" style={{ padding: "8px 12px 6px" }}>Ver o METAEXP como</div>
          {papeis.jornadas.map((j) => (
            <button key={j.papel} role="menuitem" className={j.papel === atual ? "on" : ""} onClick={() => trocar(j.papel)}>
              <span className="mi-ic"><Icon name={ICONE[j.papel]} size={16} /></span>
              <span><b>{j.nome}</b><small>{j.chamada}</small></span>
              {j.papel === atual && <Icon name="check" size={15} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { api, ir, tema, setTema } = useApp();
  const escuro = tema === "dark" || (tema === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return (
    <div className="shell">
      <header className="topbar">
        <button className="brand" onClick={() => ir({ tela: "entrada" })} aria-label="Início">
          <span className="brand-mark"><Icon name="logo" size={16} strokeWidth={2.6} /></span>
          <span className="brand-name">METAEXP</span>
          <span className="brand-sub">beOn Labs</span>
        </button>
        <div className="topbar-right">
          <span className={`modo ${api.modo}`} title={api.modo === "demo" ? "Sem backend: roteiro de demonstração" : "Conectado ao modelo"}>
            <i />{api.modo === "demo" ? "Demonstração" : "Ao vivo"}
          </span>
          <TrocarPapel />
          <button className="btn icon ghost" onClick={() => setTema(escuro ? "light" : "dark")} aria-label="Alternar tema">
            <Icon name={escuro ? "sun" : "moon"} />
          </button>
        </div>
      </header>
      <main className="conteudo">{children}</main>
    </div>
  );
}
