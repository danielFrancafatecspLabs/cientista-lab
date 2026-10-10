import { useEffect, useRef, useState } from "react";
import type { Jornada, PapelConversa, PapelId } from "../../api/types";
import { Icon } from "../../components/ui";
import { useApp } from "../../lib/app";
import "./entrada.css";

const ICONE: Record<PapelId, "chat" | "code" | "shield" | "chart"> = { solicitante: "chat", desenvolvedor: "code", lab: "shield", sponsor: "chart" };
const RECEBE: Record<PapelId, string[]> = {
  solicitante: ["Perguntas que vão ao fundo do problema", "Ficha no padrão do Lab, sem jargão", "Acompanhamento da bancada até o parecer"],
  desenvolvedor: ["Trade-offs explícitos e baseline", "Protocolo de avaliação com metas", "Kit com avaliador e CI anti-regressão"],
  lab: ["Fila de fichas para o gate G0", "Pré-análise do Agente Revisor", "Evidências da conversa ao lado"],
  sponsor: ["Portfólio por etapa", "Indicadores do metaexperimento", "Decisões que dependem de você"],
};
const CICLO = [
  { t: "Conversa", d: "O Cientista mapeia o problema" },
  { t: "Ficha", d: "Hipótese e critérios numéricos" },
  { t: "Revisão", d: "Lab aprova", g: "G0" },
  { t: "Amostra", d: "Dados sustentam o teste?", g: "G1" },
  { t: "Construção", d: "Desenvolvedor e golden path" },
  { t: "Qualidade", d: "Ralph Loop até Qk ≥ 0,85", g: "G2" },
  { t: "Parecer", d: "Veredito com evidências", g: "G3" },
  { t: "Decisão", d: "Sponsor escala ou encerra" },
];

function Personalizar({ j, onVoltar }: { j: Jornada; onVoltar: () => void }) {
  const { api, ir, perfil, setPerfil } = useApp();
  const [nome, setNome] = useState(perfil.nome);
  const [prefs, setPrefs] = useState<Record<string, string>>(() => Object.fromEntries(j.preferencias.map((p) => [p.id, p.padrao])));
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); }, [j.papel]);

  const entrar = async () => {
    setPerfil({ nome: nome.trim(), papel: j.papel });
    if (j.papel === "lab") return ir({ tela: "lab" });
    if (j.papel === "sponsor") return ir({ tela: "sponsor" });
    setCriando(true); setErro(null);
    try {
      const s = await api.criarSessao({ nome: nome.trim() || undefined, papel: j.papel as PapelConversa, preferencias: prefs });
      setPerfil({ sessoes: { [j.papel]: s.id } });
      ir({ tela: "estudio", sid: s.id });
    } catch (e) {
      setErro((e as Error).message); setCriando(false);
    }
  };

  return (
    <section className="personalizar card" aria-label={`Personalizar a jornada de ${j.nome}`}>
      <header>
        <button className="btn sm ghost" onClick={onVoltar}><Icon name="back" size={15} />Papéis</button>
        <span className="eyebrow">{j.nome}</span>
      </header>
      <h2>{j.tipo === "conversa" ? "Antes de começar" : "Quase lá"}</h2>
      <p className="muted">{j.tipo === "conversa" ? "Duas escolhas rápidas para o Cientista conversar do seu jeito. Dá para mudar depois." : "Seu nome aparece nas decisões que você registrar."}</p>
      <label className="field">
        <span>Como podemos te chamar?</span>
        <input ref={ref} className="input" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome"
          onKeyDown={(e) => e.key === "Enter" && !criando && entrar()} maxLength={60} />
      </label>
      {j.preferencias.map((p) => (
        <div className="field" key={p.id}>
          <span>{p.pergunta.replace(/:$/, "")}</span>
          <div className="seg">
            {p.opcoes.map(([id, rot]) => (
              <button key={id} aria-pressed={prefs[p.id] === id} onClick={() => setPrefs((x) => ({ ...x, [p.id]: id }))}>{rot}</button>
            ))}
          </div>
        </div>
      ))}
      {erro && <p className="erro">{erro}</p>}
      <button className="btn accent lg entrar" onClick={entrar} disabled={criando}>
        {criando ? <span className="spinner" /> : null}
        {j.papel === "lab" ? "Abrir fila de revisão" : j.papel === "sponsor" ? "Abrir portfólio" : "Começar com o Cientista"}
        <Icon name="arrow" size={17} />
      </button>
    </section>
  );
}

export function Entrada({ papel }: { papel?: PapelId }) {
  const { papeis } = useApp();
  const [sel, setSel] = useState<PapelId | null>(papel ?? null);
  useEffect(() => setSel(papel ?? null), [papel]);
  const j = papeis?.jornadas.find((x) => x.papel === sel);

  return (
    <div className="entrada">
      <section className="hero">
        <span className="eyebrow">Plataforma de experimentação do beOn Labs</span>
        <h1>Toda boa ideia merece<br />um experimento <em>honesto</em>.</h1>
        <p>O Cientista entende o seu problema a fundo, transforma em uma hipótese que dá para testar e acompanha até o resultado. O Lab revisa cada passo; as decisões são sempre de pessoas.</p>
      </section>

      <div className={`portas${j ? " com-painel" : ""}`}>
        <div className="grade" role="list">
          {(papeis?.jornadas ?? []).map((x) => (
            <button key={x.papel} role="listitem" className={`porta${sel === x.papel ? " sel" : ""}${sel && sel !== x.papel ? " apagada" : ""}`}
              onClick={() => setSel(x.papel)} aria-pressed={sel === x.papel}>
              <span className="porta-topo">
                <span className={`porta-ic t-${x.tipo}`}><Icon name={ICONE[x.papel]} size={20} /></span>
                <span className="eyebrow">{x.nome}</span>
              </span>
              <span className="porta-chamada">{x.chamada}</span>
              <span className="porta-promessa">{x.promessa}</span>
              <ul>{RECEBE[x.papel].map((r) => <li key={r}><Icon name="check" size={14} />{r}</li>)}</ul>
              <span className="porta-cta">{x.tipo === "conversa" ? "Conversar com o Cientista" : "Abrir painel"}<Icon name="arrow" size={15} /></span>
            </button>
          ))}
        </div>
        {j && <Personalizar j={j} onVoltar={() => setSel(null)} />}
      </div>

      <section className="ciclo">
        <div className="ciclo-cab">
          <h2>Um ciclo, quatro portões humanos</h2>
          <p className="muted">Agentes fazem o trabalho pesado. Em cada portão (G0–G3), uma pessoa decide com as evidências na mesa.</p>
        </div>
        <ol>
          {CICLO.map((c, i) => (
            <li key={c.t}>
              <span className="ciclo-n">{c.g ?? String(i + 1).padStart(2, "0")}</span>
              <b>{c.t}</b>
              <small>{c.d}</small>
            </li>
          ))}
        </ol>
        <div className="principios">
          <div><Icon name="search" /><b>Pergunta antes de propor</b><span>O Cientista mapeia o problema em dez dimensões e mostra por que cada pergunta importa.</span></div>
          <div><Icon name="quote" /><b>Mostra de onde vem cada sugestão</b><span>Critérios e amostras citam casos do histórico do Lab, cálculos ou dizem que são estimativas.</span></div>
          <div><Icon name="shield" /><b>Pessoas decidem nos portões</b><span>Nenhuma execução começa sem a revisão do Lab, e nada escala sem o Sponsor.</span></div>
        </div>
      </section>
    </div>
  );
}
