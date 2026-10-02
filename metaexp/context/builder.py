"""Montagem dos contextos de cada agente.

Contexto estável (papel, metodologia, catálogo de golden paths) vai no prompt de
sistema e é idêntico byte a byte entre requisições, para aproveitar o cache.
Contexto variável (casos semelhantes do corpus, perfil de um arquivo, artefatos
de etapas anteriores) entra nas mensagens ou chega como resultado de
ferramenta, nunca no prompt de sistema.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..schemas import Experimento, Ficha
from .golden_paths import GOLDEN_PATHS

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent / "prompts"


@lru_cache(maxsize=None)
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def prompt(nome: str) -> str:
    return _read(PROMPTS / f"{nome}.md")


def metodologia() -> str:
    return _read(HERE / "metodologia.md")


def catalogo_golden_paths() -> str:
    linhas = ["# Catálogo de golden paths", ""]
    for g in GOLDEN_PATHS:
        linhas.append(f"- **{g['id']}** ({g['tecnologia']}): {g['nome']}. Quando usar: {g['quando_usar']} "
                      f"Dados típicos: {g['dados_tipicos']}. Métricas: {', '.join(g['metricas_padrao'])}. "
                      f"Skills: {', '.join(g['skills'])}. Amostra mínima: {g['amostra_minima']}.")
    return "\n".join(linhas)


def _join(*parts: str) -> str:
    return "\n\n---\n\n".join(p for p in parts if p)


def system_cientista() -> str:
    return _join(prompt("cientista"), metodologia(), catalogo_golden_paths())


def system_bancada(papel: str, instrucoes: str) -> str:
    return _join(prompt("bancada"), f"# Seu papel: {papel}\n\n{instrucoes}", metodologia(), catalogo_golden_paths())


def system_sintetico() -> str:
    return _join(prompt("sintetico"), metodologia(), catalogo_golden_paths())


def system_ingestao() -> str:
    return _join(prompt("ingestao"), metodologia())


def ficha_json(ficha: Ficha) -> str:
    return json.dumps(ficha.model_dump(exclude_none=True), ensure_ascii=False, indent=2)


def exemplos_reais(exps: list[Experimento], limite_chars: int = 12000) -> str:
    """Bloco de experimentos de referência para few-shot, limitado em tamanho."""
    out, total = [], 0
    for e in exps:
        txt = e.model_dump_json(exclude_none=True, exclude={"plano"})
        if total + len(txt) > limite_chars:
            break
        out.append(f"<experimento_referencia id=\"{e.id}\">\n{txt}\n</experimento_referencia>")
        total += len(txt)
    return "\n".join(out)
