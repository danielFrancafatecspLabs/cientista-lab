"""Controle de qualidade do dataset sintético."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..corpus.search import tokenize
from ..schemas import Experimento
from .taxonomy import Especificacao

LIMIAR_DUPLICATA = 0.6   # similaridade de Jaccard entre fichas


@dataclass
class Relatorio:
    aceitos: list[str] = field(default_factory=list)
    rejeitados: list[tuple[str, list[str]]] = field(default_factory=list)
    falhas: list[tuple[str, str]] = field(default_factory=list)

    def resumo(self) -> str:
        linhas = [f"aceitos: {len(self.aceitos)}  rejeitados: {len(self.rejeitados)}  falhas: {len(self.falhas)}"]
        linhas += [f"  rejeitado {i}: {'; '.join(p)}" for i, p in self.rejeitados]
        linhas += [f"  falha {i}: {m}" for i, m in self.falhas]
        return "\n".join(linhas)


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def _texto_ficha(e: Experimento) -> str:
    f = e.ficha
    return " ".join(x for x in [f.titulo, f.problema, f.hipotese, f.tecnica] if x)


def validar(exp: Experimento, spec: Especificacao | None, existentes: list[Experimento]) -> list[str]:
    """Devolve a lista de problemas; vazia quando o registro pode entrar no corpus."""
    p: list[str] = []
    f = exp.ficha
    faltam = f.faltantes()
    if faltam:
        p.append(f"ficha incompleta: {', '.join(faltam)}")
    # Regras do método oficial: hipótese, nome, critérios, BO/Sponsor.
    p += [x for x in f.pendencias() if not x.endswith(": ausente")]
    if len(exp.conversa) < 6:
        p.append("conversa curta demais")
    if exp.conversa and exp.conversa[0].papel != "cientista":
        p.append("a conversa deve começar pelo Cientista")
    if spec:
        if exp.dominio != spec.dominio:
            p.append(f"domínio {exp.dominio} ≠ {spec.dominio}")
        if exp.perfil_solicitante != spec.perfil_solicitante:
            p.append("perfil do solicitante diferente do pedido")
        if exp.situacao_dados != spec.situacao_dados:
            p.append("situação dos dados diferente do pedido")
        if exp.parecer and exp.parecer.veredito != spec.veredito:
            p.append(f"veredito {exp.parecer.veredito} ≠ {spec.veredito}")
        esperado = "laboratorio" if spec.perfil_solicitante == "negocio" else "solicitante"
        if f.execucao and f.execucao != esperado:
            p.append("quem executa não combina com o perfil")
    if exp.parecer and exp.resultados:
        obrig = {m.nome for m in f.metricas if m.obrigatoria}
        falhou = any(not r.atendida and r.metrica in obrig for r in exp.resultados.metricas)
        if exp.parecer.veredito == "validada" and falhou:
            p.append("veredito 'validada' com métrica obrigatória não atendida")
    alvo = _texto_ficha(exp)
    for e in existentes:
        if e.id != exp.id and _jaccard(alvo, _texto_ficha(e)) >= LIMIAR_DUPLICATA:
            p.append(f"quase duplicata de {e.id}")
            break
    return p
