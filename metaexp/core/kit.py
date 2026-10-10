"""Kit do experimento: o experimento como código.

Para o desenvolvedor, a ficha vira um repositório inicial pronto para rodar:

    experimento.yaml            contrato legível: hipótese, critérios, protocolo, gates
    README.md                   contexto, como rodar e como reportar
    eval/metas.json             metas em formato de máquina (lidas pelo avaliador)
    eval/avaliar.py             avaliador sem dependências: métricas, metas e regressão
    eval/casos.exemplo.jsonl    formato dos casos de teste
    .github/workflows/experimento.yml   CI: avalia a cada push e bloqueia regressões
    RESULTADOS.md               modelo do relatório que volta para o Lab
    docs/ficha.md               a ficha aprovada

A ideia vem da avaliação contínua de agentes em CI (SWE-CI): o que importa não
é passar uma vez, é não regredir a cada mudança. O histórico de cada execução
fica em eval/historico.csv.
"""

from __future__ import annotations

import io
import json
import re
import zipfile

from metaexp.core.ficha_doc import markdown as ficha_markdown
from metaexp.core.schemas import Ficha, ProtocoloAvaliacao

# Família de avaliação por golden path: define o formato dos casos e as métricas calculadas.
FAMILIA = {
    "rag-busca-semantica": "busca", "texto-livre-voc": "classificacao", "classificacao-supervisionada": "classificacao",
    "correlacao-eventos": "classificacao", "automacao-documental": "extracao", "visao-computacional": "classificacao",
    "previsao-demanda": "previsao",
}

EXEMPLOS = {
    "busca": [{"id": "q1", "pergunta": "Como faço a portabilidade?", "relevantes": ["doc-12"], "resposta_esperada": "..."}],
    "classificacao": [{"id": "c1", "entrada": "...", "esperado": "reclamacao"}],
    "extracao": [{"id": "d1", "documento": "nf-001.pdf", "esperado": {"cnpj": "00.000.000/0001-00", "valor": "123,45"}}],
    "previsao": [{"id": "2026-01", "esperado": 1520.0}],
}
PREDICOES = {
    "busca": [{"id": "q1", "recuperados": ["doc-12", "doc-3"], "resposta": "...", "acertou": True, "latencia_ms": 820}],
    "classificacao": [{"id": "c1", "previsto": "reclamacao", "latencia_ms": 40}],
    "extracao": [{"id": "d1", "previsto": {"cnpj": "00.000.000/0001-00", "valor": "123,45"}}],
    "previsao": [{"id": "2026-01", "previsto": 1490.0}],
}

_ALVO = re.compile(r"(≥|>=|≤|<=|>|<|=)\s*([\d.,]+)\s*(%?)")


def meta_numerica(alvo: str) -> dict | None:
    """'≥ 0,85' -> {'op': '>=', 'valor': 0.85}; '≥ 85%' -> 0.85; '< 2000 ms' -> 2000."""
    m = _ALVO.search(alvo or "")
    if not m:
        return None
    op = {"≥": ">=", "≤": "<="}.get(m.group(1), m.group(1))
    num = m.group(2).replace(".", "").replace(",", ".") if "," in m.group(2) else m.group(2)
    try:
        valor = float(num)
    except ValueError:
        return None
    if m.group(3) == "%":
        valor /= 100
    return {"op": op, "valor": valor}


def _chave(nome: str) -> str:
    return re.sub(r"[^a-z0-9@]+", "_", nome.lower()).strip("_")


def metas(protocolo: ProtocoloAvaliacao | None) -> dict:
    if not protocolo:
        return {"metricas": [], "gate_regressao": None}
    out = []
    for m in protocolo.metricas:
        out.append({"nome": _chave(m.nome), "rotulo": m.nome, "alvo": m.alvo, "meta": meta_numerica(m.alvo),
                    "baseline": m.baseline, "liga_a": m.liga_a})
    return {"metricas": out, "gate_regressao": protocolo.gate_regressao, "tolerancia_regressao": 0.02}


def _yaml_str(v: str | None) -> str:
    return json.dumps(v or "", ensure_ascii=False)


def experimento_yaml(f: Ficha, familia: str) -> str:
    d = f.detalhes_tecnicos
    a = d.avaliacao if d else None
    linhas = [
        f"id: {f.id or 'EXP'}",
        f"titulo: {_yaml_str(f.titulo)}",
        f"bo: {_yaml_str(f.bo)}",
        f"sponsor: {_yaml_str(f.sponsor)}",
        f"golden_path: {f.golden_path or 'nenhum'}",
        f"familia_avaliacao: {familia}",
        f"hipotese: {_yaml_str(f.hipotese)}",
        f"objetivo: {_yaml_str(f.objetivo)}",
        "criterios_de_negocio:",
        *[f"  - metrica: {_yaml_str(m.nome)}\n    criterio: {_yaml_str(m.criterio_aceite)}\n    obrigatoria: {'true' if m.obrigatoria else 'false'}"
          for m in f.metricas],
        "desenho:",
        f"  stack: {_yaml_str(d.stack if d else None)}",
        f"  baseline: {_yaml_str(d.baseline if d else None)}",
        f"  abordagem: {_yaml_str(d.abordagem_escolhida if d else None)}",
        "avaliacao:",
        f"  conjunto: {_yaml_str(a.conjunto if a else None)}",
        f"  tamanho: {a.tamanho if a and a.tamanho else 'null'}",
        f"  divisao: {_yaml_str(a.divisao if a else None)}",
        f"  gate_regressao: {_yaml_str(a.gate_regressao if a else None)}",
        "  metricas:",
        *[f"    - nome: {_yaml_str(m.nome)}\n      alvo: {_yaml_str(m.alvo)}\n      baseline: {_yaml_str(m.baseline)}" for m in (a.metricas if a else [])],
    ]
    return "\n".join(linhas) + "\n"


AVALIADOR = r'''"""Avaliador do experimento (gerado pelo METAEXP). Sem dependências externas.

Uso:
    python eval/avaliar.py                       avalia eval/predicoes.jsonl contra eval/casos.jsonl
    python eval/avaliar.py --ci                  idem, e sai com erro se uma meta falhar ou houver regressão
    python eval/avaliar.py --congelar-baseline   grava o resultado atual como baseline de regressão

Cada execução é anexada a eval/historico.csv, com o commit, para acompanhar a evolução.
"""
import argparse, csv, json, os, statistics, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FAMILIA = "__FAMILIA__"


def ler_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def metricas_busca(casos, preds, k=5):
    rec, rr, acerto = [], [], []
    for c in casos:
        p = preds.get(c["id"], {})
        recup = p.get("recuperados", [])[:k]
        rel = set(c.get("relevantes", []))
        rec.append(len(rel & set(recup)) / len(rel) if rel else 0.0)
        pos = next((i for i, d in enumerate(recup, 1) if d in rel), None)
        rr.append(1 / pos if pos else 0.0)
        if "acertou" in p:
            acerto.append(1.0 if p["acertou"] else 0.0)
    out = {f"recall@{k}": statistics.mean(rec) if rec else 0.0, "mrr": statistics.mean(rr) if rr else 0.0}
    if acerto:
        out["respostas_corretas"] = statistics.mean(acerto)
    return out


def metricas_classificacao(casos, preds):
    y = [c["esperado"] for c in casos]
    yp = [preds.get(c["id"], {}).get("previsto") for c in casos]
    classes = sorted(set(y))
    f1s = []
    for cl in classes:
        tp = sum(1 for a, b in zip(y, yp) if a == cl and b == cl)
        fp = sum(1 for a, b in zip(y, yp) if a != cl and b == cl)
        fn = sum(1 for a, b in zip(y, yp) if a == cl and b != cl)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return {"acuracia": sum(a == b for a, b in zip(y, yp)) / len(y) if y else 0.0,
            "f1_macro": statistics.mean(f1s) if f1s else 0.0}


def metricas_extracao(casos, preds):
    total = certos = 0
    for c in casos:
        prev = preds.get(c["id"], {}).get("previsto", {})
        for campo, valor in c["esperado"].items():
            total += 1
            certos += str(prev.get(campo, "")).strip() == str(valor).strip()
    return {"extracao_correta": certos / total if total else 0.0}


def metricas_previsao(casos, preds):
    erros, vies = [], []
    for c in casos:
        real, prev = c["esperado"], preds.get(c["id"], {}).get("previsto")
        if prev is None or not real:
            continue
        erros.append(abs(prev - real) / abs(real))
        vies.append((prev - real) / abs(real))
    return {"mape": statistics.mean(erros) if erros else 1.0, "vies": statistics.mean(vies) if vies else 0.0}


def operacionais(preds):
    lat = sorted(p["latencia_ms"] for p in preds.values() if "latencia_ms" in p)
    if not lat:
        return {}
    return {"latencia_p95_ms": lat[min(len(lat) - 1, int(0.95 * len(lat)))]}


CALC = {"busca": metricas_busca, "classificacao": metricas_classificacao, "extracao": metricas_extracao, "previsao": metricas_previsao}


def atende(valor, meta):
    if meta is None or valor is None:
        return None
    op, alvo = meta["op"], meta["valor"]
    return {">=": valor >= alvo, ">": valor > alvo, "<=": valor <= alvo, "<": valor < alvo, "=": abs(valor - alvo) < 1e-9}[op]


def commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "local")[:7]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", default=AQUI / "casos.jsonl")
    ap.add_argument("--predicoes", default=AQUI / "predicoes.jsonl")
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--congelar-baseline", action="store_true")
    a = ap.parse_args()

    casos = ler_jsonl(a.casos)
    preds = {p["id"]: p for p in ler_jsonl(a.predicoes)}
    resultado = {**CALC[FAMILIA](casos, preds), **operacionais(preds)}
    metas = json.loads((AQUI / "metas.json").read_text(encoding="utf-8"))
    baseline_p = AQUI / "baseline.json"
    baseline = json.loads(baseline_p.read_text(encoding="utf-8")) if baseline_p.exists() else {}
    tol = metas.get("tolerancia_regressao", 0.02)

    falhas = []
    print(f"\n{'métrica':<22}{'valor':>10}  {'meta':<14}{'status'}")
    for m in metas["metricas"]:
        v = resultado.get(m["nome"])
        ok = atende(v, m["meta"])
        status = "sem dado" if v is None else ("ok" if ok else ("falhou" if ok is False else "sem meta"))
        if ok is False:
            falhas.append(f"{m['rotulo']}: {v:.4f} não atende {m['alvo']}")
        print(f"{m['rotulo']:<22}{(f'{v:.4f}' if v is not None else '—'):>10}  {m['alvo']:<14}{status}")
    for nome, antes in baseline.items():
        agora = resultado.get(nome)
        meta = next((m["meta"] for m in metas["metricas"] if m["nome"] == nome), None)
        menor_melhor = bool(meta and meta["op"] in ("<", "<="))
        if agora is not None and ((agora < antes - tol) if not menor_melhor else (agora > antes * (1 + tol))):
            falhas.append(f"regressão em {nome}: {antes:.4f} → {agora:.4f}")

    hist = AQUI / "historico.csv"
    novo = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if novo:
            w.writerow(["quando", "commit", *sorted(resultado)])
        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%S"), commit(), *[round(resultado[k], 4) for k in sorted(resultado)]])
    (AQUI / "resultado.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    if a.congelar_baseline:
        baseline_p.write_text(json.dumps(resultado, indent=2), encoding="utf-8")
        print("\nbaseline de regressão atualizado.")
    if falhas:
        print("\n" + "\n".join(f"✗ {f}" for f in falhas))
        if a.ci:
            sys.exit(1)
    else:
        print("\n✓ todas as metas atendidas, sem regressão.")


if __name__ == "__main__":
    main()
'''

WORKFLOW = """name: experimento
on:
  push:
  pull_request:
jobs:
  avaliar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Gerar predições
        run: |
          # Troque pelo comando que roda sua solução sobre eval/casos.jsonl
          # e grava eval/predicoes.jsonl (formato em eval/predicoes.exemplo.jsonl).
          test -f eval/predicoes.jsonl || cp eval/predicoes.exemplo.jsonl eval/predicoes.jsonl
          test -f eval/casos.jsonl || cp eval/casos.exemplo.jsonl eval/casos.jsonl
      - name: Avaliar contra as metas e o baseline
        run: python eval/avaliar.py --ci
      - uses: actions/upload-artifact@v4
        with:
          name: resultado-${{ github.sha }}
          path: eval/resultado.json
"""


def readme(f: Ficha, familia: str, stack: str | None) -> str:
    d = f.detalhes_tecnicos
    a = d.avaliacao if d else None
    alvos = "\n".join(f"| {m.nome} | {m.alvo} | {m.baseline or '—'} |" for m in (a.metricas if a else [])) or "| — | — | — |"
    return f"""# {f.titulo or 'Experimento'}

`{f.id or 'EXP'}` · gerado pelo METAEXP do beOn Labs · BO: {f.bo or '—'} · Sponsor: {f.sponsor or '—'}

> {f.hipotese or 'Hipótese a definir.'}

## O que estamos testando

{f.objetivo or '—'}

**Problema:** {f.problema or '—'}

**Baseline:** {(d.baseline if d else None) or '—'}

**Abordagem:** {(d.abordagem_escolhida if d else None) or '—'}

## Metas técnicas

| Métrica | Meta | Baseline |
|---|---|---|
{alvos}

Gate de regressão: {(a.gate_regressao if a else None) or 'queda maior que 2 p.p. em qualquer métrica'}.

## Como rodar

1. Monte o conjunto de avaliação em `eval/casos.jsonl` ({(a.conjunto if a else None) or 'veja a ficha'}). O formato está em `eval/casos.exemplo.jsonl`.
2. Construa a solução em `src/` ({stack or 'na sua stack'}) e grave as saídas em `eval/predicoes.jsonl` (formato em `eval/predicoes.exemplo.jsonl`).
3. Avalie: `python eval/avaliar.py`. Na primeira versão aceita, congele o baseline com `python eval/avaliar.py --congelar-baseline`.
4. O CI (`.github/workflows/experimento.yml`) roda a avaliação a cada push e bloqueia mudanças que quebram metas ou regridem. O histórico fica em `eval/historico.csv`.

Família de avaliação: **{familia}**. As metas vêm de `eval/metas.json`, gerado a partir da ficha; mude a ficha, não o arquivo.

## Ao terminar

Preencha `RESULTADOS.md` e envie ao Lab pelo METAEXP. O Agente Analista compara com os critérios de negócio da ficha e emite o parecer.
"""


def resultados_md(f: Ficha) -> str:
    linhas = "\n".join(f"| {m.nome} | {m.criterio_aceite} | | |" for m in f.metricas) or "| | | | |"
    return f"""# Resultados · {f.titulo or 'Experimento'}

| Critério de negócio | Meta | Resultado | Atendido? |
|---|---|---|---|
{linhas}

## Métricas técnicas finais

Cole aqui o conteúdo de `eval/resultado.json` e o trecho final de `eval/historico.csv`.

## O que aprendemos

-

## Riscos e próximos passos

-
"""


def arquivos(f: Ficha, versao: int = 1) -> dict[str, str]:
    familia = FAMILIA.get(f.golden_path or "", "classificacao")
    d = f.detalhes_tecnicos
    ex = "\n".join(json.dumps(x, ensure_ascii=False) for x in EXEMPLOS[familia]) + "\n"
    pr = "\n".join(json.dumps(x, ensure_ascii=False) for x in PREDICOES[familia]) + "\n"
    return {
        "experimento.yaml": experimento_yaml(f, familia),
        "README.md": readme(f, familia, d.stack if d else None),
        "eval/metas.json": json.dumps(metas(d.avaliacao if d else None), ensure_ascii=False, indent=2) + "\n",
        "eval/avaliar.py": AVALIADOR.replace("__FAMILIA__", familia),
        "eval/casos.exemplo.jsonl": ex,
        "eval/predicoes.exemplo.jsonl": pr,
        ".github/workflows/experimento.yml": WORKFLOW,
        "RESULTADOS.md": resultados_md(f),
        "docs/ficha.md": ficha_markdown(f, versao),
        "src/.gitkeep": "",
    }


def zipar(files: dict[str, str], raiz: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(files.items()):
            z.writestr(f"{raiz}/{nome}", conteudo)
    return buf.getvalue()


def nome_pasta(f: Ficha) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (f.titulo or f.id or "experimento").lower()).strip("-")
    return base or "experimento"
