"""Geração do dataset sintético de experimentos.

Fluxo:
  1. `taxonomy.amostrar` define N especificações equilibradas.
  2. Para cada uma, o modelo gera um `Experimento` completo (ficha, amostra,
     conversa, plano, resultados e parecer) com saída estruturada. Experimentos
     reais semelhantes entram como referência de estilo (few-shot).
  3. `quality.validar` checa coerência e descarta quase-duplicatas.
  4. Os aprovados vão para data/corpus/sintetico/.

Para lotes grandes, `gerar_lote_batch` usa a Message Batches API (metade do
custo, resultado assíncrono).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Iterable

import anthropic
from anthropic.types.messages.batch_create_params import Request
from pydantic import ValidationError

from metaexp.config import Settings, settings as default_settings
from metaexp.prompts import exemplos_reais, system_sintetico
from metaexp.corpus.golden_paths import BY_ID as GOLDEN
from metaexp.corpus.store import Corpus, save
from metaexp.llm import LLM
from metaexp.core.schemas import Experimento
from metaexp.synthetic.quality import Relatorio, validar
from metaexp.synthetic.taxonomy import Especificacao

log = logging.getLogger("metaexp.synthetic")


def _pedido(spec: Especificacao, referencias: list[Experimento]) -> str:
    gp = GOLDEN[spec.golden_path]
    partes = []
    if referencias:
        partes.append("Experimentos reais do laboratório, para referência de estilo e nível de detalhe:\n"
                      + exemplos_reais(referencias))
    partes.append(
        "Gere um experimento sintético com estas características:\n"
        + json.dumps({
            "id": spec.id,
            "origem": "sintetico",
            "dominio": spec.dominio,
            "golden_path": gp["id"],
            "tecnologia": spec.tecnologia,
            "perfil_solicitante": spec.perfil_solicitante,
            "situacao_dados": spec.situacao_dados,
            "veredito_final": spec.veredito,
            "estilo_do_solicitante_na_conversa": spec.estilo_conversa,
        }, ensure_ascii=False, indent=2)
        + "\n\nRequisitos: a conversa tem entre 10 e 18 turnos e termina com a decisão de quem executa "
          "(laboratório para negócio, o próprio solicitante para desenvolvedor). A ficha fica completa. "
          "`resultados.simulado` é true. `lead_time_dias` entre 4 e 40. Use `semente` com o id da referência mais "
          "próxima, se houver."
    )
    return "\n\n".join(partes)


def _referencias(corpus: Corpus | None, spec: Especificacao, k: int = 2) -> list[Experimento]:
    if not corpus:
        return []
    reais = [e for e in corpus.experiments if e.origem == "real"]
    if not reais:
        return []
    gp = GOLDEN[spec.golden_path]
    hits = Corpus(reais).search(f"{gp['nome']} {gp['quando_usar']} {spec.dominio}", k=k)
    return [e for e, _ in hits] or reais[:k]


def _ajustar(exp: Experimento, spec: Especificacao, semente_ids: list[str]) -> Experimento:
    exp.id, exp.origem = spec.id, "sintetico"
    exp.ficha.id = spec.id
    if exp.semente not in semente_ids:
        exp.semente = semente_ids[0] if semente_ids else None
    if exp.resultados:
        exp.resultados.simulado = True
    return exp


def gerar(specs: Iterable[Especificacao], llm: LLM, destino: Path, corpus: Corpus | None = None,
          cfg: Settings | None = None) -> Relatorio:
    """Gera sequencialmente (uma chamada por especificação)."""
    cfg = cfg or default_settings
    system = system_sintetico()
    aceitos: list[Experimento] = list(corpus.experiments) if corpus else []
    rel = Relatorio()
    for spec in specs:
        refs = _referencias(corpus, spec)
        try:
            exp = llm.structured(system=system, messages=[{"role": "user", "content": _pedido(spec, refs)}],
                                 schema=Experimento, effort=cfg.effort_synth, max_tokens=32000)
        except Exception as e:  # noqa: BLE001 - um item com falha não para o lote
            log.warning("%s falhou: %s", spec.id, e)
            rel.falhas.append((spec.id, str(e)))
            continue
        exp = _ajustar(exp, spec, [r.id for r in refs])
        problemas = validar(exp, spec, aceitos)
        if problemas:
            rel.rejeitados.append((spec.id, problemas))
            continue
        save(exp, destino)
        aceitos.append(exp)
        rel.aceitos.append(spec.id)
        log.info("%s gerado (%s, %s, %s)", spec.id, spec.dominio, spec.golden_path, spec.veredito)
    return rel


# ------------------------------------------------------------ batches ----

def gerar_lote_batch(specs: list[Especificacao], client: anthropic.Anthropic, destino: Path,
                     corpus: Corpus | None = None, cfg: Settings | None = None, poll_s: int = 30) -> Relatorio:
    """Envia todas as especificações num lote assíncrono (50% do custo) e salva os aprovados."""
    from anthropic.lib._parse._transform import transform_schema

    cfg = cfg or default_settings
    system = system_sintetico()
    schema = transform_schema(Experimento)
    by_id = {s.id: s for s in specs}
    refs_by_id = {s.id: _referencias(corpus, s) for s in specs}
    requests = [
        Request(custom_id=s.id, params={
            "model": cfg.model, "max_tokens": 32000,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": _pedido(s, refs_by_id[s.id])}],
            "output_config": {"effort": cfg.effort_synth, "format": {"type": "json_schema", "schema": schema}},
        }) for s in specs
    ]
    batch = client.messages.batches.create(requests=requests)
    log.info("lote %s enviado com %d pedidos", batch.id, len(requests))
    while client.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(poll_s)

    aceitos: list[Experimento] = list(corpus.experiments) if corpus else []
    rel = Relatorio()
    for item in client.messages.batches.results(batch.id):   # ordem arbitrária: use custom_id
        spec = by_id[item.custom_id]
        if item.result.type != "succeeded":
            rel.falhas.append((spec.id, item.result.type))
            continue
        msg = item.result.message
        if msg.stop_reason != "end_turn":
            rel.falhas.append((spec.id, f"stop_reason={msg.stop_reason}"))
            continue
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            exp = Experimento.model_validate_json(text)
        except ValidationError as e:
            rel.falhas.append((spec.id, f"json inválido: {e.error_count()} erros"))
            continue
        exp = _ajustar(exp, spec, [r.id for r in refs_by_id[spec.id]])
        problemas = validar(exp, spec, aceitos)
        if problemas:
            rel.rejeitados.append((spec.id, problemas))
            continue
        save(exp, destino)
        aceitos.append(exp)
        rel.aceitos.append(spec.id)
    return rel
