import type { Abordagem, MetricaTecnica } from "../../api/types";
import { Badge, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { STATUS, VEREDITO } from "../../lib/format";
import type { CardItem } from "./useConversa";

interface Acoes { responder: (t: string) => void; ocupado: boolean; sid: string }

function Sintese({ data, acoes }: { data: { texto: string }; acoes: Acoes }) {
  return (
    <div className="ccard sintese">
      <div className="ccard-cab"><Icon name="map" size={15} /><span>Meu entendimento do problema</span></div>
      <p className="sintese-texto">{data.texto}</p>
      <div className="ccard-acoes">
        <button className="btn sm primary" disabled={acoes.ocupado} onClick={() => acoes.responder("Isso mesmo")}><Icon name="check" size={14} />Isso mesmo</button>
        <button className="btn sm" disabled={acoes.ocupado} onClick={() => acoes.responder("Quase: vou ajustar um ponto")}>Quero corrigir</button>
      </div>
    </div>
  );
}

function Similares({ data }: { data: { id: string; titulo?: string; veredito?: string; origem: string; nota?: string; relevancia?: number }[] }) {
  return (
    <div className="ccard">
      <div className="ccard-cab"><Icon name="search" size={15} /><span>Casos parecidos no histórico do Lab</span></div>
      <ul className="similares">
        {data.map((c) => {
          const v = c.veredito ? VEREDITO[c.veredito] : null;
          return (
            <li key={c.id}>
              <span className="mono sim-id">{c.id}</span>
              <span className="sim-txt"><b>{c.titulo ?? "Experimento"}</b>{c.nota && <small>{c.nota}</small>}</span>
              {v && <Badge tom={v.tom}>{v.rotulo}</Badge>}
            </li>
          );
        })}
      </ul>
      <p className="ccard-nota"><Icon name="info" size={13} />O Cientista usa esses casos para sugerir critérios e amostras, e cita o id quando faz isso.</p>
    </div>
  );
}

function Amostra({ data }: { data: any }) {
  const total = data.total_registros ?? data.registros_validos ?? data.registros ?? 0;
  const minimo = data.minimo ?? data.tamanho_minimo ?? 385;
  const ok = total >= minimo;
  return (
    <div className="ccard">
      <div className="ccard-cab"><Icon name="doc" size={15} /><span>{data.nome ? `Amostra · ${data.nome}` : "Análise da amostra (G1)"}</span>
        <Badge tom={ok ? "ok" : "warn"}>{ok ? "Suficiente" : "Resultado indicativo"}</Badge></div>
      <div className="amostra-nums">
        <div><b>{total.toLocaleString("pt-BR")}</b><small>registros válidos</small></div>
        <div><b>{minimo.toLocaleString("pt-BR")}</b><small>mínimo do método</small></div>
        {data.completude != null && <div><b>{Math.round(data.completude * 100)}%</b><small>completude</small></div>}
      </div>
      <div className={`bar ${ok ? "ok" : "accent"}`}><i style={{ width: `${Math.min(100, (total / minimo) * 100)}%` }} /></div>
      {data.resumo && <p className="ccard-texto">{data.resumo}</p>}
      {(data.achados?.length || data.alertas?.length) ? (
        <ul className="lista-mini">
          {(data.achados ?? []).map((a: string) => <li key={a}><Icon name="check" size={13} />{a}</li>)}
          {(data.alertas ?? []).map((a: string) => <li key={a} className="alerta"><Icon name="info" size={13} />{a}</li>)}
        </ul>
      ) : null}
    </div>
  );
}

function Abordagens({ data, acoes }: { data: { abordagens: Abordagem[]; justificativa_recomendacao?: string }; acoes: Acoes }) {
  return (
    <div className="ccard largo">
      <div className="ccard-cab"><Icon name="layers" size={15} /><span>Abordagens comparadas</span><small className="muted">custos e latências são estimativas</small></div>
      <div className="abordagens">
        {data.abordagens.map((a) => (
          <div key={a.nome} className={`abordagem${a.recomendada ? " rec" : ""}`}>
            {a.recomendada && <span className="rec-tag">Recomendada</span>}
            <b>{a.nome}</b>
            <p>{a.descricao}</p>
            <dl>
              <div><dt>Custo</dt><dd>{a.custo}</dd></div>
              <div><dt>Latência</dt><dd>{a.latencia}</dd></div>
              <div><dt>Complexidade</dt><dd>{a.complexidade === "media" ? "média" : a.complexidade}</dd></div>
            </dl>
            <ul className="pc">
              {a.pros.map((p) => <li key={p} className="pro">+ {p}</li>)}
              {a.contras.map((c) => <li key={c} className="contra">− {c}</li>)}
            </ul>
            <button className="btn sm" disabled={acoes.ocupado} onClick={() => acoes.responder(`Vamos de ${a.nome}`)}>Escolher</button>
          </div>
        ))}
      </div>
      {data.justificativa_recomendacao && <p className="ccard-nota"><Icon name="spark" size={13} />{data.justificativa_recomendacao}</p>}
    </div>
  );
}

function Avaliacao({ data }: { data: { conjunto: string; tamanho?: number; divisao?: string; metricas: MetricaTecnica[]; gate_regressao?: string; baseline?: string } }) {
  return (
    <div className="ccard largo">
      <div className="ccard-cab"><Icon name="flask" size={15} /><span>Protocolo de avaliação</span><Badge tom="info">vira o CI do kit</Badge></div>
      <p className="ccard-texto"><b>Conjunto:</b> {data.conjunto}{data.tamanho ? ` · ${data.tamanho.toLocaleString("pt-BR")} casos` : ""}{data.divisao ? ` · ${data.divisao}` : ""}</p>
      <table className="tabela">
        <thead><tr><th>Métrica técnica</th><th>Hoje</th><th></th><th>Meta</th><th>Sustenta</th></tr></thead>
        <tbody>
          {data.metricas.map((m) => (
            <tr key={m.nome}>
              <td className="mono">{m.nome}</td><td className="mono muted">{m.baseline || "—"}</td>
              <td aria-hidden><Icon name="arrow" size={13} /></td><td className="mono"><b>{m.alvo}</b></td><td className="muted">{m.liga_a || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.gate_regressao && <p className="gate"><Icon name="shield" size={14} />Gate de regressão: <b>{data.gate_regressao}</b></p>}
    </div>
  );
}

function Desenho({ data }: { data: { arquitetura?: string[]; stack?: string; riscos_tecnicos?: string[] } }) {
  return (
    <div className="ccard largo">
      <div className="ccard-cab"><Icon name="layers" size={15} /><span>Arquitetura</span>{data.stack && <small className="muted">{data.stack}</small>}</div>
      <ol className="cadeia">{(data.arquitetura ?? []).map((c, i) => <li key={c}><span className="mono">{i + 1}</span>{c}</li>)}</ol>
      {data.riscos_tecnicos?.length ? <ul className="lista-mini">{data.riscos_tecnicos.map((r) => <li key={r} className="alerta"><Icon name="info" size={13} />{r}</li>)}</ul> : null}
    </div>
  );
}

function Tecnologia({ data }: { data: { tecnica: string; justificativa: string; golden_path_nome?: string } }) {
  return (
    <div className="ccard compacto">
      <div className="ccard-cab"><Icon name="code" size={15} /><span>{data.tecnica}</span>{data.golden_path_nome && <Badge>golden path · {data.golden_path_nome}</Badge>}</div>
      <p className="ccard-texto">{data.justificativa}</p>
    </div>
  );
}

function Skills({ data }: { data: { skills: { nome: string; para_que: string; nivel: number }[]; estimativa_solicitante: string; estimativa_laboratorio: string } }) {
  return (
    <div className="ccard">
      <div className="ccard-cab"><Icon name="spark" size={15} /><span>Skills para executar</span></div>
      <ul className="skills">{data.skills.map((s) => (
        <li key={s.nome}><b>{s.nome}</b><small>{s.para_que}</small><span className="nivel">{"●".repeat(s.nivel)}{"○".repeat(3 - s.nivel)}</span></li>
      ))}</ul>
      <div className="amostra-nums"><div><b>{data.estimativa_solicitante}</b><small>construindo você</small></div><div><b>{data.estimativa_laboratorio}</b><small>na bancada do Lab</small></div></div>
    </div>
  );
}

function FichaGerada({ data }: { data: { ficha: any; versao: number; markdown: string } }) {
  const baixar = () => {
    const url = URL.createObjectURL(new Blob([data.markdown], { type: "text/markdown" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${(data.ficha.titulo ?? "ficha").toLowerCase().replace(/\s+/g, "-")}.md` });
    a.click(); URL.revokeObjectURL(url);
  };
  return (
    <div className="ccard ficha-gerada">
      <div className="ccard-cab"><Icon name="doc" size={15} /><span>Ficha gerada · versão {data.versao}</span><Badge tom="ok" dot>Checklist completo</Badge></div>
      <h4>{data.ficha.titulo}</h4>
      <p className="hipotese">{data.ficha.hipotese}</p>
      <div className="ccard-acoes"><button className="btn sm" onClick={baixar}><Icon name="download" size={14} />Baixar .md</button></div>
    </div>
  );
}

function Handoff({ data, sid }: { data: { destino: string; status: keyof typeof STATUS; kit?: string[] }; sid: string }) {
  const { ir } = useApp();
  const st = STATUS[data.status];
  return (
    <div className="ccard handoff">
      <div className="ccard-cab"><Icon name="shield" size={15} /><span>Encaminhado</span><Badge tom={st.tom} dot>{st.rotulo}</Badge></div>
      <ol className="trilha">
        <li className="ok">Ficha</li>
        <li className={data.status === "em_revisao" ? "agora" : "ok"}>Revisão do Lab (G0)</li>
        <li>{data.destino === "workflow" ? "Bancada" : "Construção com o kit"}</li>
        <li>Parecer</li>
      </ol>
      {data.kit && <p className="ccard-texto"><b>Kit pronto:</b> {data.kit.length} arquivos, incluindo <span className="mono">eval/avaliar.py</span> e o CI.</p>}
      {data.destino === "workflow" && <div className="ccard-acoes"><button className="btn sm" onClick={() => ir({ tela: "bancada", sid })}>Abrir a bancada<Icon name="arrow" size={14} /></button></div>}
    </div>
  );
}

export function Card({ c, acoes }: { c: CardItem; acoes: Acoes }) {
  switch (c.kind) {
    case "sintese": return <Sintese data={c.data} acoes={acoes} />;
    case "similares": return <Similares data={c.data} />;
    case "amostra": return <Amostra data={c.data} />;
    case "abordagens": return <Abordagens data={c.data} acoes={acoes} />;
    case "avaliacao": return <Avaliacao data={c.data} />;
    case "desenho": return <Desenho data={c.data} />;
    case "tecnologia": return <Tecnologia data={c.data} />;
    case "skills": return <Skills data={c.data} />;
    case "ficha_gerada": return <FichaGerada data={c.data} />;
    case "handoff": return <Handoff data={c.data} sid={acoes.sid} />;
    default: return null;
  }
}

export { Amostra as CardAmostra };
