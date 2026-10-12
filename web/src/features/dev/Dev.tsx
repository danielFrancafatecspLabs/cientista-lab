// Portal do desenvolvedor: a caixa de ferramentas (IDP) do beOn Labs.
import { useCallback, useEffect, useState } from "react";
import type { Estado, Pedido, Toolbox } from "../../api/types";
import { Badge, Icon } from "../../components/ui";
import { useApp, type SecaoDev } from "../../lib/app";
import { STATUS } from "../../lib/format";
import { Arquitetura, lerPiloto } from "./Arquitetura";
import { ICONE_RECURSO, useToolbox } from "./comum";
import { Ferramentas } from "./Ferramentas";
import { Modelos } from "./Modelos";
import { Recursos } from "./Recursos";
import "./dev.css";

const NAV: { id: SecaoDev; rotulo: string; icone: "home" | "key" | "cpu" | "layers" | "box" }[] = [
  { id: "inicio", rotulo: "Início", icone: "home" },
  { id: "recursos", rotulo: "Recursos", icone: "key" },
  { id: "modelos", rotulo: "Modelos e benchmarks", icone: "cpu" },
  { id: "arquitetura", rotulo: "Arquitetura e piloto", icone: "layers" },
  { id: "ferramentas", rotulo: "Ferramentas e práticas", icone: "box" },
];

/** Sessão de conversa do desenvolvedor: carrega a existente ou cria uma ao abrir o chat. */
export function useSessaoDev() {
  const { api, papeis, perfil, setPerfil, ir } = useApp();
  const sid = perfil.sessoes.desenvolvedor;
  const [sessao, setSessao] = useState<Estado | null>(null);
  const [abrindo, setAbrindo] = useState(false);
  useEffect(() => {
    if (!sid) { setSessao(null); return; }
    api.sessao(sid).then(setSessao).catch(() => setSessao(null));
  }, [api, sid]);
  const abrirChat = useCallback(async () => {
    if (sessao) return ir({ tela: "estudio", sid: sessao.id });
    setAbrindo(true);
    try {
      const j = papeis?.jornadas.find((x) => x.papel === "desenvolvedor");
      const prefs = Object.fromEntries((j?.preferencias ?? []).map((p) => [p.id, p.padrao]));
      const s = await api.criarSessao({ nome: perfil.nome || undefined, papel: "desenvolvedor", preferencias: prefs });
      setPerfil({ papel: "desenvolvedor", sessoes: { desenvolvedor: s.id } });
      ir({ tela: "estudio", sid: s.id });
    } finally { setAbrindo(false); }
  }, [api, papeis, perfil.nome, sessao, setPerfil, ir]);
  return { sessao, abrirChat, abrindo };
}

function Inicio({ t, sessao, abrirChat, abrindo, pedidos }: {
  t: Toolbox; sessao: Estado | null; abrirChat: () => void; abrindo: boolean; pedidos: Pedido[];
}) {
  const { ir, perfil, api } = useApp();
  const temChave = pedidos.some((p) => p.tipo === "llm_key" && p.status === "aprovado");
  const piloto = lerPiloto(sessao?.id).length;
  const f = sessao?.ficha;
  const pend = sessao?.desenho_pendencias ?? [];
  const passos = [
    { t: "Problema e protocolo", d: "Com o Cientista: baseline, hipótese, abordagens e métricas com meta.", ok: !!sessao?.ficha_gerada || (sessao ? sessao.status !== "conversa" : false), acao: abrirChat, cta: sessao ? "Continuar conversa" : "Começar conversa" },
    { t: "Recursos", d: "Chave de LLM para testar, GitHub para o repositório, servidor quando precisar.", ok: temChave, acao: () => ir({ tela: "dev", secao: "recursos" }), cta: "Pedir recursos" },
    { t: "Construir com o kit", d: "Avaliador e CI que bloqueia regressão, gerados a partir do seu protocolo.", ok: !!sessao && ["aprovado", "em_execucao", "parecer", "decidido"].includes(sessao.status), acao: sessao?.ficha_gerada ? () => ir({ tela: "estudio", sid: sessao.id }) : abrirChat, cta: "Ver kit" },
    { t: "Arquitetura de piloto", d: "LangGraph, n8n, gateway e o checklist que o Lab confere.", ok: piloto >= t.arquitetura.piloto.length, prog: `${piloto}/${t.arquitetura.piloto.length}`, acao: () => ir({ tela: "dev", secao: "arquitetura" }), cta: "Abrir checklist" },
    { t: "Revisão do Lab e parecer", d: "G0 antes de executar; o Sponsor decide se escala.", ok: sessao?.status === "decidido", acao: sessao ? () => ir({ tela: "estudio", sid: sessao.id }) : abrirChat, cta: "Acompanhar" },
  ];
  const agora = passos.findIndex((p) => !p.ok);
  const rec = t.modelos.filter((m) => m.grupo === "recomendado");

  return (
    <div className="secao">
      <header className="inicio-hero">
        <span className="eyebrow">Caixa de ferramentas do desenvolvedor</span>
        <h1>{perfil.nome ? `${perfil.nome.split(" ")[0]}, tudo` : "Tudo"} o que você precisa para levar um experimento <em>até o piloto</em>.</h1>
        <p className="muted">Converse com o Cientista para fechar o desenho técnico, peça chaves e infraestrutura em um clique e siga o que o Lab já testou.</p>
      </header>

      <div className="inicio-topo">
        <section className="exp-card card">
          <span className="eyebrow">Seu experimento</span>
          {sessao ? (
            <>
              <div className="exp-tit"><h2>{f?.titulo || "Experimento em desenho"}</h2><Badge tom={STATUS[sessao.status].tom} dot>{STATUS[sessao.status].rotulo}</Badge></div>
              {f?.hipotese ? <p className="exp-hip">{f.hipotese}</p> : <p className="muted">O Cientista ainda está entendendo o problema com você.</p>}
              <div className="exp-meta">
                {f?.detalhes_tecnicos?.stack && <span><Icon name="code" size={13} />{f.detalhes_tecnicos.stack}</span>}
                {f?.detalhes_tecnicos?.abordagem_escolhida && <span><Icon name="layers" size={13} />{f.detalhes_tecnicos.abordagem_escolhida}</span>}
                {sessao.ficha_gerada && <span><Icon name="doc" size={13} />ficha v{sessao.ficha_versao}</span>}
              </div>
              {pend.length > 0 && sessao.status === "conversa" && <p className="exp-pend"><Icon name="info" size={13} />Falta no desenho técnico: {pend.join(", ")}</p>}
            </>
          ) : (
            <><h2>Comece pelo problema</h2><p className="muted">Em poucos minutos o Cientista fecha com você baseline, abordagens com trade-offs e um protocolo de avaliação que vira o CI do seu repositório.</p></>
          )}
          <button className="btn accent" onClick={abrirChat} disabled={abrindo}>{abrindo ? <span className="spinner" /> : <Icon name="chat" size={15} />}{sessao ? "Continuar com o Cientista" : "Conversar com o Cientista"}</button>
        </section>

        <section className="acoes-rapidas">
          <span className="eyebrow">Pedir em um clique</span>
          {t.recursos.map((r) => {
            const ult = pedidos.find((p) => p.tipo === r.tipo);
            return (
              <button key={r.tipo} className="acao" onClick={() => ir({ tela: "dev", secao: "recursos", arg: r.tipo })}>
                <span className="rc-ic sm"><Icon name={ICONE_RECURSO[r.tipo]} size={16} /></span>
                <span><b>{r.nome}</b><small>{ult ? (ult.status === "aprovado" ? "Você já tem: ver credencial" : ult.status === "pendente" ? "Pedido aguardando o Lab" : r.sla) : r.sla}</small></span>
                {ult?.status === "aprovado" ? <Badge tom="ok">ativo</Badge> : ult?.status === "pendente" ? <Badge tom="warn">pendente</Badge> : <Icon name="arrow" size={15} />}
              </button>
            );
          })}
        </section>
      </div>

      <section className="caminho">
        <h2 className="sub">Caminho até o piloto</h2>
        <ol>
          {passos.map((p, i) => (
            <li key={p.t} className={p.ok ? "ok" : i === agora ? "agora" : ""}>
              <span className="cm-n">{p.ok ? <Icon name="check" size={14} strokeWidth={3} /> : i + 1}</span>
              <div><b>{p.t}{p.prog && <small className="mono"> · {p.prog}</small>}</b><p className="muted">{p.d}</p></div>
              <button className={`btn sm${i === agora ? " primary" : ""}`} onClick={p.acao}>{p.cta}</button>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <div className="sub-linha"><h2 className="sub">Modelos recomendados</h2><button className="btn sm ghost" onClick={() => ir({ tela: "dev", secao: "modelos" })}>Ver hub e benchmarks<Icon name="arrow" size={14} /></button></div>
        <div className="rec-mini">
          {rec.map((m) => (
            <div key={m.id} className="rm card">
              <div><b>{m.nome}</b><Badge tom="accent">{m.destaque}</Badge></div>
              <p className="muted">{m.uso_ideal}</p>
              <code className="mono">{m.alias}</code>
            </div>
          ))}
          <div className="rm card hub">
            <div><b>{t.hub.nome}</b><Badge tom="info">dados na casa</Badge></div>
            <p className="muted">{t.modelos.filter((m) => m.grupo === "hub").map((m) => m.nome).join(" · ")}</p>
            <code className="mono">{api.modo === "demo" ? "llm.lab.interno/v1" : t.hub.base_url ?? "gateway LiteLLM"}</code>
          </div>
        </div>
      </section>
    </div>
  );
}

export function Dev({ secao = "inicio", arg }: { secao?: SecaoDev; arg?: string }) {
  const { api, ir, perfil } = useApp();
  const t = useToolbox();
  const { sessao, abrirChat, abrindo } = useSessaoDev();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  useEffect(() => {
    if (!perfil.nome) return;
    api.pedidos({ solicitante: perfil.nome }).then(setPedidos).catch(() => setPedidos([]));
  }, [api, perfil.nome, secao]);
  const pendentes = pedidos.filter((p) => p.status === "pendente").length;

  return (
    <div className="dev">
      <aside className="dev-nav">
        <div className="dn-cab"><span className="eyebrow">Desenvolvedor</span><b>Caixa de ferramentas</b></div>
        <nav>
          {NAV.map((n) => (
            <button key={n.id} className={secao === n.id ? "on" : ""} onClick={() => ir({ tela: "dev", secao: n.id })} aria-current={secao === n.id ? "page" : undefined}>
              <Icon name={n.icone} size={17} /><span>{n.rotulo}</span>
              {n.id === "recursos" && pendentes > 0 && <span className="dn-count">{pendentes}</span>}
            </button>
          ))}
        </nav>
        <button className="dn-chat" onClick={abrirChat} disabled={abrindo}>
          <span className="autor"><Icon name="flask" size={15} /></span>
          <span><b>Cientista</b><small>{sessao ? (sessao.ficha.titulo || "Continuar a conversa") : "Desenhar o experimento"}</small></span>
          <Icon name="arrow" size={15} />
        </button>
      </aside>
      <main className="dev-corpo scroll">
        {!t ? <div className="estudio-carregando"><span className="spinner" /></div> : (
          <>
            {secao === "inicio" && <Inicio t={t} sessao={sessao} abrirChat={abrirChat} abrindo={abrindo} pedidos={pedidos} />}
            {secao === "recursos" && <Recursos t={t} sessao={sessao} arg={arg} />}
            {secao === "modelos" && <Modelos t={t} />}
            {secao === "arquitetura" && <Arquitetura t={t} sid={sessao?.id} />}
            {secao === "ferramentas" && <Ferramentas t={t} />}
          </>
        )}
      </main>
    </div>
  );
}
