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


def sessao(papel: str = "solicitante") -> Sessao:
    return Sessao(id="t1", criada_em=datetime.now().isoformat(), nome="Ana", papel=papel)


def ficha_completa(s: Sessao) -> None:
    f = s.ficha
    f.titulo, f.problema, f.publico_afetado = "Busca na FAQ", "Analistas demoram", "40 analistas"
    f.objetivo, f.metodologia = "Testar busca semântica na FAQ", "RAG avaliado com 120 perguntas"
    f.hipotese = "Acreditamos que a busca semântica irá reduzir em 20% o tempo de busca para os analistas."
    f.tecnologia, f.tecnica = "ia_generativa", "RAG"
    f.metricas = [Metrica(nome="tempo", descricao="tempo de busca", criterio_aceite="Redução ≥ 20%", obrigatoria=True)]
    f.dados, f.amostra, f.skills = "FAQ", "468 registros", ["Python"]
    f.bo, f.sponsor = "Coordenadora de atendimento", "Diretor de atendimento"


def test_esquemas_das_ferramentas_sao_estritos():
    for t in TOOL_SPECS:
        sch = t["input_schema"]
        assert t["strict"] and sch["additionalProperties"] is False
        assert set(sch["required"]) <= set(sch["properties"])


def test_ferramenta_com_entrada_invalida_devolve_erro():
    ctx = ToolContext(sessao(), CORPUS)
    block, events = run_tool(ctx, "sugerir_respostas", {"opcoes": "não é lista"})
    assert block["is_error"] and events == []


def test_encaminhar_exige_ficha_gerada():
    s = sessao()
    ctx = ToolContext(s, CORPUS)
    block, _ = run_tool(ctx, "encaminhar", {"destino": "workflow", "resumo": "x"})
    assert "gerar_ficha" in block["content"] and s.encaminhamento is None
    block, events = run_tool(ctx, "gerar_ficha", {})
    assert '"ok": false' in block["content"] and events == [] and not s.ficha_gerada
    ficha_completa(s)
    block, events = run_tool(ctx, "gerar_ficha", {})
    assert s.ficha_gerada and s.ficha_versao == 1 and events[-1]["kind"] == "ficha_gerada"
    assert "| tempo | tempo de busca | Redução ≥ 20% | sim |" in events[-1]["data"]["markdown"]
    block, events = run_tool(ctx, "encaminhar", {"destino": "workflow", "resumo": "x"})
    assert s.encaminhamento == "workflow" and s.ficha.execucao == "laboratorio"
    assert events[-1]["type"] == "handoff"


def test_turno_do_cientista_executa_ferramentas_e_mantem_historico():
    llm = FakeLLM([
        turno("Entendi o problema.", [
            ("atualizar_ficha", {"titulo": "Busca na FAQ", "problema": "Analistas demoram para achar respostas"}),
            ("buscar_experimentos_similares", {"consulta": "faq analistas respostas"}),
            ("sugerir_respostas", {"opcoes": ["Uns 40 analistas", "Não sei medir"]}),
        ]),
        turno("**Quem sente isso no dia a dia?**"),
    ])
    s = sessao()
    eventos = list(Cientista(llm, CORPUS).responder(s, "Meus analistas perdem tempo na FAQ"))
    tipos = [e["type"] for e in eventos]
    assert tipos[0] == "text" and tipos[-1] == "done"
    assert {"ficha", "card", "chips"} <= set(tipos)
    assert s.ficha.titulo == "Busca na FAQ" and s.similares[0] == "SIN-SEED-01"
    # usuário, assistente com tool_use, usuário com 3 tool_results, assistente final
    assert [m["role"] for m in s.messages] == ["user", "assistant", "user", "assistant"]
    assert len(s.messages[2]["content"]) == 3 and all(b["type"] == "tool_result" for b in s.messages[2]["content"])
    # A segunda chamada recebeu o histórico com o primeiro turno intacto (só acrescenta).
    assert llm.chamadas[1]["messages"][:2] == s.messages[:2]


def test_atualizar_ficha_avisa_regras_do_metodo():
    s = sessao()
    ctx = ToolContext(s, CORPUS)
    block, _ = run_tool(ctx, "atualizar_ficha", {
        "titulo": "Assistente de busca semântica na FAQ",
        "hipotese": "A busca vai ajudar os analistas.",
        "metricas": [{"nome": "acuracia", "descricao": "acerto", "criterio_aceite": "alta acurácia", "obrigatoria": True}]})
    out = __import__("json").loads(block["content"])
    assert out["ok"] is False
    avisos = " ".join(out["avisos"])
    assert "Acreditamos que" in avisos and "3 palavras" in avisos and "acuracia" in avisos


def test_alterar_ficha_depois_de_gerada_exige_nova_geracao():
    s = sessao()
    ficha_completa(s)
    ctx = ToolContext(s, CORPUS)
    run_tool(ctx, "gerar_ficha", {})
    run_tool(ctx, "atualizar_ficha", {"amostra": "230 registros"})
    assert not s.ficha_gerada
    run_tool(ctx, "gerar_ficha", {})
    assert s.ficha_gerada and s.ficha_versao == 2


def test_auto_ingestao_insere_instrucao_de_sistema():
    llm = FakeLLM([turno("Li o seu documento. **Quem é o patrocinador (SPONSOR)?**")])
    s = sessao()
    texto = ("Problema: analistas demoram na FAQ.\nObjetivo: testar busca semântica.\n"
             "Hipótese: Acreditamos que a busca irá reduzir 20% do tempo.\nMétricas: tempo de busca.")
    eventos = list(Cientista(llm, CORPUS).responder(s, texto))
    assert eventos[0]["type"] == "auto_ingestao"
    assert [m["role"] for m in s.messages[:2]] == ["user", "system"]
    assert "AUTO-INGESTÃO" in s.messages[1]["content"] and "SPONSOR" in s.messages[1]["content"]
    # mensagem curta e sem seções: sem auto-ingestão
    list(Cientista(FakeLLM([turno("ok")]), CORPUS).responder(s, "Uns 40 analistas."))
    assert s.messages[-2]["role"] == "user"


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


# ------------------------------------------------------------ jornadas ----

def test_jornadas_recebem_prompt_e_ferramentas_proprios():
    llm = FakeLLM([turno("Olá"), turno("Olá")])
    c = Cientista(llm, CORPUS)
    sol, dev = sessao("solicitante"), sessao("desenvolvedor")
    dev.preferencias = {"stack": "typescript", "ia": "iniciante", "ambiente": "propria"}
    list(c.iniciar(sol)); list(c.iniciar(dev))
    t_sol, t_dev = llm.chamadas[0]["tools"], llm.chamadas[1]["tools"]
    assert "propor_abordagens" not in t_sol and "apresentar_skills" not in t_sol
    assert {"propor_abordagens", "registrar_desenho_tecnico", "apresentar_skills"} <= set(t_dev)
    assert "JORNADA: SOLICITANTE" in c.system_for("solicitante") and "JORNADA: DESENVOLVEDOR" in c.system_for("desenvolvedor")
    abertura = dev.messages[0]["content"]
    assert "Papel escolhido: Desenvolvedor" in abertura and "TypeScript" in abertura and "Começando em IA" in abertura


def test_solicitante_nao_ve_tecnica_nem_escolhe_executor():
    s = sessao("solicitante")
    ctx = ToolContext(s, CORPUS)
    _, events = run_tool(ctx, "classificar_experimento", {"tecnologia": "ia_generativa", "tecnica": "RAG", "justificativa": "x", "golden_path": "rag-busca-semantica"})
    assert not any(e.get("kind") == "tecnologia" for e in events)   # sem cartão técnico
    block, _ = run_tool(ctx, "propor_abordagens", {"abordagens": [], "justificativa_recomendacao": "x"})
    assert block["is_error"]                                          # ferramenta fora da jornada
    ficha_completa(s)
    s.ficha.skills = []
    run_tool(ctx, "gerar_ficha", {})
    block, _ = run_tool(ctx, "encaminhar", {"destino": "desenvolvedor", "resumo": "x"})
    assert "workflow" in block["content"] and s.encaminhamento is None
    run_tool(ctx, "encaminhar", {"destino": "workflow", "resumo": "x"})
    assert s.encaminhamento == "workflow"                             # skills não são exigidas do solicitante


def test_desenvolvedor_registra_desenho_tecnico():
    s = sessao("desenvolvedor")
    ctx = ToolContext(s, CORPUS)
    ab = lambda nome, rec: {"nome": nome, "descricao": "d", "pros": ["p"], "contras": ["c"], "custo": "R$ 0,01", "latencia": "p95 1 s", "complexidade": "media", "recomendada": rec}
    _, events = run_tool(ctx, "propor_abordagens", {"abordagens": [ab("BM25", False), ab("Híbrida com re-ranking", True)], "justificativa_recomendacao": "melhor recall"})
    assert events[-1]["kind"] == "abordagens" and events[-1]["data"]["recomendada"] == "Híbrida com re-ranking"
    block, events = run_tool(ctx, "registrar_desenho_tecnico", {"stack": "Python", "baseline": "Busca por palavra-chave, Recall@5 0,52",
                                                                "protocolo_avaliacao": "120 perguntas reais", "metricas_tecnicas": ["Recall@5 ≥ 0,85"],
                                                                "arquitetura": ["ingestão", "índice híbrido", "re-ranker"]})
    assert events[-1]["kind"] == "desenho" and '"desenho_incompleto": []' in block["content"]
    ficha_completa(s)
    run_tool(ctx, "gerar_ficha", {})
    from metaexp.ficha_doc import markdown
    md = markdown(s.ficha)
    assert "## Desenho técnico" in md and "| Híbrida com re-ranking |" in md and "Recall@5 ≥ 0,85" in md
