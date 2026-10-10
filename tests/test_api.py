import base64
import io
import json
import zipfile

from starlette.testclient import TestClient

from metaexp.api import create_app
from metaexp.config import ROOT, Settings
from metaexp.core.schemas import (AnaliseAmostra, AvaliacaoQA, CriterioAvaliado, NotaRubrica, Parecer, PlanoTecnico, PreRevisao,
                                  Resultados)
from metaexp.corpus.store import Corpus, load_dir
from metaexp.sessions import SessionStore

from tests.fakes import FakeLLM, turno


def eventos(resp) -> list[dict]:
    out = []
    for bloco in resp.text.strip().split("\n\n"):
        data = next(l[6:] for l in bloco.splitlines() if l.startswith("data: "))
        out.append(json.loads(data))
    return out


def app(tmp_path, llm, **cfg):
    return TestClient(create_app(llm=llm, cfg=Settings(**cfg) if cfg else None,
                                 corpus=Corpus(load_dir(ROOT / "data/corpus/sintetico")), store=SessionStore(tmp_path)))


FICHA = {
    "titulo": "Busca na FAQ", "dominio": "atendimento", "problema": "Analistas demoram para achar respostas na FAQ",
    "publico_afetado": "40 analistas, 6 min por busca", "objetivo": "Testar uma busca inteligente na FAQ",
    "hipotese": "Acreditamos que a busca inteligente irá reduzir em 20% o tempo de busca para os analistas.",
    "metodologia": "Comparar tempo de busca antes e depois com 120 perguntas reais",
    "metricas": [{"nome": "tempo", "descricao": "tempo de busca", "criterio_aceite": "Redução ≥ 20%", "obrigatoria": True}],
    "dados": "FAQ em planilha", "amostra": "468 perguntas", "bo": "Coordenadora de atendimento", "sponsor": "Diretor de atendimento",
}
CLASSIF = {"tecnologia": "ia_generativa", "tecnica": "RAG", "justificativa": "achar respostas", "golden_path": "rag-busca-semantica"}


def test_conversa_com_descoberta_e_amostra(tmp_path):
    llm = FakeLLM([
        turno("Oi, Ana! **Quando um analista não acha a resposta, o que ele faz?**", [
            ("mapear_problema", {"atualizacoes": [{"dimensao": "sintoma", "entendimento": "FAQ lenta", "profundidade": 1}],
                                 "pergunta_atual": {"dimensao": "caso_concreto", "tecnica": "caso_concreto", "por_que": "Um caso real mostra onde o tempo se perde."}}),
            ("sugerir_respostas", {"opcoes": ["Pergunta ao supervisor"]})]),
        turno(""),
        turno("Entendi.", [("solicitar_dados", {"descricao": "FAQ", "formatos": ["csv"]})]),
        turno(""),
        turno("Vi 2 registros."),
    ])
    c = app(tmp_path, llm)
    assert c.get("/api/health").json()["corpus"]["total"] >= 7
    sid = c.post("/api/sessoes", json={"nome": "Ana"}).json()["id"]

    ev = eventos(c.post(f"/api/sessoes/{sid}/iniciar"))
    tipos = [e["type"] for e in ev]
    assert tipos[0] == "text" and "mapa" in tipos and "porque" in tipos and "chips" in tipos and tipos[-1] == "done"
    porque = next(e for e in ev if e["type"] == "porque")
    assert porque["tecnica_nome"] == "Um caso real" and porque["dimensao_nome"] == "Um caso real"
    assert ev[-1]["state"]["mapa"]["dimensoes"][0]["profundidade"] == 1

    ev = eventos(c.post(f"/api/sessoes/{sid}/mensagens", json={"texto": "A FAQ é lenta"}))
    assert any(e["type"] == "upload" for e in ev)

    csv = base64.b64encode("pergunta,resposta\na,b\nc,d\n".encode()).decode()
    ev = eventos(c.post(f"/api/sessoes/{sid}/arquivos", json={"nome": "faq.csv", "conteudo_base64": csv}))
    assert ev[0]["kind"] == "amostra" and ev[0]["data"]["registros"] == 2

    # Persistida em SQLite: um store novo, apontando para o mesmo arquivo, recarrega igual.
    assert SessionStore(tmp_path).get(sid).arquivos[0]["registros"] == 2


def _ate_encaminhar(c, papel="solicitante", destino="workflow"):
    sid = c.post("/api/sessoes", json={"nome": "Ana", "papel": papel}).json()["id"]
    ev = eventos(c.post(f"/api/sessoes/{sid}/iniciar"))
    return sid, ev


def _llm_ciclo(destino="workflow", extras=None):
    ferr = [("atualizar_ficha", FICHA), ("classificar_experimento", CLASSIF)] + (extras or []) + \
           [("gerar_ficha", {}), ("encaminhar", {"destino": destino, "resumo": "Busca na FAQ"})]
    turnos = [turno("Pronto.", ferr), turno("Ficha com o Lab.")]
    # retomada após devolução: corrige e reencaminha
    turnos += [turno("O Lab pediu um ajuste.", [("atualizar_ficha", {"amostra": "468 perguntas reais"}), ("gerar_ficha", {}),
                                                ("encaminhar", {"destino": destino, "resumo": "v2"})]), turno("De volta ao Lab.")]
    plano = PlanoTecnico(abordagem="RAG", etapas=["a"], componentes=["b"], criterios_atendidos=["c"], riscos_tecnicos=[])
    estruturados = {
        "PreRevisao": lambda _: PreRevisao(resumo="Pronta.", notas=[NotaRubrica(criterio="problema", nota=4, justificativa="claro")],
                                           pontos_fortes=["problema claro"], riscos=[], ajustes_sugeridos=["detalhar a amostra"],
                                           recomendacao="aprovar_com_ajustes"),
        "AnaliseAmostra": lambda _: AnaliseAmostra(resumo="Boa.", registros_validos=468, tamanho_minimo=400, suficiente=True,
                                                   qualidade="boa", achados=[], alertas=[], decisao_g1="aprovado"),
        "PlanoTecnico": lambda _: plano,
        "AvaliacaoQA": lambda _: AvaliacaoQA(executa_sem_erro=True, outputs_existem=True, dados_validos=True,
                                             criterios=[CriterioAvaliado(criterio="c", atendido=True, evidencia="ok")], feedback=[]),
        "Resultados": lambda _: Resultados(simulado=True, metricas=[], observacoes=[]),
        "Parecer": lambda _: Parecer(veredito="validada", titulo="Deu certo", resumo="r", evidencias=[], riscos=[], proximos_passos=[], oportunidades=[]),
    }
    return FakeLLM(turnos, estruturados)


def test_ciclo_completo_lab_e_sponsor(tmp_path):
    c = app(tmp_path, _llm_ciclo())
    sid, ev = _ate_encaminhar(c)
    handoff = next(e for e in ev if e["type"] == "handoff")
    assert handoff["status"] == "em_revisao" and ev[-1]["state"]["status"] == "em_revisao"
    assert c.post(f"/api/sessoes/{sid}/mensagens", json={"texto": "oi"}).status_code == 409   # conversa fechada

    fila = c.get("/api/experimentos?status=em_revisao").json()
    assert [x["id"] for x in fila] == [sid] and fila[0]["lead_time_horas"] is not None

    pre = c.post(f"/api/experimentos/{sid}/pre-revisao").json()
    assert pre["recomendacao"] == "aprovar_com_ajustes"
    det = c.get(f"/api/experimentos/{sid}").json()
    assert det["transcricao"][0]["de"] == "cientista" and det["pre_revisao"]["notas"][0]["nota"] == 4

    # Devolver sem comentário não pode; com comentário, a conversa reabre com o feedback do Lab.
    assert c.post(f"/api/experimentos/{sid}/revisao", json={"decisao": "devolver"}).status_code == 422
    est = c.post(f"/api/experimentos/{sid}/revisao", json={"decisao": "devolver", "comentario": "Detalhe a amostra"}).json()
    assert est["status"] == "devolvido" and est["feedback_lab"]["comentario"] == "Detalhe a amostra"
    ev = eventos(c.post(f"/api/sessoes/{sid}/retomar"))
    assert ev[-1]["state"]["status"] == "em_revisao" and ev[-1]["state"]["ficha_versao"] == 2

    # Bancada não começa antes do G0.
    assert eventos(c.post(f"/api/sessoes/{sid}/bancada", json={}))[0]["type"] == "aguardando"
    est = c.post(f"/api/experimentos/{sid}/revisao", json={"decisao": "aprovar", "comentario": "Ok", "revisor": "Marina"}).json()
    assert est["status"] == "aprovado" and est["revisoes"][-1]["revisor"] == "Marina"

    eventos(c.post(f"/api/sessoes/{sid}/bancada", json={}))
    ev = eventos(c.post(f"/api/sessoes/{sid}/bancada", json={"decisao": "seguir"}))
    assert any(e.get("kind") == "parecer" for e in ev) and ev[-1]["state"]["status"] == "parecer"

    port = c.get("/api/portfolio").json()
    assert port["kpis"]["decisoes_pendentes"] == 1 and port["kpis"]["aprovacao_primeira_revisao"] == 0.0
    est = c.post(f"/api/experimentos/{sid}/decisao", json={"decisao": "escalar", "comentario": "Piloto em 2 sites"}).json()
    assert est["status"] == "decidido" and est["decisao"]["decisao"] == "escalar"


def test_revisao_lab_desligada_aprova_ao_encaminhar(tmp_path):
    c = app(tmp_path, _llm_ciclo(), revisao_lab=False)
    sid, ev = _ate_encaminhar(c)
    assert ev[-1]["state"]["status"] == "aprovado"


def test_kit_do_desenvolvedor(tmp_path):
    desenho = ("registrar_desenho_tecnico", {
        "stack": "Python", "baseline": "palavra-chave, recall@5 0,52", "abordagem_escolhida": "Híbrida",
        "avaliacao": {"conjunto": "120 perguntas reais", "tamanho": 120, "gate_regressao": "queda > 2 p.p.",
                      "metricas": [{"nome": "recall@5", "alvo": "≥ 0,85", "baseline": "0,52"},
                                   {"nome": "latencia_p95_ms", "alvo": "< 2000"}]},
        "arquitetura": ["índice", "reranker"]})
    c = app(tmp_path, _llm_ciclo("desenvolvedor", [desenho]))
    sid, ev = _ate_encaminhar(c, "desenvolvedor", "desenvolvedor")
    handoff = next(e for e in ev if e["type"] == "handoff")
    assert "eval/avaliar.py" in handoff["kit"] and ".github/workflows/experimento.yml" in handoff["kit"]
    kit = c.get(f"/api/sessoes/{sid}/kit").json()
    metas = json.loads(kit["arquivos"]["eval/metas.json"])
    assert metas["metricas"][0] == {"nome": "recall@5", "rotulo": "recall@5", "alvo": "≥ 0,85", "meta": {"op": ">=", "valor": 0.85},
                                    "baseline": "0,52", "liga_a": None}
    r = c.get(f"/api/sessoes/{sid}/kit.zip")
    nomes = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert r.headers["content-type"] == "application/zip" and "busca-na-faq/experimento.yaml" in nomes


def test_erros_http(tmp_path):
    c = app(tmp_path, FakeLLM())
    assert c.get("/api/sessoes/nao-existe").status_code == 404
    sid = c.post("/api/sessoes", json={}).json()["id"]
    r = c.post(f"/api/sessoes/{sid}/arquivos", json={"nome": "a.csv", "conteudo_base64": "@@@"})
    assert r.status_code == 400
    ev = eventos(c.post(f"/api/sessoes/{sid}/bancada", json={}))
    assert ev[0]["type"] == "error"   # ainda não foi encaminhado
    assert c.post(f"/api/experimentos/{sid}/revisao", json={"decisao": "aprovar"}).status_code == 409
    assert c.post(f"/api/experimentos/{sid}/pre-revisao").status_code == 409


def test_papeis_e_criacao_de_sessao_por_papel(tmp_path):
    c = app(tmp_path, FakeLLM())
    r = c.get("/api/papeis").json()
    assert [j["papel"] for j in r["jornadas"]] == ["solicitante", "desenvolvedor", "lab", "sponsor"]
    assert [j["tipo"] for j in r["jornadas"]] == ["conversa", "conversa", "painel", "painel"]
    assert all(len(x["raci"]) == len(r["etapas_ciclo"]) for x in r["responsabilidades"])
    assert len(r["dimensoes"]) == 10 and "caso_concreto" in r["tecnicas"]
    s = c.post("/api/sessoes", json={"papel": "desenvolvedor", "preferencias": {"stack": "java", "ia": "?"}}).json()
    assert s["papel"] == "desenvolvedor" and s["preferencias"] == {"stack": "java", "ia": "intermediario", "ambiente": "sandbox"}
    assert c.post("/api/sessoes", json={"papel": "lab"}).status_code == 422          # painel, sem conversa
    assert c.post("/api/sessoes", json={"papel": "diretor"}).status_code == 422
