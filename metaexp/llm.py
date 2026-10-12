"""Camada de acesso ao LiteLLM via API compatível com OpenAI.

Todos os agentes falam com o modelo por aqui, por meio de duas operações:

- `stream_turn`: um turno de conversa com ferramentas, transmitido token a token
  (usado pelo Agente Cientista no chat).
- `structured`: uma chamada que devolve um objeto Pydantic validado
  (usado pelos agentes da bancada, pelo gerador sintético e pelos avaliadores).

`LLM` é um protocolo: os testes usam um cliente falso com o mesmo formato, sem
rede. `AnthropicLLM` é o nome mantido por compatibilidade, mas a implementação
real fala com um proxy LiteLLM no formato OpenAI-compatible.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol, TypeVar

import httpx2
from pydantic import BaseModel

from metaexp.config import Settings, settings as default_settings

log = logging.getLogger("metaexp.llm")
T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"

# finish_reason (OpenAI) -> stop_reason que o laço do Cientista entende.
_STOP = {"stop": "end_turn", "tool_calls": "tool_use", "function_call": "tool_use",
         "length": "max_tokens", "content_filter": "refusal"}


def _compact_text(text: str, limit: int = 2000) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    out = "\n".join(lines)
    if len(out) > limit:
        out = out[:limit - 1].rstrip() + "…"
    return out


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

    content: list[dict]
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
    def __init__(self, cfg: Settings | None = None, client: httpx2.Client | None = None):
        self.cfg = cfg or default_settings
        self.base_url = (self.cfg.anthropic_base_url or "https://localhost:4000/v1").rstrip("/")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = client or httpx2.Client(base_url=self.base_url, headers=headers, timeout=120.0,
                                              verify=self.cfg.anthropic_verify_ssl)

    def _messages(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                out.append({"role": "system", "content": self._flatten(content)})
                continue
            if role == "user":
                if isinstance(content, list) and content and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    for block in content:
                        out.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id"),
                            "content": block.get("content", ""),
                        })
                    continue
                out.append({"role": "user", "content": self._flatten(content)})
                continue
            if role == "assistant":
                text_parts: list[str] = []
                tool_calls: list[dict] = []
                for block in content or []:
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(str(block.get("text", "")))
                    elif btype == "tool_use":
                        tool_calls.append({
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                            },
                        })
                item: dict[str, Any] = {"role": "assistant"}
                text = "".join(text_parts)
                if text:
                    item["content"] = text
                elif not tool_calls:
                    item["content"] = ""
                if tool_calls:
                    item["tool_calls"] = tool_calls
                out.append(item)
                continue
            out.append(msg)
        return out

    def _flatten(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
                    elif block.get("type") == "tool_result":
                        parts.append(str(block.get("content", "")))
                    else:
                        parts.append(str(block))
                else:
                    parts.append(str(block))
            return "".join(parts)
        if content is None:
            return ""
        return str(content)

    def _tools(self, tools: list[dict]) -> list[dict]:
        out: list[dict] = []
        for tool in tools:
            function = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool["input_schema"],
            }
            if tool.get("strict") is not None:
                function["strict"] = tool["strict"]
            out.append({"type": "function", "function": function})
        return out

    def _common(self, system: str, effort: str | None) -> dict:
        return {"model": self.cfg.model}

    def _conversa(self, system: str, messages: list[dict]) -> list[dict]:
        """Prompt de sistema primeiro; avisos de sistema no meio da conversa ficam onde estão."""
        return [{"role": "system", "content": system}, *self._messages(messages)] if system else self._messages(messages)

    def stream_turn(self, *, system: str, messages: list[dict], tools: list[dict],
                    effort: str | None = None) -> Iterator[TextDelta | TurnResult]:
        payload = {
            **self._common(system, effort),
            "messages": self._conversa(system, messages),
            "tools": self._tools(tools),
            "tool_choice": "auto",
            "stream": True,
        }
        with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            text_parts: list[str] = []
            tool_states: dict[int, dict[str, Any]] = {}
            usage: dict[str, Any] = {}
            finish_reason: str | None = None
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                else:
                    continue
                if data == "[DONE]":
                    break
                event = json.loads(data)
                choice = (event.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    text_parts.append(str(delta["content"]))
                for tool_call in delta.get("tool_calls") or []:
                    idx = int(tool_call.get("index", 0))
                    state = tool_states.setdefault(idx, {"id": None, "name": None, "arguments": []})
                    if tool_call.get("id"):
                        state["id"] = tool_call["id"]
                    function = tool_call.get("function") or {}
                    if function.get("name"):
                        state["name"] = function["name"]
                    if function.get("arguments"):
                        state["arguments"].append(function["arguments"])
                if choice.get("finish_reason") is not None:
                    finish_reason = choice.get("finish_reason")
                if event.get("usage"):
                    usage = event["usage"]

        content: list[dict] = []
        text = _compact_text("".join(text_parts))
        if text:
            yield TextDelta(text)
        if text_parts:
            content.append({"type": "text", "text": "".join(text_parts)})
        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_states):
            state = tool_states[idx]
            raw_args = "".join(state.get("arguments", [])) or "{}"
            try:
                parsed_args = json.loads(raw_args)
            except json.JSONDecodeError:
                parsed_args = {"raw": raw_args}
            tool_id = state.get("id") or f"toolu_{idx + 1}"
            tool_name = state.get("name") or "tool"
            content.append({"type": "tool_use", "id": tool_id, "name": tool_name, "input": parsed_args})
            tool_calls.append(ToolCall(tool_id, tool_name, parsed_args))
        stop_reason = _STOP.get(finish_reason or "", finish_reason) or ("tool_use" if tool_calls else "end_turn")
        yield TurnResult(content=content, stop_reason=stop_reason,
                         tool_calls=tool_calls, usage=usage)

    def structured(self, *, system: str, messages: list[dict], schema: type[T],
                   effort: str | None = None, max_tokens: int = 16000) -> T:
        payload = {
            **self._common(system, effort or self.cfg.effort_bench),
            "messages": self._conversa(system, messages),
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        }
        response = self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        refusal = message.get("refusal")
        if refusal:
            raise LLMRefusal(None, refusal)
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("o modelo não devolveu a saída estruturada esperada")
        try:
            return schema.model_validate_json(content)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"o modelo não devolveu JSON válido para {schema.__name__}") from exc
