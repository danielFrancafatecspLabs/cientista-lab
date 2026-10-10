"""Descoberta do problema: a camada que faz o Cientista perguntar bem.

Antes de existir hipótese, existe um problema que precisa ser entendido. O
Cientista mantém um **mapa do problema** com dez dimensões e, a cada resposta,
registra o que entendeu e com que profundidade (0 vazio, 1 raso, 2 claro,
3 profundo com evidência). Este módulo é determinístico: diz qual dimensão
vale mais a pena aprofundar agora, se já dá para escrever a hipótese e quais
técnicas de pergunta servem para cada dimensão.

O modelo escreve a pergunta; o código decide onde o entendimento está fraco.
Assim a conversa não pula para a solução antes de o problema estar claro, e a
pessoa vê por que cada pergunta está sendo feita.
"""

from __future__ import annotations

from dataclasses import dataclass

from metaexp.core.schemas import DimensaoMapa, MapaProblema


@dataclass(frozen=True)
class Dimensao:
    id: str
    nome: str
    busca: str                 # o que precisamos saber, em uma frase
    peso: int                  # importância para um bom experimento (1 a 3)
    minimo: int                # profundidade mínima antes da hipótese
    tecnicas: tuple[str, ...]  # técnicas de pergunta mais úteis


DIMENSOES: tuple[Dimensao, ...] = (
    Dimensao("sintoma", "O que acontece", "o que se observa hoje, descrito em fatos e não em soluções", 3, 2,
             ("caso_concreto", "espelhar")),
    Dimensao("quem_sofre", "Quem sente", "quem é afetado, quantas pessoas e em que momento do trabalho", 3, 2,
             ("quem_mais", "caso_concreto")),
    Dimensao("tamanho", "Tamanho do problema", "frequência, volume e custo em números, mesmo que aproximados", 3, 2,
             ("quantificar", "custo_da_inacao")),
    Dimensao("caso_concreto", "Um caso real", "o último exemplo real, com o que aconteceu passo a passo", 2, 1,
             ("caso_concreto",)),
    Dimensao("causas", "Por que acontece", "as causas prováveis, separando sintoma de causa raiz", 2, 1,
             ("cinco_porques", "ja_tentaram")),
    Dimensao("solucao_atual", "Como se resolve hoje", "o contorno atual e por que ele não basta", 2, 1,
             ("ja_tentaram", "caso_concreto")),
    Dimensao("decisao", "Decisão em jogo", "que decisão o resultado vai destravar e quem a toma", 3, 2,
             ("decisao", "contrafactual")),
    Dimensao("sucesso", "Como saberemos", "o sinal observável de sucesso, que vira métrica e critério", 3, 2,
             ("contrafactual", "criterio_de_parada")),
    Dimensao("restricoes", "Restrições", "prazo, regras, dados disponíveis, orçamento e riscos que limitam a solução", 1, 0,
             ("restricao",)),
    Dimensao("premissa_critica", "Premissa mais arriscada", "o que precisa ser verdade para valer a pena, e ainda não sabemos", 2, 1,
             ("premissa", "criterio_de_parada")),
)

POR_ID = {d.id: d for d in DIMENSOES}

# Técnicas de pergunta: o nome curto aparece para a pessoa no "por que pergunto".
TECNICAS: dict[str, tuple[str, str]] = {
    "caso_concreto": ("Um caso real", "Peça o último caso concreto, com quem, quando e o que aconteceu. Casos revelam o que opiniões escondem."),
    "espelhar": ("Confirmar entendimento", "Resuma com as palavras da pessoa e pergunte o que ficou errado ou faltando."),
    "quem_mais": ("Quem mais sente", "Pergunte quem mais sofre com isso além de quem está falando, e em que momento."),
    "quantificar": ("Ordem de grandeza", "Peça números aproximados: quantas vezes por dia, quantas pessoas, quanto tempo, quanto custa. Ofereça faixas se ela não souber."),
    "custo_da_inacao": ("Custo de não fazer nada", "Pergunte o que acontece se nada mudar nos próximos seis meses."),
    "cinco_porques": ("Por que, de novo", "Pergunte por que o sintoma acontece; diante da resposta, pergunte por que de novo, até chegar a algo que dá para mudar."),
    "ja_tentaram": ("O que já tentaram", "Pergunte o que já foi tentado, o que funcionou em parte e por que não resolveu."),
    "decisao": ("Decisão destravada", "Pergunte que decisão muda se o experimento der certo, e quem decide."),
    "contrafactual": ("Se já estivesse resolvido", "Peça para imaginar o problema resolvido: o que seria visivelmente diferente no dia a dia?"),
    "criterio_de_parada": ("Quando desistir", "Pergunte que resultado faria a área desistir da ideia. O limite de fracasso ajuda a fixar o critério de sucesso."),
    "premissa": ("Premissa arriscada", "Pergunte o que precisa ser verdade para isso valer a pena e qual dessas coisas é a menos certa."),
    "restricao": ("Limites do jogo", "Pergunte por prazos, regras, sistemas e dados que limitam a solução."),
}

LIMIAR_COBERTURA = 0.6


def _prof(mapa: MapaProblema, dim: str) -> int:
    d = mapa.dimensoes.get(dim)
    return d.profundidade if d else 0


def cobertura(mapa: MapaProblema) -> float:
    """Média ponderada da profundidade (0 a 1)."""
    total = sum(d.peso * 3 for d in DIMENSOES)
    return round(sum(d.peso * _prof(mapa, d.id) for d in DIMENSOES) / total, 3)


def lacunas(mapa: MapaProblema) -> list[Dimensao]:
    """Dimensões abaixo do mínimo para a hipótese, da mais importante para a menos."""
    return sorted((d for d in DIMENSOES if _prof(mapa, d.id) < d.minimo), key=lambda d: (-d.peso, DIMENSOES.index(d)))


def pronto_para_hipotese(mapa: MapaProblema) -> bool:
    return not lacunas(mapa) and cobertura(mapa) >= LIMIAR_COBERTURA


def proxima_dimensao(mapa: MapaProblema) -> Dimensao | None:
    """Onde a próxima pergunta rende mais: primeiro as lacunas, depois o que ainda está raso."""
    falta = lacunas(mapa)
    if falta:
        return falta[0]
    rasas = sorted((d for d in DIMENSOES if _prof(mapa, d.id) < 2), key=lambda d: (-d.peso, DIMENSOES.index(d)))
    return rasas[0] if rasas else None


def atualizar(mapa: MapaProblema, dimensao: str, entendimento: str, profundidade: int, evidencia: str | None) -> None:
    if dimensao not in POR_ID:
        raise ValueError(f"dimensão desconhecida: {dimensao}")
    atual = mapa.dimensoes.get(dimensao)
    # A profundidade nunca regride por engano; o entendimento mais recente prevalece.
    nova = max(profundidade, atual.profundidade if atual else 0)
    mapa.dimensoes[dimensao] = DimensaoMapa(entendimento=entendimento, profundidade=nova,
                                            evidencia=evidencia or (atual.evidencia if atual else None))
    if mapa.sintese_confirmada:
        mapa.sintese_confirmada = False   # entendimento mudou: a síntese precisa ser reconfirmada


def orientacao(mapa: MapaProblema) -> dict:
    """O que o Cientista recebe de volta da ferramenta: onde está o entendimento e onde aprofundar."""
    prox = proxima_dimensao(mapa)
    out: dict = {
        "cobertura": cobertura(mapa),
        "pronto_para_hipotese": pronto_para_hipotese(mapa),
        "lacunas": [d.id for d in lacunas(mapa)],
    }
    if prox:
        out["aprofundar_agora"] = {
            "dimensao": prox.id, "o_que_saber": prox.busca,
            "tecnicas": [{"id": t, "como": TECNICAS[t][1]} for t in prox.tecnicas],
        }
    if out["pronto_para_hipotese"] and not mapa.sintese_confirmada:
        out["sugestao"] = "o problema está claro: resuma o entendimento em sintese_para_confirmar antes da hipótese"
    return out


def para_front(mapa: MapaProblema) -> dict:
    """Estado do mapa para a interface, com rótulos e ordem estáveis."""
    return {
        "cobertura": cobertura(mapa),
        "pronto": pronto_para_hipotese(mapa),
        "sintese": mapa.sintese,
        "sintese_confirmada": mapa.sintese_confirmada,
        "pergunta_atual": mapa.pergunta_atual.model_dump() | {"tecnica_nome": TECNICAS.get(mapa.pergunta_atual.tecnica, ("", ""))[0]}
        if mapa.pergunta_atual else None,
        "dimensoes": [
            {"id": d.id, "nome": d.nome, "busca": d.busca, "peso": d.peso, "minimo": d.minimo,
             **(mapa.dimensoes[d.id].model_dump() if d.id in mapa.dimensoes else DimensaoMapa().model_dump())}
            for d in DIMENSOES
        ],
    }


def catalogo_markdown() -> str:
    """Bloco estável para o prompt do Cientista: dimensões e técnicas."""
    linhas = ["# Mapa do problema: dimensões", ""]
    for d in DIMENSOES:
        linhas.append(f"- `{d.id}` ({d.nome}): {d.busca}. Peso {d.peso}; profundidade mínima antes da hipótese: {d.minimo}.")
    linhas += ["", "# Técnicas de pergunta", ""]
    for tid, (nome, como) in TECNICAS.items():
        linhas.append(f"- `{tid}` ({nome}): {como}")
    return "\n".join(linhas)
