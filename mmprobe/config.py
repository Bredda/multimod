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

# Rôles de modèles Bedrock : AUCUN défaut volontairement (ids / inference profiles dépendent de la région et du compte).
# Renseigner MM_BEDROCK_MODEL_<ROLE> ; `bedrock-models` liste ce qui est disponible.
BEDROCK_ROLES = ("vision", "vision_nova", "vision_other", "audio_in", "audio_in_mini", "text_only", "sonic")

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
    ca_bundle: str | None = None      # chemin d'un bundle CA (proxy d'inspection TLS) ; boto3 utilise AWS_CA_BUNDLE
    max_tokens_param: str = "max_completion_tokens"
    image_url: str = DEFAULT_IMAGE_URL
    models: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MODELS))
    provider: str = "http"            # http (OpenAI, LiteLLM : HTTP brut) | bedrock (boto3, bedrock-runtime)
    aws_region: str | None = None
    aws_profile: str | None = None
    bedrock_models: dict[str, str] = field(default_factory=dict)
    fixtures_dir: Path = ROOT / "fixtures"
    captures_dir: Path = ROOT / "captures"

    @property
    def out_dir(self) -> Path:
        return self.captures_dir / self.label


def load_config(env_file: str | None = None, label: str | None = None, base_url: str | None = None,
                provider: str | None = None) -> Config:
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
    prov = (provider or env.get("MM_PROVIDER") or "http").lower()
    if prov not in ("http", "bedrock"):
        raise SystemExit(f"MM_PROVIDER inconnu: {prov} (http | bedrock)")
    region = env.get("MM_AWS_REGION") or env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION")
    default_label = f"bedrock-{region or 'default'}" if prov == "bedrock" else (urlparse(url).hostname or "target").replace(".", "-")
    lab = label or env.get("MM_LABEL") or default_label

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
        ca_bundle=env.get("MM_CA_BUNDLE") or None,
        max_tokens_param=env.get("MM_MAX_TOKENS_PARAM") or "max_completion_tokens",
        image_url=env.get("MM_IMAGE_URL") or DEFAULT_IMAGE_URL,
        models=models,
        provider=prov,
        aws_region=region,
        aws_profile=env.get("MM_AWS_PROFILE") or env.get("AWS_PROFILE"),
        bedrock_models={r: env[f"MM_BEDROCK_MODEL_{r.upper()}"] for r in BEDROCK_ROLES if env.get(f"MM_BEDROCK_MODEL_{r.upper()}")},
    )
