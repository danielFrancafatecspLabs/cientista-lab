import json
import subprocess
import sys

from metaexp.core import kit
from metaexp.core.schemas import DetalhesTecnicos, Ficha, Metrica, MetricaTecnica, ProtocoloAvaliacao


def _ficha(golden="classificacao-supervisionada") -> Ficha:
    return Ficha(id="EXP-T", titulo="Triagem de chamados", golden_path=golden, bo="Ana", sponsor="Bia",
                 hipotese="Acreditamos que a triagem automática irá reduzir em 30% o retrabalho para o suporte.",
                 metricas=[Metrica(nome="retrabalho", descricao="r", criterio_aceite="Redução ≥ 30%", obrigatoria=True)],
                 detalhes_tecnicos=DetalhesTecnicos(stack="Python", baseline="regras, f1 0,55", abordagem_escolhida="classificador",
                                                    avaliacao=ProtocoloAvaliacao(conjunto="500 chamados rotulados", tamanho=500,
                                                                                 metricas=[MetricaTecnica(nome="f1_macro", alvo="≥ 0,80")],
                                                                                 gate_regressao="queda > 2 p.p.")))


def test_meta_numerica():
    assert kit.meta_numerica("≥ 0,85") == {"op": ">=", "valor": 0.85}
    assert kit.meta_numerica("≥ 85%") == {"op": ">=", "valor": 0.85}
    assert kit.meta_numerica("< 2000 ms") == {"op": "<", "valor": 2000.0}
    assert kit.meta_numerica("alta") is None


def test_avaliador_gerado_roda_e_bloqueia_regressao(tmp_path):
    files = kit.arquivos(_ficha())
    assert {"experimento.yaml", "README.md", "eval/avaliar.py", ".github/workflows/experimento.yml"} <= set(files)
    for nome, conteudo in files.items():
        p = tmp_path / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
    ev = tmp_path / "eval"
    casos = [{"id": f"c{i}", "esperado": "a" if i % 2 else "b"} for i in range(10)]
    (ev / "casos.jsonl").write_text("\n".join(json.dumps(c) for c in casos))

    def rodar(acertos: int, *extra):
        preds = [{"id": c["id"], "previsto": c["esperado"] if i < acertos else "x"} for i, c in enumerate(casos)]
        (ev / "predicoes.jsonl").write_text("\n".join(json.dumps(p) for p in preds))
        return subprocess.run([sys.executable, str(ev / "avaliar.py"), "--ci", *extra], capture_output=True, text=True, cwd=tmp_path)

    ok = rodar(10, "--congelar-baseline")
    assert ok.returncode == 0 and "todas as metas atendidas" in ok.stdout
    ruim = rodar(5)                               # f1 abaixo de 0,80 e regressão contra o baseline
    assert ruim.returncode == 1 and "não atende" in ruim.stdout and "regressão em f1_macro" in ruim.stdout
    assert len((ev / "historico.csv").read_text().splitlines()) == 3


def test_zip_tem_a_pasta_do_experimento():
    import io
    import zipfile
    data = kit.zipar(kit.arquivos(_ficha("rag-busca-semantica")), kit.nome_pasta(_ficha()))
    nomes = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "triagem-de-chamados/eval/avaliar.py" in nomes
    avaliador = zipfile.ZipFile(io.BytesIO(data)).read("triagem-de-chamados/eval/avaliar.py").decode()
    assert 'FAMILIA = "busca"' in avaliador
