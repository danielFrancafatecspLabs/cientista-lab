"""Cliente de modelo falso para testes: roteiros determinísticos, sem rede."""

from __future__ import annotations

import itertools
from typing import Callable, Iterator

from metaexp.llm import TextDelta, ToolCall, TurnResult

_ids = itertools.count(1)


def turno(texto: str = "", ferramentas: list[tuple[str, dict]] | None = None) -> list:
    """Monta a saída de uma chamada stream_turn: deltas de texto + resultado final."""
    ferramentas = ferramentas or []
    content: list[dict] = []
    if texto:
        content.append({"type": "text", "text": texto})
    calls = []
    for nome, entrada in ferramentas:
        tid = f"toolu_{next(_ids)}"
        content.append({"type": "tool_use", "id": tid, "name": nome, "input": entrada})
        calls.append(ToolCall(tid, nome, entrada))
    eventos: list = [TextDelta(p + " ") for p in texto.split(" ") if p]
    eventos.append(TurnResult(content=content, stop_reason="tool_use" if calls else "end_turn", tool_calls=calls,
                              usage={"input_tokens": 10, "output_tokens": 5}))
    return eventos


class FakeLLM:
    def __init__(self, turnos: list[list] | None = None, estruturados: dict[str, Callable] | None = None):
        self.turnos = list(turnos or [])
        self.estruturados = estruturados or {}
        self.chamadas: list[dict] = []

    def stream_turn(self, *, system, messages, tools, effort=None) -> Iterator:
        # Copia rasa: o histórico real continua crescendo depois desta chamada.
        self.chamadas.append({"tipo": "turno", "messages": list(messages), "tools": [t["name"] for t in tools]})
        roteiro = self.turnos.pop(0) if self.turnos else turno("ok")
        yield from roteiro

    def structured(self, *, system, messages, schema, effort=None, max_tokens=16000):
        self.chamadas.append({"tipo": "estruturado", "schema": schema.__name__})
        fn = self.estruturados.get(schema.__name__)
        if fn is None:
            raise AssertionError(f"sem resposta falsa para {schema.__name__}")
        return fn(messages)
