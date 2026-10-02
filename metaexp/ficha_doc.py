"""Gerador de Ficha de Experimentação: o documento final no padrão beOn Labs."""

from __future__ import annotations

from .context.golden_paths import BY_ID as GOLDEN
from .schemas import Ficha

TEC = {"ia_generativa": "IA generativa", "machine_learning": "Machine learning", "estatistica": "Estatística",
       "visao_computacional": "Visão computacional", "automacao": "Automação", "otimizacao": "Otimização", "outro": "Outra"}


def markdown(f: Ficha, versao: int = 1) -> str:
    def linha(rotulo: str, valor: str | None) -> str:
        return f"**{rotulo}:** {valor or '—'}"

    gp = GOLDEN.get(f.golden_path or "")
    partes = [
        f"# {f.titulo or 'Experimento'}",
        f"`{f.id or '—'}` · versão {versao}",
        "",
        linha("Responsável (BO)", f.bo),
        linha("Patrocinador (SPONSOR)", f.sponsor),
        "",
        "## Problema", f.problema or "—",
        "## Impacto", f.publico_afetado or "—",
        "## Objetivo", f.objetivo or "—",
        "## Hipótese", f.hipotese or "—",
        "## Metodologia", f.metodologia or "—",
        linha("Tecnologia", " · ".join(x for x in [TEC.get(f.tecnologia or "", f.tecnologia), f.tecnica] if x)),
        linha("Golden path", gp["nome"] if gp else f.golden_path),
        "## Amostra", f.amostra or "—",
        linha("Dados", f.dados),
        "## Métricas e critérios de aceite",
        "| Métrica | Descrição | Critério de aceite | Obrigatória |",
        "|---|---|---|---|",
        *[f"| {m.nome} | {m.descricao} | {m.criterio_aceite} | {'sim' if m.obrigatoria else 'não'} |" for m in f.metricas],
    ]
    if f.skills:
        partes += ["## Skills necessárias", ", ".join(f.skills)]
    if f.riscos:
        partes += ["## Riscos", *[f"- {r}" for r in f.riscos]]
    if f.execucao:
        partes += ["", linha("Execução", "Laboratório (bancada de agentes)" if f.execucao == "laboratorio" else "Solicitante")]
    return "\n".join(partes).strip() + "\n"
