"""Pedidos de recursos e benchmarks do Lab: armazenamento e provisionamento.

Os pedidos ficam no mesmo arquivo SQLite das sessões (tabelas próprias). Ao
aprovar, o `Provisionador` entrega a credencial:

- chave de LLM: com `METAEXP_LITELLM_MASTER_KEY`, cria uma chave virtual de
  verdade no gateway LiteLLM (`POST /key/generate`, com modelos, validade e
  orçamento); sem ela, gera uma chave local marcada como simulada;
- servidor e GitHub: credenciais locais marcadas como simuladas. Este é o ponto
  de troca para integrar com a infraestrutura (Terraform, API do GitHub) quando
  ela existir.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Optional

import httpx2

from metaexp.config import Settings
from metaexp.core.recursos import BenchmarkLab, Credencial, PedidoRecurso, credencial_local, exemplo_llm
from metaexp.sessions import agora

log = logging.getLogger("metaexp.recursos")


class RecursoStore:
    def __init__(self, path: Path):
        path = Path(path)
        if path.suffix != ".db":
            path = path / "metaexp.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS pedidos (id TEXT PRIMARY KEY, status TEXT, solicitante TEXT, "
                         "criado_em TEXT, dados TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS benchmarks_lab (id TEXT PRIMARY KEY, em TEXT, dados TEXT NOT NULL)")
        self._db.commit()
        self._write = threading.Lock()

    # ------------------------------------------------------------ pedidos ----

    def criar(self, **campos) -> PedidoRecurso:
        p = PedidoRecurso(id=uuid.uuid4().hex[:10], criado_em=agora(), **campos)
        self.salvar(p)
        return p

    def salvar(self, p: PedidoRecurso) -> None:
        with self._write:
            self._db.execute(
                "INSERT INTO pedidos (id, status, solicitante, criado_em, dados) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET status=excluded.status, dados=excluded.dados",
                (p.id, p.status, p.solicitante, p.criado_em, p.model_dump_json()))
            self._db.commit()

    def obter(self, pid: str) -> Optional[PedidoRecurso]:
        row = self._db.execute("SELECT dados FROM pedidos WHERE id = ?", (pid,)).fetchone()
        return PedidoRecurso.model_validate_json(row[0]) if row else None

    def listar(self, status: tuple[str, ...] | None = None, solicitante: str | None = None) -> list[PedidoRecurso]:
        q, args = "SELECT dados FROM pedidos WHERE 1=1", []
        if status:
            q += f" AND status IN ({','.join('?' * len(status))})"
            args += list(status)
        if solicitante:
            q += " AND lower(solicitante) = lower(?)"
            args.append(solicitante.strip())
        q += " ORDER BY criado_em DESC"
        return [PedidoRecurso.model_validate_json(r[0]) for r in self._db.execute(q, args).fetchall()]

    # ---------------------------------------------------------- benchmarks ----

    def registrar_benchmark(self, **campos) -> BenchmarkLab:
        b = BenchmarkLab(id=uuid.uuid4().hex[:10], em=agora(), **campos)
        with self._write:
            self._db.execute("INSERT INTO benchmarks_lab (id, em, dados) VALUES (?, ?, ?)", (b.id, b.em, b.model_dump_json()))
            self._db.commit()
        return b

    def benchmarks(self) -> list[BenchmarkLab]:
        rows = self._db.execute("SELECT dados FROM benchmarks_lab ORDER BY em DESC").fetchall()
        return [BenchmarkLab.model_validate_json(r[0]) for r in rows]

    def remover_benchmark(self, bid: str) -> bool:
        with self._write:
            cur = self._db.execute("DELETE FROM benchmarks_lab WHERE id = ?", (bid,))
            self._db.commit()
        return cur.rowcount > 0


class Provisionador:
    def __init__(self, cfg: Settings, client: httpx2.Client | None = None):
        self.cfg = cfg
        self.client = client

    def _gateway(self) -> str | None:
        if not (self.cfg.litellm_master_key and self.cfg.hub_url):
            return None
        base = self.cfg.hub_url.rstrip("/")
        return base[:-3] if base.endswith("/v1") else base

    def provisionar(self, p: PedidoRecurso) -> Credencial:
        local = credencial_local(p, hub_url=self.cfg.hub_url, github_org=self.cfg.github_org)
        gateway = self._gateway()
        if p.tipo != "llm_key" or not gateway:
            return local
        d = p.detalhes
        body = {"models": d.get("modelos") or ["deepseek-v4-flash"], "duration": d.get("validade", "30d"),
                "max_budget": float(d.get("orcamento", "50")), "budget_duration": "30d",
                "key_alias": f"metaexp-{p.id}", "metadata": {"solicitante": p.solicitante, "pedido": p.id,
                                                              "experimento": p.experimento or ""}}
        client = self.client or httpx2.Client(timeout=30.0, verify=self.cfg.anthropic_verify_ssl)
        r = client.post(f"{gateway}/key/generate", json=body,
                        headers={"Authorization": f"Bearer {self.cfg.litellm_master_key}"})
        r.raise_for_status()
        data = r.json()
        base = self.cfg.hub_url.rstrip("/")
        return local.model_copy(update={"segredo": data["key"], "simulada": False,
                                        "expira_em": data.get("expires") or local.expira_em,
                                        "campos": {**local.campos, "base_url": base},
                                        "exemplo": exemplo_llm(base, body["models"][0])})

    def revogar(self, p: PedidoRecurso) -> None:
        gateway = self._gateway()
        if p.tipo != "llm_key" or not gateway or not p.credencial or p.credencial.simulada:
            return
        client = self.client or httpx2.Client(timeout=30.0, verify=self.cfg.anthropic_verify_ssl)
        r = client.post(f"{gateway}/key/delete", json={"keys": [p.credencial.segredo]},
                        headers={"Authorization": f"Bearer {self.cfg.litellm_master_key}"})
        r.raise_for_status()
