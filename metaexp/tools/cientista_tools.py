"""Ferramentas do Agente Cientista.

Cada ferramenta tem três partes: o esquema que o modelo vê, um modelo Pydantic
que valida a entrada (com streaming ansioso o servidor não valida por nós) e um
handler que altera o estado da sessão e devolve:
  - o texto do tool_result que volta para o modelo;
  - eventos de interface (dicts) que o front renderiza em tempo real.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from ..context.golden_paths import BY_ID as GOLDEN
from ..corpus.store import Corpus, resumo_para_contexto
from ..schemas import Ficha, Metrica
from .stats import margem_para_n, tamanho_amostra_proporcao


# ------------------------------------------------------- entradas validadas ----

class AtualizarFicha(BaseModel):
    titulo: Optional[str] = None
    dominio: Optional[str] = None
    problema: Optional[str] = None
    publico_afetado: Optional[str] = None
    hipotese: Optional[str] = None
    metricas: Optional[list[Metrica]] = None
    dados: Optional[str] = None
    amostra: Optional[str] = None
    riscos: Optional[list[str]] = None


class ClassificarExperimento(BaseModel):
    tecnologia: Literal["ia_generativa", "machine_learning", "estatistica", "visao_computacional", "automacao", "otimizacao", "outro"]
    tecnica: str
    justificativa: str
    golden_path: Optional[str] = None


class BuscarSimilares(BaseModel):
    consulta: str
    quantidade: int = 3


class RegistrarSinal(BaseModel):
    direcao: Literal["negocio", "desenvolvedor"]
    peso: Literal["fraco", "medio", "forte", "decisivo"]
    evidencia: str


class SugerirRespostas(BaseModel):
    opcoes: list[str] = Field(min_length=1, max_length=4)


class SolicitarDados(BaseModel):
    descricao: str
    formatos: list[str]


class CalcularAmostra(BaseModel):
    margem: float = 0.05
    confianca: float = 0.95
    registros_disponiveis: Optional[int] = None


class Skill(BaseModel):
    nome: str
    para_que: str
    nivel: Literal[1, 2, 3]


class ApresentarSkills(BaseModel):
    skills: list[Skill]
    estimativa_solicitante: str
    estimativa_laboratorio: str


class Encaminhar(BaseModel):
    destino: Literal["workflow", "desenvolvedor"]
    resumo: str


# --------------------------------------------------- esquemas para o modelo ----

def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


S = {"type": "string"}
METRICA = _obj({"nome": S, "descricao": S, "meta": S, "obrigatoria": {"type": "boolean"}},
               ["nome", "descricao", "meta", "obrigatoria"])

TOOL_SPECS: list[dict] = [
    {
        "name": "atualizar_ficha",
        "description": "Atualiza campos da ficha do experimento assim que ficarem claros na conversa. Envie apenas os campos que mudaram. `metricas` substitui a lista inteira.",
        "input_schema": _obj({
            "titulo": S, "dominio": {"type": "string", "enum": ["rede", "atendimento", "digital", "financeiro", "suprimentos", "juridico", "rh", "marketing", "operacoes", "outro"]},
            "problema": S, "publico_afetado": S,
            "hipotese": {"type": "string", "description": "Formato 'se X, então Y em Z%'"},
            "metricas": {"type": "array", "items": METRICA},
            "dados": S, "amostra": S, "riscos": {"type": "array", "items": S},
        }, []),
    },
    {
        "name": "classificar_experimento",
        "description": "Registra a tecnologia e a técnica do experimento e mostra à pessoa um cartão com a classificação. Use quando o problema e o critério de sucesso estiverem claros.",
        "input_schema": _obj({
            "tecnologia": {"type": "string", "enum": ["ia_generativa", "machine_learning", "estatistica", "visao_computacional", "automacao", "otimizacao", "outro"]},
            "tecnica": {"type": "string", "description": "Ex.: RAG, classificação supervisionada"},
            "justificativa": {"type": "string", "description": "Por que essa técnica resolve o problema, em uma frase simples"},
            "golden_path": {"type": "string", "description": "Id do golden path do catálogo, se houver"},
        }, ["tecnologia", "tecnica", "justificativa"]),
    },
    {
        "name": "buscar_experimentos_similares",
        "description": "Busca no histórico do laboratório experimentos parecidos com o problema atual (fichas, resultados e aprendizados).",
        "input_schema": _obj({"consulta": S, "quantidade": {"type": "integer", "description": "1 a 5"}}, ["consulta"]),
    },
    {
        "name": "registrar_sinal_perfil",
        "description": "Registra um indício de que a pessoa é da área de negócio ou desenvolvedora. A escolha de quem executa é um sinal decisivo.",
        "input_schema": _obj({
            "direcao": {"type": "string", "enum": ["negocio", "desenvolvedor"]},
            "peso": {"type": "string", "enum": ["fraco", "medio", "forte", "decisivo"]},
            "evidencia": {"type": "string", "description": "O que a pessoa disse ou fez, em poucas palavras"},
        }, ["direcao", "peso", "evidencia"]),
    },
    {
        "name": "sugerir_respostas",
        "description": "Mostra de 2 a 3 respostas curtas que a pessoa pode tocar para responder sua última pergunta, escritas na voz dela.",
        "input_schema": _obj({"opcoes": {"type": "array", "items": S}}, ["opcoes"]),
    },
    {
        "name": "solicitar_dados",
        "description": "Pede que a pessoa anexe um arquivo com a amostra de dados. O chat mostra o botão de anexo.",
        "input_schema": _obj({"descricao": S, "formatos": {"type": "array", "items": S}}, ["descricao", "formatos"]),
    },
    {
        "name": "calcular_tamanho_amostra",
        "description": "Calcula o tamanho mínimo de amostra para estimar uma proporção (n = z²·p(1−p)/E²) e, se informado, a margem obtida com os registros disponíveis.",
        "input_schema": _obj({
            "margem": {"type": "number", "description": "Margem de erro desejada, ex.: 0.05"},
            "confianca": {"type": "number", "description": "0.90, 0.95 ou 0.99"},
            "registros_disponiveis": {"type": "integer"},
        }, []),
    },
    {
        "name": "apresentar_skills",
        "description": "Mostra as skills necessárias para executar o experimento e as estimativas de prazo.",
        "input_schema": _obj({
            "skills": {"type": "array", "items": _obj({"nome": S, "para_que": S, "nivel": {"type": "integer", "enum": [1, 2, 3]}}, ["nome", "para_que", "nivel"])},
            "estimativa_solicitante": {"type": "string", "description": "Prazo se a própria pessoa executar"},
            "estimativa_laboratorio": {"type": "string", "description": "Prazo se o laboratório executar"},
        }, ["skills", "estimativa_solicitante", "estimativa_laboratorio"]),
    },
    {
        "name": "encaminhar",
        "description": "Conclui a conversa. `workflow`: o laboratório executa e a pessoa acompanha na bancada. `desenvolvedor`: a pessoa recebe a ficha final e executa.",
        "input_schema": _obj({"destino": {"type": "string", "enum": ["workflow", "desenvolvedor"]}, "resumo": S}, ["destino", "resumo"]),
    },
]

for _t in TOOL_SPECS:
    _t["strict"] = True
    _t["eager_input_streaming"] = True

INPUT_MODELS: dict[str, type[BaseModel]] = {
    "atualizar_ficha": AtualizarFicha, "classificar_experimento": ClassificarExperimento,
    "buscar_experimentos_similares": BuscarSimilares, "registrar_sinal_perfil": RegistrarSinal,
    "sugerir_respostas": SugerirRespostas, "solicitar_dados": SolicitarDados,
    "calcular_tamanho_amostra": CalcularAmostra, "apresentar_skills": ApresentarSkills,
    "encaminhar": Encaminhar,
}

PESOS = {"fraco": 6, "medio": 12, "forte": 20, "decisivo": 40}


# ------------------------------------------------------------- execução ----

class ToolContext:
    """Estado que as ferramentas podem ler e alterar (a sessão de conversa)."""

    def __init__(self, session: Any, corpus: Corpus):
        self.session = session
        self.corpus = corpus


Result = tuple[str, list[dict]]


def _ficha_event(session: Any, changed: list[str]) -> dict:
    return {"type": "ficha", "ficha": session.ficha.model_dump(exclude_none=True), "changed": changed,
            "faltantes": session.ficha.faltantes()}


def _atualizar(ctx: ToolContext, a: AtualizarFicha) -> Result:
    s = ctx.session
    changed = [k for k, v in a.model_dump(exclude_none=True).items()]
    data = s.ficha.model_dump()
    data.update({k: getattr(a, k) for k in changed})
    s.ficha = Ficha.model_validate(data)
    return (json.dumps({"ok": True, "faltantes": s.ficha.faltantes()}, ensure_ascii=False), [_ficha_event(s, changed)])


def _classificar(ctx: ToolContext, a: ClassificarExperimento) -> Result:
    s = ctx.session
    gp = GOLDEN.get(a.golden_path or "")
    s.ficha.tecnologia, s.ficha.tecnica, s.ficha.justificativa_tecnica = a.tecnologia, a.tecnica, a.justificativa
    s.ficha.golden_path = gp["id"] if gp else a.golden_path
    changed = ["tecnologia", "tecnica", "justificativa_tecnica", "golden_path"]
    if gp and not s.ficha.skills:
        s.ficha.skills = list(gp["skills"])
        changed.append("skills")
    card = {"type": "card", "kind": "tecnologia", "data": {**a.model_dump(), "golden_path_nome": gp["nome"] if gp else None}}
    out = {"ok": True, "golden_path": gp} if gp else {"ok": True, "aviso": "golden path não encontrado no catálogo"}
    return json.dumps(out, ensure_ascii=False), [_ficha_event(s, changed), card]


def _buscar(ctx: ToolContext, a: BuscarSimilares) -> Result:
    k = max(1, min(5, a.quantidade))
    hits = ctx.corpus.search(a.consulta, k=k, dominio=ctx.session.ficha.dominio)
    casos = [resumo_para_contexto(e) | {"relevancia": round(sc, 2)} for e, sc in hits]
    ctx.session.similares = [c["id"] for c in casos]
    event = {"type": "card", "kind": "similares", "data": [{"id": c["id"], "titulo": c.get("titulo"), "veredito": c.get("veredito"), "origem": c["origem"]} for c in casos]}
    payload = {"casos": casos} if casos else {"casos": [], "aviso": "nenhum experimento semelhante no histórico"}
    return json.dumps(payload, ensure_ascii=False), ([event] if casos else [])


def _sinal(ctx: ToolContext, a: RegistrarSinal) -> Result:
    s = ctx.session
    delta = PESOS[a.peso] * (1 if a.direcao == "desenvolvedor" else -1)
    s.perfil_score = max(4, min(96, s.perfil_score + delta))
    s.perfil_sinais.append(a.evidencia)
    if a.peso == "decisivo":
        s.perfil = a.direcao
    guess = ("Desenvolvedor" if s.perfil == "desenvolvedor" else "Área de negócio") if s.perfil else (
        "Provavelmente desenvolvedor" if s.perfil_score > 62 else "Provavelmente área de negócio" if s.perfil_score < 38 else "Ainda conhecendo você")
    return "ok", [{"type": "perfil", "score": s.perfil_score, "guess": guess, "sinais": s.perfil_sinais[-4:]}]


def _sugerir(ctx: ToolContext, a: SugerirRespostas) -> Result:
    return "ok", [{"type": "chips", "options": a.opcoes[:3]}]


def _solicitar(ctx: ToolContext, a: SolicitarDados) -> Result:
    ctx.session.aguardando_arquivo = True
    return "ok: o botão de anexo está visível para a pessoa", [{"type": "upload", "descricao": a.descricao, "formatos": a.formatos}]


def _calcular(ctx: ToolContext, a: CalcularAmostra) -> Result:
    n = tamanho_amostra_proporcao(a.margem, a.confianca)
    out: dict[str, Any] = {"tamanho_minimo": n, "margem": a.margem, "confianca": a.confianca}
    if a.registros_disponiveis is not None:
        out["registros_disponiveis"] = a.registros_disponiveis
        out["faltam"] = max(0, n - a.registros_disponiveis)
        out["margem_com_disponiveis"] = round(margem_para_n(a.registros_disponiveis, a.confianca), 4)
    return json.dumps(out), []


def _skills(ctx: ToolContext, a: ApresentarSkills) -> Result:
    s = ctx.session
    s.ficha.skills = [k.nome for k in a.skills]
    return "ok", [_ficha_event(s, ["skills"]), {"type": "card", "kind": "skills", "data": a.model_dump()}]


def _encaminhar(ctx: ToolContext, a: Encaminhar) -> Result:
    s = ctx.session
    faltam = [c for c in s.ficha.faltantes() if c != "execucao"]
    if faltam:
        return json.dumps({"ok": False, "erro": "a ficha ainda tem campos obrigatórios vazios", "faltantes": faltam}, ensure_ascii=False), []
    s.ficha.execucao = "laboratorio" if a.destino == "workflow" else "solicitante"
    s.encaminhamento = a.destino
    if s.perfil is None:
        s.perfil = "negocio" if a.destino == "workflow" else "desenvolvedor"
    events = [_ficha_event(s, ["execucao"]), {"type": "handoff", "destino": a.destino, "resumo": a.resumo,
                                              "ficha": s.ficha.model_dump(exclude_none=True)}]
    return "ok: encaminhado", events


HANDLERS: dict[str, Callable[[ToolContext, Any], Result]] = {
    "atualizar_ficha": _atualizar, "classificar_experimento": _classificar,
    "buscar_experimentos_similares": _buscar, "registrar_sinal_perfil": _sinal,
    "sugerir_respostas": _sugerir, "solicitar_dados": _solicitar,
    "calcular_tamanho_amostra": _calcular, "apresentar_skills": _skills, "encaminhar": _encaminhar,
}


def run_tool(ctx: ToolContext, name: str, raw_input: Any) -> tuple[dict, list[dict]]:
    """Valida e executa uma ferramenta. Devolve o bloco tool_result (sem id) e eventos."""
    model = INPUT_MODELS.get(name)
    if model is None:
        return {"content": f"ferramenta desconhecida: {name}", "is_error": True}, []
    try:
        args = model.model_validate(raw_input if isinstance(raw_input, dict) else {})
    except ValidationError as e:
        # Entrada truncada ou fora do esquema: devolve erro para o modelo corrigir.
        return {"content": json.dumps({"INVALID_INPUT": e.errors(include_url=False)}, ensure_ascii=False, default=str), "is_error": True}, []
    try:
        content, events = HANDLERS[name](ctx, args)
    except ValueError as e:
        return {"content": f"erro: {e}", "is_error": True}, []
    return {"content": content}, events
