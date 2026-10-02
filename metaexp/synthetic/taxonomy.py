"""Eixos de variação do dataset sintético e amostragem estratificada.

A ideia é cobrir o espaço de experimentos que o laboratório encontra, e não
repetir o caso mais comum. Cada especificação combina um valor de cada eixo;
a amostragem garante que todos os valores de cada eixo apareçam de forma
equilibrada antes de qualquer combinação se repetir.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass

from ..context.golden_paths import GOLDEN_PATHS

DOMINIOS = ["rede", "atendimento", "digital", "financeiro", "suprimentos", "juridico", "rh", "marketing", "operacoes"]
PERFIS = ["negocio", "desenvolvedor"]
SITUACOES_DADOS = ["sem_dados", "amostra_pequena", "amostra_suficiente", "dados_sensiveis"]
VEREDITOS = ["validada", "parcialmente_comprovada", "invalidada", "inconclusiva"]
ESTILOS_CONVERSA = [
    "objetivo e colaborativo",
    "vago no começo, precisa ser trazido do 'quero usar IA' para o problema",
    "chega com a solução pronta e resiste a mudar",
    "não sabe medir o impacto atual",
    "muito técnico, quer pular direto para a arquitetura",
    "apressado, responde com frases curtas",
]

# Pesos aproximados do que a esteira recebe; ajuste com os dados reais.
PESO_VEREDITO = {"validada": 0.40, "parcialmente_comprovada": 0.30, "invalidada": 0.20, "inconclusiva": 0.10}
PESO_SITUACAO = {"amostra_suficiente": 0.40, "amostra_pequena": 0.35, "sem_dados": 0.15, "dados_sensiveis": 0.10}

# Domínios onde cada golden path costuma aparecer.
AFINIDADE = {
    "rag-busca-semantica": ["atendimento", "juridico", "rh", "operacoes", "suprimentos"],
    "texto-livre-voc": ["atendimento", "marketing", "digital"],
    "classificacao-supervisionada": ["digital", "financeiro", "marketing", "atendimento"],
    "correlacao-eventos": ["rede", "operacoes"],
    "automacao-documental": ["juridico", "suprimentos", "financeiro", "rh"],
    "visao-computacional": ["rede", "operacoes"],
    "previsao-demanda": ["atendimento", "operacoes", "financeiro", "rede"],
}


@dataclass(frozen=True)
class Especificacao:
    id: str
    dominio: str
    golden_path: str
    tecnologia: str
    perfil_solicitante: str
    situacao_dados: str
    veredito: str
    estilo_conversa: str

    def to_dict(self) -> dict:
        return asdict(self)


def _weighted_cycle(rng: random.Random, weights: dict[str, float], n: int) -> list[str]:
    """Lista de tamanho n com proporções próximas dos pesos, embaralhada."""
    out: list[str] = []
    for k, w in weights.items():
        out += [k] * round(w * n)
    while len(out) < n:
        out.append(rng.choices(list(weights), weights=list(weights.values()))[0])
    rng.shuffle(out)
    return out[:n]


def _balanced(rng: random.Random, values: list[str], n: int) -> list[str]:
    out = (values * (n // len(values) + 1))[:n]
    rng.shuffle(out)
    return out


def amostrar(n: int, seed: int = 7, prefixo: str = "SIN") -> list[Especificacao]:
    rng = random.Random(seed)
    gps = _balanced(rng, [g["id"] for g in GOLDEN_PATHS], n)
    perfis = _balanced(rng, PERFIS, n)
    situacoes = _weighted_cycle(rng, PESO_SITUACAO, n)
    vereditos = _weighted_cycle(rng, PESO_VEREDITO, n)
    estilos = _balanced(rng, ESTILOS_CONVERSA, n)
    tec = {g["id"]: g["tecnologia"] for g in GOLDEN_PATHS}
    specs = []
    uso_dominio: Counter[str] = Counter()
    for i in range(n):
        gp = gps[i]
        # Entre os domínios afins ao golden path, o menos usado até agora.
        candidatos = AFINIDADE.get(gp, DOMINIOS)
        menor = min(uso_dominio[d] for d in candidatos)
        dominio = rng.choice([d for d in candidatos if uso_dominio[d] == menor])
        uso_dominio[dominio] += 1
        sit = situacoes[i]
        ver = vereditos[i]
        # Coerência: sem dados não chega a "validada".
        if sit == "sem_dados" and ver == "validada":
            ver = "inconclusiva"
        specs.append(Especificacao(id=f"{prefixo}-{i + 1:04d}", dominio=dominio, golden_path=gp, tecnologia=tec[gp],
                                   perfil_solicitante=perfis[i], situacao_dados=sit, veredito=ver,
                                   estilo_conversa=estilos[i]))
    return specs


def cobertura(specs: list[Especificacao]) -> dict:
    return {eixo: dict(Counter(getattr(s, eixo) for s in specs))
            for eixo in ("dominio", "golden_path", "perfil_solicitante", "situacao_dados", "veredito")}
