"""Agente Revisor: pré-análise da ficha para a revisão humana do Lab (gate G0).

Uma chamada estruturada com a ficha, o mapa do problema (com as falas da
pessoa como evidência) e o checklist determinístico. O checklist tem a
palavra final: com pendências, a recomendação nunca é aprovar.
"""

from __future__ import annotations

import json

from metaexp.core import descoberta
from metaexp.core.schemas import PreRevisao
from metaexp.llm import LLM
from metaexp.prompts import ficha_json, system_revisor
from metaexp.sessions import Sessao


def contexto(s: Sessao) -> str:
    mapa = {d["id"]: {k: d[k] for k in ("entendimento", "profundidade", "evidencia")}
            for d in descoberta.para_front(s.mapa)["dimensoes"] if d["profundidade"]}
    pend = s.ficha.pendencias()
    partes = [
        f"<ficha versao=\"{s.ficha_versao}\" papel=\"{s.papel}\">\n{ficha_json(s.ficha)}\n</ficha>",
        f"<mapa_do_problema cobertura=\"{descoberta.cobertura(s.mapa)}\">\n{json.dumps(mapa, ensure_ascii=False, indent=1)}\n</mapa_do_problema>",
        f"<sintese_confirmada>{s.mapa.sintese if s.mapa.sintese_confirmada else 'não houve'}</sintese_confirmada>",
        f"<checklist_pendencias>{json.dumps(pend, ensure_ascii=False)}</checklist_pendencias>",
        f"<arquivos_de_amostra>{json.dumps(s.arquivos, ensure_ascii=False)}</arquivos_de_amostra>",
    ]
    if s.revisoes:
        partes.append("<revisoes_anteriores>\n" + "\n".join(f"- v{r.versao_ficha}: {r.decisao} · {r.comentario}" for r in s.revisoes)
                      + "\n</revisoes_anteriores>")
    return "\n".join(partes)


def pre_revisar(llm: LLM, s: Sessao, effort: str | None = None) -> PreRevisao:
    rev = llm.structured(system=system_revisor(), messages=[{"role": "user", "content": contexto(s)}],
                         schema=PreRevisao, effort=effort)
    if s.ficha.pendencias() and rev.recomendacao == "aprovar":
        rev.recomendacao = "devolver"
        rev.riscos = [*rev.riscos, "o checklist do método tem pendências"]
    return rev
