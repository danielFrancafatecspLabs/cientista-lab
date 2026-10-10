import { useEffect, useMemo, useRef, useState } from "react";
import type { Estado, Porque } from "../../api/types";
import { Badge, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { STATUS } from "../../lib/format";
import { Markdown } from "../../lib/markdown";
import { Card } from "./cards";
import { Painel } from "./Painel";
import { useConversa, type Item } from "./useConversa";
import "./estudio.css";
import "./cards.css";

// --------------------------------------------------------------- jornada ----

function etapasFeitas(e: Estado): boolean[] {
  const f = e.ficha, d = f.detalhes_tecnicos, m = e.mapa;
  const prof = (id: string) => m.dimensoes.find((x) => x.id === id)?.profundidade ?? 0;
  const depois = ["aprovado", "em_execucao", "parecer", "decidido"].includes(e.status);
  const encaminhada = e.status !== "conversa";
  if (e.papel === "desenvolvedor") {
    return [prof("sintoma") >= 1, !!d?.stack, !!d?.baseline, !!f.hipotese, !!d?.abordagens?.length || !!d?.abordagem_escolhida,
      !!d?.avaliacao?.metricas?.length, !!f.amostra, e.ficha_gerada || encaminhada, encaminhada];
  }
  return [prof("sintoma") >= 1, m.pronto || m.sintese_confirmada, !!f.hipotese, !!f.metricas?.length, !!f.amostra, !!(f.bo && f.sponsor),
    e.ficha_gerada || encaminhada, depois, ["em_execucao", "parecer", "decidido"].includes(e.status)];
}

function Jornada({ estado }: { estado: Estado }) {
  const { papeis } = useApp();
  const etapas = papeis?.jornadas.find((j) => j.papel === estado.papel)?.etapas ?? [];
  const feitas = etapasFeitas(estado);
  const agora = feitas.findIndex((x) => !x);
  return (
    <ol className="jornada" aria-label="Etapas da jornada">
      {etapas.map((t, i) => (
        <li key={t} className={feitas[i] ? "ok" : i === agora ? "agora" : ""}>
          <span className="j-dot">{feitas[i] ? <Icon name="check" size={11} strokeWidth={3} /> : null}</span>
          <span className="j-txt">{t}</span>
        </li>
      ))}
    </ol>
  );
}

// -------------------------------------------------------------- mensagem ----

function PorQue({ p }: { p: Porque }) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className={`porque${aberto ? " aberto" : ""}`}>
      <button onClick={() => setAberto((x) => !x)} aria-expanded={aberto}>
        <Icon name="info" size={13} />Por que pergunto isso
        <span className="porque-tags"><span>{p.dimensao_nome ?? p.dimensao}</span>
          {(p.tecnica_nome ?? p.tecnica) !== (p.dimensao_nome ?? p.dimensao) && <span>{p.tecnica_nome ?? p.tecnica}</span>}</span>
      </button>
      {aberto && <p>{p.por_que}</p>}
    </div>
  );
}

function Mensagem({ it, acoes }: { it: Item; acoes: { responder: (t: string) => void; ocupado: boolean; sid: string } }) {
  if (it.de === "pessoa") return <div className="msg pessoa"><div className="bolha">{it.texto}</div></div>;
  if (it.de === "sistema") return <div className={`msg sistema${it.erro ? " erro" : ""}`}><Icon name="info" size={14} />{it.texto}</div>;
  const digitando = it.aberto && !it.texto && !it.cards.length;
  return (
    <div className="msg cientista">
      <span className="autor" aria-hidden><Icon name="flask" size={15} /></span>
      <div className="msg-corpo">
        {digitando ? <span className="digitando" aria-label="O Cientista está pensando"><i /><i /><i /></span> : null}
        {it.texto && <div className="prosa"><Markdown texto={it.texto} />{it.aberto && <span className="cursor" />}</div>}
        {it.porque && !it.aberto && <PorQue p={it.porque} />}
        {it.cards.map((c, i) => <Card key={i} c={c} acoes={acoes} />)}
      </div>
    </div>
  );
}

// ------------------------------------------------------------- composer ----

function Composer({ chips, upload, ocupado, onEnviar, onAnexar }: {
  chips: string[]; upload: { descricao: string; formatos: string[] } | null; ocupado: boolean;
  onEnviar: (t: string) => void; onAnexar: (f: File) => void;
}) {
  const [texto, setTexto] = useState("");
  const ta = useRef<HTMLTextAreaElement>(null);
  const arq = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const el = ta.current;
    if (el) { el.style.height = "auto"; el.style.height = `${Math.min(220, el.scrollHeight)}px`; }
  }, [texto]);
  useEffect(() => { if (!ocupado) ta.current?.focus({ preventScroll: true }); }, [ocupado]);
  const enviar = (t = texto) => {
    const v = t.trim();
    if (!v || ocupado) return;
    onEnviar(v); setTexto("");
  };
  return (
    <div className="composer-wrap">
      {chips.length > 0 && !ocupado && (
        <div className="chips" aria-label="Respostas sugeridas">
          {chips.map((c) => <button key={c} className="chip" onClick={() => enviar(c)}>{c}</button>)}
        </div>
      )}
      {upload && !ocupado && (
        <button className="upload-pedido" onClick={() => arq.current?.click()}>
          <Icon name="clip" size={16} /><span><b>Anexar {upload.descricao}</b><small>{upload.formatos.join(", ")} · até 15 MB · os dados ficam no ambiente do Lab</small></span>
          <Icon name="arrow" size={15} />
        </button>
      )}
      <div className={`composer${ocupado ? " ocupado" : ""}`}>
        <button className="btn icon ghost" onClick={() => arq.current?.click()} disabled={ocupado} aria-label="Anexar arquivo"><Icon name="clip" /></button>
        <textarea ref={ta} rows={1} value={texto} disabled={ocupado} onChange={(e) => setTexto(e.target.value)}
          placeholder={ocupado ? "O Cientista está respondendo…" : "Responda ou cole um documento: o Cientista extrai tudo de uma vez"}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }} aria-label="Mensagem" />
        <button className="btn icon accent" onClick={() => enviar()} disabled={ocupado || !texto.trim()} aria-label="Enviar"><Icon name="send" /></button>
        <input ref={arq} type="file" hidden accept=".csv,.xlsx,.xls,.json,.jsonl,.txt" onChange={(e) => { const f = e.target.files?.[0]; if (f) onAnexar(f); e.target.value = ""; }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------- encerramento ----

function Encerramento({ estado, onRetomar }: { estado: Estado; onRetomar: () => void }) {
  const { ir } = useApp();
  const st = STATUS[estado.status];
  if (estado.status === "devolvido" && estado.feedback_lab) {
    return (
      <div className="encerramento devolvido">
        <div><Badge tom="accent" dot>{st.rotulo}</Badge><p><b>O Lab pediu ajustes:</b> “{estado.feedback_lab.comentario}”</p><small>Revisado por {estado.feedback_lab.revisor}</small></div>
        <button className="btn accent" onClick={onRetomar}>Ajustar com o Cientista<Icon name="arrow" size={15} /></button>
      </div>
    );
  }
  const textos: Record<string, string> = {
    em_revisao: "Sua ficha está com o Lab para a revisão G0. Você recebe o resultado aqui.",
    aprovado: estado.encaminhamento === "workflow" ? "Ficha aprovada pelo Lab. A bancada já pode começar." : "Ficha aprovada pelo Lab. O kit está pronto para você construir.",
    em_execucao: "A bancada está executando o experimento.",
    parecer: "O parecer está pronto. O Sponsor decide os próximos passos.",
    decidido: "Experimento decidido pelo Sponsor.",
    encerrado: "Experimento encerrado. O aprendizado ficou registrado no histórico do Lab.",
  };
  return (
    <div className="encerramento">
      <div><Badge tom={st.tom} dot>{st.rotulo}</Badge><p>{textos[estado.status]}</p></div>
      {estado.encaminhamento === "workflow" && <button className="btn primary" onClick={() => ir({ tela: "bancada", sid: estado.id })}>Abrir a bancada<Icon name="arrow" size={15} /></button>}
    </div>
  );
}

// ---------------------------------------------------------------- tela ----

export function Estudio({ sid }: { sid: string }) {
  const c = useConversa(sid);
  const { ir } = useApp();
  const lista = useRef<HTMLDivElement>(null);
  const [painelMobile, setPainelMobile] = useState(false);
  const acoes = useMemo(() => ({ responder: (t: string) => c.enviar(t), ocupado: c.ocupado, sid }), [c.enviar, c.ocupado, sid]);

  // Rola só a lista de mensagens (nunca a janela), e só se a pessoa já estava perto do fim.
  const grudado = useRef(true);
  useEffect(() => {
    const el = lista.current;
    if (el && grudado.current) el.scrollTop = el.scrollHeight;
  }, [c.itens, c.chips, c.ocupado]);

  if (c.erroCarga) {
    return (
      <div className="estudio-erro">
        <h2>Não encontramos esta conversa</h2>
        <p className="muted">{c.erroCarga}. No modo demonstração, conversas não sobrevivem a um recarregamento da página.</p>
        <button className="btn primary" onClick={() => ir({ tela: "entrada" })}>Começar de novo</button>
      </div>
    );
  }
  if (!c.estado) return <div className="estudio-carregando"><span className="spinner" /></div>;
  const e = c.estado;
  const conversa = e.status === "conversa";
  const ultimoPessoa = c.itens[c.itens.length - 1]?.de === "pessoa";

  return (
    <div className="estudio">
      <section className="conversa">
        <div className="conversa-topo">
          <div className="titulo-exp">
            <span className="eyebrow">{e.papel === "desenvolvedor" ? "Desenvolvedor" : "Solicitante"} · {e.ficha.id}</span>
            <h1>{e.ficha.titulo || "Novo experimento"}</h1>
          </div>
          <button className="btn sm painel-toggle" onClick={() => setPainelMobile(true)}><Icon name="map" size={15} />Mapa e ficha</button>
        </div>
        <Jornada estado={e} />
        <div className="mensagens scroll" ref={lista} aria-live="polite"
          onScroll={(ev) => { const el = ev.currentTarget; grudado.current = el.scrollHeight - el.scrollTop - el.clientHeight < 160; }}>
          {c.itens.map((it) => <Mensagem key={it.id} it={it} acoes={acoes} />)}
          {c.ocupado && ultimoPessoa && (
            <div className="msg cientista"><span className="autor" aria-hidden><Icon name="flask" size={15} /></span>
              <div className="msg-corpo"><span className="digitando"><i /><i /><i /></span>{c.lendoDocumento && <small className="muted">Lendo seu documento e extraindo tudo de uma vez…</small>}</div></div>
          )}
        </div>
        {conversa
          ? <Composer chips={c.chips} upload={c.upload} ocupado={c.ocupado} onEnviar={c.enviar} onAnexar={c.anexar} />
          : <Encerramento estado={e} onRetomar={c.retomar} />}
      </section>
      <Painel estado={e} mudou={c.mudou} aberto={painelMobile} onFechar={() => setPainelMobile(false)} />
    </div>
  );
}
