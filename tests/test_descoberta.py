from datetime import datetime

from metaexp.agents.ferramentas import ToolContext, run_tool
from metaexp.config import ROOT
from metaexp.core import descoberta
from metaexp.core.schemas import MapaProblema
from metaexp.corpus.store import Corpus, load_dir
from metaexp.sessions import Sessao

CORPUS = Corpus(load_dir(ROOT / "data/corpus/sintetico"))


def _mapa(**prof) -> MapaProblema:
    m = MapaProblema()
    for dim, p in prof.items():
        descoberta.atualizar(m, dim, f"entendi {dim}", p, None)
    return m


def test_mapa_vazio_aprofunda_primeiro_o_sintoma():
    m = MapaProblema()
    assert descoberta.cobertura(m) == 0 and not descoberta.pronto_para_hipotese(m)
    assert descoberta.proxima_dimensao(m).id == "sintoma"
    assert [d.id for d in descoberta.lacunas(m)][:3] == ["sintoma", "quem_sofre", "tamanho"]


def test_pronto_para_hipotese_exige_minimos_e_cobertura():
    minimos = {d.id: d.minimo for d in descoberta.DIMENSOES}
    m = _mapa(**minimos)
    assert not descoberta.lacunas(m)
    assert descoberta.pronto_para_hipotese(m) == (descoberta.cobertura(m) >= descoberta.LIMIAR_COBERTURA)
    m = _mapa(**{k: max(v, 2) for k, v in minimos.items()})
    assert descoberta.pronto_para_hipotese(m)
    assert "sintese_para_confirmar" in descoberta.orientacao(m)["sugestao"]


def test_profundidade_nao_regride_e_reabre_a_sintese():
    m = _mapa(sintoma=3)
    m.sintese, m.sintese_confirmada = "x", True
    descoberta.atualizar(m, "sintoma", "nova leitura", 1, None)
    assert m.dimensoes["sintoma"].profundidade == 3 and m.dimensoes["sintoma"].entendimento == "nova leitura"
    assert m.sintese_confirmada is False


def test_ferramenta_mapear_problema_emite_mapa_porque_e_sintese():
    s = Sessao(id="t", criada_em=datetime.now().isoformat(), papel="solicitante")
    ctx = ToolContext(s, CORPUS)
    block, events = run_tool(ctx, "mapear_problema", {
        "atualizacoes": [{"dimensao": "tamanho", "entendimento": "300 chamados/dia", "profundidade": 2, "evidencia": "uns 300 por dia"}],
        "pergunta_atual": {"dimensao": "decisao", "tecnica": "decisao", "por_que": "Para saber o que muda se der certo."},
        "sintese_para_confirmar": "Os analistas perdem tempo..."})
    tipos = [e["type"] for e in events]
    assert tipos == ["mapa", "porque", "card"] and events[2]["kind"] == "sintese"
    assert '"aprofundar_agora"' in block["content"] and s.mapa.dimensoes["tamanho"].evidencia == "uns 300 por dia"
    block, _ = run_tool(ctx, "mapear_problema", {"atualizacoes": [{"dimensao": "inventada", "entendimento": "x", "profundidade": 1}]})
    assert block["is_error"]


def test_hipotese_com_mapa_raso_recebe_aviso():
    s = Sessao(id="t", criada_em=datetime.now().isoformat(), papel="solicitante")
    block, _ = run_tool(ToolContext(s, CORPUS), "atualizar_ficha",
                        {"hipotese": "Acreditamos que a busca irá reduzir em 20% o tempo para os analistas."})
    assert "mapa do problema ainda está raso" in block["content"]
