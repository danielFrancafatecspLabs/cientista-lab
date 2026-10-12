import { useEffect, useMemo, useState } from "react";
import type { BenchmarkLab, Modelo, Toolbox } from "../../api/types";
import { Badge, Empty, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { Copiar } from "./comum";

function ModeloCard({ m }: { m: Modelo }) {
  const { ir } = useApp();
  return (
    <article className={`modelo card${m.grupo === "recomendado" ? " rec" : ""}`}>
      <header>
        <div><span className="eyebrow">{m.fornecedor}</span><h3>{m.nome}</h3></div>
        <Badge tom={m.grupo === "recomendado" ? "accent" : "info"} dot>{m.destaque}</Badge>
      </header>
      <dl className="modelo-ficha">
        <div><dt>Arquitetura</dt><dd>{m.arquitetura}</dd></div>
        <div><dt>Contexto</dt><dd>{m.contexto}</dd></div>
        <div><dt>Licença</dt><dd>{m.licenca}</dd></div>
        {m.modos && <div><dt>Modos</dt><dd>{m.modos.join(" · ")}</dd></div>}
      </dl>
      <p><b>Use para:</b> {m.uso_ideal}</p>
      <p className="muted"><b>Cuidado:</b> {m.cuidados}</p>
      <footer>
        <span className="alias"><code className="mono">{m.alias}</code><Copiar texto={m.alias} rotulo="Copiar alias" /></span>
        <button className="btn sm" onClick={() => ir({ tela: "dev", secao: "recursos", arg: `llm_key~${m.alias}` })}><Icon name="key" size={14} />Pedir chave</button>
      </footer>
    </article>
  );
}

export function BenchmarksLabTabela({ itens, onRemover }: { itens: BenchmarkLab[]; onRemover?: (id: string) => void }) {
  const tarefas = useMemo(() => [...new Set(itens.map((b) => b.tarefa))], [itens]);
  return (
    <div className="bench-lab">
      {tarefas.map((tarefa) => (
        <div key={tarefa} className="bl-grupo">
          <b>{tarefa}</b>
          <table className="tabela">
            <thead><tr><th>Modelo</th><th>Métrica</th><th>Resultado</th><th>Observações</th><th>Quando</th>{onRemover && <th />}</tr></thead>
            <tbody>{itens.filter((b) => b.tarefa === tarefa).map((b) => (
              <tr key={b.id}>
                <td>{b.modelo}{b.ilustrativo && <Badge tom="outline" title="Dado de exemplo do modo demonstração">ilustrativo</Badge>}</td>
                <td>{b.metrica}</td><td className="mono forte">{b.valor}</td>
                <td className="muted">{[b.conjunto, b.observacoes].filter(Boolean).join(" · ") || "—"}</td>
                <td className="muted">{new Date(b.em).toLocaleDateString("pt-BR")} · {b.responsavel}</td>
                {onRemover && <td><button className="btn icon ghost sm" onClick={() => onRemover(b.id)} aria-label="Remover"><Icon name="trash" size={14} /></button></td>}
              </tr>
            ))}</tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export function Modelos({ t }: { t: Toolbox }) {
  const { api } = useApp();
  const [lab, setLab] = useState<BenchmarkLab[] | null>(null);
  useEffect(() => { api.benchmarksLab().then(setLab).catch(() => setLab([])); }, [api]);
  const bp = t.benchmarks_publicos;
  return (
    <div className="secao">
      <header className="secao-cab">
        <span className="eyebrow">Modelos e benchmarks</span>
        <h1>Qual modelo usar</h1>
        <p className="muted">Dá para testar com quase todos os modelos pelo gateway do Lab. Para começar, o Lab recomenda o <b>DeepSeek V4 Flash</b> e, para tarefas difíceis, o <b>V4 Pro</b>. Dados que não podem sair da casa vão para o hub de GPUs.</p>
      </header>

      <h2 className="sub">Recomendados pelo Lab</h2>
      <div className="modelos-grade rec">{t.modelos.filter((m) => m.grupo === "recomendado").map((m) => <ModeloCard key={m.id} m={m} />)}</div>

      <div className="hub-cab">
        <h2 className="sub"><Icon name="cpu" size={18} />{t.hub.nome}</h2>
        <p className="muted">{t.hub.descricao} <span className="mono">{t.hub.protocolo}</span></p>
      </div>
      <div className="modelos-grade">{t.modelos.filter((m) => m.grupo === "hub").map((m) => <ModeloCard key={m.id} m={m} />)}</div>

      <h2 className="sub">Benchmarks do Lab</h2>
      <p className="muted sub-desc">Medidos pelo Lab nos nossos dados e tarefas. Valem mais que qualquer ranking público para decidir.</p>
      {lab === null ? <span className="spinner" /> : lab.length === 0
        ? <Empty icone="chart" titulo="O Lab ainda não registrou benchmarks">Quando o Lab medir um modelo numa tarefa da casa, o resultado aparece aqui.</Empty>
        : <BenchmarksLabTabela itens={lab} />}

      <h2 className="sub">Benchmarks públicos · open-weight</h2>
      <p className="aviso"><Icon name="info" size={14} />{bp.aviso} <span className="muted">Coleta: {bp.coletado_em}.</span></p>
      <div className="tabela-wrap scroll">
        <table className="tabela">
          <thead><tr><th>Modelo</th>{bp.metricas.map((m) => <th key={m.id} title={m.o_que_mede}>{m.nome}</th>)}<th>Fonte</th></tr></thead>
          <tbody>{bp.linhas.map((l) => (
            <tr key={l.modelo}>
              <td><b>{l.modelo}</b></td>
              {bp.metricas.map((m) => <td key={m.id} className="mono">{l.valores[m.id] ?? <span className="muted">—</span>}</td>)}
              <td><a href={l.url} target="_blank" rel="noreferrer" className="fonte">{l.fonte}<Icon name="ext" size={12} /></a></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <div className="leaderboards">
        {bp.leaderboards.map((l) => (
          <a key={l.nome} href={l.url} target="_blank" rel="noreferrer" className="lb card"><b>{l.nome}<Icon name="ext" size={13} /></b><span className="muted">{l.o_que_mede}</span></a>
        ))}
      </div>
    </div>
  );
}
