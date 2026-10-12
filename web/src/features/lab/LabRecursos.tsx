// Gestão do Lab: pedidos de recursos dos desenvolvedores e benchmarks da casa.
import { useCallback, useEffect, useState } from "react";
import type { BenchmarkLab, NovoBenchmark, Pedido, StatusPedido } from "../../api/types";
import { Avatar, Badge, Empty, Icon, Tabs } from "../../components/ui";
import { useApp } from "../../lib/app";
import { haQuanto } from "../../lib/format";
import { CredencialView, ICONE_RECURSO, rotuloDetalhe, STATUS_PEDIDO, useToolbox } from "../dev/comum";
import { BenchmarksLabTabela } from "../dev/Modelos";

type Fila = "pendentes" | "aprovados" | "encerrados";
const FILAS: Record<Fila, StatusPedido[]> = { pendentes: ["pendente"], aprovados: ["aprovado"], encerrados: ["negado", "revogado"] };

function DetalhePedido({ p, onMudou }: { p: Pedido; onMudou: () => void }) {
  const { api, perfil } = useApp();
  const t = useToolbox();
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const revisor = perfil.nome ? `${perfil.nome} (Lab)` : "Lab";
  const spec = t?.recursos.find((r) => r.tipo === p.tipo);
  const agir = async (acao: "aprovar" | "negar" | "revogar") => {
    setEnviando(acao); setErro(null);
    try {
      if (acao === "revogar") await api.revogarPedido(p.id, { revisor, comentario });
      else await api.decidirPedido(p.id, { decisao: acao, comentario, revisor });
      setComentario(""); onMudou();
    } catch (e) { setErro((e as Error).message); }
    setEnviando(null);
  };
  const st = STATUS_PEDIDO[p.status];
  return (
    <section className="lab-detalhe">
      <header className="ld-cab">
        <div className="ld-meta">
          <Avatar nome={p.solicitante} tom="var(--ag-dev)" />
          <span><b>{p.solicitante}</b><small>Desenvolvedor · pedido {haQuanto(p.criado_em)}{p.experimento ? ` · ${p.experimento}` : ""}</small></span>
          <Badge tom={st.tom} dot>{st.rotulo}</Badge>
        </div>
        <h2><Icon name={ICONE_RECURSO[p.tipo]} size={22} style={{ verticalAlign: "-3px", marginRight: 8 }} />{spec?.nome ?? p.tipo}</h2>
      </header>
      <div className="ld-corpo scroll">
        <div className="lr-bloco">
          <span className="eyebrow">Justificativa</span>
          <p className="lr-just">{p.justificativa}</p>
        </div>
        <dl className="lr-det">
          {spec?.campos.map((c) => <div key={c.id}><dt>{c.rotulo}</dt><dd>{rotuloDetalhe(t, p.tipo, c.id, p.detalhes[c.id]) || "—"}</dd></div>)}
          {spec && <div><dt>SLA</dt><dd>{spec.sla}</dd></div>}
        </dl>
        {p.decidido_por && <p className="muted">{p.status === "aprovado" ? "Aprovado" : p.status === "negado" ? "Negado" : "Revogado"} por {p.decidido_por} {p.decidido_em ? haQuanto(p.decidido_em) : ""}{p.comentario ? `: “${p.comentario}”` : ""}</p>}
        {p.status === "aprovado" && p.credencial && <CredencialView id={p.id} c={p.credencial} carregar={api.credencial} />}
        {p.status === "pendente" && t?.hub.chaves_reais === false && p.tipo === "llm_key" && (
          <p className="dica"><Icon name="info" size={14} />Sem <code>METAEXP_LITELLM_MASTER_KEY</code> configurada, a chave é gerada localmente e marcada como simulada. Com a master key, aprovar cria a chave virtual no gateway LiteLLM com os modelos, a validade e o orçamento do pedido.</p>
        )}
      </div>
      {(p.status === "pendente" || p.status === "aprovado") && (
        <footer className="ld-decisao">
          <textarea className="textarea" rows={2} value={comentario} onChange={(e) => setComentario(e.target.value)}
            placeholder={p.status === "pendente" ? "Comentário para o desenvolvedor (obrigatório para negar)" : "Motivo da revogação (opcional)"} />
          {erro && <p className="erro">{erro}</p>}
          <div className="ld-botoes">
            {p.status === "pendente" ? (
              <>
                <button className="btn" onClick={() => agir("negar")} disabled={!!enviando || !comentario.trim()}>{enviando === "negar" ? <span className="spinner" /> : <Icon name="x" size={15} />}Negar</button>
                <button className="btn accent" onClick={() => agir("aprovar")} disabled={!!enviando}>{enviando === "aprovar" ? <span className="spinner" /> : <Icon name="check" size={15} />}Aprovar e gerar credencial</button>
              </>
            ) : (
              <button className="btn" onClick={() => agir("revogar")} disabled={!!enviando}>{enviando === "revogar" ? <span className="spinner" /> : <Icon name="x" size={15} />}Revogar acesso</button>
            )}
          </div>
        </footer>
      )}
    </section>
  );
}

export function LabRecursos({ id }: { id?: string }) {
  const { api, ir } = useApp();
  const t = useToolbox();
  const [fila, setFila] = useState<Fila>("pendentes");
  const [todos, setTodos] = useState<Pedido[] | null>(null);
  const carregar = useCallback(() => api.pedidos().then(setTodos), [api]);
  useEffect(() => { carregar(); }, [carregar]);
  const itens = (todos ?? []).filter((p) => FILAS[fila].includes(p.status));
  const n = (f: Fila) => (todos ?? []).filter((p) => FILAS[f].includes(p.status)).length;
  const sel = (todos ?? []).find((p) => p.id === id);
  useEffect(() => { if (!id && itens.length) ir({ tela: "lab", aba: "recursos", id: itens[0].id }); }, [todos, fila]); // eslint-disable-line

  return (
    <div className="lab">
      <aside className="lab-fila">
        <div className="lf-cab">
          <span className="eyebrow">Lab · caixa de ferramentas</span>
          <h1>Pedidos de recursos</h1>
          <Tabs valor={fila} onChange={setFila} itens={[
            { id: "pendentes", rotulo: "Pendentes", count: n("pendentes") }, { id: "aprovados", rotulo: "Ativos", count: n("aprovados") },
            { id: "encerrados", rotulo: "Encerrados", count: n("encerrados") }]} />
        </div>
        <ul className="lf-lista scroll">
          {todos === null && <li className="estudio-carregando"><span className="spinner" /></li>}
          {todos && itens.length === 0 && <li><Empty icone="key" titulo={fila === "pendentes" ? "Nenhum pedido esperando" : "Nada por aqui"}>{fila === "pendentes" ? "Quando um desenvolvedor pedir chave, servidor ou GitHub, o pedido aparece aqui." : ""}</Empty></li>}
          {itens.map((p) => (
            <li key={p.id}>
              <button className={`lf-item${p.id === id ? " sel" : ""}`} onClick={() => ir({ tela: "lab", aba: "recursos", id: p.id })}>
                <span className="lf-topo"><b><Icon name={ICONE_RECURSO[p.tipo]} size={14} style={{ verticalAlign: "-2px", marginRight: 6 }} />{t?.recursos.find((r) => r.tipo === p.tipo)?.nome ?? p.tipo}</b>
                  <Badge tom={STATUS_PEDIDO[p.status].tom}>{STATUS_PEDIDO[p.status].rotulo}</Badge></span>
                <span className="lf-hip">{p.justificativa}</span>
                <span className="lf-pe"><span>{p.solicitante}</span>{p.experimento && <span>{p.experimento}</span>}<span>{haQuanto(p.criado_em)}</span></span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      {sel ? <DetalhePedido key={sel.id + sel.status} p={sel} onMudou={carregar} /> : <section className="lab-detalhe"><Empty icone="key" titulo="Escolha um pedido na fila" /></section>}
    </div>
  );
}

const VAZIO: NovoBenchmark = { modelo: "", tarefa: "", metrica: "", valor: "", conjunto: "", observacoes: "", responsavel: "" };

export function LabBenchmarks() {
  const { api, perfil } = useApp();
  const t = useToolbox();
  const [itens, setItens] = useState<BenchmarkLab[] | null>(null);
  const [form, setForm] = useState<NovoBenchmark>(VAZIO);
  const [erro, setErro] = useState<string | null>(null);
  const carregar = useCallback(() => api.benchmarksLab().then(setItens), [api]);
  useEffect(() => { carregar(); }, [carregar]);
  const set = (k: keyof NovoBenchmark, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const ok = form.modelo.trim() && form.tarefa.trim() && form.metrica.trim() && form.valor.trim();
  const salvar = async () => {
    setErro(null);
    try {
      await api.registrarBenchmark({ ...form, responsavel: form.responsavel?.trim() || (perfil.nome ? `${perfil.nome} (Lab)` : "Lab"),
        conjunto: form.conjunto?.trim() || null, observacoes: form.observacoes?.trim() || null });
      setForm((f) => ({ ...VAZIO, modelo: f.modelo, tarefa: f.tarefa })); carregar();
    } catch (e) { setErro((e as Error).message); }
  };
  const remover = async (bid: string) => { await api.removerBenchmark(bid); carregar(); };
  return (
    <div className="lab-bench scroll">
      <div className="secao">
        <header className="secao-cab">
          <span className="eyebrow">Lab · caixa de ferramentas</span>
          <h1>Benchmarks do Lab</h1>
          <p className="muted">Resultados medidos pelo Lab nos dados e tarefas da casa. Aparecem para os desenvolvedores em Modelos e benchmarks.</p>
        </header>
        <section className="bench-form card">
          <b>Registrar resultado</b>
          <div className="bf-grade">
            <label className="field"><span>Modelo</span><input className="input" list="modelos-lab" value={form.modelo} onChange={(e) => set("modelo", e.target.value)} placeholder="DeepSeek V4 Flash" /></label>
            <label className="field"><span>Tarefa</span><input className="input" value={form.tarefa} onChange={(e) => set("tarefa", e.target.value)} placeholder="RAG sobre a FAQ de atendimento" /></label>
            <label className="field"><span>Métrica</span><input className="input" value={form.metrica} onChange={(e) => set("metrica", e.target.value)} placeholder="acerto, F1 macro, latência p95" /></label>
            <label className="field"><span>Resultado</span><input className="input" value={form.valor} onChange={(e) => set("valor", e.target.value)} placeholder="88%" /></label>
            <label className="field"><span>Conjunto ou experimento</span><input className="input" value={form.conjunto ?? ""} onChange={(e) => set("conjunto", e.target.value)} placeholder="opcional" /></label>
            <label className="field"><span>Observações</span><input className="input" value={form.observacoes ?? ""} onChange={(e) => set("observacoes", e.target.value)} placeholder="modo, hardware, quantização" /></label>
          </div>
          <datalist id="modelos-lab">{t?.modelos.map((m) => <option key={m.id} value={m.nome} />)}</datalist>
          {erro && <p className="erro">{erro}</p>}
          <div className="pf-acoes"><button className="btn accent" onClick={salvar} disabled={!ok}><Icon name="plus" size={15} />Registrar</button></div>
        </section>
        {itens === null ? <span className="spinner" /> : itens.length === 0
          ? <Empty icone="chart" titulo="Nenhum benchmark registrado">Registre o primeiro resultado acima.</Empty>
          : <BenchmarksLabTabela itens={itens} onRemover={remover} />}
      </div>
    </div>
  );
}
