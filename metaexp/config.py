"""Configuração central, lida de variáveis de ambiente (ou de um arquivo .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Carrega KEY=VALUE de um .env simples sem sobrescrever o ambiente."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Modelo principal de todos os agentes. Esforço por papel: conversa é
    # interativa (medium), artefatos da bancada pedem mais raciocínio (high).
    model: str = field(default_factory=lambda: _env("METAEXP_MODEL", "claude-opus-5-5"))
    effort_chat: str = field(default_factory=lambda: _env("METAEXP_EFFORT_CHAT", "medium"))
    effort_bench: str = field(default_factory=lambda: _env("METAEXP_EFFORT_BENCH", "high"))
    effort_synth: str = field(default_factory=lambda: _env("METAEXP_EFFORT_SYNTH", "medium"))
    # Reexecuta recusas de classificadores em outro modelo, no servidor.
    use_fallbacks: bool = field(default_factory=lambda: _env("METAEXP_FALLBACKS", "1") == "1")

    corpus_dirs: tuple[Path, ...] = field(
        default_factory=lambda: tuple(
            Path(p) for p in _env(
                "METAEXP_CORPUS_DIRS",
                f"{ROOT / 'data/corpus/real'}{os.pathsep}{ROOT / 'data/corpus/sintetico'}",
            ).split(os.pathsep) if p
        )
    )
    real_docs_dir: Path = field(default_factory=lambda: Path(_env("METAEXP_REAL_DOCS", str(ROOT / "data/real"))))
    sessions_dir: Path = field(default_factory=lambda: Path(_env("METAEXP_SESSIONS_DIR", str(ROOT / "data/sessions"))))
    frontend_dir: Path = field(default_factory=lambda: Path(_env("METAEXP_FRONTEND_DIR", str(ROOT / "prototipo"))))

    # Ralph Loop (seção 4.6 da proposta)
    q_min: float = 0.85
    k_max: int = 5


settings = Settings()
