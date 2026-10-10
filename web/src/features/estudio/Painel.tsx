import { useEffect, useMemo, useState } from "react";
import type { Estado, Kit } from "../../api/types";
import { Badge, Empty, Icon, Meter, Ring, Tabs } from "../../components/ui";
import { useApp } from "../../lib/app";
import "./painel.css";

type Aba = "mapa" | "ficha" | "desenho" | "kit";

function Mapa({ estado }: { estado: Estado }) {
  const m = estado.mapa;
  const atual = m.pergunta_atual?.dimensao;
  const lacunas = m.dimensoes.filter((d) => d.profundidade < d.minimo);
  return (
    <div className="mapa">
      <div className="mapa-cab">
        <Ring valor={m.cobertura} size={54} stroke={5}>{Math.round(m.cobertura * 100)}</Ring>
        <div>
          <b>{m.pronto ? "Problema claro: pronto para a hipótese" : m.cobertura === 0 ? "O Cientista ainda está ouvindo" : "Entendendo o problema"}</b>
          <small>{m.pronto ? "As dimensões essenciais estão claras e com evidência." : lacunas.length ? `Falta aprofundar: ${lacunas.slice(0, 3).map((d) => d.nome.toLowerCase()).join(", ")}` : "Quase lá."}</small>
        </div>
      </div>
      {m.sintese && (
        <div className={`mapa-sintese${m.sintese_confirmada ? " ok" : ""}`}>
          <span className="eyebrow">{m.sintese_confirmada ? "Entendimento confirmado" : "Entendimento para confirmar"}</span>
          <p>{m.sintese}</p>
        </div>
      )}
      <ul className="dims">
        {m.dimensoes.map((d) => (
          <li key={d.id} className={`${d.id === atual ? "atual" : ""}${d.profundidade === 0 ? " vazia" : ""}`}>
            <div className="dim-cab">
              <b>{d.nome}</b>
              {d.id === atual && <Badge tom="accent">perguntando agora</Badge>}
              {d.profundidade < d.minimo && d.id !== atual && d.profundidade > 0 && <Badge tom="warn">raso</Badge>}
              <Meter valor={d.profundidade} accent={d.id === atual} rotulo={`Profundidade de ${d.nome}`} />
            </div>
            {d.entendimento ? <p>{d.entendimento}</p> : <p className="busca">{d.busca}</p>}
            {d.evidencia && <q>{d.evidencia}</q>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Campo({ rotulo, valor, mudou }: { rotulo: string; valor?: string | null; mudou?: boolean }) {
  return (
    <div className={`campo${mudou ? " mudou" : ""}${valor ? "" : " vazio"}`}>
      <span className="eyebrow">{rotulo}</span>
      <p>{valor || "—"}</p>
    </div>
  );
}

function Ficha({ estado, mudou }: { estado: Estado; mudou: string[] }) {
  const f = estado.ficha;
  const ausentes = estado.pendencias.filter((p) => p.endsWith("ausente")).length;
  const feitos = 10 - ausentes;
  const regras = estado.pendencias.filter((p) => !p.endsWith("ausente"));
  const m = (k: string) => mudou.includes(k);
  return (
    <div className="ficha">
      <div className="ficha-check">
        <div className="fc-topo">
          <b>{estado.ficha_gerada ? "Ficha gerada" : `${feitos} de 10 itens do checklist`}</b>
          {estado.ficha_gerada ? <Badge tom="ok" dot>versão {estado.ficha_versao}</Badge> : <span className="mono muted">{f.id}</span>}
        </div>
        <div className="bar ok"><i style={{ width: `${feitos * 10}%` }} /></div>
        {regras.length > 0 && <ul className="regras">{regras.map((r) => <li key={r}><Icon name="info" size={13} />{r}</li>)}</ul>}
      </div>
      <h3 className={`ficha-titulo${m("titulo") ? " mudou" : ""}`}>{f.titulo || <span className="muted">Nome do experimento (até 3 palavras)</span>}</h3>
      <div className="ficha-hip">
        <span className="eyebrow">Hipótese</span>
        <p className={m("hipotese") ? "mudou" : ""}>{f.hipotese || <span className="muted">Acreditamos que [ação] irá gerar [resultado mensurável] para [contexto].</span>}</p>
      </div>
      <Campo rotulo="Problema" valor={f.problema} mudou={m("problema")} />
      <Campo rotulo="Impacto" valor={f.publico_afetado} mudou={m("publico_afetado")} />
      <Campo rotulo="Objetivo" valor={f.objetivo} mudou={m("objetivo")} />
      <Campo rotulo="Metodologia" valor={f.metodologia} mudou={m("metodologia")} />
      <div className={`campo${m("metricas") ? " mudou" : ""}`}>
        <span className="eyebrow">Métricas e critérios de aceite</span>
        {f.metricas?.length ? (
          <ul className="metricas">{f.metricas.map((x) => (
            <li key={x.nome}><span>{x.descricao}</span><b className="mono">{x.criterio_aceite}</b>{x.obrigatoria && <Badge>obrigatória</Badge>}</li>
          ))}</ul>
        ) : <p className="muted">—</p>}
      </div>
      <Campo rotulo="Dados e amostra" valor={[f.dados, f.amostra].filter(Boolean).join(" · ")} mudou={m("amostra") || m("dados")} />
      <div className="duas">
        <Campo rotulo="BO" valor={f.bo} mudou={m("bo")} />
        <Campo rotulo="Sponsor" valor={f.sponsor} mudou={m("sponsor")} />
      </div>
      {f.tecnica && estado.papel === "desenvolvedor" && <Campo rotulo="Técnica" valor={`${f.tecnica}${f.golden_path ? ` · ${f.golden_path}` : ""}`} />}
    </div>
  );
}

function Desenho({ estado }: { estado: Estado }) {
  const d = estado.ficha.detalhes_tecnicos;
  const pend = estado.desenho_pendencias ?? [];
  if (!d) return <Empty icone="layers" titulo="O desenho técnico aparece aqui">Stack, baseline, abordagens e protocolo de avaliação, conforme a conversa avança.</Empty>;
  return (
    <div className="desenho">
      <div className="ficha-check">
        <div className="fc-topo"><b>{pend.length ? `Faltam ${pend.length} itens para o kit` : "Desenho completo: kit pronto"}</b>{!pend.length && <Badge tom="ok" dot>pronto</Badge>}</div>
        {pend.length > 0 && <p className="muted" style={{ fontSize: 13 }}>{pend.join(" · ")}</p>}
      </div>
      <div className="duas"><Campo rotulo="Stack" valor={d.stack} /><Campo rotulo="Fontes de dados" valor={d.fontes_dados} /></div>
      <Campo rotulo="Baseline" valor={d.baseline} />
      <Campo rotulo="Abordagem escolhida" valor={d.abordagem_escolhida} />
      {d.restricoes?.length ? <div className="campo"><span className="eyebrow">Restrições</span><ul className="tags">{d.restricoes.map((r) => <li key={r}>{r}</li>)}</ul></div> : null}
      {d.avaliacao && (
        <div className="campo">
          <span className="eyebrow">Protocolo de avaliação</span>
          <p>{d.avaliacao.conjunto}{d.avaliacao.tamanho ? ` · ${d.avaliacao.tamanho} casos` : ""}</p>
          <ul className="metricas">{d.avaliacao.metricas.map((x) => (
            <li key={x.nome}><span className="mono">{x.nome}</span><b className="mono">{x.baseline ? `${x.baseline} → ` : ""}{x.alvo}</b></li>
          ))}</ul>
          {d.avaliacao.gate_regressao && <p className="gate-mini"><Icon name="shield" size={13} />{d.avaliacao.gate_regressao}</p>}
        </div>
      )}
      {d.arquitetura?.length ? <div className="campo"><span className="eyebrow">Arquitetura</span><ol className="arq">{d.arquitetura.map((c) => <li key={c}>{c}</li>)}</ol></div> : null}
    </div>
  );
}

function KitAba({ estado }: { estado: Estado }) {
  const { api } = useApp();
  const [kit, setKit] = useState<Kit | null>(null);
  const [sel, setSel] = useState("README.md");
  const versao = `${estado.ficha_versao}-${JSON.stringify(estado.ficha.detalhes_tecnicos ?? {}).length}`;
  useEffect(() => { api.kit(estado.id).then(setKit).catch(() => setKit(null)); }, [api, estado.id, versao]);
  const arquivos = useMemo(() => Object.keys(kit?.arquivos ?? {}).sort((a, b) => a.split("/").length - b.split("/").length || a.localeCompare(b)), [kit]);
  if (!estado.ficha.detalhes_tecnicos?.avaliacao) return <Empty icone="kit" titulo="O kit nasce do protocolo de avaliação">Quando o protocolo estiver definido, você vê aqui o repositório inicial com avaliador, metas e CI.</Empty>;
  if (!kit) return <div className="estudio-carregando"><span className="spinner" /></div>;
  const url = api.kitUrl(estado.id);
  return (
    <div className="kit">
      <div className="kit-cab">
        <div><b className="mono">{kit.pasta}/</b><small>{arquivos.length} arquivos · CI bloqueia metas não atendidas e regressões</small></div>
        {url ? <a className="btn sm primary" href={url} download><Icon name="download" size={14} />Baixar .zip</a>
          : <span className="badge outline" title="Disponível com o backend">.zip com a API</span>}
      </div>
      <div className="kit-corpo">
        <ul className="arvore">{arquivos.map((a) => (
          <li key={a}><button className={a === sel ? "on" : ""} onClick={() => setSel(a)}><Icon name={a.endsWith(".py") || a.endsWith(".yml") ? "code" : "doc"} size={14} /><span className="mono">{a}</span></button></li>
        ))}</ul>
        <pre className="preview scroll"><code>{kit.arquivos[sel] ?? ""}</code></pre>
      </div>
    </div>
  );
}

export function Painel({ estado, mudou, aberto, onFechar }: { estado: Estado; mudou: string[]; aberto: boolean; onFechar: () => void }) {
  const dev = estado.papel === "desenvolvedor";
  const [aba, setAba] = useState<Aba>("mapa");
  useEffect(() => { if (estado.ficha_gerada && aba === "mapa") setAba("ficha"); }, [estado.ficha_gerada]); // eslint-disable-line
  const itens: { id: Aba; rotulo: string; icone: "map" | "doc" | "layers" | "kit" }[] = [
    { id: "mapa", rotulo: "Entendimento", icone: "map" },
    { id: "ficha", rotulo: "Ficha", icone: "doc" },
    ...(dev ? [{ id: "desenho" as Aba, rotulo: "Desenho", icone: "layers" as const }, { id: "kit" as Aba, rotulo: "Kit", icone: "kit" as const }] : []),
  ];
  return (
    <aside className={`painel${aberto ? " aberto" : ""}`} aria-label="Painel do experimento">
      <div className="painel-topo">
        <Tabs valor={aba} onChange={setAba} itens={itens} />
        <button className="btn icon ghost painel-fechar" onClick={onFechar} aria-label="Fechar painel"><Icon name="x" /></button>
      </div>
      <div className="painel-corpo scroll">
        {aba === "mapa" && <Mapa estado={estado} />}
        {aba === "ficha" && <Ficha estado={estado} mudou={mudou} />}
        {aba === "desenho" && <Desenho estado={estado} />}
        {aba === "kit" && <KitAba estado={estado} />}
      </div>
    </aside>
  );
}
