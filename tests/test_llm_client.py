"""Confere o formato das requisições que o SDK oficial envia, sem rede."""

import json

import anthropic
import httpx2
import pytest
from anthropic import DefaultHttpxClient

from metaexp.config import Settings
from metaexp.llm import FALLBACK_BETA, AnthropicLLM, LLMRefusal, TextDelta, TurnResult
from metaexp.core.schemas import PlanoTecnico

PLANO = {"abordagem": "RAG", "etapas": ["a"], "componentes": ["b"], "criterios_atendidos": ["c"], "riscos_tecnicos": []}


def _msg(content, stop="end_turn", stop_details=None):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "stop_details": stop_details,
            "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}


def _client(handler):
    return anthropic.Anthropic(api_key="teste", max_retries=0,
                               http_client=DefaultHttpxClient(transport=httpx2.MockTransport(handler)))


def test_structured_envia_formato_esforco_cache_e_fallback():
    vistos = {}

    def handler(req: httpx2.Request):
        vistos["body"] = json.loads(req.content)
        vistos["beta"] = req.headers.get("anthropic-beta")
        return httpx2.Response(200, json=_msg([{"type": "text", "text": json.dumps(PLANO)}]))

    llm = AnthropicLLM(Settings(), client=_client(handler))
    plano = llm.structured(system="sistema", messages=[{"role": "user", "content": "oi"}], schema=PlanoTecnico, effort="high")
    assert plano.abordagem == "RAG"
    b = vistos["body"]
    assert b["model"] == "claude-opus-5-5" and b["fallbacks"] == "default" and FALLBACK_BETA in vistos["beta"]
    assert b["output_config"]["effort"] == "high" and b["output_config"]["format"]["type"] == "json_schema"
    assert b["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "thinking" not in b   # Opus 5.5: pensamento adaptativo por padrão


def test_structured_recusa_vira_excecao():
    def handler(req):
        return httpx2.Response(200, json=_msg([], stop="refusal", stop_details={"type": "refusal", "category": "cyber", "explanation": "x"}))

    llm = AnthropicLLM(Settings(), client=_client(handler))
    with pytest.raises(LLMRefusal) as e:
        llm.structured(system="s", messages=[{"role": "user", "content": "oi"}], schema=PlanoTecnico)
    assert e.value.category == "cyber"


def _sse(events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)


def test_stream_turn_texto_e_ferramenta():
    vistos = {}
    eventos = [
        {"type": "message_start", "message": _msg([], stop=None) | {"usage": {"input_tokens": 10, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Olá, "}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Ana."}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "sugerir_respostas", "input": {}}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{\"opcoes\": [\"A\"]}"}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 12}},
        {"type": "message_stop"},
    ]

    def handler(req):
        vistos["body"] = json.loads(req.content)
        return httpx2.Response(200, text=_sse(eventos), headers={"content-type": "text/event-stream"})

    llm = AnthropicLLM(Settings(), client=_client(handler))
    out = list(llm.stream_turn(system="s", messages=[{"role": "user", "content": "oi"}],
                               tools=[{"name": "sugerir_respostas", "description": "d", "strict": True, "eager_input_streaming": True,
                                       "input_schema": {"type": "object", "properties": {"opcoes": {"type": "array", "items": {"type": "string"}}},
                                                        "required": ["opcoes"], "additionalProperties": False}}]))
    assert "".join(e.text for e in out if isinstance(e, TextDelta)) == "Olá, Ana."
    final = out[-1]
    assert isinstance(final, TurnResult) and final.stop_reason == "tool_use"
    assert final.tool_calls[0].input == {"opcoes": ["A"]} and final.content[1]["type"] == "tool_use"
    b = vistos["body"]
    assert b["stream"] is True and b["cache_control"] == {"type": "ephemeral"} and b["tools"][0]["eager_input_streaming"] is True


def test_mensagem_de_sistema_no_meio_da_conversa_vai_para_a_api():
    vistos = {}

    def handler(req):
        vistos["body"] = json.loads(req.content)
        return httpx2.Response(200, json=_msg([{"type": "text", "text": json.dumps(PLANO)}]))

    llm = AnthropicLLM(Settings(), client=_client(handler))
    llm.structured(system="s", schema=PlanoTecnico, messages=[
        {"role": "user", "content": "texto longo"}, {"role": "system", "content": "AUTO-INGESTÃO ativada"}])
    assert vistos["body"]["messages"][1] == {"role": "system", "content": "AUTO-INGESTÃO ativada"}
