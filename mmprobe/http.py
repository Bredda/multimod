"""Exécution d'une requête HTTP brute + mesure (TTFB, chunks). Aucun SDK."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Config

DROP = object()  # sentinelle : retire la clé du body


@dataclass
class FilePart:
    field: str
    filename: str
    data: bytes
    content_type: str = "application/octet-stream"
    src: str | None = None  # chemin fixture (pour générer le curl)


@dataclass
class Req:
    path: str
    method: str = "POST"
    json: Any = None
    fields: list[tuple[str, str]] = field(default_factory=list)  # multipart (clés répétables)
    files: list[FilePart] = field(default_factory=list)
    urlencoded: dict[str, str] | None = None
    raw_body: bytes | None = None
    headers: dict[str, str | None] = field(default_factory=dict)  # None => header retiré
    is_multipart: bool = False


@dataclass
class Exchange:
    req: Any                      # Req (HTTP) ou BCall (boto3)
    url: str
    sent_headers: dict[str, str]
    status: int | None = None
    reason: str = ""
    http_version: str = ""
    resp_headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    ttfb_ms: float | None = None
    total_ms: float | None = None
    chunks: int = 0
    retries: int = 0
    error: str | None = None
    dry_run: bool = False
    # --- champs spécifiques boto3 (kind == "boto")
    kind: str = "http"
    data: Any = None              # réponse désérialisée (ou e.response pour une ClientError)
    events: list | None = None    # événements d'un flux (converse_stream, invoke_model_with_response_stream)
    err_code: str | None = None   # Error.Code AWS (ValidationException, ThrottlingException, ...)
    client_side: bool = False     # rejeté par botocore AVANT tout appel réseau (ParamValidationError)

    @property
    def content_type(self) -> str:
        return self.resp_headers.get("content-type", "").split(";")[0].strip().lower()

    def json(self) -> Any:
        if self.kind == "boto":
            return self.data
        try:
            return json.loads(self.body)
        except Exception:
            return None


def redact_headers(h: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in h.items():
        if k.lower() in ("authorization", "x-api-key", "api-key", "cookie"):
            out[k] = (v[:10] + "…<redacted>") if len(v) > 10 else "<redacted>"
        else:
            out[k] = v
    return out


def build_headers(cfg: Config, req: Req) -> dict[str, str]:
    headers: dict[str, str] = {"Authorization": f"Bearer {cfg.api_key}", **cfg.extra_headers}
    for k, v in req.headers.items():
        if v is None:
            headers = {hk: hv for hk, hv in headers.items() if hk.lower() != k.lower()}
        else:
            headers[k] = v
    if req.json is not None:
        headers.setdefault("Content-Type", "application/json")
    return headers


def execute(cfg: Config, req: Req, *, dry_run: bool = False) -> Exchange:
    url = cfg.base_url + req.path
    headers = build_headers(cfg, req)
    ex = Exchange(req=req, url=url, sent_headers=headers, dry_run=dry_run)
    if dry_run:
        return ex

    kwargs: dict[str, Any] = {}
    if req.json is not None:
        kwargs["content"] = json.dumps(req.json, ensure_ascii=False).encode()
    elif req.raw_body is not None:
        kwargs["content"] = req.raw_body
    elif req.urlencoded is not None:
        kwargs["data"] = req.urlencoded
    elif req.is_multipart and req.files:
        data: dict[str, list[str]] = {}
        for k, v in req.fields:
            data.setdefault(k, []).append(v)
        kwargs["data"] = data
        kwargs["files"] = [(f.field, (f.filename, f.data, f.content_type)) for f in req.files]
    elif req.is_multipart:
        # multipart sans aucun fichier : httpx ne sait pas l'émettre, on construit le corps
        boundary = "----mmprobe0123456789"
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
            for k, v in req.fields
        ]
        parts.append(f"--{boundary}--\r\n".encode())
        kwargs["content"] = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        ex.sent_headers = headers

    attempt = 0
    while True:
        t0 = time.perf_counter()
        chunks: list[bytes] = []
        try:
            with httpx.Client(timeout=cfg.timeout, verify=(cfg.ca_bundle or cfg.verify_tls), follow_redirects=False) as client:
                with client.stream(req.method, url, headers=headers, **kwargs) as r:
                    ex.ttfb_ms = round((time.perf_counter() - t0) * 1000, 1)
                    ex.status = r.status_code
                    ex.reason = r.reason_phrase
                    ex.http_version = r.http_version
                    ex.resp_headers = {k.lower(): v for k, v in r.headers.items()}
                    for c in r.iter_bytes():
                        chunks.append(c)
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
            ex.body = b"".join(chunks)
            ex.chunks = len(chunks)
            ex.error = None
        except Exception as e:  # réseau, TLS, timeout...
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
            ex.error = f"{type(e).__name__}: {e}"
            ex.body = b"".join(chunks)
            ex.chunks = len(chunks)
        if ex.status == 429 and attempt < 3:  # seul retry : rate-limit, tracé dans `retries`
            wait = min(float(ex.resp_headers.get("retry-after", 2 ** attempt * 2)), 30)
            time.sleep(wait)
            attempt += 1
            ex.retries = attempt
            ex.status = None
            continue
        return ex
