"""Agente Cientista: o laço de conversa com ferramentas.

Um turno da pessoa pode gerar várias chamadas ao modelo (texto, ferramentas,
mais texto). Tudo sai como uma sequência de eventos que a API transmite ao
front por SSE (contrato completo em `web/src/api/types.ts`):

  {"type": "text", "delta": "..."}              pedaço de texto do Cientista
  {"type": "mapa" | "porque" | "ficha" | "card" | "chips" | "upload" | "handoff", ...}
  {"type": "auto_ingestao"} | {"type": "retry"}
  {"type": "error", "message": "..."}
  {"type": "done", "state": {...}}
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from metaexp.agents.ferramentas import ToolContext, run_tool, tools_for
from metaexp.core.metodo import precisa_auto_ingestao
from metaexp.core.papeis import jornada
from metaexp.core.profiling import PerfilArquivo
from metaexp.corpus.golden_paths import BY_ID as GOLDEN
from metaexp.corpus.store import Corpus
from metaexp.llm import LLM, TextDelta, TurnResult
from metaexp.prompts import system_cientista
from metaexp.sessions import Sessao

log = logging.getLogger("metaexp.cientista")

ABERTURA = ("<abertura>\nA pessoa acabou de abrir o METAEXP.\nNome: {nome}\nPapel: {papel} ({descricao})\n"
            "Preferências:\n{preferencias}\n</abertura>\n"
            "Cumprimente pelo nome, diga em uma frase o que vamos construir juntos e faça a primeira pergunta.")
RETOMADA = "Voltei para ajustar a ficha conforme a revisão do Lab."
MAX_ITERACOES = 10
MAX_JSON_RETRIES = 2


def _amostra_minima(sessao: Sessao) -> int:
    gp = GOLDEN.get(sessao.ficha.golden_path or "")
    if gp:
        digits = "".join(ch if ch.isdigit() else " " for ch in gp["amostra_minima"].replace(".", "")).split()
        if digits:
            return int(digits[0])
    return 385


class Cientista:
    def __init__(self, llm: LLM, corpus: Corpus, effort: str | None = None, revisao_lab: bool = True):
        self.llm = llm
        self.corpus = corpus
        self.effort = effort
        self.revisao_lab = revisao_lab

    # ------------------------------------------------------------ entradas ----

    def iniciar(self, sessao: Sessao) -> Iterator[dict]:
        if sessao.messages:
            yield {"type": "done", "state": sessao.snapshot()}
            return
        j = jornada(sessao.papel)
        yield from self._turno(sessao, ABERTURA.format(nome=sessao.nome, papel=j.nome, descricao=j.descricao,
                                                       preferencias=j.descreve_preferencias(sessao.preferencias)))

    def responder(self, sessao: Sessao, texto: str) -> Iterator[dict]:
        aviso = None
        if precisa_auto_ingestao(texto):
            pend = sessao.ficha.pendencias()
            aviso = ("AUTO-INGESTÃO: a mensagem anterior é um texto longo ou estruturado. Extraia de uma vez tudo o que "
                     "ela traz: registre o entendimento do problema com mapear_problema e os campos da ficha com "
                     "atualizar_ficha. Depois, se faltar algo, pergunte só pelo item ausente de maior valor. Não gere a "
                     f"ficha com pendências. Pendências antes desta mensagem: {'; '.join(pend) if pend else 'nenhuma'}.")
        yield from self._turno(sessao, texto, aviso_sistema=aviso)

    def retomar(self, sessao: Sessao) -> Iterator[dict]:
        """O Lab devolveu a ficha: a conversa volta com o feedback como instrução do operador."""
        rev = sessao.feedback_pendente()
        if rev is None:
            yield {"type": "error", "message": "Não há revisão do Lab pendente para esta ficha."}
            yield {"type": "done", "state": sessao.snapshot()}
            return
        sessao.ficha_gerada = False
        sessao.mudar_status("conversa", "retomada após revisão do Lab")
        aviso = ("REVISÃO DO LAB: a ficha versão {v} foi devolvida pelo Lab com o comentário abaixo. Explique à pessoa, "
                 "em linguagem simples e em até três frases, o que precisa mudar e por quê, e conduza os ajustes um de "
                 "cada vez. Depois gere a ficha de novo e encaminhe.\n<comentario_lab>\n{c}\n</comentario_lab>"
                 ).format(v=rev.versao_ficha, c=rev.comentario or "(sem comentário)")
        if sessao.pre_revisao and sessao.pre_revisao.ajustes_sugeridos:
            aviso += "\n<ajustes_sugeridos_pelo_revisor>\n" + "\n".join(f"- {a}" for a in sessao.pre_revisao.ajustes_sugeridos) + \
                     "\n</ajustes_sugeridos_pelo_revisor>"
        yield from self._turno(sessao, RETOMADA, aviso_sistema=aviso)

    def receber_arquivo(self, sessao: Sessao, perfil: PerfilArquivo) -> Iterator[dict]:
        sessao.arquivos.append(perfil.to_dict())
        sessao.aguardando_arquivo = False
        total = sum(a["registros"] for a in sessao.arquivos)
        minimo = _amostra_minima(sessao)
        yield {"type": "card", "kind": "amostra", "data": {
            **perfil.to_dict(), "total_registros": total, "minimo": minimo, "arquivos": len(sessao.arquivos)}}
        conteudo = (
            f"<arquivo_anexado>\n{json.dumps(perfil.to_dict(), ensure_ascii=False)}\n</arquivo_anexado>\n"
            f"<total_acumulado registros=\"{total}\" arquivos=\"{len(sessao.arquivos)}\" referencia_minima=\"{minimo}\"/>\n"
            f"Anexei o arquivo {perfil.nome}."
        )
        yield from self._turno(sessao, conteudo)

    # --------------------------------------------------------------- laço ----

    def _turno(self, sessao: Sessao, conteudo: str | list, aviso_sistema: str | None = None) -> Iterator[dict]:
        sessao.messages.append({"role": "user", "content": conteudo})
        if aviso_sistema:
            # Mensagem de sistema no meio da conversa: instrução do operador, sem
            # invalidar o prefixo cacheado e sem misturar com a fala da pessoa.
            sessao.messages.append({"role": "system", "content": aviso_sistema})
            if aviso_sistema.startswith("AUTO-INGESTÃO"):
                yield {"type": "auto_ingestao"}
        ctx = ToolContext(sessao, self.corpus, revisao_lab=self.revisao_lab)
        system, tools = system_cientista(sessao.papel), tools_for(sessao.papel)
        json_retries = 0
        iteracao = 0
        while iteracao < MAX_ITERACOES:
            iteracao += 1
            result: TurnResult | None = None
            try:
                for ev in self.llm.stream_turn(system=system, messages=sessao.messages, tools=tools, effort=self.effort):
                    if isinstance(ev, TextDelta):
                        yield {"type": "text", "delta": ev.text}
                    else:
                        result = ev
            except ValueError:
                # JSON de ferramenta que o SDK não conseguiu interpretar: refaz a chamada.
                json_retries += 1
                yield {"type": "retry"}  # o front descarta o texto parcial desta tentativa
                if json_retries > MAX_JSON_RETRIES:
                    yield {"type": "error", "message": "O Cientista se confundiu ao preencher uma ferramenta. Tente reformular."}
                    break
                iteracao -= 1
                continue
            json_retries = 0
            assert result is not None
            sessao.somar_uso(result.usage)

            if result.stop_reason == "refusal":
                yield {"type": "error", "message": "Não consigo ajudar com esse pedido. Tente descrever o problema de outra forma."}
                if result.content:
                    sessao.messages.append({"role": "assistant", "content": result.content})
                break

            sessao.messages.append({"role": "assistant", "content": result.content})

            if result.stop_reason == "pause_turn":
                continue
            if result.stop_reason == "max_tokens":
                if result.tool_calls:
                    # Entradas possivelmente truncadas: não executa, mas fecha cada chamada
                    # para o histórico continuar válido no próximo turno.
                    sessao.messages.append({"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": c.id, "is_error": True,
                         "content": "não executada: resposta cortada em max_tokens"} for c in result.tool_calls]})
                yield {"type": "error", "message": "A resposta ficou longa demais e foi cortada."}
                break
            if not result.tool_calls:
                break

            tool_results = []
            for call in result.tool_calls:
                block, events = run_tool(ctx, call.name, call.input)
                tool_results.append({"type": "tool_result", "tool_use_id": call.id, **block})
                yield from events
            # Todos os resultados no mesmo turno de usuário.
            sessao.messages.append({"role": "user", "content": tool_results})
        else:
            yield {"type": "error", "message": "O Cientista atingiu o limite de passos neste turno."}

        yield {"type": "done", "state": sessao.snapshot()}
