"""Configuration : variables d'environnement (+ fichier .env optionnel)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_MODELS = {
    "tts": "gpt-4o-mini-tts",
    "tts_legacy": "tts-1",
    "stt": "gpt-4o-transcribe",
    "stt_mini": "gpt-4o-mini-transcribe",
    "stt_whisper": "whisper-1",
    "stt_diarize": "gpt-4o-transcribe-diarize",
    "vision": "gpt-4o-mini",
    "text_only": "gpt-3.5-turbo",
    "audio_chat": "gpt-audio",
}

DEFAULT_IMAGE_URL = "https://www.python.org/static/community_logos/python-logo.png"

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #")[0].strip().strip('"').strip("'")
        out[k.strip()] = v
    return out


@dataclass
class Config:
    base_url: str
    api_key: str
    label: str
    extra_headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 180.0
    verify_tls: bool = True
    max_tokens_param: str = "max_completion_tokens"
    image_url: str = DEFAULT_IMAGE_URL
    models: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MODELS))
    fixtures_dir: Path = ROOT / "fixtures"
    captures_dir: Path = ROOT / "captures"

    @property
    def out_dir(self) -> Path:
        return self.captures_dir / self.label


def load_config(env_file: str | None = None, label: str | None = None, base_url: str | None = None) -> Config:
    # le fichier fournit les valeurs, l'environnement du shell a priorité
    file_env: dict[str, str] = {}
    if env_file:
        p = Path(env_file)
        if not p.exists():
            raise SystemExit(f"env file introuvable: {p}")
        file_env = _load_env_file(p)
    elif (ROOT / ".env").exists():
        file_env = _load_env_file(ROOT / ".env")
    env = {**file_env, **os.environ}

    url = base_url or env.get("MM_BASE_URL") or "https://api.openai.com/v1"
    key = env.get("MM_API_KEY") or env.get("OPENAI_API_KEY") or ""
    lab = label or env.get("MM_LABEL") or (urlparse(url).hostname or "target").replace(".", "-")

    models = dict(DEFAULT_MODELS)
    for k in models:
        v = env.get(f"MM_MODEL_{k.upper()}")
        if v:
            models[k] = v

    return Config(
        base_url=url.rstrip("/"),
        api_key=key,
        label=lab,
        extra_headers=json.loads(env.get("MM_EXTRA_HEADERS") or "{}"),
        timeout=float(env.get("MM_TIMEOUT") or 180),
        verify_tls=(env.get("MM_VERIFY_TLS", "true").lower() not in ("0", "false", "no")),
        max_tokens_param=env.get("MM_MAX_TOKENS_PARAM") or "max_completion_tokens",
        image_url=env.get("MM_IMAGE_URL") or DEFAULT_IMAGE_URL,
        models=models,
    )
