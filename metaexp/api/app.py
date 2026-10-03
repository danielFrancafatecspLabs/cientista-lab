"""API HTTP do METAEXP.

Rotas (todas sob /api):
  GET  /health                                  verifica se o backend e o corpus estão de pé
  GET  /papeis                                  papéis, jornadas, preferências e matriz de responsabilidades
  POST /sessoes                  {nome?, papel, preferencias}  cria uma sessão na jornada do papel
  GET  /sessoes/{id}                            estado atual (ficha, perfil, bancada)
  POST /sessoes/{id}/iniciar                    SSE: mensagem de abertura do Cientista
  POST /sessoes/{id}/mensagens   {texto}        SSE: turno de conversa
  POST /sessoes/{id}/arquivos    {nome, conteudo_base64}  SSE: análise de amostra
  POST /sessoes/{id}/bancada     {decisao?, comentario?}  SSE: avança a bancada
  GET  /experimentos                            corpus (resumo) + sessões
O front (prototipo/index.html) é servido em /.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from dataclasses import asdict
from typing import Callable, Iterator, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..agents.bancada import Bancada
from ..agents.cientista import Cientista
from ..config import Settings, settings as default_settings
from ..corpus.store import Corpus, resumo_para_contexto
from ..llm.client import LLM, AnthropicLLM
from ..papeis import ETAPAS_CICLO, JORNADAS, RESPONSABILIDADES
from ..sessions import Sessao, SessionStore
from ..tools.profiling import perfilar

log = logging.getLogger("metaexp.api")
MAX_UPLOAD = 15 * 1024 * 1024


class NovaSessao(BaseModel):
    nome: Optional[str] = None
    papel: Literal["solicitante", "desenvolvedor"] = "solicitante"
    preferencias: dict[str, str] = Field(default_factory=dict)


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=8000)


class Arquivo(BaseModel):
    nome: str
    conteudo_base64: str


class Decisao(BaseModel):
    decisao: Optional[str] = None
    comentario: Optional[str] = None


def _sse(events: Iterator[dict]) -> Iterator[str]:
    for ev in events:
        yield f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"


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

    app = FastAPI(title="METAEXP", version="0.2.0")

    def sessao(sid: str) -> Sessao:
        s = store.get(sid)
        if not s:
            raise HTTPException(404, "sessão não encontrada")
        return s

    def stream(s: Sessao, gen: Callable[[], Iterator[dict]]) -> StreamingResponse:
        lock = store.lock(s.id)
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "esta sessão já está processando uma mensagem")

        def run() -> Iterator[str]:
            try:
                yield from _sse(gen())
            except Exception as e:  # noqa: BLE001
                log.exception("falha no stream")
                yield from _sse(iter([{"type": "error", "message": f"Erro ao falar com o modelo: {type(e).__name__}"},
                                      {"type": "done", "state": s.snapshot()}]))
            finally:
                store.save(s)
                lock.release()

        return StreamingResponse(run(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/health")
    def health():
        return {"ok": True, "modelo": cfg.model, "corpus": corpus.stats()}

    @app.post("/api/sessoes")
    def criar(body: NovaSessao):
        s = store.create(body.nome, body.papel, body.preferencias)
        return s.snapshot()

    @app.get("/api/papeis")
    def papeis():
        return {
            "jornadas": [asdict(j) | {"prompt": None, "ferramentas": list(j.ferramentas)} for j in JORNADAS.values()],
            "etapas_ciclo": list(ETAPAS_CICLO),
            "responsabilidades": RESPONSABILIDADES,
        }

    @app.get("/api/sessoes/{sid}")
    def obter(sid: str):
        return sessao(sid).snapshot()

    @app.post("/api/sessoes/{sid}/iniciar")
    def iniciar(sid: str):
        s = sessao(sid)
        return stream(s, lambda: Cientista(get_llm(), corpus, cfg.effort_chat).iniciar(s))

    @app.post("/api/sessoes/{sid}/mensagens")
    def mensagem(sid: str, body: Mensagem):
        s = sessao(sid)
        return stream(s, lambda: Cientista(get_llm(), corpus, cfg.effort_chat).responder(s, body.texto))

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
        return stream(s, lambda: Cientista(get_llm(), corpus, cfg.effort_chat).receber_arquivo(s, perfil))

    @app.post("/api/sessoes/{sid}/bancada")
    def bancada(sid: str, body: Decisao):
        s = sessao(sid)
        return stream(s, lambda: Bancada(get_llm(), cfg=cfg).avancar(s, body.decisao, body.comentario))

    @app.get("/api/sessoes/{sid}/ficha.md")
    def ficha_md(sid: str):
        from fastapi.responses import PlainTextResponse
        from ..ficha_doc import markdown
        s = sessao(sid)
        return PlainTextResponse(markdown(s.ficha, max(1, s.ficha_versao)), media_type="text/markdown; charset=utf-8")

    @app.get("/api/experimentos")
    def experimentos():
        return {
            "corpus": [resumo_para_contexto(e) for e in corpus.experiments],
            "sessoes": [{"id": x.id, "titulo": x.ficha.titulo, "encaminhamento": x.encaminhamento,
                         "bancada": x.bancada.status} for x in store.list() if x.ficha.titulo],
        }

    index = cfg.frontend_dir / "index.html"

    @app.get("/")
    def front():
        if not index.exists():
            raise HTTPException(404, "front não encontrado; rode prototipo/build.sh")
        return FileResponse(index)

    return app
