import { useCallback, useEffect, useRef, useState } from "react";
import type { Estado, Evento, Rodada } from "../../api/types";
import { Badge, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { STATUS, VEREDITO } from "../../lib/format";
import { CardAmostra } from "../estudio/cards";
import "../estudio/cards.css";
import "./bancada.css";

const ETAPAS = [
  { id: "ficha", nome: "Ficha aprovada", gate: "G0", agente: "cientista", quem: "Cientista + Lab" },
  { id: "amostra", nome: "Amostra e dados", gate: "G1", agente: "dados", quem: "Agente de Dados" },
  { id: "construcao", nome: "Construção", gate: "", agente: "dev", quem: "Agente Desenvolvedor" },
  { id: "qualidade", nome: "Qualidade · Ralph Loop", gate: "G2", agente: "qa", quem: "Agente QA" },
  { id: "resultado", nome: "Parecer", gate: "G3", agente: "analista", quem: "Agente Analista" },
];
type Feed = { tipo: "msg"; agente: string; texto: string } | { tipo: "card"; kind: string; data: any };

function Rodadas({ rodadas, qmin = 0.85 }: { rodadas: Rodada[]; qmin?: number }) {
  return (
    <div className="ccard largo">
      <div className="ccard-cab"><Icon name="chart" size={15} /><span>Ralph Loop: qualidade por rodada</span><small className="muted">meta Qk ≥ {qmin.toString().replace(".", ",")}</small></div>
      <div className="rodadas">
        <span className="qmin" style={{ bottom: `${qmin * 100}%` }} />
        {rodadas.map((r) => (
          <div key={r.k} className={`rodada${r.q >= qmin ? " ok" : ""}`} title={r.feedback.join(" · ")}>
            <span className="r-bar" style={{ height: `${Math.max(4, r.q * 100)}%` }}><b>{Math.round(r.q * 100)}</b></span>
            <span className="r-k mono">k={r.k}</span>
          </div>
        ))}
      </div>
      {rodadas.some((r) => r.feedback.length) && (
        <ul className="lista-mini">{rodadas.filter((r) => r.feedback.length).map((r) => <li key={r.k} className="alerta"><Icon name="info" size={13} />Rodada {r.k}: {r.feedback.join("; ")}</li>)}</ul>
      )}
    </div>
  );
}

function Plano({ data }: { data: any }) {
  return (
    <div className="ccard largo">
      <div className="ccard-cab"><Icon name="layers" size={15} /><span>Plano da solução</span></div>
      <p className="ccard-texto">{data.abordagem}</p>
      <ol className="cadeia">{(data.componentes ?? []).map((c: string, i: number) => <li key={c}><span className="mono">{i + 1}</span>{c}</li>)}</ol>
    </div>
  );
}

export function Parecer({ data }: { data: any }) {
  const v = VEREDITO[data.veredito] ?? { rotulo: data.veredito, tom: "" };
  return (
    <div className="ccard largo parecer">
      <div className="ccard-cab"><Icon name="doc" size={15} /><span>Parecer do Agente Analista</span>
        {data.resultados?.simulado && <Badge tom="warn" title="Executor simulado: os números não foram medidos">resultados simulados</Badge>}</div>
      <div className="veredito"><Badge tom={v.tom} dot>{v.rotulo}</Badge><h3>{data.titulo}</h3></div>
      <p className="ccard-texto">{data.resumo}</p>
      {data.resultados?.metricas?.length ? (
        <table className="tabela">
          <thead><tr><th>Critério</th><th>Meta</th><th>Resultado</th><th></th></tr></thead>
          <tbody>{data.resultados.metricas.map((m: any) => (
            <tr key={m.metrica}><td className="mono">{m.metrica}</td><td className="mono">{m.meta}</td><td className="mono"><b>{m.resultado}</b></td>
              <td>{m.atendida ? <Badge tom="ok">atendido</Badge> : <Badge tom="accent">não atendido</Badge>}</td></tr>
          ))}</tbody>
        </table>
      ) : null}
      <div className="parecer-cols">
        {data.evidencias?.length ? <div><span className="eyebrow">Evidências</span><ul>{data.evidencias.map((x: string) => <li key={x}>{x}</li>)}</ul></div> : null}
        {data.riscos?.length ? <div><span className="eyebrow">Riscos</span><ul>{data.riscos.map((x: string) => <li key={x}>{x}</li>)}</ul></div> : null}
        {data.proximos_passos?.length ? <div><span className="eyebrow">Próximos passos</span><ul>{data.proximos_passos.map((x: string) => <li key={x}>{x}</li>)}</ul></div> : null}
      </div>
    </div>
  );
}

function feedInicial(e: Estado): Record<string, Feed[]> {
  const a = e.bancada.artefatos;
  const f: Record<string, Feed[]> = {};
  if (e.bancada.iniciada) f.ficha = [{ tipo: "msg", agente: "cientista", texto: "A ficha foi aprovada pelo Lab." }];
  if (a.amostra) f.amostra = [{ tipo: "card", kind: "amostra", data: a.amostra }];
  if (a.plano) f.construcao = [{ tipo: "card", kind: "plano", data: a.plano }];
  if (e.bancada.rodadas.length) f.qualidade = [{ tipo: "card", kind: "rodadas", data: e.bancada.rodadas }];
  if (a.parecer) f.resultado = [{ tipo: "card", kind: "parecer", data: { ...a.parecer, resultados: a.resultados ?? a.parecer.resultados } }];
  return f;
}

export function Bancada({ sid }: { sid: string }) {
  const { api, ir } = useApp();
  const [estado, setEstado] = useState<Estado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [status, setStatus] = useState<Record<string, string>>({});
  const [feed, setFeed] = useState<Record<string, Feed[]>>({});
  const [aprovacao, setAprovacao] = useState<{ etapa: string; opcoes: { id: string; rotulo: string }[] } | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const etapaAtual = useRef("ficha");
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.sessao(sid).then((e) => {
      setEstado(e); setStatus(e.bancada.status); setFeed(feedInicial(e));
      if (e.bancada.aguardando) setAprovacao({ etapa: e.bancada.aguardando, opcoes: e.bancada.aguardando === "amostra" ? [{ id: "seguir", rotulo: "Pode seguir" }] : [{ id: "orientar", rotulo: "Enviar orientação" }] });
    }).catch((x) => setErro(x.message));
  }, [api, sid]);

  const on = useCallback((ev: Evento) => {
    const add = (item: Feed) => setFeed((f) => ({ ...f, [etapaAtual.current]: [...(f[etapaAtual.current] ?? []), item] }));
    switch (ev.type) {
      case "etapa": etapaAtual.current = ev.etapa; setStatus((s) => ({ ...s, [ev.etapa]: ev.status })); break;
      case "mensagem": add({ tipo: "msg", agente: ev.agente, texto: ev.texto }); break;
      case "card":
        if (ev.kind === "rodada") {
          setFeed((f) => {
            const lista = f.qualidade ?? [];
            const rod = lista.find((x) => x.tipo === "card" && x.kind === "rodadas") as Extract<Feed, { tipo: "card" }> | undefined;
            const outros = lista.filter((x) => x !== rod);
            return { ...f, qualidade: [{ tipo: "card", kind: "rodadas", data: [...(rod?.data ?? []), ev.data] }, ...outros] };
          });
        } else if (ev.kind !== "ficha") add({ tipo: "card", kind: ev.kind, data: ev.data });
        break;
      case "aprovacao": setAprovacao({ etapa: ev.etapa, opcoes: ev.opcoes }); break;
      case "aguardando": setAviso(ev.message); break;
      case "error": setAviso(ev.message); break;
      case "done": setEstado(ev.state); break;
    }
    setTimeout(() => fim.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 30);
  }, []);

  const avancar = async (decisao?: string) => {
    setOcupado(true); setAprovacao(null); setAviso(null);
    await api.bancada(sid, { decisao }, on);
    setOcupado(false);
  };

  if (erro) return <div className="estudio-erro"><h2>Experimento não encontrado</h2><p className="muted">{erro}</p><button className="btn primary" onClick={() => ir({ tela: "entrada" })}>Voltar ao início</button></div>;
  if (!estado) return <div className="estudio-carregando"><span className="spinner" /></div>;
  const st = STATUS[estado.status];
  const podeIniciar = !estado.bancada.iniciada && estado.status === "aprovado";

  return (
    <div className="bancada">
      <header className="bancada-cab">
        <button className="btn sm ghost" onClick={() => ir({ tela: "estudio", sid })}><Icon name="back" size={15} />Conversa</button>
        <div>
          <span className="eyebrow">Bancada de agentes · {estado.ficha.id}</span>
          <h1>{estado.ficha.titulo}</h1>
          <p className="hip">{estado.ficha.hipotese}</p>
        </div>
        <Badge tom={st.tom} dot>{st.rotulo}</Badge>
      </header>

      {!estado.bancada.iniciada && (
        <div className={`bancada-inicio card${podeIniciar ? "" : " espera"}`}>
          <Icon name={podeIniciar ? "flask" : "clock"} size={22} />
          <div>
            <b>{podeIniciar ? "Ficha aprovada pelo Lab. Tudo pronto para a bancada." : "Aguardando a revisão do Lab (G0)"}</b>
            <p className="muted">{podeIniciar ? "Os agentes analisam a amostra, constroem, testam no Ralph Loop e emitem o parecer. Você decide nos portões." : "A bancada começa assim que um pesquisador do Lab aprovar a ficha. Dica: troque para o papel Lab no topo para ver o outro lado."}</p>
          </div>
          {podeIniciar && <button className="btn accent" onClick={() => avancar()} disabled={ocupado}>{ocupado ? <span className="spinner" /> : null}Iniciar a bancada<Icon name="arrow" size={15} /></button>}
        </div>
      )}
      {aviso && <div className="aviso"><Icon name="info" size={15} />{aviso}</div>}

      <ol className="etapas">
        {ETAPAS.map((et) => {
          const s = status[et.id] ?? "";
          const itens = feed[et.id] ?? [];
          return (
            <li key={et.id} className={`etapa ${s}`}>
              <div className="etapa-marca"><span className={`ag ag-${et.agente}`}>{s === "ok" ? <Icon name="check" size={14} strokeWidth={2.6} /> : s === "run" ? <span className="spinner" /> : et.gate || "·"}</span></div>
              <div className="etapa-corpo">
                <div className="etapa-cab">
                  <b>{et.nome}</b>{et.gate && <span className="mono gate-tag">{et.gate}</span>}
                  <small className="muted">{et.quem}</small>
                  {s === "wait" && <Badge tom="warn" dot>sua decisão</Badge>}
                  {s === "bloqueada" && <Badge tom="accent" dot>bloqueada</Badge>}
                </div>
                {itens.map((it, i) => it.tipo === "msg"
                  ? <p key={i} className={`fala ag-t-${it.agente}`}>{it.texto}</p>
                  : <div key={i}>{it.kind === "amostra" ? <CardAmostra data={it.data} /> : it.kind === "plano" ? <Plano data={it.data} />
                    : it.kind === "rodadas" ? <Rodadas rodadas={it.data} /> : it.kind === "parecer" ? <Parecer data={it.data} /> : null}</div>)}
                {aprovacao?.etapa === et.id && (
                  <div className="aprovacao">
                    {aprovacao.opcoes.map((o) => <button key={o.id} className="btn primary sm" onClick={() => avancar(o.id)} disabled={ocupado}>{o.rotulo}</button>)}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <div ref={fim} />
    </div>
  );
}
