"""Caixa de ferramentas do desenvolvedor: catálogo e pedidos de recursos.

O catálogo (modelos, benchmarks, ferramentas, práticas, arquitetura e os tipos de
recurso que dá para pedir) vive em `metaexp/catalogo/toolbox.json`, fonte única
lida pela API, pelo prompt do Cientista e pelo modo demonstração do app.

Um pedido de recurso segue um ciclo curto:

    pendente → aprovado (credencial entregue) → revogado
            ↘ negado

Este módulo é domínio puro: valida pedidos e monta credenciais locais. Quem fala
com o gateway LiteLLM de verdade é `metaexp/recursos.py`.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo" / "toolbox.json"

TipoRecurso = Literal["llm_key", "servidor", "github"]
StatusPedido = Literal["pendente", "aprovado", "negado", "revogado"]


@lru_cache(maxsize=1)
def catalogo() -> dict:
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def tipo_recurso(tipo: str) -> dict:
    for r in catalogo()["recursos"]:
        if r["tipo"] == tipo:
            return r
    raise ValueError(f"tipo de recurso desconhecido: {tipo}")


# ------------------------------------------------------------------ pedidos ----

class Credencial(BaseModel):
    """O que o desenvolvedor recebe. `segredo` só sai pela rota da credencial."""

    resumo: str
    campos: dict[str, str] = Field(default_factory=dict)   # visíveis: URL, usuário, host...
    segredo: Optional[str] = None                           # chave, senha ou token
    exemplo: Optional[str] = None                           # snippet para começar a usar
    expira_em: Optional[str] = None
    simulada: bool = True                                   # gerada localmente, sem provisionar de verdade


class PedidoRecurso(BaseModel):
    id: str
    tipo: TipoRecurso
    solicitante: str
    justificativa: str
    detalhes: dict[str, Any] = Field(default_factory=dict)
    sessao_id: Optional[str] = None
    experimento: Optional[str] = None                       # título da ficha, quando ligado a um experimento
    status: StatusPedido = "pendente"
    criado_em: str
    decidido_em: Optional[str] = None
    decidido_por: Optional[str] = None
    comentario: Optional[str] = None
    credencial: Optional[Credencial] = None

    def publico(self) -> dict:
        """Versão para listas: a credencial vai sem o segredo (só os 4 últimos caracteres)."""
        d = self.model_dump()
        if self.credencial and self.credencial.segredo:
            d["credencial"]["segredo"] = None
            d["credencial"]["segredo_final"] = self.credencial.segredo[-4:]
        return d


def validar_detalhes(tipo: str, detalhes: dict[str, Any]) -> dict[str, Any]:
    """Mantém só os campos do tipo, completa com o padrão e confere opções válidas."""
    spec = tipo_recurso(tipo)
    out: dict[str, Any] = {}
    for campo in spec["campos"]:
        cid, valor = campo["id"], detalhes.get(campo["id"])
        opcoes = [o[0] for o in campo.get("opcoes", [])]
        if campo["tipo"] == "multi":
            itens = valor if isinstance(valor, list) else ([valor] if valor else [campo["padrao"]])
            invalidos = [x for x in itens if x not in opcoes]
            if invalidos:
                raise ValueError(f"{campo['rotulo']}: opção inválida ({', '.join(map(str, invalidos))})")
            out[cid] = list(dict.fromkeys(itens)) or [campo["padrao"]]
        elif campo["tipo"] == "select":
            valor = valor or campo["padrao"]
            if valor not in opcoes:
                raise ValueError(f"{campo['rotulo']}: opção inválida ({valor})")
            out[cid] = valor
        else:
            out[cid] = str(valor or campo["padrao"]).strip()[:120]
    if tipo == "github" and not out.get("usuario"):
        raise ValueError("informe seu usuário no GitHub")
    return out


def _dias(codigo: str) -> int:
    return int(codigo.rstrip("d")) if codigo and codigo.rstrip("d").isdigit() else 30


def _expira(dias: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=dias)).isoformat(timespec="seconds")


def _slug(texto: str) -> str:
    base = "".join(ch if ch.isalnum() else "-" for ch in texto.lower()).strip("-")
    return "-".join(p for p in base.split("-") if p)[:40] or "experimento"


def exemplo_llm(base_url: str, modelo: str) -> str:
    return (
        "# pip install openai\n"
        "import os\n"
        "from openai import OpenAI\n\n"
        f'client = OpenAI(base_url="{base_url}", api_key=os.environ["LAB_LLM_KEY"])\n'
        "resp = client.chat.completions.create(\n"
        f'    model="{modelo}",\n'
        '    messages=[{"role": "user", "content": "Olá!"}],\n'
        ")\n"
        "print(resp.choices[0].message.content)\n"
    )


def credencial_local(p: PedidoRecurso, *, hub_url: str | None, github_org: str) -> Credencial:
    """Credencial gerada no próprio METAEXP, para quando ainda não há integração com a infraestrutura."""
    d = p.detalhes
    if p.tipo == "llm_key":
        base = hub_url or "https://llm.lab.interno/v1"
        modelos = d.get("modelos") or ["deepseek-v4-flash"]
        dias = _dias(d.get("validade", "30d"))
        return Credencial(
            resumo=f"Chave do gateway LiteLLM para {', '.join(modelos)}",
            campos={"base_url": base, "modelos": ", ".join(modelos), "orcamento_mensal": f"US$ {d.get('orcamento', '50')}"},
            segredo="sk-lab-" + secrets.token_urlsafe(24),
            exemplo=exemplo_llm(base, modelos[0]),
            expira_em=_expira(dias),
        )
    if p.tipo == "servidor":
        perfil = d.get("perfil", "cpu-p")
        nome = f"lab-{perfil}-{p.id[:6]}"
        usuario = _slug(p.solicitante).replace("-", "")[:16] or "dev"
        return Credencial(
            resumo=f"Servidor {nome} ({perfil})",
            campos={"host": f"{nome}.lab.interno", "usuario": usuario, "perfil": perfil, "uso": d.get("uso", "prototipo")},
            segredo=secrets.token_urlsafe(18),
            exemplo=f"ssh {usuario}@{nome}.lab.interno\n# troque a senha no primeiro acesso: passwd",
            expira_em=_expira(_dias(d.get("duracao", "30d"))),
        )
    repo = d.get("repositorio") or _slug(p.experimento or p.justificativa)
    return Credencial(
        resumo=f"Acesso à organização {github_org} e ao repositório {repo}",
        campos={"organizacao": github_org, "repositorio": f"{github_org}/{repo}", "usuario": d.get("usuario", ""),
                "permissao": d.get("permissao", "write")},
        exemplo=(f"# aceite o convite em https://github.com/orgs/{github_org}/invitation\n"
                 f"git clone git@github.com:{github_org}/{repo}.git\n"
                 "# descompacte o kit do METAEXP na raiz e faça o primeiro push: o CI de avaliação já vem pronto"),
    )


# -------------------------------------------------------- benchmarks do Lab ----

class BenchmarkLab(BaseModel):
    id: str
    modelo: str
    tarefa: str                      # ex.: "RAG sobre FAQ de atendimento"
    metrica: str                     # ex.: "acerto", "latência p95"
    valor: str                       # texto, para aceitar "88%" ou "1,4 s"
    conjunto: Optional[str] = None   # dataset ou experimento de origem
    observacoes: Optional[str] = None
    responsavel: str = "Lab"
    em: str


# ------------------------------------------------------- contexto do prompt ----

def resumo_para_prompt() -> str:
    """Resumo estável da caixa de ferramentas para o prompt do Cientista (jornada Desenvolvedor)."""
    c = catalogo()
    rec = [m for m in c["modelos"] if m["grupo"] == "recomendado"]
    hub = [m for m in c["modelos"] if m["grupo"] == "hub"]
    linhas = [
        "# Caixa de ferramentas do Lab (o desenvolvedor vê isto na plataforma)",
        "",
        "## Modelos",
        "Recomendados pelo Lab: " + "; ".join(f"**{m['nome']}** (`{m['alias']}`): {m['uso_ideal']}" for m in rec),
        "No hub de GPUs (dados não saem da casa): " + "; ".join(f"**{m['nome']}** (`{m['alias']}`): {m['uso_ideal']}" for m in hub),
        "Todo acesso a modelo passa pelo gateway LiteLLM (API compatível com OpenAI) com uma chave pedida na plataforma.",
        "",
        "## Ferramentas que o Lab já testou",
        *[f"- {f['nome']} ({f['status']}): {f['nota_lab']}" for f in c["ferramentas"]],
        "",
        "## Arquitetura recomendada",
        c["arquitetura"]["combinacao"],
        f"LangGraph: {c['arquitetura']['langgraph']['quando']}",
        f"n8n: {c['arquitetura']['n8n']['quando']}",
        "",
        "## Para virar piloto",
        *[f"- {i['item']}" for i in c["arquitetura"]["piloto"]],
        "",
        "## Recursos que o desenvolvedor pode pedir (o Lab aprova)",
        *[f"- `{r['tipo']}`: {r['nome']}. {r['descricao']}" for r in c["recursos"]],
        "Quando a pessoa precisar de um desses recursos para avançar, use `sugerir_recurso`: o chat mostra o botão do pedido.",
    ]
    return "\n".join(linhas)
