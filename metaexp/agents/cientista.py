"""Agente Cientista: o laço de conversa com ferramentas.

Um turno da pessoa pode gerar várias chamadas ao modelo (texto, ferramentas,
mais texto). Tudo sai como uma sequência de eventos que a API transmite ao
front por SSE:

  {"type": "text", "delta": "..."}         pedaço de texto do Cientista
  {"type": "ficha" | "perfil" | "card" | "chips" | "upload" | "handoff", ...}
  {"type": "error", "message": "..."}
  {"type": "done", "state": {...}}
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from ..context.builder import system_cientista
from ..context.golden_paths import BY_ID as GOLDEN
from ..corpus.store import Corpus
from ..llm.client import LLM, TextDelta, TurnResult
from ..sessions import Sessao
from ..tools.cientista_tools import TOOL_SPECS, ToolContext, run_tool
from ..tools.profiling import PerfilArquivo

log = logging.getLogger("metaexp.cientista")

ABERTURA = ("(A pessoa acabou de abrir o METAEXP. Nome: {nome}. "
            "Cumprimente pelo nome, apresente-se em uma frase e pergunte qual problema ela quer resolver.)")
MAX_ITERACOES = 8
MAX_JSON_RETRIES = 2


def _amostra_minima(sessao: Sessao) -> int:
    gp = GOLDEN.get(sessao.ficha.golden_path or "")
    if gp:
        digits = "".join(ch if ch.isdigit() else " " for ch in gp["amostra_minima"].replace(".", "")).split()
        if digits:
            return int(digits[0])
    return 385


class Cientista:
    def __init__(self, llm: LLM, corpus: Corpus, effort: str | None = None):
        self.llm = llm
        self.corpus = corpus
        self.effort = effort
        self.system = system_cientista()

    # ------------------------------------------------------------ entradas ----

    def iniciar(self, sessao: Sessao) -> Iterator[dict]:
        if sessao.messages:
            yield {"type": "done", "state": sessao.snapshot()}
            return
        yield from self._turno(sessao, ABERTURA.format(nome=sessao.nome))

    def responder(self, sessao: Sessao, texto: str) -> Iterator[dict]:
        yield from self._turno(sessao, texto)

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

    def _turno(self, sessao: Sessao, conteudo: str | list) -> Iterator[dict]:
        sessao.messages.append({"role": "user", "content": conteudo})
        ctx = ToolContext(sessao, self.corpus)
        json_retries = 0
        iteracao = 0
        while iteracao < MAX_ITERACOES:
            iteracao += 1
            result: TurnResult | None = None
            try:
                for ev in self.llm.stream_turn(system=self.system, messages=sessao.messages,
                                               tools=TOOL_SPECS, effort=self.effort):
                    if isinstance(ev, TextDelta):
                        yield {"type": "text", "delta": ev.text}
                    else:
                        result = ev
            except ValueError:
                # JSON de ferramenta que o SDK não conseguiu interpretar: reenvia o turno.
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
            if not result.tool_calls:
                break
            if result.stop_reason == "max_tokens":
                yield {"type": "error", "message": "A resposta ficou longa demais e foi cortada."}
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
