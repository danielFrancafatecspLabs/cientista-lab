"""Gerador de Ficha de Experimentação: o documento final no padrão beOn Labs."""

from __future__ import annotations

from metaexp.corpus.golden_paths import BY_ID as GOLDEN
from metaexp.core.schemas import Ficha

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
    d = f.detalhes_tecnicos
    if d:
        partes += ["## Desenho técnico"]
        partes += [x for x in [linha("Stack", d.stack) if d.stack else None, linha("Fontes de dados", d.fontes_dados) if d.fontes_dados else None,
                               linha("Baseline", d.baseline) if d.baseline else None,
                               linha("Abordagem escolhida", d.abordagem_escolhida) if d.abordagem_escolhida else None] if x]
        if d.restricoes:
            partes += ["**Restrições:**", *[f"- {r}" for r in d.restricoes]]
        if d.avaliacao:
            a = d.avaliacao
            partes += ["**Protocolo de avaliação:**", f"- Conjunto: {a.conjunto}" + (f" ({a.tamanho} casos)" if a.tamanho else "")]
            if a.divisao:
                partes.append(f"- Divisão: {a.divisao}")
            if a.gate_regressao:
                partes.append(f"- Gate de regressão: {a.gate_regressao}")
            if a.metricas:
                partes += ["", "| Métrica técnica | Alvo | Baseline | Sustenta |", "|---|---|---|---|",
                           *[f"| {m.nome} | {m.alvo} | {m.baseline or '—'} | {m.liga_a or '—'} |" for m in a.metricas]]
        if d.arquitetura:
            partes += ["**Arquitetura:**", *[f"{i}. {c}" for i, c in enumerate(d.arquitetura, 1)]]
        if d.abordagens:
            partes += ["**Abordagens avaliadas:**", "| Abordagem | Custo | Latência | Complexidade | Recomendada |", "|---|---|---|---|---|",
                       *[f"| {a.nome} | {a.custo} | {a.latencia} | {a.complexidade} | {'sim' if a.recomendada else 'não'} |" for a in d.abordagens]]
        if d.riscos_tecnicos:
            partes += ["**Riscos técnicos:**", *[f"- {r}" for r in d.riscos_tecnicos]]
    if f.skills:
        partes += ["## Skills necessárias", ", ".join(f.skills)]
    if f.riscos:
        partes += ["## Riscos", *[f"- {r}" for r in f.riscos]]
    if f.execucao:
        partes += ["", linha("Execução", "Laboratório (bancada de agentes)" if f.execucao == "laboratorio" else "Solicitante")]
    return "\n".join(partes).strip() + "\n"
