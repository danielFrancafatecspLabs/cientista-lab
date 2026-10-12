import { useCallback, useEffect, useMemo, useState } from "react";
import type { Estado, Pedido, SpecRecurso, TipoRecurso, Toolbox } from "../../api/types";
import { Badge, Empty, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import { haQuanto } from "../../lib/format";
import { CredencialView, ICONE_RECURSO, rotuloDetalhe, STATUS_PEDIDO } from "./comum";

function Formulario({ spec, sessao, preset, onFeito, onCancelar }: {
  spec: SpecRecurso; sessao: Estado | null; preset?: string; onFeito: (p: Pedido) => void; onCancelar: () => void;
}) {
  const { api, perfil, setPerfil } = useApp();
  const [nome, setNome] = useState(perfil.nome);
  const [detalhes, setDetalhes] = useState<Record<string, any>>(() => Object.fromEntries(spec.campos.map((c) => [c.id,
    c.tipo === "multi" ? (preset && c.opcoes?.some((o) => o[0] === preset) ? [preset] : [c.padrao]) : c.padrao])));
  const [justificativa, setJustificativa] = useState("");
  const [vincular, setVincular] = useState(!!sessao);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const set = (id: string, v: any) => setDetalhes((d) => ({ ...d, [id]: v }));
  const alternar = (id: string, v: string) => setDetalhes((d) => {
    const atual: string[] = d[id] ?? [];
    const novo = atual.includes(v) ? atual.filter((x) => x !== v) : [...atual, v];
    return { ...d, [id]: novo.length ? novo : atual };
  });

  const enviar = async () => {
    setEnviando(true); setErro(null);
    try {
      if (nome.trim() !== perfil.nome) setPerfil({ nome: nome.trim() });
      const p = await api.pedir({ tipo: spec.tipo, solicitante: nome.trim(), justificativa: justificativa.trim(), detalhes,
        sessao_id: vincular && sessao ? sessao.id : undefined });
      onFeito(p);
    } catch (e) { setErro((e as Error).message); setEnviando(false); }
  };

  return (
    <section className="pedido-form card" aria-label={`Pedir ${spec.nome}`}>
      <header>
        <span className="rc-ic"><Icon name={ICONE_RECURSO[spec.tipo]} size={20} /></span>
        <div><h3>{spec.nome}</h3><small className="muted">{spec.sla} · aprovado por uma pessoa do Lab</small></div>
        <button className="btn icon ghost" onClick={onCancelar} aria-label="Fechar"><Icon name="x" /></button>
      </header>
      {!perfil.nome && (
        <label className="field"><span>Seu nome</span><input className="input" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={60} placeholder="Como o Lab te identifica" /></label>
      )}
      {spec.campos.map((c) => (
        <div className="field" key={c.id}>
          <span>{c.rotulo}</span>
          {c.tipo === "texto"
            ? <input className="input" value={detalhes[c.id] ?? ""} onChange={(e) => set(c.id, e.target.value)} maxLength={120}
                placeholder={c.id === "repositorio" ? (sessao?.ficha.titulo ? sessao.ficha.titulo.toLowerCase().replace(/[^a-z0-9]+/g, "-") : "nome-do-repositorio") : ""} />
            : <div className="seg">{c.opcoes?.map(([id, rot]) => (
                <button key={id} aria-pressed={c.tipo === "multi" ? (detalhes[c.id] ?? []).includes(id) : detalhes[c.id] === id}
                  onClick={() => (c.tipo === "multi" ? alternar(c.id, id) : set(c.id, id))}>{rot}</button>
              ))}</div>}
        </div>
      ))}
      {spec.tipo === "llm_key" && (
        <p className="dica"><Icon name="info" size={14} />O Lab recomenda começar pelo <b>DeepSeek V4 Flash</b> e subir para o <b>V4 Pro</b> se o protocolo de avaliação pedir. Dados sensíveis: use os modelos do hub.</p>
      )}
      <label className="field">
        <span>Para que você precisa?</span>
        <textarea className="textarea" rows={3} value={justificativa} onChange={(e) => setJustificativa(e.target.value)} maxLength={1000}
          placeholder="Ex.: comparar o V4 Flash com o GPT-OSS 120B no protocolo de avaliação do experimento" />
      </label>
      {sessao && (
        <label className="check"><input type="checkbox" checked={vincular} onChange={(e) => setVincular(e.target.checked)} />
          Vincular ao experimento <b>{sessao.ficha.titulo || sessao.ficha.id}</b></label>
      )}
      {erro && <p className="erro">{erro}</p>}
      <div className="pf-acoes">
        <button className="btn ghost" onClick={onCancelar}>Cancelar</button>
        <button className="btn accent" onClick={enviar} disabled={enviando || !justificativa.trim() || !nome.trim()}>
          {enviando ? <span className="spinner" /> : <Icon name="send" size={15} />}Enviar ao Lab
        </button>
      </div>
    </section>
  );
}

export function PedidoItem({ p, t, destaque }: { p: Pedido; t: Toolbox | null; destaque?: boolean }) {
  const { api } = useApp();
  const st = STATUS_PEDIDO[p.status];
  const nome = t?.recursos.find((r) => r.tipo === p.tipo)?.nome ?? p.tipo;
  return (
    <li className={`pedido${destaque ? " novo" : ""}`}>
      <div className="pedido-topo">
        <span className="rc-ic sm"><Icon name={ICONE_RECURSO[p.tipo]} size={16} /></span>
        <div><b>{nome}</b><small className="muted">{p.experimento ? `${p.experimento} · ` : ""}pedido {haQuanto(p.criado_em)}</small></div>
        <Badge tom={st.tom} dot>{st.rotulo}</Badge>
      </div>
      <p className="pedido-just">{p.justificativa}</p>
      <div className="pedido-det">{Object.entries(p.detalhes).filter(([, v]) => v && (!Array.isArray(v) || v.length)).map(([k, v]) => (
        <span key={k}>{rotuloDetalhe(t, p.tipo, k, v)}</span>
      ))}</div>
      {p.status === "pendente" && <p className="pedido-nota"><Icon name="clock" size={13} />O Lab foi avisado. A credencial aparece aqui assim que alguém aprovar.</p>}
      {p.status === "negado" && <p className="pedido-nota neg"><Icon name="info" size={13} />{p.decidido_por}: “{p.comentario}”</p>}
      {p.status === "revogado" && <p className="pedido-nota"><Icon name="info" size={13} />Revogado por {p.decidido_por}{p.comentario ? `: “${p.comentario}”` : ""}</p>}
      {p.status === "aprovado" && p.credencial && <CredencialView id={p.id} c={p.credencial} carregar={api.credencial} />}
    </li>
  );
}

export function Recursos({ t, sessao, arg }: { t: Toolbox; sessao: Estado | null; arg?: string }) {
  const { api, perfil, ir } = useApp();
  const [tipoArg, preset] = (arg ?? "").split("~");
  const aberto = t.recursos.find((r) => r.tipo === tipoArg) ?? null;
  const [meus, setMeus] = useState<Pedido[] | null>(null);
  const [novo, setNovo] = useState<string | null>(null);
  const carregar = useCallback(() => {
    if (!perfil.nome) { setMeus([]); return; }
    api.pedidos({ solicitante: perfil.nome }).then(setMeus).catch(() => setMeus([]));
  }, [api, perfil.nome]);
  useEffect(() => { carregar(); }, [carregar]);
  const pendentes = useMemo(() => (meus ?? []).filter((p) => p.status === "pendente").length, [meus]);
  // Enquanto houver pedido esperando o Lab, confere de tempos em tempos.
  useEffect(() => {
    if (!pendentes) return;
    const h = setInterval(carregar, 5000);
    return () => clearInterval(h);
  }, [pendentes, carregar]);

  const abrir = (tipo?: TipoRecurso) => ir({ tela: "dev", secao: "recursos", arg: tipo });
  return (
    <div className="secao">
      <header className="secao-cab">
        <span className="eyebrow">Self-service · aprovado pelo Lab</span>
        <h1>Recursos</h1>
        <p className="muted">Peça o que você precisa para testar e construir. O pedido vai para a fila do Lab; quando alguém aprova, a credencial aparece aqui, pronta para usar.</p>
      </header>

      <div className="recursos-grade">
        {t.recursos.map((r) => (
          <button key={r.tipo} className={`recurso-card${aberto?.tipo === r.tipo ? " sel" : ""}`} onClick={() => abrir(r.tipo)}>
            <span className="rc-ic"><Icon name={ICONE_RECURSO[r.tipo]} size={20} /></span>
            <b>{r.nome}</b>
            <span className="muted">{r.descricao}</span>
            <span className="rc-pe"><small>{r.sla}</small><span className="rc-cta">Pedir<Icon name="arrow" size={14} /></span></span>
          </button>
        ))}
      </div>

      {aberto && (
        <Formulario key={aberto.tipo + preset} spec={aberto} sessao={sessao} preset={preset}
          onCancelar={() => abrir()} onFeito={(p) => { setNovo(p.id); abrir(); carregar(); }} />
      )}

      <section className="meus-pedidos">
        <div className="mp-cab"><h2>Meus pedidos</h2>{pendentes > 0 && <Badge tom="warn" dot>{pendentes} aguardando o Lab</Badge>}</div>
        {api.modo === "demo" && pendentes > 0 && (
          <p className="dica"><Icon name="swap" size={14} />No modo demonstração, troque o papel para <b>Lab</b> (menu no topo) e aprove o pedido em <b>Recursos</b>. Volte aqui para ver a credencial.</p>
        )}
        {meus === null && <span className="spinner" />}
        {meus && meus.length === 0 && <Empty icone="key" titulo="Nenhum pedido ainda">Peça uma chave de LLM para começar a testar os modelos do Lab.</Empty>}
        <ul className="pedidos">{(meus ?? []).map((p) => <PedidoItem key={p.id} p={p} t={t} destaque={p.id === novo} />)}</ul>
      </section>
    </div>
  );
}
