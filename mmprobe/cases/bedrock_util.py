"""Helpers pour construire des appels Converse / InvokeModel (paramètres boto3, pas du JSON HTTP)."""
from __future__ import annotations

from ..bedrock import BCall
from ..fixtures import ext_of


def model(ctx, role: str) -> str:
    m = ctx.cfg.bedrock_models.get(role)
    if not m:
        ctx.skip(f"MM_BEDROCK_MODEL_{role.upper()} non défini (voir .env.example ; `bedrock-models` liste les ids disponibles)")
    return m


def need_family(ctx, role: str, marker: str) -> str:
    m = model(ctx, role)
    if marker not in m.lower():
        ctx.skip(f"le rôle '{role}' ({m}) n'est pas un modèle '{marker}' : cas ignoré")
    return m


def user(*blocks) -> dict:
    return {"role": "user", "content": list(blocks)}


def assistant(*blocks) -> dict:
    return {"role": "assistant", "content": list(blocks)}


def txt(t: str) -> dict:
    return {"text": t}


def fmt_of(name: str) -> str:
    e = ext_of(name)
    return {"jpg": "jpeg"}.get(e, e)


def img(ctx, fixture: str, fmt: str | None = None) -> dict:
    return {"image": {"format": fmt or fmt_of(fixture), "source": {"bytes": ctx.fx.bytes(fixture)}}}


def aud(ctx, fixture: str, fmt: str | None = None) -> dict:
    return {"audio": {"format": fmt or fmt_of(fixture), "source": {"bytes": ctx.fx.bytes(fixture)}}}


def converse(ctx, role: str, messages: list, system: str | None = None, tokens: int | None = 300, stream: bool = False, **extra) -> BCall:
    p: dict = {"modelId": model(ctx, role), "messages": messages}
    if system:
        p["system"] = [{"text": system}]
    if tokens:
        p["inferenceConfig"] = {"maxTokens": tokens}
    p.update(extra)
    return BCall("converse_stream" if stream else "converse", p)
