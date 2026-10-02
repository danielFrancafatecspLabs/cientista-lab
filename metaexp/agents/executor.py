"""Executores: quem roda a solução e mede os resultados.

Hoje o laboratório usa o `ExecutorSimulado`, que pede ao modelo resultados
plausíveis e marca tudo como simulado. O ponto de troca para execução real é
esta interface: um `ExecutorSandbox` deve gerar e rodar o código num ambiente
isolado (por exemplo, com a ferramenta de execução de código do Claude ou um
contêiner próprio) e devolver `Resultados(simulado=False, ...)` medidos.
"""

from __future__ import annotations

import json
from typing import Protocol

from ..context.builder import ficha_json, system_bancada
from ..llm.client import LLM
from ..schemas import AnaliseAmostra, Ficha, PlanoTecnico, Resultados


class Executor(Protocol):
    def executar(self, ficha: Ficha, plano: PlanoTecnico, analise: AnaliseAmostra | None) -> Resultados: ...


class ExecutorSimulado:
    PAPEL = "Executor simulado"
    INSTRUCOES = (
        "Gere resultados plausíveis para a execução do plano sobre a amostra descrita, como se o experimento "
        "tivesse rodado. Seja realista: nem todo experimento atinge as metas, e amostras pequenas geram resultados "
        "menos confiáveis. Preencha `simulado` como true e inclua uma métrica de resultado para cada métrica da ficha."
    )

    def __init__(self, llm: LLM):
        self.llm = llm
        self.system = system_bancada(self.PAPEL, self.INSTRUCOES)

    def executar(self, ficha: Ficha, plano: PlanoTecnico, analise: AnaliseAmostra | None) -> Resultados:
        msg = (f"<ficha>\n{ficha_json(ficha)}\n</ficha>\n<plano>\n{plano.model_dump_json()}\n</plano>\n"
               f"<analise_amostra>\n{analise.model_dump_json() if analise else 'não disponível'}\n</analise_amostra>")
        res = self.llm.structured(system=self.system, messages=[{"role": "user", "content": msg}], schema=Resultados)
        res.simulado = True
        return res


class ExecutorSandbox:
    """Execução real em sandbox. Ainda não implementado."""

    def executar(self, ficha: Ficha, plano: PlanoTecnico, analise: AnaliseAmostra | None) -> Resultados:
        raise NotImplementedError(
            "Conecte aqui o ambiente de execução isolado (execution_env da proposta) e devolva métricas medidas."
        )


def resultados_do_solicitante(texto_ou_json: str) -> Resultados:
    """Para o caminho do desenvolvedor: resultados enviados por quem executou."""
    data = json.loads(texto_ou_json)
    data["simulado"] = False
    return Resultados.model_validate(data)
