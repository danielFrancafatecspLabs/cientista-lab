"""Sessões: a conversa, a ficha, o ciclo de vida do experimento e a bancada.

Cada sessão é um experimento em construção. O estado completo é um documento
JSON guardado em SQLite (uma tabela, uma linha por sessão), o que mantém a
operação simples hoje e permite trocar por Postgres sem mudar o domínio.

Ciclo de vida (`status`):

    conversa → em_revisao → aprovado → em_execucao → parecer → decidido
                    ↓            (bancada, só no destino workflow)
                devolvido → conversa (o Cientista retoma com o feedback do Lab)

`encerrado` vale para experimentos interrompidos (por exemplo, sem dados).
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from metaexp.core import descoberta
from metaexp.core.schemas import DecisaoSponsor, Ficha, MapaProblema, PreRevisao, Revisao

STATUS = ("conversa", "em_revisao", "devolvido", "aprovado", "em_execucao", "parecer", "decidido", "encerrado")


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class EstadoBancada:
    iniciada: bool = False
    etapa: int = 0                                  # índice em bancada.ETAPAS
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
    papel: str = "solicitante"                      # solicitante | desenvolvedor (ver core/papeis.py)
    preferencias: dict = field(default_factory=dict)
    # Histórico exato enviado à API. Só cresce: nada é editado ou removido,
    # para manter o cache e os blocos de raciocínio válidos.
    messages: list[dict] = field(default_factory=list)
    ficha: Ficha = field(default_factory=Ficha)
    mapa: MapaProblema = field(default_factory=MapaProblema)
    ficha_gerada: bool = False                      # passou pelo Gerador de Ficha com checklist completo
    ficha_versao: int = 0
    status: str = "conversa"
    eventos: list[dict] = field(default_factory=list)       # linha do tempo: {em, tipo, detalhe}
    similares: list[str] = field(default_factory=list)
    arquivos: list[dict] = field(default_factory=list)      # perfis dos arquivos enviados
    aguardando_arquivo: bool = False
    encaminhamento: Optional[str] = None
    pre_revisao: Optional[PreRevisao] = None
    revisoes: list[Revisao] = field(default_factory=list)
    decisao: Optional[DecisaoSponsor] = None
    bancada: EstadoBancada = field(default_factory=EstadoBancada)
    uso: dict[str, int] = field(default_factory=dict)       # tokens acumulados

    # ------------------------------------------------------------ ciclo ----

    def registrar(self, tipo: str, detalhe: str = "") -> None:
        self.eventos.append({"em": agora(), "tipo": tipo, "detalhe": detalhe})

    def mudar_status(self, novo: str, detalhe: str = "") -> None:
        if novo not in STATUS:
            raise ValueError(f"status inválido: {novo}")
        self.status = novo
        self.registrar(f"status:{novo}", detalhe)

    def lead_time_horas(self) -> float | None:
        """Da abertura da conversa até o primeiro encaminhamento da ficha (H1 do metaexperimento)."""
        fim = next((e["em"] for e in self.eventos if e["tipo"] == "status:em_revisao"), None)
        if not fim:
            return None
        return round((datetime.fromisoformat(fim) - datetime.fromisoformat(self.criada_em)).total_seconds() / 3600, 2)

    def feedback_pendente(self) -> Revisao | None:
        if self.status == "devolvido" and self.revisoes and self.revisoes[-1].decisao == "devolver":
            return self.revisoes[-1]
        return None

    # ------------------------------------------------------------ vistas ----

    def resumo(self) -> dict:
        """Linha do portfólio e da fila do Lab."""
        parecer = self.bancada.artefatos.get("parecer")
        return {
            "id": self.id, "titulo": self.ficha.titulo or "Sem título", "papel": self.papel, "nome": self.nome,
            "status": self.status, "dominio": self.ficha.dominio, "hipotese": self.ficha.hipotese,
            "bo": self.ficha.bo, "sponsor": self.ficha.sponsor, "criada_em": self.criada_em,
            "atualizada_em": self.eventos[-1]["em"] if self.eventos else self.criada_em,
            "versao": self.ficha_versao, "encaminhamento": self.encaminhamento,
            "lead_time_horas": self.lead_time_horas(), "revisoes": len(self.revisoes),
            "recomendacao": self.pre_revisao.recomendacao if self.pre_revisao else None,
            "veredito": parecer.get("veredito") if parecer else None,
            "decisao": self.decisao.decisao if self.decisao else None,
            "cobertura": descoberta.cobertura(self.mapa),
        }

    def snapshot(self) -> dict:
        """Estado completo para o front."""
        d = self.ficha.detalhes_tecnicos
        return {
            "id": self.id, "nome": self.nome, "papel": self.papel, "preferencias": self.preferencias,
            "status": self.status,
            "ficha": self.ficha.model_dump(exclude_none=True),
            "faltantes": self.ficha.faltantes(),
            "pendencias": self.ficha.pendencias(),
            "ficha_gerada": self.ficha_gerada, "ficha_versao": self.ficha_versao,
            "mapa": descoberta.para_front(self.mapa),
            "desenho_pendencias": d.pendencias() if d else None,
            "encaminhamento": self.encaminhamento,
            "pre_revisao": self.pre_revisao.model_dump() if self.pre_revisao else None,
            "revisoes": [r.model_dump() for r in self.revisoes],
            "feedback_lab": self.feedback_pendente().model_dump() if self.feedback_pendente() else None,
            "decisao": self.decisao.model_dump() if self.decisao else None,
            "eventos": self.eventos[-30:],
            "bancada": asdict(self.bancada),
            "arquivos": self.arquivos,
            "similares": self.similares,
        }

    def somar_uso(self, usage: dict) -> None:
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            v = usage.get(k)
            if isinstance(v, int):
                self.uso[k] = self.uso.get(k, 0) + v

    # ------------------------------------------------------- persistência ----

    def to_json(self) -> str:
        d = asdict(self)
        d["ficha"] = self.ficha.model_dump()
        d["mapa"] = self.mapa.model_dump()
        d["pre_revisao"] = self.pre_revisao.model_dump() if self.pre_revisao else None
        d["revisoes"] = [r.model_dump() for r in self.revisoes]
        d["decisao"] = self.decisao.model_dump() if self.decisao else None
        return json.dumps(d, ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, text: str) -> "Sessao":
        d = json.loads(text)
        known = set(cls.__dataclass_fields__)
        d = {k: v for k, v in d.items() if k in known}      # ignora campos de versões antigas
        d["ficha"] = Ficha.model_validate(d.get("ficha") or {})
        d["mapa"] = MapaProblema.model_validate(d.get("mapa") or {})
        d["bancada"] = EstadoBancada(**(d.get("bancada") or {}))
        d["pre_revisao"] = PreRevisao.model_validate(d["pre_revisao"]) if d.get("pre_revisao") else None
        d["revisoes"] = [Revisao.model_validate(r) for r in d.get("revisoes") or []]
        d["decisao"] = DecisaoSponsor.model_validate(d["decisao"]) if d.get("decisao") else None
        return cls(**d)


class SessionStore:
    """Sessões em SQLite. Um lock por sessão impede dois turnos simultâneos no mesmo experimento."""

    def __init__(self, path: Path):
        path = Path(path)
        if path.suffix != ".db":
            path = path / "metaexp.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""CREATE TABLE IF NOT EXISTS sessoes (
            id TEXT PRIMARY KEY, papel TEXT, status TEXT, atualizada_em TEXT, dados TEXT NOT NULL)""")
        self._db.commit()
        self._write = threading.Lock()
        self._cache: dict[str, Sessao] = {}
        self._locks: dict[str, threading.Lock] = {}

    def create(self, nome: str | None = None, papel: str = "solicitante", preferencias: dict | None = None) -> Sessao:
        from metaexp.core.papeis import jornada
        j = jornada(papel)
        s = Sessao(id=uuid.uuid4().hex[:12], criada_em=agora(), nome=(nome or "").strip() or "você",
                   papel=j.papel, preferencias=j.valida_preferencias(preferencias))
        s.ficha.id = f"EXP-{s.id[:6].upper()}"
        s.registrar("criada", j.nome)
        self.save(s)
        return s

    def get(self, sid: str) -> Sessao | None:
        if sid in self._cache:
            return self._cache[sid]
        row = self._db.execute("SELECT dados FROM sessoes WHERE id = ?", (sid,)).fetchone()
        if not row:
            return None
        s = Sessao.from_json(row[0])
        self._cache[sid] = s
        return s

    def save(self, s: Sessao) -> None:
        self._cache[s.id] = s
        with self._write:
            self._db.execute(
                "INSERT INTO sessoes (id, papel, status, atualizada_em, dados) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET papel=excluded.papel, status=excluded.status, "
                "atualizada_em=excluded.atualizada_em, dados=excluded.dados",
                (s.id, s.papel, s.status, agora(), s.to_json()))
            self._db.commit()

    def lock(self, sid: str) -> threading.Lock:
        return self._locks.setdefault(sid, threading.Lock())

    def list(self, status: tuple[str, ...] | None = None) -> list[Sessao]:
        q = "SELECT id FROM sessoes"
        args: tuple = ()
        if status:
            q += f" WHERE status IN ({','.join('?' * len(status))})"
            args = status
        q += " ORDER BY atualizada_em DESC"
        return [s for (sid,) in self._db.execute(q, args).fetchall() if (s := self.get(sid))]
