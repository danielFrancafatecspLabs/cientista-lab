import json
from pathlib import Path

import pytest

from metaexp.config import ROOT
from metaexp.corpus.search import BM25, tokenize
from metaexp.corpus.store import Corpus, load_dir
from metaexp.core.schemas import AvaliacaoQA, CriterioAvaliado, Ficha
from metaexp.synthetic.quality import validar
from metaexp.synthetic.taxonomy import amostrar, cobertura
from metaexp.core.profiling import perfilar
from metaexp.core.stats import margem_para_n, reducao_lead_time, tamanho_amostra_proporcao

SEEDS = ROOT / "data/corpus/sintetico"


def test_tamanho_amostra_da_proposta():
    # Eq. 7: E = 0,05, 95%, p = 0,5 -> 385
    assert tamanho_amostra_proporcao() == 385
    assert round(margem_para_n(230), 3) == 0.065
    assert round(reducao_lead_time(36, 14), 2) == 0.61


def test_qualidade_ralph_loop_multiplicativa():
    crit = [CriterioAvaliado(criterio=f"c{i}", atendido=i < 8, evidencia="") for i in range(9)]
    av = AvaliacaoQA(executa_sem_erro=True, outputs_existem=True, dados_validos=True, criterios=crit, feedback=[])
    assert round(av.qualidade(), 2) == 0.89
    av.outputs_existem = False
    assert av.qualidade() == 0.0   # falha crítica anula a aderência


def test_ficha_faltantes():
    f = Ficha(titulo="x", problema="y")
    assert "hipotese" in f.faltantes() and "titulo" not in f.faltantes()
    assert "bo" in f.faltantes() and "sponsor" in f.faltantes() and "objetivo" in f.faltantes()


def test_regras_do_metodo():
    from metaexp.core.metodo import criterio_valido, hipotese_valida, precisa_auto_ingestao, titulo_valido
    assert criterio_valido("Acurácia ≥ 85%") and criterio_valido("MAPE < 10%") and criterio_valido("Viés entre -3% e 3%")
    assert not criterio_valido("Alta acurácia") and not criterio_valido("85%") and not criterio_valido("")
    assert hipotese_valida("Acreditamos que X irá gerar 20% de redução para Y.") == []
    assert any("Acreditamos" in p for p in hipotese_valida("Se X, então Y em 20%."))
    assert any("mensurável" in p for p in hipotese_valida("Acreditamos que X irá ajudar Y."))
    assert any("2 linhas" in p for p in hipotese_valida("Acreditamos que " + "x " * 150 + "20%"))
    assert titulo_valido("Busca Semântica FAQ") == [] and titulo_valido("Busca semântica na FAQ")
    assert precisa_auto_ingestao("a" * 401)
    assert precisa_auto_ingestao("Problema: x\nObjetivo: y\nMétricas: z")
    assert not precisa_auto_ingestao("Problema: só uma linha curta")


def test_objetivo_igual_hipotese_e_pendencia():
    f = Ficha(objetivo="Acreditamos que X irá gerar 20%.", hipotese="Acreditamos que X irá gerar 20%.")
    assert any("objetivo e hipótese" in p for p in f.pendencias())


def test_tokenize_remove_acentos_e_stopwords():
    assert tokenize("Correlação dos alarmes de vídeo") == ["correl", "alarm", "video"]


def test_bm25_ordena_por_relevancia():
    idx = BM25(["faq de atendimento e respostas", "alarmes da rede de video", "previsao de chamadas"])
    assert idx.search("respostas da faq")[0][0] == 0


def test_corpus_inicial_valido_e_buscavel():
    exps = load_dir(SEEDS)
    assert len(exps) >= 7
    for e in exps:
        assert validar(e, None, [x for x in exps if x.id != e.id]) == [], e.id
    c = Corpus(exps)
    assert c.search("analistas demoram para achar resposta na FAQ", k=1)[0][0].id == "SIN-SEED-01"


def test_amostragem_estratificada_cobre_todos_os_eixos():
    specs = amostrar(28, seed=1)
    cob = cobertura(specs)
    assert len(cob["golden_path"]) == 7 and set(cob["golden_path"].values()) == {4}
    assert cob["perfil_solicitante"] == {"negocio": 14, "desenvolvedor": 14}
    assert all(not (s.situacao_dados == "sem_dados" and s.veredito == "validada") for s in specs)
    assert amostrar(28, seed=1) == specs   # reprodutível


def test_validar_detecta_incoerencias():
    e = load_dir(SEEDS)[0]
    e2 = e.model_copy(deep=True)
    e2.id = "X"
    assert any("quase duplicata" in p for p in validar(e2, None, [e]))
    e3 = e.model_copy(deep=True)
    e3.id = "Y"
    e3.parecer.veredito = "validada"
    e3.resultados.metricas[0].atendida = False
    assert any("obrigatória não atendida" in p for p in validar(e3, None, []))


def test_perfil_csv_e_json():
    csv_bytes = "pergunta;resposta\nComo pago?;Pelo app\nComo pago?;Pelo app\nPrazo?;\n".encode()
    p = perfilar("faq.csv", csv_bytes)
    assert p.registros == 3 and p.duplicadas == 1 and p.colunas == ["pergunta", "resposta"]
    assert p.vazias_por_coluna == {"resposta": 1}
    pj = perfilar("x.json", json.dumps({"itens": [{"a": 1}, {"a": 2, "b": 3}]}).encode())
    assert pj.registros == 2 and pj.colunas == ["a", "b"]


def test_perfil_xlsx(tmp_path: Path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["pergunta", "resposta"])
    for i in range(10):
        ws.append([f"p{i}", f"r{i}"])
    f = tmp_path / "faq.xlsx"
    wb.save(f)
    p = perfilar("faq.xlsx", f.read_bytes())
    assert p.registros == 10 and p.completude == 1.0


@pytest.mark.parametrize("ext", [".pdf", ".zip"])
def test_perfil_formato_nao_suportado(ext):
    p = perfilar("a" + ext, b"...")
    assert p.registros == 0 and p.observacoes
