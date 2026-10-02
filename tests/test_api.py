import base64
import json

from starlette.testclient import TestClient

from metaexp.api.app import create_app
from metaexp.config import ROOT
from metaexp.corpus.store import Corpus, load_dir
from metaexp.sessions import SessionStore

from .fakes import FakeLLM, turno


def eventos(resp) -> list[dict]:
    out = []
    for bloco in resp.text.strip().split("\n\n"):
        data = next(l[6:] for l in bloco.splitlines() if l.startswith("data: "))
        out.append(json.loads(data))
    return out


def app(tmp_path, llm):
    return TestClient(create_app(llm=llm, corpus=Corpus(load_dir(ROOT / "data/corpus/sintetico")),
                                 store=SessionStore(tmp_path)))


def test_fluxo_http(tmp_path):
    llm = FakeLLM([
        turno("Oi, Ana! **Qual problema você quer resolver?**", [("sugerir_respostas", {"opcoes": ["A FAQ é lenta"]})]),
        turno(""),
        turno("Entendi.", [("solicitar_dados", {"descricao": "FAQ", "formatos": ["csv"]})]),
        turno(""),
        turno("Vi 2 registros."),
    ])
    c = app(tmp_path, llm)
    assert c.get("/api/health").json()["corpus"]["total"] >= 7
    sid = c.post("/api/sessoes", json={"nome": "Ana"}).json()["id"]

    ev = eventos(c.post(f"/api/sessoes/{sid}/iniciar"))
    assert ev[0]["type"] == "text" and any(e["type"] == "chips" for e in ev) and ev[-1]["type"] == "done"

    ev = eventos(c.post(f"/api/sessoes/{sid}/mensagens", json={"texto": "A FAQ é lenta"}))
    assert any(e["type"] == "upload" for e in ev)

    csv = base64.b64encode("pergunta,resposta\na,b\nc,d\n".encode()).decode()
    ev = eventos(c.post(f"/api/sessoes/{sid}/arquivos", json={"nome": "faq.csv", "conteudo_base64": csv}))
    assert ev[0]["kind"] == "amostra" and ev[0]["data"]["registros"] == 2

    # A sessão foi persistida em disco e recarrega igual.
    estado = c.get(f"/api/sessoes/{sid}").json()
    assert estado["id"] == sid
    assert (tmp_path / f"{sid}.json").exists()


def test_erros_http(tmp_path):
    c = app(tmp_path, FakeLLM())
    assert c.get("/api/sessoes/nao-existe").status_code == 404
    sid = c.post("/api/sessoes", json={}).json()["id"]
    r = c.post(f"/api/sessoes/{sid}/arquivos", json={"nome": "a.csv", "conteudo_base64": "@@@"})
    assert r.status_code == 400
    ev = eventos(c.post(f"/api/sessoes/{sid}/bancada", json={}))
    assert ev[0]["type"] == "error"   # ainda não foi encaminhado
