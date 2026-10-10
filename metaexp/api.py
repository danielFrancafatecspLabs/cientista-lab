"""API HTTP do METAEXP (todas as rotas sob /api; o app React é servido em /).

Conversa com o Cientista (SSE)
  POST /sessoes                       {nome?, papel, preferencias}   cria a sessão na jornada do papel
  GET  /sessoes/{id}                  estado completo
  POST /sessoes/{id}/iniciar          abertura do Cientista
  POST /sessoes/{id}/mensagens        {texto}                        turno de conversa
  POST /sessoes/{id}/arquivos         {nome, conteudo_base64}        análise de amostra
  POST /sessoes/{id}/retomar          volta à conversa com o feedback do Lab
  POST /sessoes/{id}/bancada          {decisao?, comentario?}        avança a bancada
  GET  /sessoes/{id}/ficha.md         ficha no padrão oficial
  GET  /sessoes/{id}/kit              arquivos do kit (desenvolvedor)
  GET  /sessoes/{id}/kit.zip          kit para baixar

Lab e Sponsor
  GET  /experimentos                  fila e portfólio (resumos)       ?status=em_revisao,aprovado
  GET  /experimentos/{id}             detalhe com transcrição e mapa
  POST /experimentos/{id}/pre-revisao Agente Revisor
  POST /experimentos/{id}/revisao     {decisao, comentario, revisor}  gate G0
  POST /experimentos/{id}/decisao     {decisao, comentario}           decisão do Sponsor
  GET  /portfolio                     indicadores do metaexperimento

Metadados
  GET  /health, /papeis
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import statistics
from collections import Counter
from dataclasses import asdict
from typing import Callable, Iterator, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from metaexp.agents.bancada import Bancada
from metaexp.agents.cientista import Cientista
from metaexp.agents.revisor import pre_revisar
from metaexp.config import Settings, settings as default_settings
from metaexp.core import descoberta, kit
from metaexp.core.ficha_doc import markdown as ficha_markdown
from metaexp.core.papeis import ETAPAS_CICLO, JORNADAS, PAPEIS_CONVERSA, RESPONSABILIDADES
from metaexp.core.profiling import perfilar
from metaexp.core.schemas import DecisaoSponsor, Revisao
from metaexp.corpus.store import Corpus, resumo_para_contexto
from metaexp.llm import LLM, AnthropicLLM
from metaexp.sessions import STATUS, Sessao, SessionStore, agora

log = logging.getLogger("metaexp.api")
MAX_UPLOAD = 15 * 1024 * 1024


class NovaSessao(BaseModel):
    nome: Optional[str] = Field(None, max_length=80)
    papel: Literal["solicitante", "desenvolvedor"] = "solicitante"
    preferencias: dict[str, str] = Field(default_factory=dict)


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=12000)


class Arquivo(BaseModel):
    nome: str
    conteudo_base64: str


class Decisao(BaseModel):
    decisao: Optional[str] = None
    comentario: Optional[str] = None


class NovaRevisao(BaseModel):
    decisao: Literal["aprovar", "devolver"]
    comentario: str = Field("", max_length=4000)
    revisor: str = Field("Lab", max_length=80)


class NovaDecisao(BaseModel):
    decisao: Literal["escalar", "iterar", "encerrar"]
    comentario: str = Field("", max_length=4000)


def _sse(events: Iterator[dict]) -> Iterator[str]:
    for ev in events:
        yield f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"


def transcricao(s: Sessao) -> list[dict]:
    """A conversa legível (sem ferramentas nem instruções do sistema), para a revisão do Lab."""
    out = []
    for m in s.messages:
        c = m.get("content")
        if m["role"] == "user" and isinstance(c, str):
            if c.startswith("<abertura>"):
                continue
            if c.startswith("<arquivo_anexado>"):
                c = "📎 " + c.rsplit("\n", 1)[-1]
            out.append({"de": "pessoa", "texto": c})
        elif m["role"] == "assistant" and isinstance(c, list):
            texto = "".join(b.get("text", "") for b in c if b.get("type") == "text").strip()
            if texto:
                out.append({"de": "cientista", "texto": texto})
    return out


def create_app(llm: LLM | None = None, cfg: Settings | None = None, corpus: Corpus | None = None,
               store: SessionStore | None = None) -> FastAPI:
    cfg = cfg or default_settings
    corpus = corpus or Corpus.from_dirs(cfg.corpus_dirs)
    store = store or SessionStore(cfg.sessions_dir)
    _llm: dict[str, LLM] = {}

    def get_llm() -> LLM:
        # Criado sob demanda para o servidor subir mesmo sem credenciais configuradas.
        if "x" not in _llm:
            _llm["x"] = llm or AnthropicLLM(cfg)
        return _llm["x"]

    def cientista() -> Cientista:
        return Cientista(get_llm(), corpus, cfg.effort_chat, revisao_lab=cfg.revisao_lab)

    app = FastAPI(title="METAEXP", version="0.3.0")

    def sessao(sid: str) -> Sessao:
        s = store.get(sid)
        if not s:
            raise HTTPException(404, "experimento não encontrado")
        return s

    def stream(s: Sessao, gen: Callable[[], Iterator[dict]]) -> StreamingResponse:
        lock = store.lock(s.id)
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "este experimento já está processando uma mensagem")

        def run() -> Iterator[str]:
            try:
                yield from _sse(gen())
            except Exception as e:  # noqa: BLE001 - a falha vira evento para o front
                log.exception("falha no stream")
                yield from _sse(iter([{"type": "error", "message": f"Erro ao falar com o modelo: {type(e).__name__}"},
                                      {"type": "done", "state": s.snapshot()}]))
            finally:
                store.save(s)
                lock.release()

        return StreamingResponse(run(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ----------------------------------------------------------- metadados ----

    @app.get("/api/health")
    def health():
        return {"ok": True, "modelo": cfg.model, "revisao_lab": cfg.revisao_lab, "corpus": corpus.stats()}

    @app.get("/api/papeis")
    def papeis():
        return {
            "jornadas": [{k: v for k, v in asdict(j).items() if k not in ("prompt", "ferramentas")} for j in JORNADAS.values()],
            "etapas_ciclo": list(ETAPAS_CICLO),
            "responsabilidades": RESPONSABILIDADES,
            "dimensoes": [asdict(d) for d in descoberta.DIMENSOES],
            "tecnicas": {k: {"nome": n, "como": c} for k, (n, c) in descoberta.TECNICAS.items()},
        }

    # ------------------------------------------------------------ conversa ----

    @app.post("/api/sessoes")
    def criar(body: NovaSessao):
        if body.papel not in PAPEIS_CONVERSA:
            raise HTTPException(422, "papel sem conversa com o Cientista")
        return store.create(body.nome, body.papel, body.preferencias).snapshot()

    @app.get("/api/sessoes/{sid}")
    def obter(sid: str):
        s = sessao(sid)
        return {**s.snapshot(), "transcricao": transcricao(s)}

    @app.post("/api/sessoes/{sid}/iniciar")
    def iniciar(sid: str):
        s = sessao(sid)
        return stream(s, lambda: cientista().iniciar(s))

    @app.post("/api/sessoes/{sid}/mensagens")
    def mensagem(sid: str, body: Mensagem):
        s = sessao(sid)
        if s.status != "conversa":
            raise HTTPException(409, f"a conversa está fechada (status: {s.status})")
        return stream(s, lambda: cientista().responder(s, body.texto))

    @app.post("/api/sessoes/{sid}/arquivos")
    def arquivo(sid: str, body: Arquivo):
        s = sessao(sid)
        try:
            data = base64.b64decode(body.conteudo_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "conteúdo base64 inválido")
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "arquivo maior que 15 MB")
        try:
            perfil = perfilar(body.nome, data)
        except Exception as e:  # noqa: BLE001 - arquivo corrompido ou formato inesperado
            raise HTTPException(422, f"não foi possível ler o arquivo: {e}")
        return stream(s, lambda: cientista().receber_arquivo(s, perfil))

    @app.post("/api/sessoes/{sid}/retomar")
    def retomar(sid: str):
        s = sessao(sid)
        return stream(s, lambda: cientista().retomar(s))

    @app.post("/api/sessoes/{sid}/bancada")
    def bancada(sid: str, body: Decisao):
        s = sessao(sid)
        return stream(s, lambda: Bancada(get_llm(), cfg=cfg).avancar(s, body.decisao, body.comentario))

    @app.get("/api/sessoes/{sid}/ficha.md")
    def ficha_md(sid: str):
        s = sessao(sid)
        return PlainTextResponse(ficha_markdown(s.ficha, max(1, s.ficha_versao)), media_type="text/markdown; charset=utf-8")

    @app.get("/api/sessoes/{sid}/kit")
    def kit_json(sid: str):
        s = sessao(sid)
        return {"pasta": kit.nome_pasta(s.ficha), "arquivos": kit.arquivos(s.ficha, max(1, s.ficha_versao))}

    @app.get("/api/sessoes/{sid}/kit.zip")
    def kit_zip(sid: str):
        s = sessao(sid)
        pasta = kit.nome_pasta(s.ficha)
        data = kit.zipar(kit.arquivos(s.ficha, max(1, s.ficha_versao)), pasta)
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{pasta}.zip"'})

    # ------------------------------------------------------- Lab e Sponsor ----

    @app.get("/api/experimentos")
    def experimentos(status: Optional[str] = Query(None)):
        filtro = tuple(x for x in (status or "").split(",") if x in STATUS) or None
        return [s.resumo() for s in store.list(filtro) if s.ficha_versao > 0 or s.status != "conversa"]

    @app.get("/api/experimentos/{sid}")
    def experimento(sid: str):
        s = sessao(sid)
        return {**s.snapshot(), "resumo": s.resumo(), "transcricao": transcricao(s),
                "markdown": ficha_markdown(s.ficha, max(1, s.ficha_versao))}

    @app.post("/api/experimentos/{sid}/pre-revisao")
    def pre_revisao(sid: str):
        s = sessao(sid)
        if s.ficha_versao == 0:
            raise HTTPException(409, "ainda não há ficha gerada para revisar")
        s.pre_revisao = pre_revisar(get_llm(), s, cfg.effort_bench)
        s.registrar("pre_revisao", s.pre_revisao.recomendacao)
        store.save(s)
        return s.pre_revisao.model_dump()

    @app.post("/api/experimentos/{sid}/revisao")
    def revisao(sid: str, body: NovaRevisao):
        s = sessao(sid)
        if s.status != "em_revisao":
            raise HTTPException(409, f"o experimento não está em revisão (status: {s.status})")
        if body.decisao == "devolver" and not body.comentario.strip():
            raise HTTPException(422, "explique o que precisa mudar para devolver a ficha")
        s.revisoes.append(Revisao(decisao=body.decisao, comentario=body.comentario.strip(), revisor=body.revisor,
                                  versao_ficha=s.ficha_versao, em=agora()))
        s.mudar_status("aprovado" if body.decisao == "aprovar" else "devolvido", body.comentario.strip())
        store.save(s)
        return s.snapshot()

    @app.post("/api/experimentos/{sid}/decisao")
    def decisao(sid: str, body: NovaDecisao):
        s = sessao(sid)
        if s.status not in ("parecer", "aprovado", "em_execucao"):
            raise HTTPException(409, f"ainda não há o que decidir (status: {s.status})")
        s.decisao = DecisaoSponsor(decisao=body.decisao, comentario=body.comentario.strip(), em=agora())
        s.mudar_status("decidido", body.decisao)
        store.save(s)
        return s.snapshot()

    @app.get("/api/portfolio")
    def portfolio():
        sessoes = [s for s in store.list() if s.ficha_versao > 0 or s.status != "conversa"]
        revisadas = [s for s in sessoes if s.revisoes]
        primeira = [s for s in revisadas if s.revisoes[0].decisao == "aprovar"]
        leads = [lt for s in sessoes if (lt := s.lead_time_horas()) is not None]
        vereditos = Counter(s.resumo()["veredito"] for s in sessoes if s.resumo()["veredito"])
        historico = [resumo_para_contexto(e) for e in corpus.experiments]
        return {
            "kpis": {
                "experimentos": len(sessoes),
                "em_revisao": sum(s.status == "em_revisao" for s in sessoes),
                "aprovacao_primeira_revisao": round(len(primeira) / len(revisadas), 3) if revisadas else None,
                "lead_time_mediano_horas": round(statistics.median(leads), 2) if leads else None,
                "cobertura_media_mapa": round(statistics.mean(descoberta.cobertura(s.mapa) for s in sessoes), 3) if sessoes else None,
                "decisoes_pendentes": sum(s.status == "parecer" for s in sessoes),
            },
            "por_status": dict(Counter(s.status for s in sessoes)),
            "vereditos": dict(vereditos),
            "historico": {"total": len(historico), "vereditos": dict(Counter(h.get("veredito") for h in historico if h.get("veredito")))},
        }

    # ------------------------------------------------------------- front ----

    if (cfg.frontend_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=cfg.frontend_dir, html=True), name="web")
    else:
        @app.get("/")
        def sem_front():
            return PlainTextResponse("Front não encontrado: rode `npm run build` em web/ (ou use `npm run dev`).", status_code=404)

    return app
