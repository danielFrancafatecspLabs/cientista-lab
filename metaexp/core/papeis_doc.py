"""Gera docs/papeis-e-responsabilidades.md a partir de metaexp/core/papeis.py."""

from __future__ import annotations

from metaexp.core.descoberta import DIMENSOES
from metaexp.core.papeis import ETAPAS_CICLO, JORNADAS, RESPONSABILIDADES


def markdown() -> str:
    L: list[str] = []
    L.append("# Papéis e responsabilidades do METAEXP\n")
    L.append("O METAEXP é a plataforma interna de experimentação (IDP) do beOn Labs. Este documento define quem participa de um experimento, o que cada papel faz e por qual porta entra na plataforma. A fonte é `metaexp/core/papeis.py`, a mesma usada pelo backend (`GET /api/papeis`) e pelo app.\n")
    L.append("## As quatro portas de entrada\n")
    L.append("A primeira tela pede que a pessoa escolha o papel. Solicitante e Desenvolvedor conversam com o Cientista; Lab e Sponsor trabalham em painéis.\n")
    L.append("| Papel | Porta | Quem é | O que recebe | Etapas |")
    L.append("|---|---|---|---|---|")
    for j in JORNADAS.values():
        L.append(f"| **{j.nome}** | {j.chamada} | {j.descricao} | {j.promessa} | {' → '.join(j.etapas)} |")
    L.append("")
    sol, dev = JORNADAS["solicitante"], JORNADAS["desenvolvedor"]

    def prefs(j):
        return "<br>".join(f"{p.pergunta} {', '.join(r for _, r in p.opcoes)}" for p in j.preferencias)

    L.append("## As duas conversas com o Cientista\n")
    L += [
        "| | Solicitante | Desenvolvedor |", "|---|---|---|",
        "| Tom | Reunião com quem conhece o próprio negócio: linguagem de negócio, nenhum termo técnico | Revisão de design com um tech lead: técnico, direto, trade-offs explícitos |",
        "| Descoberta do problema | Longa e profunda: casos concretos, quantificação, decisão em jogo | Curta e afiada: quem sofre, tamanho, decisão, sinal de sucesso |",
        "| Depois da descoberta | Objetivo, hipótese, sucesso em termos de negócio, dados, responsáveis | Contexto técnico, baseline, abordagens, protocolo de avaliação, arquitetura |",
        "| Ferramentas exclusivas | — | " + ", ".join(f"`{t}`" for t in dev.ferramentas if t not in sol.ferramentas) + " |",
        "| Ao final | Ficha vai para a revisão do Lab e depois para a bancada | Ficha, desenho e kit (avaliador + CI); bancada opcional |",
        f"| Personalização | {prefs(sol)} | {prefs(dev)} |\n",
    ]
    L.append("Nas duas, o Cientista mantém um **mapa do problema** com dez dimensões e mostra à pessoa por que cada pergunta importa:\n")
    L += [f"- **{d.nome}**: {d.busca}." for d in DIMENSOES]
    L.append("\nO método oficial vale para todos: hipótese começando com \"Acreditamos que\", critérios de aceite numéricos, nome com até 3 palavras, BO e Sponsor, checklist de qualidade mínima e Gerador de Ficha.\n")
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
    L.append("\nQuando o desenvolvedor constrói por conta própria, Construção e Qualidade ficam com ele (o CI do kit faz o papel do QA); se escolher a bancada, voltam para os agentes.\n")
    L.append("## Como mudar\n")
    L += [
        "- Papéis, preferências, ferramentas e encaminhamentos: `metaexp/core/papeis.py`.",
        "- Dimensões do mapa do problema e técnicas de pergunta: `metaexp/core/descoberta.py`.",
        "- Tom de cada jornada: `metaexp/prompts/papel_solicitante.md` e `metaexp/prompts/papel_desenvolvedor.md`.",
        "- Regras comuns do método: `metaexp/prompts/cientista.md` e `metaexp/core/metodo.py`.",
        "- Depois de mudar, regere este documento com `python -m metaexp papeis` e rode `python -m metaexp avaliar --n 5 --sim`.",
    ]
    return "\n".join(L) + "\n"
