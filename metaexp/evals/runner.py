"""Avaliação do Agente Cientista com solicitantes simulados.

Cada caso parte de um experimento do corpus. Um segundo modelo interpreta o
solicitante daquele experimento (perfil, problema, dados, estilo), sem ver a
ficha final, e conversa com o Cientista até o encaminhamento ou até o limite
de turnos. Depois comparamos o resultado com o gabarito do registro.

Métricas determinísticas: perfil detectado, encaminhamento coerente,
tecnologia, ficha completa, metas numéricas, número de turnos.
Métrica por juiz (LLM): rubrica de condução da conversa, de 1 a 5.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..agents.cientista import Cientista
from ..corpus.store import Corpus
from ..llm.client import LLM
from ..metodo import criterio_valido
from ..schemas import Experimento
from ..sessions import Sessao
from ..tools.profiling import PerfilArquivo

log = logging.getLogger("metaexp.evals")

SYSTEM_SOLICITANTE = """Você interpreta uma pessoa da empresa conversando com o Cientista do METAEXP para criar um experimento.
Responda como essa pessoa responderia: curto, em português do Brasil, no estilo indicado. Não revele tudo de uma vez;
responda ao que foi perguntado. Você só conhece os fatos do seu caso. Se o Cientista pedir um arquivo e você tiver
dados, marque `anexar_arquivo` como true. Quando ele perguntar quem executa, responda de acordo com o seu perfil:
área de negócio pede que o laboratório execute; desenvolvedor executa por conta própria."""

SYSTEM_JUIZ = """Você avalia a condução de uma conversa do Cientista do METAEXP, um agente que transforma o problema de
uma pessoa em uma ficha de experimento. Dê nota de 1 a 5 para cada critério, com uma justificativa curta.
Critérios: (1) faz uma pergunta por vez, em no máximo 5 linhas; (2) traz soluções vagas de volta para o problema;
(3) exige critério de aceite numérico para cada métrica; (4) trata a falta ou insuficiência de dados de forma honesta;
(5) adapta a linguagem ao perfil da pessoa; (6) segue o fluxo Problema → Impacto → Objetivo → Hipótese → Metodologia →
Amostra → Métricas → Critérios e não confunde objetivo com hipótese."""


class RespostaSimulada(BaseModel):
    texto: str
    anexar_arquivo: bool


class NotaCriterio(BaseModel):
    criterio: Literal["uma_pergunta_por_vez", "problema_antes_da_solucao", "criterios_numericos", "honestidade_dados", "adaptacao_perfil", "fluxo_do_metodo"]
    nota: int = Field(description="1 a 5")
    justificativa: str


class AvaliacaoJuiz(BaseModel):
    notas: list[NotaCriterio]


@dataclass
class ResultadoCaso:
    caso: str
    perfil_esperado: str
    perfil_detectado: str | None
    encaminhamento: str | None
    tecnologia_esperada: str | None
    tecnologia_obtida: str | None
    ficha_completa: bool
    metas_numericas: bool
    turnos: int
    regras_metodo: bool = False
    notas_juiz: dict[str, int] = field(default_factory=dict)
    erro: str | None = None

    @property
    def acertos(self) -> dict[str, bool]:
        destino = "workflow" if self.perfil_esperado == "negocio" else "desenvolvedor"
        return {
            "perfil": self.perfil_detectado == self.perfil_esperado,
            "encaminhamento": self.encaminhamento == destino,
            "tecnologia": self.tecnologia_obtida == self.tecnologia_esperada,
            "ficha_completa": self.ficha_completa,
            "metas_numericas": self.metas_numericas,
            "regras_metodo": self.regras_metodo,
        }


def _caso_para_solicitante(exp: Experimento) -> str:
    f = exp.ficha
    fatos = {
        "perfil": "área de negócio" if exp.perfil_solicitante == "negocio" else "desenvolvedor",
        "dominio": exp.dominio,
        "problema_como_voce_descreveria": f.problema,
        "quem_sente_o_problema": f.publico_afetado,
        "o_que_seria_sucesso": [m.descricao for m in f.metricas if m.obrigatoria],
        "dados_que_voce_tem": exp.descricao_amostra,
        "situacao_dos_dados": exp.situacao_dados,
    }
    estilo = next((t.texto for t in exp.conversa if t.papel == "solicitante"), "")
    return (f"<seu_caso>\n{json.dumps(fatos, ensure_ascii=False, indent=2)}\n</seu_caso>\n"
            f"<exemplo_do_seu_jeito_de_falar>{estilo}</exemplo_do_seu_jeito_de_falar>")


def _arquivo_simulado(exp: Experimento) -> PerfilArquivo:
    base = {"amostra_pequena": 160, "amostra_suficiente": 520, "dados_sensiveis": 300}.get(exp.situacao_dados, 0)
    return PerfilArquivo(nome="amostra.csv", formato="csv", registros=base, colunas=["id", "texto", "categoria", "data"],
                         completude=0.96, duplicadas=base // 40,
                         exemplos=[{"id": "1", "texto": exp.descricao_amostra[:160], "categoria": exp.dominio, "data": "2026-05-02"}],
                         observacoes=["contém dados pessoais"] if exp.situacao_dados == "dados_sensiveis" else [])


def _texto_assistente(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    return " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")


def rodar_caso(exp: Experimento, cientista: Cientista, llm_solicitante: LLM, juiz: LLM | None,
               max_turnos: int = 14) -> ResultadoCaso:
    s = Sessao(id=f"eval-{exp.id}", criada_em=datetime.now().isoformat(), nome="Ana")
    contexto = _caso_para_solicitante(exp)
    transcript: list[str] = []
    turnos = 0
    erro = None
    try:
        for _ in cientista.iniciar(s):
            pass
        while turnos < max_turnos and not s.encaminhamento:
            ultima = _texto_assistente(next(m for m in reversed(s.messages) if m["role"] == "assistant"))
            transcript.append(f"Cientista: {ultima}")
            r = llm_solicitante.structured(
                system=SYSTEM_SOLICITANTE,
                messages=[{"role": "user", "content": contexto + "\n<conversa>\n" + "\n".join(transcript) +
                           "\n</conversa>\nQual é a sua próxima resposta?"}],
                schema=RespostaSimulada, effort="low", max_tokens=2000)
            turnos += 1
            transcript.append(f"Pessoa: {r.texto}")
            if r.anexar_arquivo and s.aguardando_arquivo and exp.situacao_dados != "sem_dados":
                for _ in cientista.receber_arquivo(s, _arquivo_simulado(exp)):
                    pass
            else:
                for _ in cientista.responder(s, r.texto):
                    pass
    except Exception as e:  # noqa: BLE001
        erro = f"{type(e).__name__}: {e}"

    res = ResultadoCaso(
        caso=exp.id, perfil_esperado=exp.perfil_solicitante, perfil_detectado=s.perfil,
        encaminhamento=s.encaminhamento, tecnologia_esperada=exp.ficha.tecnologia, tecnologia_obtida=s.ficha.tecnologia,
        ficha_completa=s.ficha.completa(),
        metas_numericas=bool(s.ficha.metricas) and all(criterio_valido(m.criterio_aceite) for m in s.ficha.metricas),
        regras_metodo=not s.ficha.pendencias(),
        turnos=turnos, erro=erro)
    if juiz and transcript:
        av = juiz.structured(system=SYSTEM_JUIZ, messages=[{"role": "user", "content":
                             f"Perfil real da pessoa: {exp.perfil_solicitante}\n<conversa>\n" + "\n".join(transcript) + "\n</conversa>"}],
                             schema=AvaliacaoJuiz, effort="medium", max_tokens=4000)
        res.notas_juiz = {n.criterio: n.nota for n in av.notas}
    return res


def rodar(corpus: Corpus, llm: LLM, n: int = 5, saida: Path | None = None, usar_juiz: bool = True) -> dict:
    casos = [e for e in corpus.experiments if e.conversa][:n]
    cientista = Cientista(llm, corpus, effort="medium")
    resultados = []
    for exp in casos:
        log.info("avaliando %s", exp.id)
        # O próprio caso sai do corpus de busca, para o Cientista não "colar" a resposta.
        cientista.corpus = Corpus([e for e in corpus.experiments if e.id != exp.id])
        resultados.append(rodar_caso(exp, cientista, llm, llm if usar_juiz else None))
    agregado: dict[str, float] = {}
    for chave in ("perfil", "encaminhamento", "tecnologia", "ficha_completa", "metas_numericas", "regras_metodo"):
        agregado[chave] = sum(r.acertos[chave] for r in resultados) / len(resultados) if resultados else 0.0
    notas = [v for r in resultados for v in r.notas_juiz.values()]
    agregado["nota_juiz_media"] = sum(notas) / len(notas) if notas else 0.0
    agregado["turnos_medios"] = sum(r.turnos for r in resultados) / len(resultados) if resultados else 0.0
    out = {"data": datetime.now().isoformat(timespec="seconds"), "casos": len(resultados), "agregado": agregado,
           "resultados": [asdict(r) | {"acertos": r.acertos} for r in resultados]}
    if saida:
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
