import { useEffect, useMemo, useState } from "react";
import type { BlocoArquitetura, Toolbox } from "../../api/types";
import { Icon, Ring } from "../../components/ui";
import { Copiar } from "./comum";

function Bloco({ b, icone }: { b: BlocoArquitetura; icone: "layers" | "spark" }) {
  return (
    <article className="arq-bloco card">
      <header><span className="rc-ic"><Icon name={icone} size={20} /></span><h3>{b.titulo}</h3></header>
      <p className="arq-resumo">{b.resumo}</p>
      <ul>{b.pontos.map((p) => <li key={p}><Icon name="check" size={14} />{p}</li>)}</ul>
      <p className="arq-quando"><b>Quando usar:</b> {b.quando}</p>
    </article>
  );
}

const chave = (sid?: string) => `metaexp.piloto.${sid ?? "geral"}`;
export function lerPiloto(sid?: string): string[] {
  try { return JSON.parse(localStorage.getItem(chave(sid)) || "[]"); } catch { return []; }
}

export function Arquitetura({ t, sid }: { t: Toolbox; sid?: string }) {
  const a = t.arquitetura;
  const [feitos, setFeitos] = useState<string[]>(() => lerPiloto(sid));
  useEffect(() => { try { localStorage.setItem(chave(sid), JSON.stringify(feitos)); } catch { /* sem armazenamento */ } }, [feitos, sid]);
  const categorias = useMemo(() => [...new Set(a.piloto.map((i) => i.categoria))], [a.piloto]);
  const alternar = (id: string) => setFeitos((f) => (f.includes(id) ? f.filter((x) => x !== id) : [...f, id]));
  const markdown = `# Checklist para virar piloto\n\n${a.piloto.map((i) => `- [${feitos.includes(i.id) ? "x" : " "}] ${i.item} (${i.categoria})`).join("\n")}\n`;
  const pct = a.piloto.length ? feitos.length / a.piloto.length : 0;

  return (
    <div className="secao">
      <header className="secao-cab">
        <span className="eyebrow">Boas práticas de arquitetura</span>
        <h1>Do protótipo ao piloto</h1>
        <p className="muted">O que o Lab já testou e recomenda para construir rápido sem jogar trabalho fora quando o experimento der certo.</p>
      </header>

      <div className="arq-duo">
        <Bloco b={a.langgraph} icone="layers" />
        <Bloco b={a.n8n} icone="spark" />
      </div>
      <p className="combinacao"><Icon name="info" size={16} />{a.combinacao}</p>

      <h2 className="sub">Arquitetura de referência</h2>
      <ol className="camadas">
        {a.camadas.map((c, i) => (
          <li key={c.nome} style={{ ["--i" as string]: i }}>
            <span className="camada-nome">{c.nome}</span>
            <span className="camada-itens">{c.itens.map((x) => <span key={x}>{x}</span>)}</span>
          </li>
        ))}
      </ol>

      <div className="piloto card" id="piloto">
        <header>
          <Ring valor={pct} size={52} stroke={5}>{feitos.length}/{a.piloto.length}</Ring>
          <div><h2>O que precisa ter para virar piloto</h2><p className="muted">Marque o que seu experimento já tem. O Lab usa esta lista na revisão do piloto.</p></div>
          <Copiar texto={markdown} rotulo="Copiar em Markdown" />
        </header>
        <div className="piloto-grupos">
          {categorias.map((cat) => (
            <div key={cat}>
              <span className="eyebrow">{cat}</span>
              <ul>{a.piloto.filter((i) => i.categoria === cat).map((i) => (
                <li key={i.id}>
                  <label className={feitos.includes(i.id) ? "ok" : ""}>
                    <input type="checkbox" checked={feitos.includes(i.id)} onChange={() => alternar(i.id)} />
                    <span><b>{i.item}</b><small>{i.por_que}</small></span>
                  </label>
                </li>
              ))}</ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
