from pathlib import Path

from metaexp import cli
from metaexp.config import ROOT
from metaexp.corpus.store import Corpus, load_dir
from metaexp.synthetic.generator import gerar
from metaexp.synthetic.ingest import ingerir, unidades
from metaexp.synthetic.taxonomy import Especificacao

from tests.fakes import FakeLLM

SEEDS = load_dir(ROOT / "data/corpus/sintetico")


def _spec_de(exp, id_="SIN-T-0001") -> Especificacao:
    return Especificacao(id=id_, dominio=exp.dominio, golden_path=exp.ficha.golden_path, tecnologia=exp.ficha.tecnologia,
                         perfil_solicitante=exp.perfil_solicitante, situacao_dados=exp.situacao_dados,
                         veredito=exp.parecer.veredito, estilo_conversa="objetivo")


def test_gerador_aceita_coerente_e_rejeita_duplicata(tmp_path: Path):
    base = SEEDS[0]
    novo = base.model_copy(deep=True)
    novo.ficha.titulo = "Normas de RH"
    novo.ficha.problema = "Gestores não encontram regras de férias e benefícios na intranet."
    novo.ficha.hipotese = "Acreditamos que consultar normas em linguagem natural irá reduzir em 30% os chamados ao RH para os gestores."
    novo.ficha.objetivo = "Testar um assistente de perguntas sobre normas internas de RH."
    novo.ficha.tecnica = "Perguntas e respostas sobre normas"
    respostas = iter([novo, base.model_copy(deep=True)])
    llm = FakeLLM(estruturados={"Experimento": lambda _: next(respostas)})
    specs = [_spec_de(base, "SIN-T-0001"), _spec_de(base, "SIN-T-0002")]
    rel = gerar(specs, llm, tmp_path, corpus=Corpus(SEEDS))
    assert rel.aceitos == ["SIN-T-0001"]
    assert rel.rejeitados and "quase duplicata" in rel.rejeitados[0][1][0]
    salvo = load_dir(tmp_path)[0]
    assert salvo.id == "SIN-T-0001" and salvo.origem == "sintetico" and salvo.resultados.simulado


def test_ingestao_agrupa_por_pasta_e_valida_json(tmp_path: Path):
    import docx
    origem, destino = tmp_path / "real", tmp_path / "corpus"
    (origem / "EXP-VOC-01").mkdir(parents=True)
    d = docx.Document()
    d.add_paragraph("Ficha: classificação de manifestações. Hipótese: F1 acima de 0,8.")
    d.save(origem / "EXP-VOC-01" / "ficha.docx")
    (origem / "EXP-VOC-01" / "notas.md").write_text("Resultado: F1 0,74.")
    (origem / "antigo.json").write_text(SEEDS[1].model_dump_json())
    (origem / "README.md").write_text("ignorar")
    us = dict(unidades(origem))
    assert sorted(us) == ["ANTIGO", "EXP-VOC-01"] and len(us["EXP-VOC-01"]) == 2

    vistos = []

    def fake_exp(messages):
        vistos.append(messages[0]["content"])
        e = SEEDS[4].model_copy(deep=True)
        e.id = "REAL-EXP-VOC-01"
        return e

    ids = ingerir(FakeLLM(estruturados={"Experimento": fake_exp}), origem, destino)
    assert sorted(ids) == ["REAL-ANTIGO", "REAL-EXP-VOC-01"]
    assert all(e.origem == "real" for e in load_dir(destino))
    blocos = vistos[0]
    assert "classificação de manifestações" in blocos[0]["text"] and "F1 0,74" in blocos[1]["text"]


def test_cli_plano_e_confirmacao_de_gasto(capsys):
    assert cli.main(["plano-sintetico", "--n", "14"]) == 0
    assert '"golden_path"' in capsys.readouterr().out
    assert cli.main(["sintetico", "--n", "3"]) == 1   # sem --sim não chama o modelo
    assert "--sim" in capsys.readouterr().out


def test_documento_de_papeis_esta_em_dia():
    from metaexp.core.papeis_doc import markdown
    doc = (ROOT / "docs/papeis-e-responsabilidades.md").read_text(encoding="utf-8")
    assert doc == markdown(), "rode `python -m metaexp papeis` para regerar o documento"
