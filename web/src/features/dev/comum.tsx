// Peças compartilhadas da caixa de ferramentas (portal do desenvolvedor e telas do Lab).
import { useEffect, useState } from "react";
import type { Backend, Credencial, StatusPedido, TipoRecurso, Toolbox } from "../../api/types";
import { Badge, Icon } from "../../components/ui";
import { useApp } from "../../lib/app";

let cache: { api: Backend; p: Promise<Toolbox> } | null = null;
export function useToolbox(): Toolbox | null {
  const { api } = useApp();
  const [t, setT] = useState<Toolbox | null>(null);
  useEffect(() => {
    if (!cache || cache.api !== api) cache = { api, p: api.toolbox() };
    let vivo = true;
    cache.p.then((x) => vivo && setT(x)).catch(() => { cache = null; });
    return () => { vivo = false; };
  }, [api]);
  return t;
}

export const ICONE_RECURSO: Record<TipoRecurso, "key" | "server" | "git"> = { llm_key: "key", servidor: "server", github: "git" };
export const STATUS_PEDIDO: Record<StatusPedido, { rotulo: string; tom: string }> = {
  pendente: { rotulo: "Aguardando o Lab", tom: "warn" }, aprovado: { rotulo: "Aprovado", tom: "ok" },
  negado: { rotulo: "Negado", tom: "accent" }, revogado: { rotulo: "Revogado", tom: "" },
};
const ROTULO_CAMPO: Record<string, string> = {
  base_url: "Base URL", modelos: "Modelos", orcamento_mensal: "Orçamento", host: "Host", usuario: "Usuário", perfil: "Perfil",
  uso: "Uso", organizacao: "Organização", repositorio: "Repositório", permissao: "Permissão",
};

export function Copiar({ texto, rotulo = "Copiar" }: { texto: string; rotulo?: string }) {
  const [ok, setOk] = useState(false);
  const copiar = async () => {
    try { await navigator.clipboard.writeText(texto); setOk(true); setTimeout(() => setOk(false), 1400); } catch { /* sem área de transferência */ }
  };
  return <button className="btn sm ghost copiar" onClick={copiar} aria-label={rotulo}><Icon name={ok ? "check" : "copy"} size={14} />{ok ? "Copiado" : rotulo}</button>;
}

export function Codigo({ codigo, titulo }: { codigo: string; titulo?: string }) {
  return (
    <div className="codigo">
      <div className="codigo-cab"><span className="mono">{titulo ?? "exemplo"}</span><Copiar texto={codigo} /></div>
      <pre className="scroll"><code>{codigo}</code></pre>
    </div>
  );
}

export function CredencialView({ id, c, carregar }: { id: string; c: Credencial; carregar: (id: string) => Promise<Credencial> }) {
  const [cheia, setCheia] = useState<Credencial | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const revelar = async () => { try { setCheia(await carregar(id)); } catch (e) { setErro((e as Error).message); } };
  const cred = cheia ?? c;
  const tem = cheia ? !!cheia.segredo : !!c.segredo_final;
  return (
    <div className="credencial">
      <div className="cred-cab">
        <b>{cred.resumo}</b>
        {cred.simulada
          ? <Badge tom="warn" title="Gerada localmente pelo METAEXP: ainda não há integração com a infraestrutura para este recurso.">simulada</Badge>
          : <Badge tom="ok" dot>ativa no gateway</Badge>}
      </div>
      <dl className="cred-campos">
        {Object.entries(cred.campos).filter(([, v]) => v).map(([k, v]) => (
          <div key={k}><dt>{ROTULO_CAMPO[k] ?? k}</dt><dd className="mono">{v}</dd></div>
        ))}
        {tem && (
          <div className="cred-segredo"><dt>{cred.campos.base_url ? "Chave" : cred.campos.host ? "Senha inicial" : "Token"}</dt>
            <dd>{cheia?.segredo
              ? <><code className="mono">{cheia.segredo}</code><Copiar texto={cheia.segredo} /></>
              : <><code className="mono">••••••••••••{c.segredo_final}</code><button className="btn sm" onClick={revelar}><Icon name="eye" size={14} />Mostrar</button></>}
            </dd></div>
        )}
        {cred.expira_em && <div><dt>Expira</dt><dd>{new Date(cred.expira_em).toLocaleDateString("pt-BR")}</dd></div>}
      </dl>
      {erro && <p className="erro">{erro}</p>}
      {cred.exemplo && <Codigo codigo={cheia?.segredo && cred.campos.base_url ? `export LAB_LLM_KEY=${cheia.segredo}\n\n${cred.exemplo}` : cred.exemplo} titulo="como usar" />}
    </div>
  );
}

export function rotuloDetalhe(t: Toolbox | null, tipo: TipoRecurso, campo: string, valor: unknown): string {
  const spec = t?.recursos.find((r) => r.tipo === tipo)?.campos.find((c) => c.id === campo);
  const nome = (v: string) => spec?.opcoes?.find((o) => o[0] === v)?.[1] ?? v;
  return Array.isArray(valor) ? valor.map((v) => nome(String(v))).join(", ") : nome(String(valor ?? ""));
}
