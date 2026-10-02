"""Camada de acesso ao Claude.

Todos os agentes falam com o modelo por aqui, por meio de duas operações:

- `stream_turn`: um turno de conversa com ferramentas, transmitido token a token
  (usado pelo Agente Cientista no chat).
- `structured`: uma chamada que devolve um objeto Pydantic validado
  (usado pelos agentes da bancada, pelo gerador sintético e pelos avaliadores).

`LLM` é um protocolo: os testes usam um cliente falso com o mesmo formato, sem
rede. `AnthropicLLM` é a implementação real com o SDK oficial.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from ..config import Settings, settings as default_settings

log = logging.getLogger("metaexp.llm")
T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMRefusal(RuntimeError):
    """O modelo (e o fallback) recusou a solicitação."""

    def __init__(self, category: str | None, explanation: str | None):
        super().__init__(f"recusa do modelo ({category or 'sem categoria'}): {explanation or ''}")
        self.category = category
        self.explanation = explanation


# ------------------------------------------------------- eventos de turno ----

@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCall:
    id: str
    name: str
    input: Any


@dataclass
class TurnResult:
    """Resultado final de um turno: o conteúdo completo vai para o histórico."""

    content: list[dict]          # blocos do assistente, como dicts, para reenviar sem edição
    stop_reason: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    refusal_category: str | None = None


class LLM(Protocol):
    def stream_turn(self, *, system: str, messages: list[dict], tools: list[dict],
                    effort: str | None = None) -> Iterator[TextDelta | TurnResult]: ...

    def structured(self, *, system: str, messages: list[dict], schema: type[T],
                   effort: str | None = None, max_tokens: int = 16000) -> T: ...


# ------------------------------------------------------- implementação real ----

class AnthropicLLM:
    def __init__(self, cfg: Settings | None = None, client: anthropic.Anthropic | None = None):
        self.cfg = cfg or default_settings
        # Credenciais vêm do ambiente: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN
        # ou um perfil do `ant auth login`.
        self.client = client or anthropic.Anthropic()

    def _common(self, system: str, effort: str | None) -> dict:
        kw: dict[str, Any] = {
            "model": self.cfg.model,
            # Prompt de sistema estável e cacheado; nada volátil vai aqui.
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "output_config": {"effort": effort or self.cfg.effort_chat},
        }
        if self.cfg.use_fallbacks:
            kw["betas"] = [FALLBACK_BETA]
            kw["fallbacks"] = "default"
        return kw

    def stream_turn(self, *, system: str, messages: list[dict], tools: list[dict],
                    effort: str | None = None) -> Iterator[TextDelta | TurnResult]:
        kw = self._common(system, effort)
        with self.client.beta.messages.stream(
            max_tokens=64000,
            messages=messages,
            tools=tools,
            # Cache automático do último bloco: o histórico vira prefixo cacheado.
            cache_control={"type": "ephemeral"},
            **kw,
        ) as stream:
            for event in stream:
                if event.type == "text":
                    yield TextDelta(event.text)
            final = stream.get_final_message()

        data = final.to_dict()
        tool_calls = [ToolCall(b.id, b.name, b.input) for b in final.content if b.type == "tool_use"]
        refusal = None
        if final.stop_reason == "refusal" and final.stop_details:
            refusal = final.stop_details.category
        usage = data.get("usage", {})
        log.info("turno stop=%s in=%s out=%s cache_read=%s", final.stop_reason, usage.get("input_tokens"),
                 usage.get("output_tokens"), usage.get("cache_read_input_tokens"))
        yield TurnResult(content=data["content"], stop_reason=final.stop_reason,
                         tool_calls=tool_calls, usage=usage, refusal_category=refusal)

    def structured(self, *, system: str, messages: list[dict], schema: type[T],
                   effort: str | None = None, max_tokens: int = 16000) -> T:
        kw = self._common(system, effort or self.cfg.effort_bench)
        response = self.client.beta.messages.parse(
            max_tokens=max_tokens,
            messages=messages,
            output_format=schema,
            **kw,
        )
        if response.stop_reason == "refusal":
            d = response.stop_details
            raise LLMRefusal(d.category if d else None, d.explanation if d else None)
        if response.stop_reason == "max_tokens":
            raise RuntimeError(f"saída estruturada truncada em max_tokens={max_tokens}; aumente o limite")
        if response.parsed_output is None:
            raise RuntimeError("o modelo não devolveu a saída estruturada esperada")
        return response.parsed_output
