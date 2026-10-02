from datetime import datetime

from metaexp.agents.bancada import Bancada
from metaexp.agents.cientista import Cientista
from metaexp.config import ROOT, Settings
from metaexp.corpus.store import Corpus, load_dir
from metaexp.schemas import (AnaliseAmostra, AvaliacaoQA, CriterioAvaliado, Metrica, Parecer, PlanoTecnico,
                             ResultadoMetrica, Resultados)
from metaexp.sessions import Sessao
from metaexp.tools.cientista_tools import TOOL_SPECS, ToolContext, run_tool
from metaexp.tools.profiling import PerfilArquivo

from .fakes import FakeLLM, turno

CORPUS = Corpus(load_dir(ROOT / "data/corpus/sintetico"))


def sessao() -> Sessao:
    return Sessao(id="t1", criada_em=datetime.now().isoformat(), nome="Ana")


def ficha_completa(s: Sessao) -> None:
    f = s.ficha
    f.titulo, f.problema, f.publico_afetado = "Busca na FAQ", "Analistas demoram", "40 analistas"
    f.hipotese, f.tecnologia, f.tecnica = "Se X, então Y em 20%", "ia_generativa", "RAG"
    f.metricas = [Metrica(nome="tempo", descricao="tempo de busca", meta="-20%", obrigatoria=True)]
    f.dados, f.amostra, f.skills = "FAQ", "468 registros", ["Python"]


def test_esquemas_das_ferramentas_sao_estritos():
    for t in TOOL_SPECS:
        sch = t["input_schema"]
        assert t["strict"] and sch["additionalProperties"] is False
        assert set(sch["required"]) <= set(sch["properties"])


def test_ferramenta_com_entrada_invalida_devolve_erro():
    ctx = ToolContext(sessao(), CORPUS)
    block, events = run_tool(ctx, "registrar_sinal_perfil", {"direcao": "talvez"})
    assert block["is_error"] and events == []


def test_encaminhar_exige_ficha_completa():
    s = sessao()
    ctx = ToolContext(s, CORPUS)
    block, _ = run_tool(ctx, "encaminhar", {"destino": "workflow", "resumo": "x"})
    assert "faltantes" in block["content"] and s.encaminhamento is None
    ficha_completa(s)
    block, events = run_tool(ctx, "encaminhar", {"destino": "workflow", "resumo": "x"})
    assert s.encaminhamento == "workflow" and s.ficha.execucao == "laboratorio" and s.perfil == "negocio"
    assert events[-1]["type"] == "handoff"


def test_turno_do_cientista_executa_ferramentas_e_mantem_historico():
    llm = FakeLLM([
        turno("Entendi o problema.", [
            ("atualizar_ficha", {"titulo": "Busca na FAQ", "problema": "Analistas demoram para achar respostas"}),
            ("buscar_experimentos_similares", {"consulta": "faq analistas respostas"}),
            ("registrar_sinal_perfil", {"direcao": "negocio", "peso": "medio", "evidencia": "fala de impacto"}),
            ("sugerir_respostas", {"opcoes": ["Uns 40 analistas", "Não sei medir"]}),
        ]),
        turno("**Quem sente isso no dia a dia?**"),
    ])
    s = sessao()
    eventos = list(Cientista(llm, CORPUS).responder(s, "Meus analistas perdem tempo na FAQ"))
    tipos = [e["type"] for e in eventos]
    assert tipos[0] == "text" and tipos[-1] == "done"
    assert {"ficha", "card", "perfil", "chips"} <= set(tipos)
    assert s.ficha.titulo == "Busca na FAQ" and s.perfil_score < 50 and s.similares[0] == "SIN-SEED-01"
    # usuário, assistente com tool_use, usuário com 4 tool_results, assistente final
    assert [m["role"] for m in s.messages] == ["user", "assistant", "user", "assistant"]
    assert len(s.messages[2]["content"]) == 4 and all(b["type"] == "tool_result" for b in s.messages[2]["content"])
    # A segunda chamada recebeu o histórico com o primeiro turno intacto (só acrescenta).
    assert llm.chamadas[1]["messages"][:2] == s.messages[:2]


def test_arquivo_vira_cartao_e_contexto():
    llm = FakeLLM([turno("Vi 230 registros bem estruturados.")])
    s = sessao()
    s.ficha.golden_path = "rag-busca-semantica"
    perfil = PerfilArquivo(nome="faq.xlsx", formato="xlsx", registros=230, colunas=["pergunta", "resposta"])
    eventos = list(Cientista(llm, CORPUS).receber_arquivo(s, perfil))
    card = eventos[0]
    assert card["kind"] == "amostra" and card["data"]["minimo"] == 400 and card["data"]["total_registros"] == 230
    assert "<arquivo_anexado>" in s.messages[0]["content"]


def _fake_bancada(qs: list[float]) -> FakeLLM:
    rodadas = iter(qs)

    def qa(_):
        q = next(rodadas)
        n_ok = round(q * 10)
        return AvaliacaoQA(executa_sem_erro=True, outputs_existem=True, dados_validos=True,
                           criterios=[CriterioAvaliado(criterio=f"c{i}", atendido=i < n_ok, evidencia="") for i in range(10)],
                           feedback=["ajustar janela"])

    plano = PlanoTecnico(abordagem="RAG", etapas=["a"], componentes=["b"], criterios_atendidos=["c"], riscos_tecnicos=[])
    return FakeLLM(estruturados={
        "AnaliseAmostra": lambda _: AnaliseAmostra(resumo="Amostra boa.", registros_validos=462, tamanho_minimo=385, suficiente=True,
                                                   qualidade="boa", achados=["ok"], alertas=[], decisao_g1="aprovado"),
        "PlanoTecnico": lambda _: plano,
        "AvaliacaoQA": qa,
        "Resultados": lambda _: Resultados(simulado=False, metricas=[ResultadoMetrica(metrica="tempo", meta="-20%", resultado="-27%", atendida=True)], observacoes=[]),
        "Parecer": lambda _: Parecer(veredito="validada", titulo="Deu certo", resumo="r", evidencias=[], riscos=[], proximos_passos=[], oportunidades=[]),
    })


def test_bancada_completa_com_ralph_loop():
    s = sessao()
    ficha_completa(s)
    s.encaminhamento = "workflow"
    b = Bancada(_fake_bancada([0.6, 0.7, 0.9]), cfg=Settings())
    ev1 = list(b.avancar(s))
    assert ev1[-2]["type"] == "aprovacao" and s.bancada.aguardando == "ficha"
    ev2 = list(b.avancar(s, "aprovar"))
    assert any(e.get("kind") == "amostra" for e in ev2) and s.bancada.aguardando == "amostra"
    ev3 = list(b.avancar(s, "seguir"))
    rodadas = [e["data"] for e in ev3 if e.get("kind") == "rodada"]
    assert [r["q"] for r in rodadas] == [0.6, 0.7, 0.9]
    parecer = next(e for e in ev3 if e.get("kind") == "parecer")
    assert parecer["data"]["resultados"]["simulado"] is True   # o executor simulado sempre marca
    assert s.bancada.status == {"ficha": "ok", "amostra": "ok", "construcao": "ok", "qualidade": "ok", "resultado": "ok"}


def test_bancada_escalona_no_kmax_e_retoma_com_orientacao():
    s = sessao()
    ficha_completa(s)
    s.encaminhamento = "workflow"
    b = Bancada(_fake_bancada([0.5, 0.5, 0.6, 0.6, 0.7, 0.9]), cfg=Settings())
    list(b.avancar(s)); list(b.avancar(s, "aprovar"))
    ev = list(b.avancar(s, "seguir"))
    assert len(s.bancada.rodadas) == 5 and s.bancada.aguardando == "qualidade"
    assert ev[-2]["type"] == "aprovacao"
    list(b.avancar(s, "orientar", "Inclua vizinhança de 2 saltos"))
    assert len(s.bancada.rodadas) == 6 and s.bancada.status["resultado"] == "ok"
