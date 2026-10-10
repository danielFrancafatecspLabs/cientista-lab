import { useCallback, useEffect, useState } from "react";
import type { Detalhe, Portfolio, Resumo, Status } from "../../api/types";
import { Badge, Empty, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { DOMINIO, horas, pct, STATUS, VEREDITO } from "../../lib/format";
import { Parecer } from "../bancada/Bancada";
import { FichaDoc } from "../lab/Lab";
import "../estudio/cards.css";
import "../bancada/bancada.css";
import "./sponsor.css";

const COLUNAS: { status: Status[]; nome: string }[] = [
  { status: ["em_revisao", "devolvido"], nome: "Revisão do Lab" },
  { status: ["aprovado"], nome: "Aprovados" },
  { status: ["em_execucao"], nome: "Na bancada" },
  { status: ["parecer"], nome: "Parecer pronto" },
  { status: ["decidido", "encerrado"], nome: "Decididos" },
];

function Kpi({ rotulo, valor, nota, destaque }: { rotulo: string; valor: string; nota?: string; destaque?: boolean }) {
  return <div className={`kpi${destaque ? " destaque" : ""}`}><span className="eyebrow">{rotulo}</span><b>{valor}</b>{nota && <small>{nota}</small>}</div>;
}

function Decisao({ r, onDecidido }: { r: Resumo; onDecidido: () => void }) {
  const { api, ir } = useApp();
  const [d, setD] = useState<Detalhe | null>(null);
  const [escolha, setEscolha] = useState<"escalar" | "iterar" | "encerrar" | null>(null);
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { api.experimento(r.id).then(setD); }, [api, r.id]);
  const parecer = d?.bancada.artefatos.parecer;
  const v = VEREDITO[r.veredito ?? ""];
  const enviar = async () => {
    if (!escolha) return;
    setEnviando(true);
    await api.decisao(r.id, { decisao: escolha, comentario });
    setEnviando(false); onDecidido();
  };
  return (
    <div className="decisao card">
      <div className="dec-cab">{v && <Badge tom={v.tom} dot>{v.rotulo}</Badge>}<span className="mono muted">{r.titulo}</span>
        <button className="btn sm ghost" onClick={() => ir({ tela: "sponsor", id: r.id })}>Detalhes<Icon name="arrow" size={14} /></button></div>
      <h3>{parecer?.titulo ?? r.titulo}</h3>
      <small className="muted">{DOMINIO[r.dominio ?? ""] ?? ""} · BO: {r.bo ?? "—"} · Sponsor: {r.sponsor ?? "—"}</small>
      <p className="muted">{parecer?.resumo ?? r.hipotese}</p>
      {parecer?.proximos_passos?.length ? <p className="dec-passos"><b>Próximos passos sugeridos:</b> {parecer.proximos_passos.join(" · ")}</p> : null}
      <div className="seg">
        {(["escalar", "iterar", "encerrar"] as const).map((x) => (
          <button key={x} aria-pressed={escolha === x} onClick={() => setEscolha(x)}>{x === "escalar" ? "Escalar para piloto" : x === "iterar" ? "Iterar outro ciclo" : "Encerrar com aprendizado"}</button>
        ))}
      </div>
      {escolha && (
        <div className="dec-form">
          <textarea className="textarea" rows={2} value={comentario} onChange={(e) => setComentario(e.target.value)} placeholder="Contexto da decisão (opcional)" />
          <button className="btn accent" onClick={enviar} disabled={enviando}>{enviando ? <span className="spinner" /> : <Icon name="check" size={15} />}Registrar decisão</button>
        </div>
      )}
    </div>
  );
}

function Gaveta({ id, onFechar }: { id: string; onFechar: () => void }) {
  const { api } = useApp();
  const [d, setD] = useState<Detalhe | null>(null);
  useEffect(() => { setD(null); api.experimento(id).then(setD); }, [api, id]);
  return (
    <div className="gaveta-fundo" onClick={onFechar}>
      <aside className="gaveta" onClick={(e) => e.stopPropagation()} aria-label="Detalhes do experimento">
        <div className="gaveta-cab"><span className="eyebrow">{d?.ficha.id}</span><button className="btn icon ghost" onClick={onFechar} aria-label="Fechar"><Icon name="x" /></button></div>
        {!d ? <div className="estudio-carregando"><span className="spinner" /></div> : (
          <div className="gaveta-corpo scroll">
            <h2>{d.ficha.titulo}</h2>
            <div className="gaveta-meta"><Badge tom={STATUS[d.status].tom} dot>{STATUS[d.status].rotulo}</Badge><span className="muted">{d.nome} · {d.revisoes.length} revisão(ões) do Lab</span></div>
            {d.bancada.artefatos.parecer && <Parecer data={d.bancada.artefatos.parecer} />}
            {d.decisao && <p className="dec-feita"><Icon name="check" size={14} />Decisão: <b>{d.decisao.decisao}</b>{d.decisao.comentario ? ` · ${d.decisao.comentario}` : ""}</p>}
            <FichaDoc d={d} />
          </div>
        )}
      </aside>
    </div>
  );
}

export function Sponsor({ id }: { id?: string }) {
  const { api, ir } = useApp();
  const [port, setPort] = useState<Portfolio | null>(null);
  const [lista, setLista] = useState<Resumo[] | null>(null);
  const carregar = useCallback(() => { api.portfolio().then(setPort); api.experimentos().then(setLista); }, [api]);
  useEffect(() => { carregar(); }, [carregar]);
  const k = port?.kpis;
  const pendentes = (lista ?? []).filter((r) => r.status === "parecer");

  return (
    <div className="sponsor">
      <header className="sp-cab">
        <span className="eyebrow">Sponsor · portfólio do beOn Labs</span>
        <h1>O que está em jogo agora</h1>
      </header>

      <section className="kpis">
        <Kpi rotulo="Experimentos" valor={String(k?.experimentos ?? "—")} nota={port ? `${port.historico.total} no histórico do Lab` : undefined} />
        <Kpi rotulo="Lead time da ficha" valor={horas(k?.lead_time_mediano_horas)} nota="mediana, conversa até a ficha (H1)" />
        <Kpi rotulo="Aprovadas na 1ª revisão" valor={pct(k?.aprovacao_primeira_revisao)} nota="convergência com o padrão do Lab (H2)" />
        <Kpi rotulo="Entendimento do problema" valor={pct(k?.cobertura_media_mapa)} nota="cobertura média do mapa" />
        <Kpi rotulo="Em revisão no Lab" valor={String(k?.em_revisao ?? "—")} />
        <Kpi rotulo="Decisões suas" valor={String(k?.decisoes_pendentes ?? "—")} destaque={!!k?.decisoes_pendentes} />
      </section>

      <section className="sp-secao">
        <div className="sp-sec-cab"><h2>Decisões que dependem de você</h2><span className="muted">Pareceres prontos esperando escalar, iterar ou encerrar.</span></div>
        {lista && pendentes.length === 0 && <div className="card"><Empty icone="check" titulo="Nenhuma decisão pendente">Quando um parecer ficar pronto, ele aparece aqui.</Empty></div>}
        <div className="decisoes">{pendentes.map((r) => <Decisao key={r.id} r={r} onDecidido={carregar} />)}</div>
      </section>

      <section className="sp-secao">
        <div className="sp-sec-cab"><h2>Portfólio por etapa</h2></div>
        <div className="quadro">
          {COLUNAS.map((c) => {
            const itens = (lista ?? []).filter((r) => c.status.includes(r.status));
            return (
              <div key={c.nome} className="coluna">
                <div className="col-cab"><b>{c.nome}</b><span className="mono">{itens.length}</span></div>
                {itens.map((r) => (
                  <button key={r.id} className="exp" onClick={() => ir({ tela: "sponsor", id: r.id })}>
                    <b>{r.titulo}</b>
                    <small>{DOMINIO[r.dominio ?? ""] ?? "—"} · {r.nome}</small>
                    <span className="exp-pe">
                      {r.veredito && <Badge tom={VEREDITO[r.veredito]?.tom}>{VEREDITO[r.veredito]?.rotulo}</Badge>}
                      {r.decisao && <Badge>{r.decisao}</Badge>}
                      {r.status === "devolvido" && <Badge tom="accent">ajustes</Badge>}
                    </span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      </section>

      <section className="sp-secao">
        <div className="sp-sec-cab"><h2>O metaexperimento</h2><span className="muted">O METAEXP também é um experimento. Estas são as hipóteses que decidem se ele escala.</span></div>
        <div className="hipoteses">
          <div><span className="mono">H1</span><b>Lead time da ficha cai 50–70%</b><small>Hoje: {horas(k?.lead_time_mediano_horas)} na mediana. Comparar com o histórico manual no piloto.</small></div>
          <div><span className="mono">H2</span><b>Fichas convergem ao padrão do Lab (&gt; 80%)</b><small>Aprovação na 1ª revisão: {pct(k?.aprovacao_primeira_revisao)}. A revisão cega decide.</small></div>
          <div><span className="mono">H3</span><b>Ralph Loop elimina entregas vazias</b><small>Medido a cada rodada do QA na bancada.</small></div>
          <div><span className="mono">H4</span><b>G0 reduz interrupções tardias (≥ 40%)</b><small>Medido nos experimentos do piloto.</small></div>
        </div>
      </section>
      {id && <Gaveta id={id} onFechar={() => ir({ tela: "sponsor" })} />}
    </div>
  );
}
