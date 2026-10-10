import { useCallback, useEffect, useState } from "react";
import type { Detalhe, Resumo, Status } from "../../api/types";
import { Avatar, Badge, Empty, Icon, Meter, Ring, Tabs } from "../../components/ui";
import { useApp } from "../../lib/app";
import { DOMINIO, haQuanto, RECOMENDACAO, STATUS } from "../../lib/format";
import { Markdown } from "../../lib/markdown";
import "./lab.css";

type Fila = "revisar" | "aprovados" | "devolvidos";
const FILAS: Record<Fila, Status[]> = { revisar: ["em_revisao"], aprovados: ["aprovado", "em_execucao", "parecer", "decidido"], devolvidos: ["devolvido"] };
const RUBRICA: Record<string, string> = { problema: "Problema", hipotese: "Hipótese", criterios: "Critérios", dados: "Dados", viabilidade: "Viabilidade" };

export function FichaDoc({ d }: { d: Detalhe }) {
  const f = d.ficha;
  return (
    <div className="ficha-doc">
      <div className="fd-hip"><span className="eyebrow">Hipótese</span><p>{f.hipotese}</p></div>
      <dl>
        {([["Problema", f.problema], ["Impacto", f.publico_afetado], ["Objetivo", f.objetivo], ["Metodologia", f.metodologia],
          ["Dados", f.dados], ["Amostra", f.amostra], ["BO", f.bo], ["Sponsor", f.sponsor]] as [string, string | undefined][]).map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd>{v || <span className="muted">—</span>}</dd></div>
        ))}
      </dl>
      <div>
        <span className="eyebrow">Métricas e critérios</span>
        <ul className="fd-metricas">{(f.metricas ?? []).map((m) => <li key={m.nome}><span>{m.descricao}</span><b className="mono">{m.criterio_aceite}</b>{m.obrigatoria && <Badge>obrigatória</Badge>}</li>)}</ul>
      </div>
      {f.detalhes_tecnicos?.avaliacao && (
        <div>
          <span className="eyebrow">Protocolo de avaliação</span>
          <p className="fd-p">{f.detalhes_tecnicos.avaliacao.conjunto}</p>
          <ul className="fd-metricas">{f.detalhes_tecnicos.avaliacao.metricas.map((m) => <li key={m.nome}><span className="mono">{m.nome}</span><b className="mono">{m.baseline ? `${m.baseline} → ` : ""}{m.alvo}</b></li>)}</ul>
        </div>
      )}
      {d.pendencias.length > 0 && <div className="fd-pend"><Icon name="info" size={14} />Checklist com pendências: {d.pendencias.join("; ")}</div>}
    </div>
  );
}

function PreRevisaoView({ d, onPedir, pedindo, onUsar }: { d: Detalhe; onPedir: () => void; pedindo: boolean; onUsar: (t: string) => void }) {
  const p = d.pre_revisao;
  if (!p) {
    return (
      <div className="pre-vazia">
        <span className="pv-ic"><Icon name="spark" size={22} /></span>
        <h3>Pré-análise do Agente Revisor</h3>
        <p className="muted">O Revisor lê a ficha, o mapa do problema e a conversa, dá nota na rubrica do Lab citando a evidência de cada nota e sugere ajustes concretos. Quem decide é você.</p>
        <button className="btn primary" onClick={onPedir} disabled={pedindo}>{pedindo ? <><span className="spinner" />Lendo ficha, mapa e conversa…</> : <>Pedir pré-análise<Icon name="arrow" size={15} /></>}</button>
      </div>
    );
  }
  const r = RECOMENDACAO[p.recomendacao];
  return (
    <div className="pre">
      <div className="pre-cab"><Badge tom={r.tom} dot>Recomendação: {r.rotulo}</Badge><button className="btn sm ghost" onClick={onPedir} disabled={pedindo}>{pedindo ? <span className="spinner" /> : <Icon name="spark" size={14} />}Refazer</button></div>
      <p className="pre-resumo">{p.resumo}</p>
      <ul className="rubrica">
        {p.notas.map((n) => (
          <li key={n.criterio}>
            <span className="rb-nome">{RUBRICA[n.criterio] ?? n.criterio}</span>
            <span className={`rb-nota n${n.nota}`}>{n.nota}<small>/5</small></span>
            <Meter valor={n.nota} max={5} accent={n.nota <= 2} rotulo={`Nota de ${n.criterio}`} />
            <q className="rb-just">{n.justificativa}</q>
          </li>
        ))}
      </ul>
      <div className="pre-cols">
        <div><span className="eyebrow">Pontos fortes</span><ul>{p.pontos_fortes.map((x) => <li key={x}><Icon name="check" size={13} />{x}</li>)}</ul></div>
        <div><span className="eyebrow">Riscos</span><ul className="riscos">{p.riscos.map((x) => <li key={x}><Icon name="info" size={13} />{x}</li>)}</ul></div>
      </div>
      {p.ajustes_sugeridos.length > 0 && (
        <div className="ajustes">
          <span className="eyebrow">Ajustes sugeridos</span>
          <ul>{p.ajustes_sugeridos.map((x) => <li key={x}><span>{x}</span><button className="btn sm ghost" onClick={() => onUsar(x)}>Usar no comentário</button></li>)}</ul>
        </div>
      )}
    </div>
  );
}

function Evidencias({ d }: { d: Detalhe }) {
  const dims = d.mapa.dimensoes.filter((x) => x.profundidade > 0);
  return (
    <div className="evidencias">
      <div className="ev-mapa">
        <div className="ev-cab"><Ring valor={d.mapa.cobertura} size={40} stroke={4}>{Math.round(d.mapa.cobertura * 100)}</Ring>
          <div><b>Mapa do problema</b><small>{d.mapa.sintese_confirmada ? "Entendimento confirmado pela pessoa" : "Síntese não confirmada"}</small></div></div>
        {d.mapa.sintese && <p className="ev-sintese">{d.mapa.sintese}</p>}
        <ul>{dims.map((x) => (
          <li key={x.id}><div><b>{x.nome}</b><Meter valor={x.profundidade} /></div><p>{x.entendimento}</p>{x.evidencia && <q>{x.evidencia}</q>}</li>
        ))}</ul>
      </div>
      <div className="ev-conversa">
        <span className="eyebrow">Conversa com o Cientista</span>
        {d.transcricao.length === 0 && <p className="muted">Sem transcrição.</p>}
        {d.transcricao.map((t, i) => (
          <div key={i} className={`tr ${t.de}`}><span className="tr-de">{t.de === "pessoa" ? d.nome : "Cientista"}</span><div className="prosa-mini"><Markdown texto={t.texto} /></div></div>
        ))}
      </div>
    </div>
  );
}

function Detalhe({ id, onMudou }: { id: string; onMudou: () => void }) {
  const { api, perfil } = useApp();
  const [d, setD] = useState<Detalhe | null>(null);
  const [aba, setAba] = useState<"pre" | "ficha" | "evidencias">("pre");
  const [pedindo, setPedindo] = useState(false);
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState<"aprovar" | "devolver" | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(() => api.experimento(id).then(setD).catch((e) => setErro(e.message)), [api, id]);
  useEffect(() => { setD(null); setComentario(""); setErro(null); setAba("pre"); carregar(); }, [carregar]);

  const pedir = async () => {
    setPedindo(true); setErro(null);
    try { await api.preRevisao(id); await carregar(); onMudou(); } catch (e) { setErro((e as Error).message); }
    setPedindo(false);
  };
  const decidir = async (decisao: "aprovar" | "devolver") => {
    setEnviando(decisao); setErro(null);
    try { await api.revisao(id, { decisao, comentario, revisor: perfil.nome ? `${perfil.nome} (Lab)` : "Lab" }); await carregar(); onMudou(); setComentario(""); }
    catch (e) { setErro((e as Error).message); }
    setEnviando(null);
  };

  if (!d) return <div className="lab-detalhe"><div className="estudio-carregando"><span className="spinner" /></div></div>;
  const st = STATUS[d.status];
  const emRevisao = d.status === "em_revisao";
  return (
    <section className="lab-detalhe">
      <header className="ld-cab">
        <div className="ld-meta">
          <Avatar nome={d.nome} tom={d.papel === "desenvolvedor" ? "var(--ag-dev)" : "var(--ag-cientista)"} />
          <span><b>{d.nome}</b><small>{d.papel === "desenvolvedor" ? "Desenvolvedor" : "Solicitante"} · {DOMINIO[d.ficha.dominio ?? ""] ?? "—"} · versão {d.ficha_versao}</small></span>
          <Badge tom={st.tom} dot>{st.rotulo}</Badge>
        </div>
        <h2>{d.ficha.titulo}</h2>
        <Tabs valor={aba} onChange={setAba} itens={[
          { id: "pre", rotulo: "Pré-análise", icone: "spark" }, { id: "ficha", rotulo: "Ficha", icone: "doc" }, { id: "evidencias", rotulo: "Evidências", icone: "quote" }]} />
      </header>
      <div className="ld-corpo scroll">
        {aba === "pre" && <PreRevisaoView d={d} onPedir={pedir} pedindo={pedindo} onUsar={(t) => setComentario((c) => (c ? `${c}\n- ${t}` : `- ${t}`))} />}
        {aba === "ficha" && <FichaDoc d={d} />}
        {aba === "evidencias" && <Evidencias d={d} />}
        {d.revisoes.length > 0 && (
          <div className="historico-rev">
            <span className="eyebrow">Histórico de revisões</span>
            {d.revisoes.map((r, i) => <p key={i}><Badge tom={r.decisao === "aprovar" ? "ok" : "accent"}>{r.decisao === "aprovar" ? "Aprovada" : "Devolvida"}</Badge> v{r.versao_ficha} · {r.revisor}{r.comentario ? `: “${r.comentario}”` : ""}</p>)}
          </div>
        )}
      </div>
      {emRevisao && (
        <footer className="ld-decisao">
          <textarea className="textarea" rows={2} value={comentario} onChange={(e) => setComentario(e.target.value)}
            placeholder="Comentário para o Cientista e para a pessoa (obrigatório para devolver)" />
          {erro && <p className="erro">{erro}</p>}
          <div className="ld-botoes">
            <button className="btn" onClick={() => decidir("devolver")} disabled={!!enviando || !comentario.trim()}>{enviando === "devolver" ? <span className="spinner" /> : <Icon name="back" size={15} />}Devolver com ajustes</button>
            <button className="btn accent" onClick={() => decidir("aprovar")} disabled={!!enviando}>{enviando === "aprovar" ? <span className="spinner" /> : <Icon name="check" size={15} />}Aprovar (G0)</button>
          </div>
        </footer>
      )}
    </section>
  );
}

export function Lab({ id }: { id?: string }) {
  const { api, ir } = useApp();
  const [fila, setFila] = useState<Fila>("revisar");
  const [todos, setTodos] = useState<Resumo[] | null>(null);
  const carregar = useCallback(() => api.experimentos().then(setTodos), [api]);
  useEffect(() => { carregar(); }, [carregar]);
  const itens = (todos ?? []).filter((r) => FILAS[fila].includes(r.status));
  const contagem = (f: Fila) => (todos ?? []).filter((r) => FILAS[f].includes(r.status)).length;
  useEffect(() => {
    if (!id && todos && itens.length) ir({ tela: "lab", id: itens[0].id });
  }, [todos, fila]); // eslint-disable-line

  return (
    <div className="lab">
      <aside className="lab-fila">
        <div className="lf-cab">
          <span className="eyebrow">Lab · gate G0</span>
          <h1>Revisão de fichas</h1>
          <Tabs valor={fila} onChange={setFila} itens={[
            { id: "revisar", rotulo: "Para revisar", count: contagem("revisar") }, { id: "devolvidos", rotulo: "Devolvidas", count: contagem("devolvidos") },
            { id: "aprovados", rotulo: "Aprovadas", count: contagem("aprovados") }]} />
        </div>
        <ul className="lf-lista scroll">
          {todos === null && <li className="estudio-carregando"><span className="spinner" /></li>}
          {todos && itens.length === 0 && <li><Empty icone="check" titulo={fila === "revisar" ? "Nada para revisar" : "Nada por aqui"}>{fila === "revisar" ? "Quando alguém encaminhar uma ficha, ela aparece aqui." : ""}</Empty></li>}
          {itens.map((r) => (
            <li key={r.id}>
              <button className={`lf-item${r.id === id ? " sel" : ""}`} onClick={() => ir({ tela: "lab", id: r.id })}>
                <span className="lf-topo"><b>{r.titulo}</b>{r.recomendacao && <Badge tom={RECOMENDACAO[r.recomendacao].tom}>{RECOMENDACAO[r.recomendacao].rotulo}</Badge>}</span>
                <span className="lf-hip">{r.hipotese}</span>
                <span className="lf-pe"><span>{r.nome}</span><span>{DOMINIO[r.dominio ?? ""] ?? ""}</span><span>v{r.versao}</span><span>{haQuanto(r.atualizada_em)}</span>
                  <span className="lf-cob" title="Cobertura do mapa do problema"><Icon name="map" size={12} />{Math.round(r.cobertura * 100)}%</span></span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      {id ? <Detalhe key={id} id={id} onMudou={carregar} /> : <section className="lab-detalhe"><Empty icone="shield" titulo="Escolha uma ficha na fila" /></section>}
    </div>
  );
}
