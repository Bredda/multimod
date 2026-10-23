from __future__ import annotations

from typing import Any

from ..fixtures import ext_of
from ..http import DROP, FilePart, Req


def clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not DROP}


def json_req(path: str, body: dict, **kw) -> Req:
    return Req(path=path, json=clean(body), **kw)


def chat_req(ctx, model_key: str, messages: list, tokens: int | None = 200, **extra) -> Req:
    body: dict[str, Any] = {"model": ctx.model(model_key) if model_key in ctx.cfg.models else model_key, "messages": messages}
    if tokens:
        body[ctx.cfg.max_tokens_param] = tokens
    body.update(extra)
    return json_req("/chat/completions", body)


def user(*parts) -> dict:
    return {"role": "user", "content": list(parts)}


def text(t: str) -> dict:
    return {"type": "text", "text": t}


def image(url: str, detail: str | None = None) -> dict:
    iu: dict[str, Any] = {"url": url}
    if detail:
        iu["detail"] = detail
    return {"type": "image_url", "image_url": iu}


def input_audio(data_b64: str, fmt: str) -> dict:
    return {"type": "input_audio", "input_audio": {"data": data_b64, "format": fmt}}


def file_part(ctx, name: str, as_name: str | None = None, ctype: str | None = None, field: str = "file") -> FilePart:
    return FilePart(field=field, filename=as_name or name, data=ctx.fx.bytes(name),
                    content_type=ctype or ctx.fx.mime(as_name or name), src=f"fixtures/{name}")


def multipart(path: str, fields: list[tuple[str, str]], files: list[FilePart]) -> Req:
    return Req(path=path, fields=fields, files=files, is_multipart=True)
