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

from metaexp.core import descoberta
from metaexp.corpus.golden_paths import BY_ID as GOLDEN
from metaexp.corpus.store import Corpus, resumo_para_contexto
from metaexp.core import kit
from metaexp.core.ficha_doc import markdown as ficha_markdown
from metaexp.core.metodo import hipotese_valida, metricas_validas, titulo_valido
from metaexp.core.papeis import jornada
from metaexp.core.schemas import Abordagem, DetalhesTecnicos, Ficha, Metrica, PerguntaGuia, ProtocoloAvaliacao
from metaexp.core.stats import margem_para_n, tamanho_amostra_proporcao


# ------------------------------------------------------- entradas validadas ----

DimensaoId = Literal["sintoma", "quem_sofre", "tamanho", "caso_concreto", "causas", "solucao_atual", "decisao",
                     "sucesso", "restricoes", "premissa_critica"]
TecnicaId = Literal["caso_concreto", "espelhar", "quem_mais", "quantificar", "custo_da_inacao", "cinco_porques",
                    "ja_tentaram", "decisao", "contrafactual", "criterio_de_parada", "premissa", "restricao"]


class AtualizacaoMapa(BaseModel):
    dimensao: DimensaoId
    entendimento: str
    profundidade: int = Field(ge=0, le=3)
    evidencia: Optional[str] = None


class PerguntaAtual(BaseModel):
    dimensao: DimensaoId
    tecnica: TecnicaId
    por_que: str


class MapearProblema(BaseModel):
    atualizacoes: list[AtualizacaoMapa] = Field(default_factory=list)
    pergunta_atual: Optional[PerguntaAtual] = None
    sintese_para_confirmar: Optional[str] = None
    sintese_confirmada: Optional[bool] = None


class AtualizarFicha(BaseModel):
    titulo: Optional[str] = None
    dominio: Optional[str] = None
    problema: Optional[str] = None
    publico_afetado: Optional[str] = None
    objetivo: Optional[str] = None
    hipotese: Optional[str] = None
    metodologia: Optional[str] = None
    metricas: Optional[list[Metrica]] = None
    dados: Optional[str] = None
    amostra: Optional[str] = None
    bo: Optional[str] = None
    sponsor: Optional[str] = None
    riscos: Optional[list[str]] = None


class GerarFicha(BaseModel):
    pass


class ClassificarExperimento(BaseModel):
    tecnologia: Literal["ia_generativa", "machine_learning", "estatistica", "visao_computacional", "automacao", "otimizacao", "outro"]
    tecnica: str
    justificativa: str
    golden_path: Optional[str] = None


class BuscarSimilares(BaseModel):
    consulta: str
    quantidade: int = 3


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


class ProporAbordagens(BaseModel):
    abordagens: list[Abordagem] = Field(min_length=2, max_length=4)
    justificativa_recomendacao: str


class RegistrarDesenho(BaseModel):
    stack: Optional[str] = None
    fontes_dados: Optional[str] = None
    restricoes: Optional[list[str]] = None
    baseline: Optional[str] = None
    abordagem_escolhida: Optional[str] = None
    avaliacao: Optional[ProtocoloAvaliacao] = None
    arquitetura: Optional[list[str]] = None
    riscos_tecnicos: Optional[list[str]] = None


class Encaminhar(BaseModel):
    destino: Literal["workflow", "desenvolvedor"]
    resumo: str


# --------------------------------------------------- esquemas para o modelo ----

def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


S = {"type": "string"}
METRICA = _obj({"nome": S, "descricao": S,
                "criterio_aceite": {"type": "string", "description": "Valor numérico com condição de sucesso, ex.: 'Acurácia ≥ 85%'"},
                "obrigatoria": {"type": "boolean"}},
               ["nome", "descricao", "criterio_aceite", "obrigatoria"])

DIMENSOES_ENUM = [d.id for d in descoberta.DIMENSOES]
TECNICAS_ENUM = list(descoberta.TECNICAS)
METRICA_TECNICA = _obj({"nome": {"type": "string", "description": "Ex.: recall@5, f1_macro, latencia_p95_ms"},
                        "alvo": {"type": "string", "description": "Meta com condição, ex.: '≥ 0,85' ou '< 2000 ms'"},
                        "baseline": {"type": "string", "description": "Valor de hoje, se conhecido"},
                        "liga_a": {"type": "string", "description": "Métrica de negócio da ficha que ela sustenta"}},
                       ["nome", "alvo"])

TOOL_SPECS: list[dict] = [
    {
        "name": "mapear_problema",
        "description": (
            "Registra o que você entendeu do problema no mapa de descoberta e diz qual dimensão aprofundar agora. "
            "Use depois de cada resposta que traga informação nova: uma atualização por dimensão tocada, com a "
            "profundidade honesta (0 vazio, 1 raso, 2 claro, 3 profundo com evidência) e a fala da pessoa como evidência. "
            "Em `pergunta_atual`, informe a dimensão e a técnica da pergunta que você está fazendo nesta mensagem e, em uma "
            "frase para a pessoa, por que ela importa. Use `sintese_para_confirmar` quando o problema estiver claro, para a "
            "pessoa confirmar seu entendimento antes da hipótese; `sintese_confirmada` quando ela confirmar."),
        "input_schema": _obj({
            "atualizacoes": {"type": "array", "items": _obj({
                "dimensao": {"type": "string", "enum": DIMENSOES_ENUM},
                "entendimento": {"type": "string", "description": "O que você entendeu, em uma ou duas frases"},
                "profundidade": {"type": "integer", "enum": [0, 1, 2, 3]},
                "evidencia": {"type": "string", "description": "Fala ou número trazido pela pessoa"},
            }, ["dimensao", "entendimento", "profundidade"])},
            "pergunta_atual": _obj({
                "dimensao": {"type": "string", "enum": DIMENSOES_ENUM},
                "tecnica": {"type": "string", "enum": TECNICAS_ENUM},
                "por_que": {"type": "string", "description": "Uma frase, dirigida à pessoa, dizendo por que a pergunta importa"},
            }, ["dimensao", "tecnica", "por_que"]),
            "sintese_para_confirmar": {"type": "string", "description": "Seu entendimento do problema em até 4 frases, nas palavras da pessoa"},
            "sintese_confirmada": {"type": "boolean"},
        }, []),
    },
    {
        "name": "atualizar_ficha",
        "description": "Atualiza campos da ficha do experimento assim que ficarem claros na conversa. Envie apenas os campos que mudaram. `metricas` substitui a lista inteira. A resposta traz as pendências do checklist de qualidade mínima.",
        "input_schema": _obj({
            "titulo": {"type": "string", "description": "Nome do experimento: no máximo 3 palavras"},
            "dominio": {"type": "string", "enum": ["rede", "atendimento", "digital", "financeiro", "suprimentos", "juridico", "rh", "marketing", "operacoes", "outro"]},
            "problema": S,
            "publico_afetado": {"type": "string", "description": "Impacto: quem sente o problema e quanto custa hoje"},
            "objetivo": {"type": "string", "description": "O que será realizado"},
            "hipotese": {"type": "string", "description": "Acreditamos que [ação] irá gerar [resultado mensurável] para [contexto]. Máximo 2 linhas"},
            "metodologia": {"type": "string", "description": "Como o experimento será conduzido"},
            "metricas": {"type": "array", "items": METRICA},
            "dados": S, "amostra": S,
            "bo": {"type": "string", "description": "Responsável pelo experimento (BO)"},
            "sponsor": {"type": "string", "description": "Patrocinador (SPONSOR)"},
            "riscos": {"type": "array", "items": S},
        }, []),
    },
    {
        "name": "gerar_ficha",
        "description": "Gerador de Ficha de Experimentação. Valida o checklist de qualidade mínima e, se estiver completo, gera a ficha final e mostra à pessoa. Se houver pendências, devolve a lista e não gera.",
        "input_schema": _obj({}, []),
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
        "name": "propor_abordagens",
        "description": "Mostra à pessoa de 2 a 4 abordagens técnicas para o problema, com prós, contras, custo, latência, complexidade e qual você recomenda.",
        "input_schema": _obj({
            "abordagens": {"type": "array", "items": _obj({
                "nome": S, "descricao": S, "pros": {"type": "array", "items": S}, "contras": {"type": "array", "items": S},
                "custo": {"type": "string", "description": "Ex.: 'R$ 0,03 por consulta'"},
                "latencia": {"type": "string", "description": "Ex.: 'p95 ≈ 1,5 s'"},
                "complexidade": {"type": "string", "enum": ["baixa", "media", "alta"]},
                "recomendada": {"type": "boolean"},
            }, ["nome", "descricao", "pros", "contras", "custo", "latencia", "complexidade", "recomendada"])},
            "justificativa_recomendacao": S,
        }, ["abordagens", "justificativa_recomendacao"]),
    },
    {
        "name": "registrar_desenho_tecnico",
        "description": "Registra o desenho técnico: stack, fontes de dados, restrições, baseline, abordagem escolhida, protocolo de avaliação (conjunto, divisão, métricas técnicas com alvo e baseline, gate de regressão), arquitetura e riscos. Envie só os campos que mudaram; `avaliacao` substitui o protocolo inteiro. O protocolo vira o CI do kit do experimento.",
        "input_schema": _obj({
            "stack": S, "fontes_dados": {"type": "string", "description": "Sistemas, formatos, volume e atualização"},
            "restricoes": {"type": "array", "items": S}, "baseline": {"type": "string", "description": "O que existe hoje e seu desempenho"},
            "abordagem_escolhida": S,
            "avaliacao": _obj({
                "conjunto": {"type": "string", "description": "De onde vêm os casos de teste e como são rotulados"},
                "tamanho": {"type": "integer", "description": "Número de casos no conjunto de avaliação"},
                "divisao": {"type": "string", "description": "Ex.: teste congelado de 20%, sem vazamento por cliente"},
                "metricas": {"type": "array", "items": METRICA_TECNICA},
                "gate_regressao": {"type": "string", "description": "Quando uma mudança é bloqueada no CI"},
            }, ["conjunto", "metricas"]),
            "arquitetura": {"type": "array", "items": {"type": "string", "description": "Componente da solução"}},
            "riscos_tecnicos": {"type": "array", "items": S},
        }, []),
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
    "mapear_problema": MapearProblema, "atualizar_ficha": AtualizarFicha, "classificar_experimento": ClassificarExperimento,
    "buscar_experimentos_similares": BuscarSimilares,
    "sugerir_respostas": SugerirRespostas, "solicitar_dados": SolicitarDados,
    "calcular_tamanho_amostra": CalcularAmostra, "apresentar_skills": ApresentarSkills,
    "encaminhar": Encaminhar, "gerar_ficha": GerarFicha,
    "propor_abordagens": ProporAbordagens, "registrar_desenho_tecnico": RegistrarDesenho,
}



# ------------------------------------------------------------- execução ----

class ToolContext:
    """Estado que as ferramentas podem ler e alterar (a sessão de conversa)."""

    def __init__(self, session: Any, corpus: Corpus, revisao_lab: bool = True):
        self.session = session
        self.corpus = corpus
        self.revisao_lab = revisao_lab


Result = tuple[str, list[dict]]


def _ficha_event(session: Any, changed: list[str]) -> dict:
    return {"type": "ficha", "ficha": session.ficha.model_dump(exclude_none=True), "changed": changed,
            "pendencias": session.ficha.pendencias(), "gerada": session.ficha_gerada}


def _mapa_event(session: Any) -> dict:
    return {"type": "mapa", "mapa": descoberta.para_front(session.mapa)}


def _mapear(ctx: ToolContext, a: MapearProblema) -> Result:
    s = ctx.session
    for u in a.atualizacoes:
        descoberta.atualizar(s.mapa, u.dimensao, u.entendimento, u.profundidade, u.evidencia)
    events: list[dict] = []
    if a.pergunta_atual:
        s.mapa.pergunta_atual = PerguntaGuia(**a.pergunta_atual.model_dump())
        events.append({"type": "porque", **a.pergunta_atual.model_dump(),
                       "tecnica_nome": descoberta.TECNICAS[a.pergunta_atual.tecnica][0],
                       "dimensao_nome": descoberta.POR_ID[a.pergunta_atual.dimensao].nome})
    if a.sintese_para_confirmar:
        s.mapa.sintese, s.mapa.sintese_confirmada = a.sintese_para_confirmar, False
        events.append({"type": "card", "kind": "sintese", "data": {"texto": a.sintese_para_confirmar}})
    if a.sintese_confirmada is not None and s.mapa.sintese:
        s.mapa.sintese_confirmada = a.sintese_confirmada
    events.insert(0, _mapa_event(s))
    return json.dumps(descoberta.orientacao(s.mapa), ensure_ascii=False), events


def _atualizar(ctx: ToolContext, a: AtualizarFicha) -> Result:
    s = ctx.session
    changed = [k for k, v in a.model_dump(exclude_none=True).items()]
    data = s.ficha.model_dump()
    data.update({k: getattr(a, k) for k in changed})
    s.ficha = Ficha.model_validate(data)
    if s.ficha_gerada and changed:
        s.ficha_gerada = False   # mudou depois de gerada: precisa gerar de novo
    # Avisos imediatos sobre os campos recém-alterados, para corrigir já neste turno.
    avisos: list[str] = []
    if "hipotese" in changed:
        avisos += hipotese_valida(s.ficha.hipotese)
        if not descoberta.pronto_para_hipotese(s.mapa):
            falta = ", ".join(d.nome.lower() for d in descoberta.lacunas(s.mapa)[:3])
            avisos.append(f"o mapa do problema ainda está raso ({falta or 'cobertura baixa'}): confirme com a pessoa antes de fechar a hipótese")
    if "titulo" in changed:
        avisos += titulo_valido(s.ficha.titulo)
    if "metricas" in changed:
        avisos += metricas_validas(s.ficha.metricas)
    out = {"ok": not avisos, "avisos": avisos, "pendencias": s.ficha.pendencias()}
    return json.dumps(out, ensure_ascii=False), [_ficha_event(s, changed)]


def _gerar(ctx: ToolContext, a: GerarFicha) -> Result:
    s = ctx.session
    pend = s.ficha.pendencias()
    if pend:
        return json.dumps({"ok": False, "erro": "ficha não gerada: o checklist de qualidade mínima tem pendências",
                           "pendencias": pend}, ensure_ascii=False), []
    s.ficha_gerada = True
    s.ficha_versao += 1
    s.registrar("ficha_gerada", f"versão {s.ficha_versao}")
    doc = ficha_markdown(s.ficha, s.ficha_versao)
    card = {"type": "card", "kind": "ficha_gerada", "data": {"ficha": s.ficha.model_dump(exclude_none=True),
                                                            "versao": s.ficha_versao, "markdown": doc}}
    return json.dumps({"ok": True, "versao": s.ficha_versao}), [_ficha_event(s, []), card]


def _classificar(ctx: ToolContext, a: ClassificarExperimento) -> Result:
    s = ctx.session
    gp = GOLDEN.get(a.golden_path or "")
    s.ficha.tecnologia, s.ficha.tecnica, s.ficha.justificativa_tecnica = a.tecnologia, a.tecnica, a.justificativa
    s.ficha.golden_path = gp["id"] if gp else a.golden_path
    changed = ["tecnologia", "tecnica", "justificativa_tecnica", "golden_path"]
    if gp and not s.ficha.skills:
        s.ficha.skills = list(gp["skills"])
        changed.append("skills")
    out = {"ok": True, "golden_path": gp} if gp else {"ok": True, "aviso": "golden path não encontrado no catálogo"}
    events = [_ficha_event(s, changed)]
    if s.papel == "desenvolvedor":
        events.append({"type": "card", "kind": "tecnologia", "data": {**a.model_dump(), "golden_path_nome": gp["nome"] if gp else None}})
    else:
        out["lembrete"] = "registrado na ficha; não explique a técnica para o solicitante"
    return json.dumps(out, ensure_ascii=False), events


def _buscar(ctx: ToolContext, a: BuscarSimilares) -> Result:
    k = max(1, min(5, a.quantidade))
    hits = ctx.corpus.search(a.consulta, k=k, dominio=ctx.session.ficha.dominio)
    casos = [resumo_para_contexto(e) | {"relevancia": round(sc, 2)} for e, sc in hits]
    ctx.session.similares = [c["id"] for c in casos]
    event = {"type": "card", "kind": "similares", "data": [{"id": c["id"], "titulo": c.get("titulo"), "veredito": c.get("veredito"), "origem": c["origem"]} for c in casos]}
    payload = {"casos": casos} if casos else {"casos": [], "aviso": "nenhum experimento semelhante no histórico"}
    return json.dumps(payload, ensure_ascii=False), ([event] if casos else [])


def _detalhes(s: Any) -> DetalhesTecnicos:
    if s.ficha.detalhes_tecnicos is None:
        s.ficha.detalhes_tecnicos = DetalhesTecnicos()
    return s.ficha.detalhes_tecnicos


def _abordagens(ctx: ToolContext, a: ProporAbordagens) -> Result:
    s = ctx.session
    d = _detalhes(s)
    d.abordagens = a.abordagens
    rec = next((x.nome for x in a.abordagens if x.recomendada), None)
    card = {"type": "card", "kind": "abordagens", "data": {**a.model_dump(), "recomendada": rec}}
    return json.dumps({"ok": True, "recomendada": rec}, ensure_ascii=False), [_ficha_event(s, ["detalhes_tecnicos"]), card]


def _desenho(ctx: ToolContext, a: RegistrarDesenho) -> Result:
    s = ctx.session
    d = _detalhes(s)
    changed = list(a.model_dump(exclude_none=True))
    for k in changed:
        setattr(d, k, getattr(a, k))
    if s.ficha_gerada and changed:
        s.ficha_gerada = False
    events = [_ficha_event(s, ["detalhes_tecnicos"])]
    if "avaliacao" in changed:
        events.append({"type": "card", "kind": "avaliacao", "data": d.avaliacao.model_dump() | {"baseline": d.baseline}})
    if "arquitetura" in changed:
        events.append({"type": "card", "kind": "desenho", "data": d.model_dump(exclude={"abordagens", "avaliacao"})})
    out: dict[str, Any] = {"ok": True, "desenho_incompleto": d.pendencias()}
    if d.avaliacao:
        sem_meta = [m.nome for m in d.avaliacao.metricas if kit.meta_numerica(m.alvo) is None]
        if sem_meta:
            out["aviso"] = f"alvo sem número e condição (o CI não consegue checar): {', '.join(sem_meta)}"
    return json.dumps(out, ensure_ascii=False), events


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
    if s.status != "conversa":
        return json.dumps({"ok": False, "erro": f"a ficha já foi encaminhada (status: {s.status})"}, ensure_ascii=False), []
    if not s.ficha_gerada:
        return json.dumps({"ok": False, "erro": "gere a ficha com gerar_ficha antes de encaminhar",
                           "pendencias": s.ficha.pendencias()}, ensure_ascii=False), []
    destinos = jornada(s.papel).destinos
    if a.destino not in destinos:
        return json.dumps({"ok": False, "erro": f"na jornada de {s.papel} o encaminhamento é para: {', '.join(destinos)}"},
                          ensure_ascii=False), []
    faltam = [c for c in s.ficha.faltantes() if c != "execucao"]
    if s.papel == "solicitante":
        faltam = [c for c in faltam if c != "skills"]   # skills são decisão do laboratório
    if faltam:
        return json.dumps({"ok": False, "erro": "a ficha ainda tem campos obrigatórios vazios", "faltantes": faltam}, ensure_ascii=False), []
    s.ficha.execucao = "laboratorio" if a.destino == "workflow" else "solicitante"
    s.encaminhamento = a.destino
    s.mudar_status("em_revisao", a.resumo)
    if not ctx.revisao_lab:
        s.mudar_status("aprovado", "revisão do Lab desativada")
    handoff = {"type": "handoff", "destino": a.destino, "resumo": a.resumo, "status": s.status,
               "ficha": s.ficha.model_dump(exclude_none=True), "markdown": ficha_markdown(s.ficha, s.ficha_versao)}
    if a.destino == "desenvolvedor":
        handoff["kit"] = sorted(kit.arquivos(s.ficha, s.ficha_versao))
    proximo = ("a ficha foi para a revisão do Lab (G0); diga isso à pessoa em uma frase" if s.status == "em_revisao"
               else "ficha aprovada automaticamente")
    return f"ok: encaminhado; {proximo}", [_ficha_event(s, ["execucao"]), handoff]


HANDLERS: dict[str, Callable[[ToolContext, Any], Result]] = {
    "mapear_problema": _mapear, "atualizar_ficha": _atualizar, "classificar_experimento": _classificar,
    "buscar_experimentos_similares": _buscar,
    "sugerir_respostas": _sugerir, "solicitar_dados": _solicitar,
    "calcular_tamanho_amostra": _calcular, "apresentar_skills": _skills, "encaminhar": _encaminhar,
    "gerar_ficha": _gerar, "propor_abordagens": _abordagens, "registrar_desenho_tecnico": _desenho,
}


def tools_for(papel: str) -> list[dict]:
    """Ferramentas que o Cientista recebe na jornada do papel, em ordem estável (cache)."""
    permitidas = set(jornada(papel).ferramentas)
    return [t for t in TOOL_SPECS if t["name"] in permitidas]


def run_tool(ctx: ToolContext, name: str, raw_input: Any) -> tuple[dict, list[dict]]:
    """Valida e executa uma ferramenta. Devolve o bloco tool_result (sem id) e eventos."""
    model = INPUT_MODELS.get(name)
    if model is None or name not in jornada(ctx.session.papel).ferramentas:
        return {"content": f"ferramenta indisponível nesta jornada: {name}", "is_error": True}, []
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
