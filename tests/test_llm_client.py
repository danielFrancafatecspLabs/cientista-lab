"""Confere o formato das requisições para o proxy LiteLLM, sem rede."""

import json

import httpx2
import pytest

from metaexp.config import Settings
from metaexp.llm import FALLBACK_BETA, AnthropicLLM, LLMRefusal, TextDelta, TurnResult
from metaexp.core.schemas import PlanoTecnico

PLANO = {
    "abordagem": "RAG",
    "etapas": ["a"],
    "componentes": ["b"],
    "criterios_atendidos": ["c"],
    "riscos_tecnicos": [],
}


def _client(handler):
    return httpx2.Client(
        base_url="http://teste",
        transport=httpx2.MockTransport(handler),
        headers={"Authorization": "Bearer teste"},
    )


def test_structured_envia_formato_esforco_e_schema():
    vistos = {}

    def handler(req: httpx2.Request):
        vistos["body"] = json.loads(req.content)
        return httpx2.Response(200, json={"choices": [{"message": {"content": json.dumps(PLANO)}}]})

    llm = AnthropicLLM(Settings(), client=_client(handler))
    plano = llm.structured(system="sistema", messages=[{"role": "user", "content": "oi"}], schema=PlanoTecnico, effort="high")
    assert plano.abordagem == "RAG"
    b = vistos["body"]
    assert b["model"] == "deepseek-v4-flash"
    assert b["max_tokens"] == 16000
    assert b["response_format"]["type"] == "json_schema"
    assert b["response_format"]["json_schema"]["schema"]["title"] == "PlanoTecnico"
    assert b["messages"][0] == {"role": "system", "content": "sistema"}


def test_structured_recusa_vira_excecao():
    def handler(req: httpx2.Request):
        return httpx2.Response(200, json={"choices": [{"message": {"refusal": "x"}}]})

    llm = AnthropicLLM(Settings(), client=_client(handler))
    with pytest.raises(LLMRefusal) as e:
        llm.structured(system="s", messages=[{"role": "user", "content": "oi"}], schema=PlanoTecnico)
    assert e.value.explanation == "x"


def _sse(events):
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"


def test_stream_turn_texto_e_ferramenta():
    vistos = {}
    eventos = [
        {"choices": [{"delta": {"content": "Olá, "}}]},
        {"choices": [{"delta": {"content": "Ana."}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "toolu_1", "type": "function",
                                                  "function": {"name": "sugerir_respostas", "arguments": "{\"opcoes\": [\"A\"]}"}}]},
                      "finish_reason": "tool_calls"}]},
    ]

    def handler(req: httpx2.Request):
        vistos["body"] = json.loads(req.content)
        return httpx2.Response(200, text=_sse(eventos), headers={"content-type": "text/event-stream"})

    llm = AnthropicLLM(Settings(), client=_client(handler))
    out = list(llm.stream_turn(system="s", messages=[{"role": "user", "content": "oi"}],
                               tools=[{"name": "sugerir_respostas", "description": "d", "strict": True, "input_schema": {"type": "object", "properties": {"opcoes": {"type": "array", "items": {"type": "string"}}}, "required": ["opcoes"], "additionalProperties": False}}]))
    assert "".join(e.text for e in out if isinstance(e, TextDelta)) == "Olá, Ana."
    final = out[-1]
    assert isinstance(final, TurnResult) and final.stop_reason == "tool_use"
    assert final.tool_calls[0].input == {"opcoes": ["A"]} and final.content[1]["type"] == "tool_use"
    b = vistos["body"]
    assert b["stream"] is True
    assert b["tool_choice"] == "auto"
    assert b["tools"][0]["type"] == "function"
    assert b["tools"][0]["function"]["strict"] is True


def test_mensagem_de_sistema_no_meio_da_conversa_vai_para_a_api():
    vistos = {}

    def handler(req: httpx2.Request):
        vistos["body"] = json.loads(req.content)
        return httpx2.Response(200, json={"choices": [{"message": {"content": json.dumps(PLANO)}}]})

    llm = AnthropicLLM(Settings(), client=_client(handler))
    llm.structured(system="s", schema=PlanoTecnico, messages=[
        {"role": "user", "content": "texto longo"}, {"role": "system", "content": "AUTO-INGESTÃO ativada"}])
    assert vistos["body"]["messages"][2] == {"role": "system", "content": "AUTO-INGESTÃO ativada"}
