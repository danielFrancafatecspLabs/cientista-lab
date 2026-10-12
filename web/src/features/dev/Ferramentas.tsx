import { useState } from "react";
import type { Ferramenta, Toolbox } from "../../api/types";
import { Badge, Icon, Tabs } from "../../components/ui";

const STATUS: Record<Ferramenta["status"], { rotulo: string; tom: string }> = {
  adotada: { rotulo: "Adotada pelo Lab", tom: "ok" }, em_avaliacao: { rotulo: "Em avaliação", tom: "warn" }, evitar: { rotulo: "Evitar", tom: "accent" },
};

export function Ferramentas({ t }: { t: Toolbox }) {
  const [filtro, setFiltro] = useState<"todas" | Ferramenta["status"]>("todas");
  const itens = t.ferramentas.filter((f) => filtro === "todas" || f.status === filtro);
  const n = (s: Ferramenta["status"]) => t.ferramentas.filter((f) => f.status === s).length;
  return (
    <div className="secao">
      <header className="secao-cab">
        <span className="eyebrow">Ferramentas e práticas</span>
        <h1>O que o Lab já testou</h1>
        <p className="muted">Ferramentas com o veredito do Lab e as práticas que separam um protótipo de algo que aguenta um piloto.</p>
      </header>
      <Tabs valor={filtro} onChange={setFiltro} itens={[
        { id: "todas", rotulo: "Todas", count: t.ferramentas.length }, { id: "adotada", rotulo: "Adotadas", count: n("adotada") },
        { id: "em_avaliacao", rotulo: "Em avaliação", count: n("em_avaliacao") }, { id: "evitar", rotulo: "Evitar", count: n("evitar") }]} />
      <div className="ferramentas-grade">
        {itens.map((f) => (
          <article key={f.nome} className={`ferramenta card s-${f.status}`}>
            <header><span className="eyebrow">{f.categoria}</span><Badge tom={STATUS[f.status].tom} dot>{STATUS[f.status].rotulo}</Badge></header>
            <h3>{f.nome}</h3>
            <p>{f.para_que}</p>
            <p className="nota-lab"><Icon name="flask" size={14} />{f.nota_lab}</p>
          </article>
        ))}
      </div>

      <h2 className="sub">Boas práticas de desenvolvimento</h2>
      <div className="praticas">
        {t.praticas.map((p, i) => (
          <article key={p.titulo} className="pratica card">
            <span className="pratica-n mono">{String(i + 1).padStart(2, "0")}</span>
            <h3>{p.titulo}</h3>
            <p className="muted">{p.porque}</p>
            <ul>{p.como.map((c) => <li key={c}><Icon name="check" size={13} />{c}</li>)}</ul>
          </article>
        ))}
      </div>
    </div>
  );
}
