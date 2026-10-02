"""Linha de comando: `python -m metaexp <comando>`.

  servir                   sobe a API e o front em http://localhost:8000
  corpus                   mostra a composição do corpus (reais × sintéticos, domínios, vereditos)
  ingerir                  converte documentos de data/real/ em registros do corpus
  sintetico --n 30         gera experimentos sintéticos equilibrados (--batch usa a Batches API)
  plano-sintetico --n 30   mostra a cobertura das especificações, sem chamar o modelo
  avaliar --n 5            roda a avaliação do Cientista com solicitantes simulados
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime

from .config import ROOT, settings
from .corpus.store import Corpus


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="metaexp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("servir")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sub.add_parser("corpus")
    sub.add_parser("ingerir")
    for nome in ("sintetico", "plano-sintetico"):
        p = sub.add_parser(nome)
        p.add_argument("--n", type=int, default=30)
        p.add_argument("--seed", type=int, default=7)
        p.add_argument("--prefixo", default=f"SIN{datetime.now():%y%m%d}")
        if nome == "sintetico":
            p.add_argument("--batch", action="store_true", help="usa a Message Batches API (50%% do custo, assíncrono)")
            p.add_argument("--sim", action="store_true", help="confirma o gasto com o modelo")
    av = sub.add_parser("avaliar")
    av.add_argument("--n", type=int, default=5)
    av.add_argument("--sem-juiz", action="store_true")
    av.add_argument("--sim", action="store_true", help="confirma o gasto com o modelo")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "servir":
        import uvicorn

        from .api.app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    corpus = Corpus.from_dirs(settings.corpus_dirs)

    if args.cmd == "corpus":
        print(json.dumps(corpus.stats(), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "plano-sintetico":
        from .synthetic.taxonomy import amostrar, cobertura
        specs = amostrar(args.n, args.seed, args.prefixo)
        print(json.dumps(cobertura(specs), ensure_ascii=False, indent=2))
        return 0

    from .llm.client import AnthropicLLM
    llm = AnthropicLLM()

    if args.cmd == "ingerir":
        from .synthetic.ingest import ingerir
        ids = ingerir(llm)
        print(f"{len(ids)} experimento(s) ingerido(s): {', '.join(ids) or '-'}")
        return 0

    if args.cmd in ("sintetico", "avaliar") and not args.sim:
        n = args.n
        chamadas = n if args.cmd == "sintetico" else n * 30
        print(f"Isto faz cerca de {chamadas} chamadas ao modelo {settings.model}. Rode de novo com --sim para confirmar.")
        return 1

    if args.cmd == "sintetico":
        from .synthetic.generator import gerar, gerar_lote_batch
        from .synthetic.taxonomy import amostrar
        destino = ROOT / "data/corpus/sintetico"
        specs = amostrar(args.n, args.seed, args.prefixo)
        rel = gerar_lote_batch(specs, llm.client, destino, corpus) if args.batch else gerar(specs, llm, destino, corpus)
        print(rel.resumo())
        return 0

    if args.cmd == "avaliar":
        from .evals.runner import rodar
        saida = ROOT / f"data/evals/avaliacao-{datetime.now():%Y%m%d-%H%M%S}.json"
        out = rodar(corpus, llm, n=args.n, saida=saida, usar_juiz=not args.sem_juiz)
        print(json.dumps(out["agregado"], ensure_ascii=False, indent=2))
        print(f"detalhes em {saida}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
