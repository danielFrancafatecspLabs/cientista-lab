"""Bancada: o workflow de agentes que executa o experimento para a área de negócio.

A bancada só começa com a ficha aprovada pelo Lab (gate G0). Depois avança por
etapas e para sempre que precisa de uma decisão humana (liberar a amostra,
resolver um escalonamento). O front chama `avancar(sessao, decisao)` e recebe
eventos até a próxima parada:

  {"type": "etapa", "etapa": "amostra", "status": "run|wait|ok|bloqueada"}
  {"type": "mensagem", "agente": "dados", "texto": "..."}
  {"type": "card", "kind": "ficha|amostra|plano|rodada|parecer", "data": {...}}
  {"type": "aprovacao", "etapa": "...", "opcoes": [{"id": "...", "rotulo": "..."}]}
  {"type": "done", "state": {...}}
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from metaexp.config import Settings, settings as default_settings
from metaexp.prompts import ficha_json, system_bancada
from metaexp.llm import LLM
from metaexp.core.schemas import AnaliseAmostra, AvaliacaoQA, Parecer, PlanoTecnico, Resultados
from metaexp.sessions import Sessao
from metaexp.core.stats import tamanho_amostra_proporcao
from metaexp.agents.executor import Executor, ExecutorSimulado

log = logging.getLogger("metaexp.bancada")

ETAPAS = ["ficha", "amostra", "construcao", "qualidade", "resultado"]

PAPEIS = {
    "dados": ("Agente de Amostra e Dados",
              "Avalie se a amostra permite testar a hipótese da ficha (gate G1). Use os perfis dos arquivos enviados. "
              "Compare o volume com o tamanho mínimo informado. Reprove apenas se o experimento não puder gerar "
              "nem um resultado indicativo; aprove com ressalva quando o volume estiver abaixo do ideal."),
    "dev": ("Agente Desenvolvedor",
            "Proponha o plano técnico da solução a partir da ficha, da análise da amostra e do golden path. "
            "Quando receber feedback do QA, revise o plano atendendo a cada ponto, sem perder o que já estava certo."),
    "qa": ("Agente QA",
           "Avalie o plano técnico contra cada métrica e critério da ficha, como numa iteração do Ralph Loop. "
           "Liste um critério avaliado para cada métrica da ficha e para cada requisito explícito de dados e de "
           "saída. Seja exigente: marque como atendido só o que o plano cobre de forma concreta e verificável. "
           "O feedback deve dizer exatamente o que mudar."),
    "analista": ("Agente Analista",
                 "Compare os resultados com a hipótese, as metas e os critérios obrigatórios da ficha e dê o veredito "
                 "(gate G3). Se algum critério obrigatório não foi atendido, a hipótese não está validada. "
                 "Se os resultados forem simulados, diga isso no resumo."),
}


def _ev_etapa(etapa: str, status: str) -> dict:
    return {"type": "etapa", "etapa": etapa, "status": status}


def _ev_msg(agente: str, texto: str) -> dict:
    return {"type": "mensagem", "agente": agente, "texto": texto}


class Bancada:
    def __init__(self, llm: LLM, executor: Executor | None = None, cfg: Settings | None = None):
        self.llm = llm
        self.cfg = cfg or default_settings
        self.executor = executor or ExecutorSimulado(llm)
        self.systems = {k: system_bancada(*v) for k, v in PAPEIS.items()}

    def _call(self, papel: str, conteudo: str, schema):
        return self.llm.structured(system=self.systems[papel], messages=[{"role": "user", "content": conteudo}],
                                   schema=schema, effort=self.cfg.effort_bench)

    # --------------------------------------------------------------- API ----

    def avancar(self, s: Sessao, decisao: str | None = None, comentario: str | None = None) -> Iterator[dict]:
        b = s.bancada
        if s.encaminhamento != "workflow":
            yield {"type": "error", "message": "Este experimento não foi encaminhado para a bancada."}
            yield {"type": "done", "state": s.snapshot()}
            return
        try:
            if not b.iniciada:
                if s.status != "aprovado":
                    yield {"type": "aguardando", "motivo": "revisao_lab", "status": s.status,
                           "message": "A ficha ainda está com o Lab para revisão (G0)."}
                    yield {"type": "done", "state": s.snapshot()}
                    return
                b.iniciada = True
                s.mudar_status("em_execucao")
                yield from self._ficha_aprovada(s)
                yield from self._amostra(s)
            elif b.aguardando == "amostra":
                if decisao == "encerrar":
                    yield from self._encerrar(s, "Encerrado na etapa de amostra por falta de dados.")
                else:
                    yield from self._concluir("amostra", s)
                    yield from self._construcao_e_qualidade(s)
            elif b.aguardando == "qualidade":
                # Escalonamento após Kmax: o especialista orienta e o loop continua uma vez.
                yield from self._construcao_e_qualidade(s, orientacao=comentario or "Revise o plano atendendo a todo o feedback anterior.")
            else:
                yield {"type": "error", "message": "Nada a fazer: a bancada não espera uma decisão agora."}
        except Exception as e:  # noqa: BLE001 - a falha vira evento para o front
            log.exception("falha na bancada")
            yield {"type": "error", "message": f"Falha na etapa: {e}"}
        yield {"type": "done", "state": s.snapshot()}

    # ------------------------------------------------------------ etapas ----

    def _concluir(self, etapa: str, s: Sessao) -> Iterator[dict]:
        s.bancada.status[etapa] = "ok"
        s.bancada.aguardando = None
        yield _ev_etapa(etapa, "ok")

    def _esperar(self, etapa: str, s: Sessao, opcoes: list[tuple[str, str]]) -> Iterator[dict]:
        s.bancada.status[etapa] = "wait"
        s.bancada.aguardando = etapa
        s.bancada.etapa = ETAPAS.index(etapa)
        yield _ev_etapa(etapa, "wait")
        yield {"type": "aprovacao", "etapa": etapa, "opcoes": [{"id": i, "rotulo": r} for i, r in opcoes]}

    def _ficha_aprovada(self, s: Sessao) -> Iterator[dict]:
        rev = s.revisoes[-1] if s.revisoes else None
        nota = f" Comentário do Lab: {rev.comentario}" if rev and rev.comentario else ""
        yield _ev_msg("cientista", f"A ficha foi aprovada pelo Lab. Vamos começar, {s.nome}.{nota}")
        yield {"type": "card", "kind": "ficha", "data": s.ficha.model_dump(exclude_none=True)}
        yield from self._concluir("ficha", s)

    def _amostra(self, s: Sessao) -> Iterator[dict]:
        s.bancada.status["amostra"] = "run"
        yield _ev_etapa("amostra", "run")
        minimo = tamanho_amostra_proporcao()
        conteudo = (f"<ficha>\n{ficha_json(s.ficha)}\n</ficha>\n"
                    f"<perfis_arquivos>\n{json.dumps(s.arquivos, ensure_ascii=False)}\n</perfis_arquivos>\n"
                    f"<referencia>tamanho mínimo para proporção com E=0,05 e 95%: {minimo}</referencia>")
        analise = self._call("dados", conteudo, AnaliseAmostra)
        s.bancada.artefatos["amostra"] = analise.model_dump()
        texto = f"Conferi a amostra. {analise.resumo}"
        if analise.decisao_g1 == "reprovado":
            s.bancada.status["amostra"] = "bloqueada"
            yield _ev_msg("dados", texto + " Com estes dados não dá para testar a hipótese.")
            yield {"type": "card", "kind": "amostra", "data": analise.model_dump()}
            yield from self._esperar("amostra", s, [("encerrar", "Encerrar com aprendizado")])
            return
        yield _ev_msg("dados", texto + " Por enquanto está ok. Posso dar o próximo passo?")
        yield {"type": "card", "kind": "amostra", "data": analise.model_dump()}
        yield from self._esperar("amostra", s, [("seguir", "Pode seguir")])

    def _construcao_e_qualidade(self, s: Sessao, orientacao: str | None = None) -> Iterator[dict]:
        b = s.bancada
        analise = AnaliseAmostra.model_validate(b.artefatos["amostra"]) if "amostra" in b.artefatos else None
        base = (f"<ficha>\n{ficha_json(s.ficha)}\n</ficha>\n"
                f"<analise_amostra>\n{analise.model_dump_json() if analise else '{}'}\n</analise_amostra>")

        if "plano" not in b.artefatos:
            b.status["construcao"] = "run"
            yield _ev_etapa("construcao", "run")
            plano = self._call("dev", base, PlanoTecnico)
            b.artefatos["plano"] = plano.model_dump()
            yield _ev_msg("dev", f"Plano da solução pronto: {plano.abordagem}")
            yield {"type": "card", "kind": "plano", "data": plano.model_dump()}
            yield from self._concluir("construcao", s)
        plano = PlanoTecnico.model_validate(b.artefatos["plano"])

        # Ralph Loop: QA avalia, Desenvolvedor corrige, até Qk >= Qmin ou Kmax.
        b.status["qualidade"] = "run"
        b.aguardando = None
        yield _ev_etapa("qualidade", "run")
        if orientacao:
            plano = self._call("dev", base + f"\n<plano_atual>\n{plano.model_dump_json()}\n</plano_atual>\n"
                               f"<orientacao_especialista>\n{orientacao}\n</orientacao_especialista>", PlanoTecnico)
            b.artefatos["plano"] = plano.model_dump()
            yield _ev_msg("dev", "Apliquei a orientação do especialista. Voltando ao QA.")
        limite = len(b.rodadas) + (1 if orientacao else self.cfg.k_max)
        while len(b.rodadas) < limite:
            k = len(b.rodadas) + 1
            av = self._call("qa", base + f"\n<plano>\n{plano.model_dump_json()}\n</plano>\n<iteracao k=\"{k}\"/>", AvaliacaoQA)
            q = av.qualidade()
            rodada = {"k": k, "q": round(q, 3), "aderencia": round(av.aderencia(), 3), "e": av.executa_sem_erro,
                      "o": av.outputs_existem, "d": av.dados_validos, "feedback": av.feedback,
                      "criterios": [c.model_dump() for c in av.criterios]}
            b.rodadas.append(rodada)
            yield {"type": "card", "kind": "rodada", "data": rodada}
            if q >= self.cfg.q_min:
                yield _ev_msg("qa", f"Aprovado na rodada {k}: qualidade {round(q * 100)}%, acima da meta de {round(self.cfg.q_min * 100)}%.")
                yield from self._concluir("qualidade", s)
                yield from self._resultado(s, plano, analise)
                return
            if len(b.rodadas) < limite:
                plano = self._call("dev", base + f"\n<plano_atual>\n{plano.model_dump_json()}\n</plano_atual>\n"
                                   f"<feedback_qa>\n{json.dumps(av.feedback, ensure_ascii=False)}\n</feedback_qa>", PlanoTecnico)
                b.artefatos["plano"] = plano.model_dump()
                yield _ev_msg("dev", f"Rodada {k}: corrigi {len(av.feedback)} pontos apontados pelo QA.")
        yield _ev_msg("qa", f"Atingimos {len(b.rodadas)} rodadas sem chegar à meta de qualidade. Vou encaminhar a um especialista.")
        yield from self._esperar("qualidade", s, [("orientar", "Enviar orientação do especialista")])

    def _resultado(self, s: Sessao, plano: PlanoTecnico, analise: AnaliseAmostra | None) -> Iterator[dict]:
        b = s.bancada
        b.status["resultado"] = "run"
        yield _ev_etapa("resultado", "run")
        resultados: Resultados = self.executor.executar(s.ficha, plano, analise)
        b.artefatos["resultados"] = resultados.model_dump()
        conteudo = (f"<ficha>\n{ficha_json(s.ficha)}\n</ficha>\n<resultados>\n{resultados.model_dump_json()}\n</resultados>\n"
                    f"<rodadas_qa>{len(b.rodadas)}</rodadas_qa>")
        parecer = self._call("analista", conteudo, Parecer)
        b.artefatos["parecer"] = parecer.model_dump()
        yield _ev_msg("analista", f"Terminei a análise. {parecer.titulo}")
        yield {"type": "card", "kind": "parecer", "data": {**parecer.model_dump(), "resultados": resultados.model_dump()}}
        yield from self._concluir("resultado", s)
        s.mudar_status("parecer", parecer.veredito)

    def _encerrar(self, s: Sessao, motivo: str) -> Iterator[dict]:
        s.bancada.decisao_final = "encerrado"
        s.bancada.aguardando = None
        s.mudar_status("encerrado", motivo)
        yield _ev_msg("cientista", motivo + " O aprendizado fica registrado no histórico do laboratório.")
