"""Busca lexical BM25 em português, sem dependências externas.

Suficiente para algumas centenas ou milhares de experimentos. Para um corpus
maior, troque esta classe por busca vetorial mantendo a interface `search`.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre entre
e ou mas que se como quando onde qual quais quem cujo ao aos à às pelo pela pelos pelas
é ser são foi era está estão ter tem têm há isso isto esse essa este esta aquele aquela
mais menos muito pouco já não sim também só cada todo toda todos todas seu sua seus suas
nosso nossa nossos nossas meu minha eles elas ele ela nós você vocês lhe lhes me te
""".split())


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    text = _strip_accents(text.lower())
    toks = re.findall(r"[a-z0-9]+", text)
    out = []
    for t in toks:
        if len(t) < 3 or t in STOPWORDS:
            continue
        # Stemming leve: plural e sufixos mais comuns.
        for suf in ("coes", "mente", "acao", "cao", "oes", "ais", "eis", "es", "s"):
            if len(t) > len(suf) + 3 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_tokens: list[str], i: int) -> float:
        d, length = self.docs[i], self.lens[i]
        s = 0.0
        for t in query_tokens:
            if t not in d:
                continue
            tf = d[t]
            s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / (self.avg or 1)))
        return s

    def search(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        q = tokenize(query)
        scored = [(i, self.score(q, i)) for i in range(len(self.docs))]
        scored = [x for x in scored if x[1] > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
