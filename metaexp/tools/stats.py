"""Funções estatísticas determinísticas usadas pelos agentes (stats_tools)."""

from __future__ import annotations

import math

Z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}


def tamanho_amostra_proporcao(margem: float = 0.05, confianca: float = 0.95, p: float = 0.5) -> int:
    """n = z² · p(1 − p) / E² (Eq. 7 da proposta), arredondado para cima."""
    if not 0 < margem < 1:
        raise ValueError("margem deve estar entre 0 e 1")
    z = Z.get(round(confianca, 2))
    if z is None:
        raise ValueError(f"confiança suportada: {sorted(Z)}")
    return math.ceil(z * z * p * (1 - p) / (margem * margem))


def margem_para_n(n: int, confianca: float = 0.95, p: float = 0.5) -> float:
    """Margem de erro obtida com n registros."""
    if n <= 0:
        return 1.0
    z = Z[round(confianca, 2)]
    return z * math.sqrt(p * (1 - p) / n)


def reducao_lead_time(t_manual: float, t_meta: float) -> float:
    """ΔT = (Tman − Tmeta) / Tman (Eq. 2)."""
    return (t_manual - t_meta) / t_manual if t_manual else 0.0


def convergencia(n_conv: int, n_exec: int) -> float:
    """C = Nconv / Nexec (Eq. 1)."""
    return n_conv / n_exec if n_exec else 0.0
