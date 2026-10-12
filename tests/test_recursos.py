"""Caixa de ferramentas do desenvolvedor: catálogo, pedidos de recursos e benchmarks do Lab."""

import json

import httpx2
import pytest

from metaexp.agents.ferramentas import ToolContext, run_tool, tools_for
from metaexp.config import ROOT, Settings
from metaexp.core.recursos import PedidoRecurso, catalogo, resumo_para_prompt, validar_detalhes
from metaexp.corpus.store import Corpus, load_dir
from metaexp.prompts import system_cientista
from metaexp.recursos import Provisionador
from metaexp.sessions import SessionStore

from tests.fakes import FakeLLM
from tests.test_api import app

CORPUS = Corpus(load_dir(ROOT / "data/corpus/sintetico"))


def test_catalogo_tem_modelos_recomendados_e_do_hub():
    c = catalogo()
    rec = {m["id"] for m in c["modelos"] if m["grupo"] == "recomendado"}
    hub = {m["id"] for m in c["modelos"] if m["grupo"] == "hub"}
    assert rec == {"deepseek-v4-flash", "deepseek-v4-pro"}
    assert {"gpt-oss-120b", "gemma-4", "qwen-3-5"} <= hub
    assert {r["tipo"] for r in c["recursos"]} == {"llm_key", "servidor", "github"}
    assert all(l["fonte"] and l["url"] for l in c["benchmarks_publicos"]["linhas"])
    # Os modelos do formulário de chave existem no catálogo.
    aliases = {m["alias"] for m in c["modelos"]}
    campo = next(x for x in c["recursos"][0]["campos"] if x["id"] == "modelos")
    assert {o[0] for o in campo["opcoes"]} <= aliases


def test_validar_detalhes_completa_padrao_e_recusa_opcao_invalida():
    assert validar_detalhes("llm_key", {}) == {"modelos": ["deepseek-v4-flash"], "validade": "30d", "orcamento": "50"}
    with pytest.raises(ValueError):
        validar_detalhes("llm_key", {"modelos": ["gpt-9"]})
    with pytest.raises(ValueError):
        validar_detalhes("github", {"repositorio": "x"})       # usuário obrigatório


def test_ciclo_do_pedido_de_chave(tmp_path):
    c = app(tmp_path, FakeLLM([]))
    r = c.post("/api/recursos/pedidos", json={"tipo": "llm_key", "solicitante": "Rui", "justificativa": "testar RAG",
                                               "detalhes": {"modelos": ["deepseek-v4-flash", "gpt-oss-120b"]}})
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "pendente" and p["credencial"] is None
    assert c.get(f"/api/recursos/pedidos/{p['id']}/credencial").status_code == 409
    assert [x["id"] for x in c.get("/api/recursos/pedidos?status=pendente").json()] == [p["id"]]
    assert c.get("/api/recursos/pedidos?solicitante=ana").json() == []

    # Negar exige motivo; aprovar entrega a credencial.
    assert c.post(f"/api/recursos/pedidos/{p['id']}/decisao", json={"decisao": "negar"}).status_code == 422
    r = c.post(f"/api/recursos/pedidos/{p['id']}/decisao", json={"decisao": "aprovar", "revisor": "Lia (Lab)"})
    pub = r.json()
    assert pub["status"] == "aprovado" and pub["credencial"]["segredo"] is None and len(pub["credencial"]["segredo_final"]) == 4
    cred = c.get(f"/api/recursos/pedidos/{p['id']}/credencial").json()
    assert cred["segredo"].startswith("sk-lab-") and cred["simulada"] is True
    assert "deepseek-v4-flash" in cred["exemplo"] and cred["segredo"] not in cred["exemplo"]
    assert c.post(f"/api/recursos/pedidos/{p['id']}/decisao", json={"decisao": "aprovar"}).status_code == 409

    r = c.post(f"/api/recursos/pedidos/{p['id']}/revogar", json={"revisor": "Lia (Lab)"})
    assert r.json()["status"] == "revogado"
    assert c.get(f"/api/recursos/pedidos/{p['id']}/credencial").status_code == 409


def test_pedido_ligado_ao_experimento_e_servidor(tmp_path):
    c = app(tmp_path, FakeLLM([]))
    sid = c.post("/api/sessoes", json={"papel": "desenvolvedor", "nome": "Rui"}).json()["id"]
    p = c.post("/api/recursos/pedidos", json={"tipo": "servidor", "solicitante": "Rui", "justificativa": "piloto",
                                               "detalhes": {"perfil": "gpu-24"}, "sessao_id": sid}).json()
    assert p["experimento"].startswith("EXP-") and p["detalhes"]["perfil"] == "gpu-24"
    c.post(f"/api/recursos/pedidos/{p['id']}/decisao", json={"decisao": "aprovar"})
    cred = c.get(f"/api/recursos/pedidos/{p['id']}/credencial").json()
    assert cred["campos"]["host"].endswith(".lab.interno") and cred["exemplo"].startswith("ssh ")


def test_toolbox_e_benchmarks_do_lab(tmp_path):
    c = app(tmp_path, FakeLLM([]))
    t = c.get("/api/toolbox").json()
    assert t["hub"]["chaves_reais"] is False and t["arquitetura"]["piloto"]
    assert c.get("/api/benchmarks-lab").json() == []
    b = c.post("/api/benchmarks-lab", json={"modelo": "DeepSeek V4 Flash", "tarefa": "RAG FAQ", "metrica": "acerto", "valor": "88%"}).json()
    assert [x["id"] for x in c.get("/api/benchmarks-lab").json()] == [b["id"]]
    assert c.delete(f"/api/benchmarks-lab/{b['id']}").json() == {"ok": True}
    assert c.delete(f"/api/benchmarks-lab/{b['id']}").status_code == 404


def test_provisionador_cria_chave_virtual_no_litellm():
    vistos = {}

    def handler(req: httpx2.Request):
        vistos["url"], vistos["auth"], vistos["body"] = str(req.url), req.headers["authorization"], json.loads(req.content)
        return httpx2.Response(200, json={"key": "sk-real-123", "expires": "2026-11-11T00:00:00Z"})

    cfg = Settings(litellm_master_key="mk", hub_url="https://gw.lab/v1")
    prov = Provisionador(cfg, client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    p = PedidoRecurso(id="abc", tipo="llm_key", solicitante="Rui", justificativa="x", criado_em="agora",
                      detalhes={"modelos": ["deepseek-v4-pro"], "validade": "7d", "orcamento": "10"})
    cred = prov.provisionar(p)
    assert vistos["url"] == "https://gw.lab/key/generate" and vistos["auth"] == "Bearer mk"
    assert vistos["body"]["models"] == ["deepseek-v4-pro"] and vistos["body"]["duration"] == "7d" and vistos["body"]["max_budget"] == 10.0
    assert cred.segredo == "sk-real-123" and cred.simulada is False and cred.campos["base_url"] == "https://gw.lab/v1"


def test_cientista_do_desenvolvedor_conhece_a_caixa_e_sugere_recurso(tmp_path):
    assert "sugerir_recurso" in {t["name"] for t in tools_for("desenvolvedor")}
    assert "sugerir_recurso" not in {t["name"] for t in tools_for("solicitante")}
    assert "DeepSeek V4 Flash" in system_cientista("desenvolvedor") and "DeepSeek V4 Flash" not in system_cientista("solicitante")
    assert "LangGraph" in resumo_para_prompt()
    s = SessionStore(tmp_path).create("Rui", "desenvolvedor")
    block, events = run_tool(ToolContext(s, CORPUS), "sugerir_recurso", {"tipo": "llm_key", "motivo": "testar o Flash"})
    assert not block.get("is_error") and events[0]["kind"] == "recurso" and events[0]["data"]["nome"] == "Chave de API de LLM"
