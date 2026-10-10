"""Regras do método oficial do beOn Labs, validadas de forma determinística.

O prompt do Cientista pede essas regras ao modelo; este módulo as confere no
código. A ficha só é gerada quando `pendencias(ficha)` volta vazia.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metaexp.core.schemas import Ficha, Metrica

MAX_PALAVRAS_TITULO = 3
MAX_CHARS_HIPOTESE = 240          # aproximação de "máximo 2 linhas"
LIMIAR_AUTO_INGESTAO = 400        # caracteres
MIN_SECOES_AUTO_INGESTAO = 3

_COMPARADOR = re.compile(r"(≥|≤|>=|<=|>|<|=|≠|\bentre\b|\bno máximo\b|\bno mínimo\b|\baté\b|\bpelo menos\b)", re.I)
_NUMERO = re.compile(r"\d")


def criterio_valido(criterio: str | None) -> bool:
    """Critério de aceite = valor numérico + condição clara (ex.: 'Acurácia ≥ 85%')."""
    return bool(criterio) and bool(_NUMERO.search(criterio)) and bool(_COMPARADOR.search(criterio))


def hipotese_valida(h: str | None) -> list[str]:
    if not h:
        return ["hipótese ausente"]
    problemas = []
    if not h.strip().lower().startswith("acreditamos que"):
        problemas.append("a hipótese deve começar com 'Acreditamos que...'")
    if len(h) > MAX_CHARS_HIPOTESE or h.count("\n") > 1:
        problemas.append("a hipótese deve ter no máximo 2 linhas")
    if not _NUMERO.search(h):
        problemas.append("a hipótese deve ser mensurável (inclua o resultado numérico esperado)")
    return problemas


def titulo_valido(t: str | None) -> list[str]:
    if not t:
        return ["nome do experimento ausente"]
    if len(t.split()) > MAX_PALAVRAS_TITULO:
        return [f"o nome do experimento deve ter no máximo {MAX_PALAVRAS_TITULO} palavras"]
    return []


def metricas_validas(metricas: list["Metrica"]) -> list[str]:
    if not metricas:
        return ["nenhuma métrica definida"]
    sem = [m.nome for m in metricas if not criterio_valido(m.criterio_aceite)]
    out = []
    if sem:
        out.append(f"critério de aceite sem valor numérico ou condição clara: {', '.join(sem)}")
    if not any(m.obrigatoria for m in metricas):
        out.append("nenhuma métrica obrigatória")
    return out


# Checklist de qualidade mínima, na ordem do fluxo obrigatório.
CHECKLIST = [
    ("problema", "Problema identificado"),
    ("publico_afetado", "Impacto"),
    ("objetivo", "Objetivo definido"),
    ("hipotese", "Hipótese mensurável"),
    ("metodologia", "Metodologia compreensível"),
    ("amostra", "Amostra definida"),
    ("metricas", "Métricas e critérios com valores numéricos"),
    ("bo", "Responsável pelo experimento (BO)"),
    ("sponsor", "Patrocinador (SPONSOR)"),
    ("titulo", "Nome do experimento"),
]


def pendencias(f: "Ficha") -> list[str]:
    """Itens que impedem gerar a ficha, em linguagem de checklist."""
    out: list[str] = []
    for campo, rotulo in CHECKLIST:
        valor = getattr(f, campo)
        if not valor:
            out.append(f"{rotulo}: ausente")
    if f.hipotese:
        out += hipotese_valida(f.hipotese)
    if f.metricas:
        out += metricas_validas(f.metricas)
    if f.titulo:
        out += titulo_valido(f.titulo)
    if f.objetivo and f.hipotese and f.objetivo.strip().lower() == f.hipotese.strip().lower():
        out.append("objetivo e hipótese estão iguais: o objetivo diz o que será feito; a hipótese, o que se espera comprovar")
    return out


def precisa_auto_ingestao(texto: str) -> bool:
    """Texto longo ou com três ou mais seções estruturadas (títulos, rótulos 'X:' ou listas)."""
    if len(texto) > LIMIAR_AUTO_INGESTAO:
        return True
    secoes = 0
    for linha in texto.splitlines():
        l = linha.strip()
        if re.match(r"^(#{1,6}\s+\S|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ú ()/]{1,40}:\s*\S?|\d+[.)]\s+[A-ZÁÉÍÓÚ])", l):
            secoes += 1
    return secoes >= MIN_SECOES_AUTO_INGESTAO
