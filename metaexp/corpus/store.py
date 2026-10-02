"""Corpus de experimentos: carrega registros reais e sintéticos do disco.

Cada experimento é um arquivo JSON no formato `schemas.Experimento`. Registros
reais (gerados por `metaexp ingerir`) ficam em `data/corpus/real/` e não vão
para o Git; sintéticos ficam em `data/corpus/sintetico/`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from ..schemas import Experimento
from .search import BM25

log = logging.getLogger("metaexp.corpus")


def load_dir(path: Path) -> list[Experimento]:
    out: list[Experimento] = []
    if not path.exists():
        return out
    for f in sorted(path.glob("*.json")):
        try:
            out.append(Experimento.model_validate_json(f.read_text(encoding="utf-8")))
        except (ValidationError, json.JSONDecodeError) as e:
            log.warning("ignorando %s: %s", f.name, e)
    return out


def save(exp: Experimento, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{exp.id}.json"
    path.write_text(exp.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    return path


class Corpus:
    def __init__(self, experiments: Iterable[Experimento]):
        self.experiments = list(experiments)
        self.by_id = {e.id: e for e in self.experiments}
        self.index = BM25([e.texto_busca() for e in self.experiments])

    @classmethod
    def from_dirs(cls, dirs: Iterable[Path]) -> "Corpus":
        exps: list[Experimento] = []
        seen: set[str] = set()
        for d in dirs:
            for e in load_dir(d):
                if e.id not in seen:
                    seen.add(e.id)
                    exps.append(e)
        return cls(exps)

    def search(self, query: str, k: int = 3, dominio: str | None = None) -> list[tuple[Experimento, float]]:
        hits = self.index.search(query, k=k * 3 if dominio else k)
        out = [(self.experiments[i], s) for i, s in hits]
        if dominio:
            preferred = [h for h in out if h[0].dominio == dominio]
            out = (preferred + [h for h in out if h[0].dominio != dominio])
        return out[:k]

    def stats(self) -> dict:
        from collections import Counter
        return {
            "total": len(self.experiments),
            "origem": dict(Counter(e.origem for e in self.experiments)),
            "dominio": dict(Counter(e.dominio for e in self.experiments)),
            "tecnologia": dict(Counter(e.ficha.tecnologia or "?" for e in self.experiments)),
            "perfil": dict(Counter(e.perfil_solicitante for e in self.experiments)),
            "situacao_dados": dict(Counter(e.situacao_dados for e in self.experiments)),
            "veredito": dict(Counter(e.parecer.veredito if e.parecer else "sem_parecer" for e in self.experiments)),
        }


def resumo_para_contexto(exp: Experimento) -> dict:
    """Versão compacta de um experimento para entregar ao modelo como contexto."""
    f = exp.ficha
    d = {
        "id": exp.id,
        "origem": exp.origem,
        "titulo": f.titulo,
        "dominio": exp.dominio,
        "problema": f.problema,
        "hipotese": f.hipotese,
        "tecnologia": f.tecnologia,
        "tecnica": f.tecnica,
        "metricas": [f"{m.nome} {m.meta}" for m in f.metricas],
        "amostra": exp.descricao_amostra,
        "lead_time_dias": exp.lead_time_dias,
    }
    if exp.parecer:
        d["veredito"] = exp.parecer.veredito
        d["aprendizados"] = exp.parecer.riscos[:2] + exp.parecer.proximos_passos[:1]
    return {k: v for k, v in d.items() if v not in (None, [], "")}
