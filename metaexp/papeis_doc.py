"""Gera docs/papeis-e-responsabilidades.md a partir de metaexp/papeis.py."""

from __future__ import annotations

from .papeis import ETAPAS_CICLO, JORNADAS, RESPONSABILIDADES


def markdown() -> str:
    L: list[str] = []
    L.append("# Papéis e responsabilidades do METAEXP\n")
    L.append("O METAEXP é a plataforma interna de experimentação (IDP) do beOn Labs. Este documento define quem participa de um experimento, o que cada papel faz e por qual jornada entra na plataforma. A fonte é `metaexp/papeis.py`, a mesma usada pelo backend e pela rota `GET /api/papeis`.\n")
    L.append("## Quem entra pela plataforma\n")
    L.append("A primeira tela pede que a pessoa escolha o papel. Cada papel tem uma jornada própria, com prompt, ferramentas, etapas e encaminhamento diferentes.\n")
    sol, dev = JORNADAS["solicitante"], JORNADAS["desenvolvedor"]

    def prefs(j):
        return "<br>".join(f"{p.pergunta} {', '.join(r for _, r in p.opcoes)}" for p in j.preferencias)

    L += [
        "| | Solicitante | Desenvolvedor |", "|---|---|---|",
        f"| Quem é | {sol.descricao} | {dev.descricao} |",
        f"| Promessa | {sol.promessa} | {dev.promessa} |",
        "| Tom da conversa | Fluida e cadenciada, linguagem de negócio, nenhum termo técnico | Técnica e profunda desde a primeira pergunta, como uma revisão de design |",
        "| O que o Cientista aprofunda | Frequência e custo do problema, impacto no cliente, quem decide, o que muda se der certo | Stack, fontes de dados, restrições, baseline, abordagens com trade-offs, protocolo de avaliação, arquitetura |",
        f"| Etapas | {' → '.join(sol.etapas)} | {' → '.join(dev.etapas)} |",
        "| Tecnologia | Escolhida pelo laboratório e registrada na ficha, sem explicação técnica na conversa | Discutida abertamente: 2 a 4 abordagens com prós, contras, custo, latência e recomendação |",
        "| Ferramentas exclusivas | — | " + ", ".join(f"`{t}`" for t in dev.ferramentas if t not in sol.ferramentas) + " |",
        "| Encaminhamento | Sempre para a bancada do laboratório | Recebe ficha, desenho técnico e kit; a bancada é opcional |",
        f"| Personalização na entrada | {prefs(sol)} | {prefs(dev)} |\n",
    ]
    L.append("As duas jornadas seguem o mesmo método oficial: hipótese começando com \"Acreditamos que\", critérios de aceite numéricos, nome com até 3 palavras, BO e Sponsor, checklist de qualidade mínima e Gerador de Ficha. O que muda é a profundidade e o vocabulário.\n")
    L.append("## Todos os papéis\n")
    for r in RESPONSABILIDADES:
        tipo = "agente de IA" if r["tipo"] == "agente" else "pessoa"
        L.append(f"### {r['papel']} ({tipo})\n")
        L.append(f"{r['missao']}\n")
        L += [f"- {x}" for x in r["responsabilidades"]]
        L.append("")
    L.append("## Matriz por etapa do ciclo\n")
    L.append("R = responsável por executar · A = aprova ou decide · C = consultado · I = informado\n")
    L.append("| Papel | " + " | ".join(ETAPAS_CICLO) + " |")
    L.append("|---|" + "---|" * len(ETAPAS_CICLO))
    for r in RESPONSABILIDADES:
        L.append(f"| {r['papel']} | " + " | ".join(r["raci"]) + " |")
    L.append("\nNa jornada do solicitante, as colunas Construção e Qualidade ficam com os agentes da bancada. Na jornada do desenvolvedor, quando ele constrói por conta própria, essas colunas ficam com ele; se escolher a bancada, voltam para os agentes.\n")
    L.append("## Como mudar\n")
    L += [
        "- Papéis, preferências, ferramentas e encaminhamentos: `metaexp/papeis.py`.",
        "- Tom e profundidade de cada jornada: `metaexp/prompts/jornada_solicitante.md` e `metaexp/prompts/jornada_desenvolvedor.md`.",
        "- Regras comuns do método: `metaexp/prompts/cientista.md` e `metaexp/metodo.py`.",
        "- Depois de mudar, regere este documento com `python -m metaexp papeis` e rode `python -m metaexp avaliar --n 5 --sim`.",
    ]
    return "\n".join(L) + "\n"
