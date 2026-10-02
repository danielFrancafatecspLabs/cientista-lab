"""Sessões de conversa: estado do chat, da ficha e da bancada, persistido em JSON."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .schemas import Ficha


@dataclass
class EstadoBancada:
    iniciada: bool = False
    etapa: int = 0                                  # índice em bench.ETAPAS
    status: dict[str, str] = field(default_factory=dict)   # etapa -> run|wait|ok|bloqueada
    aguardando: Optional[str] = None                # etapa que espera decisão humana
    artefatos: dict[str, Any] = field(default_factory=dict)
    rodadas: list[dict] = field(default_factory=list)       # histórico do Ralph Loop
    decisao_final: Optional[str] = None


@dataclass
class Sessao:
    id: str
    criada_em: str
    nome: str = "você"
    # Histórico exato enviado à API. Só cresce: nada é editado ou removido,
    # para manter o cache e os blocos de raciocínio válidos.
    messages: list[dict] = field(default_factory=list)
    ficha: Ficha = field(default_factory=Ficha)
    ficha_gerada: bool = False                      # passou pelo Gerador de Ficha com checklist completo
    ficha_versao: int = 0
    perfil_score: int = 50                          # 0 = negócio, 100 = desenvolvedor
    perfil: Optional[str] = None
    perfil_sinais: list[str] = field(default_factory=list)
    similares: list[str] = field(default_factory=list)
    arquivos: list[dict] = field(default_factory=list)      # perfis dos arquivos enviados
    aguardando_arquivo: bool = False
    encaminhamento: Optional[str] = None
    bancada: EstadoBancada = field(default_factory=EstadoBancada)
    uso: dict[str, int] = field(default_factory=dict)       # tokens acumulados

    def snapshot(self) -> dict:
        """Estado resumido para o front."""
        return {
            "id": self.id,
            "ficha": self.ficha.model_dump(exclude_none=True),
            "faltantes": self.ficha.faltantes(),
            "pendencias": self.ficha.pendencias(),
            "ficha_gerada": self.ficha_gerada,
            "perfil": {"score": self.perfil_score, "perfil": self.perfil, "sinais": self.perfil_sinais[-4:]},
            "encaminhamento": self.encaminhamento,
            "bancada": asdict(self.bancada),
        }

    def somar_uso(self, usage: dict) -> None:
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            v = usage.get(k)
            if isinstance(v, int):
                self.uso[k] = self.uso.get(k, 0) + v

    def to_json(self) -> str:
        d = asdict(self)
        d["ficha"] = self.ficha.model_dump()
        return json.dumps(d, ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, text: str) -> "Sessao":
        d = json.loads(text)
        d["ficha"] = Ficha.model_validate(d.get("ficha") or {})
        d["bancada"] = EstadoBancada(**(d.get("bancada") or {}))
        return cls(**d)


class SessionStore:
    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Sessao] = {}
        self._locks: dict[str, threading.Lock] = {}

    def create(self, nome: str | None = None) -> Sessao:
        s = Sessao(id=uuid.uuid4().hex[:12], criada_em=datetime.now(timezone.utc).isoformat(), nome=nome or "você")
        s.ficha.id = f"EXP-{s.id[:6].upper()}"
        self.save(s)
        return s

    def get(self, sid: str) -> Sessao | None:
        if sid in self._cache:
            return self._cache[sid]
        path = self.dir / f"{sid}.json"
        if not path.exists():
            return None
        s = Sessao.from_json(path.read_text(encoding="utf-8"))
        self._cache[sid] = s
        return s

    def save(self, s: Sessao) -> None:
        self._cache[s.id] = s
        (self.dir / f"{s.id}.json").write_text(s.to_json(), encoding="utf-8")

    def lock(self, sid: str) -> threading.Lock:
        return self._locks.setdefault(sid, threading.Lock())

    def list(self) -> list[Sessao]:
        out = []
        for f in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            s = self.get(f.stem)
            if s:
                out.append(s)
        return out
