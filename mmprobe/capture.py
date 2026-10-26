"""Sérialisation d'un échange : request.json / response.json / binaires / curl.sh."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import wave
from pathlib import Path
from typing import Any

from .http import Exchange, FilePart, redact_headers

B64_RE = re.compile(r"^[A-Za-z0-9+/=_\-\s]+$")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def shrink(obj: Any, limit: int = 256) -> Any:
    """Remplace les gros blobs base64 / data-URL par un descripteur lisible."""
    if isinstance(obj, dict):
        return {k: shrink(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shrink(v, limit) for v in obj]
    if isinstance(obj, str) and len(obj) > limit:
        if obj.startswith("data:") and ";base64," in obj:
            head, payload = obj.split(";base64,", 1)
            return f"{head};base64,<{len(payload)} chars, sha256:{sha(payload.encode())}>"
        if B64_RE.match(obj[:200]):
            return f"<base64 {len(obj)} chars, sha256:{sha(obj.encode())}>"
        return obj[:2000] + f"…(+{len(obj) - 2000} chars)" if len(obj) > 2000 else obj
    return obj


def sniff_audio(b: bytes) -> str:
    if b[:3] == b"ID3":
        return "mp3"
    if len(b) > 1 and b[0] == 0xFF and (b[1] & 0xF0) == 0xF0:
        return "aac" if (b[1] & 0x06) == 0 else "mp3"  # ADTS : bits de layer = 00 ; MP3 : layer III = 01
    if len(b) > 1 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0:
        return "mp3"
    if b[:4] == b"RIFF" and b[8:12] == b"WAVE":
        return "wav"
    if b[:4] == b"fLaC":
        return "flac"
    if b[:4] == b"OggS":
        return "ogg"
    if b[4:8] == b"ftyp":
        return "mp4"
    if b[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if b[:1] in (b"{", b"["):
        return "json?"
    return "unknown/raw"


AUDIO_EXT = {"mp3": "mp3", "wav": "wav", "flac": "flac", "ogg": "ogg", "aac": "aac", "mp4": "m4a", "webm": "webm"}


def write_pcm_wav(path: Path, pcm: bytes, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in re.split(r"\r?\n\r?\n", text):
        if not block.strip():
            continue
        ev: dict[str, Any] = {}
        data_lines = []
        for line in block.splitlines():
            if line.startswith("event:"):
                ev["event"] = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip(" "))
            elif line.startswith(":"):
                ev.setdefault("comments", []).append(line[1:].strip())
        raw = "\n".join(data_lines)
        if raw == "[DONE]":
            ev["data"] = "[DONE]"
        else:
            try:
                ev["data"] = json.loads(raw)
            except Exception:
                ev["data"] = raw
        events.append(ev)
    return events


def _chat_audio_from_message(body: dict) -> tuple[bytes | None, str | None]:
    try:
        a = body["choices"][0]["message"]["audio"]
        return base64.b64decode(a["data"]), a.get("transcript")
    except Exception:
        return None, None


def _stream_audio(events: list[dict]) -> tuple[bytes, str]:
    pcm, transcript = b"", ""
    for e in events:
        d = e.get("data")
        if not isinstance(d, dict):
            continue
        if d.get("type") == "speech.audio.delta" and d.get("audio"):  # /audio/speech?stream_format=sse
            pcm += base64.b64decode(d["audio"])
        for ch in d.get("choices") or []:  # /chat/completions stream
            a = (ch.get("delta") or {}).get("audio")
            if a:
                if a.get("data"):
                    pcm += base64.b64decode(a["data"])
                transcript += a.get("transcript") or ""
    return pcm, transcript


def stream_summary(events: list[dict]) -> dict:
    """Agrège un flux SSE chat (texte, finish_reason, usage) ou audio (types d'events)."""
    text, finish, usage, types, first_keys = "", None, None, {}, None
    for e in events:
        d = e.get("data")
        if not isinstance(d, dict):
            continue
        if first_keys is None:
            first_keys = sorted(d.keys())
        if "type" in d:
            types[d["type"]] = types.get(d["type"], 0) + 1
            if d["type"] == "transcript.text.delta":
                text += d.get("delta", "")
            if d["type"] == "transcript.text.done" and not text:
                text = d.get("text", "")
        for ch in d.get("choices") or []:
            text += (ch.get("delta") or {}).get("content") or ""
            finish = ch.get("finish_reason") or finish
        if d.get("usage"):
            usage = d["usage"]
    return {
        "events": len(events),
        "ends_with_done": bool(events) and events[-1].get("data") == "[DONE]",
        "event_types": types or None,
        "first_event_keys": first_keys,
        "text": text or None,
        "finish_reason": finish,
        "usage": usage,
    }


def request_dump(ex: Exchange) -> dict:
    r = ex.req
    d: dict[str, Any] = {
        "method": r.method,
        "url": ex.url,
        "headers": redact_headers(ex.sent_headers),
    }
    if r.json is not None:
        d["body"] = shrink(r.json)
    elif r.is_multipart:
        d["multipart"] = {
            "fields": [[k, v] for k, v in r.fields],
            "files": [
                {"field": f.field, "filename": f.filename, "content_type": f.content_type,
                 "bytes": len(f.data), "sha256": sha(f.data), "magic": sniff_audio(f.data[:16]) if f.data else "empty"}
                for f in r.files
            ],
        }
    elif r.urlencoded is not None:
        d["urlencoded"] = r.urlencoded
    elif r.raw_body is not None:
        d["raw_body"] = r.raw_body[:500].decode("utf-8", "replace")
    return d


def curl_script(ex: Exchange, dirpath: Path) -> str:
    r = ex.req
    path = r.path
    lines = ["#!/usr/bin/env bash", "# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet",
             f'curl -sS -i -X {r.method} "$MM_BASE_URL{path}" \\']
    for k, v in ex.sent_headers.items():
        if k.lower() == "authorization":
            lines.append('  -H "Authorization: Bearer $MM_API_KEY" \\')
        elif k.lower() == "content-type" and r.is_multipart:
            continue
        else:
            lines.append(f'  -H "{k}: {v}" \\')
    if r.json is not None:
        lines.append(f"  --data-binary @{(dirpath / 'request.raw.json').as_posix()}")
    elif r.is_multipart:
        for k, v in r.fields:
            lines.append(f"  -F '{k}={v}' \\")
        for f in r.files:
            src = f.src or f"<{f.filename}>"
            lines.append(f"  -F '{f.field}=@{src};filename={f.filename};type={f.content_type}' \\")
        lines[-1] = lines[-1].rstrip(" \\")
    elif r.urlencoded is not None:
        for k, v in r.urlencoded.items():
            lines.append(f"  --data-urlencode '{k}={v}' \\")
        lines[-1] = lines[-1].rstrip(" \\")
    elif r.raw_body is not None:
        lines.append(f"  --data-binary '{r.raw_body.decode('utf-8', 'replace')}'")
    else:
        lines[-1] = lines[-1].rstrip(" \\")
    return "\n".join(lines) + "\n"


def save(ex: Exchange, d: Path) -> dict:
    """Écrit tous les artefacts d'un échange dans `d`. Retourne un résumé court pour l'index."""
    d.mkdir(parents=True, exist_ok=True)
    if ex.kind == "boto":
        return save_boto(ex, d)
    (d / "request.json").write_text(json.dumps(request_dump(ex), indent=2, ensure_ascii=False))
    if ex.req.json is not None:
        (d / "request.raw.json").write_text(json.dumps(ex.req.json, ensure_ascii=False))
    (d / "curl.sh").write_text(curl_script(ex, d))
    if ex.dry_run:
        return {"status": None, "dry_run": True}

    resp: dict[str, Any] = {
        "status": ex.status,
        "reason": ex.reason,
        "http_version": ex.http_version,
        "headers": ex.resp_headers,
        "timing": {"ttfb_ms": ex.ttfb_ms, "total_ms": ex.total_ms, "chunks": ex.chunks, "retries_429": ex.retries},
        "bytes": len(ex.body),
    }
    if ex.error:
        resp["transport_error"] = ex.error
    ct = ex.content_type
    body = ex.body
    extra: dict[str, Any] = {}

    if ct == "text/event-stream" or body.startswith(b"data:"):
        text = body.decode("utf-8", "replace")
        (d / "response.sse.txt").write_text(text if len(text) < 2_000_000 else text[:2_000_000])
        events = parse_sse(text)
        resp["kind"] = "sse"
        resp["stream_summary"] = stream_summary(events)
        resp["events"] = shrink(events)
        pcm, tr = _stream_audio(events)
        if pcm:
            # chat stream => pcm16 24kHz mono ; speech sse => selon response_format (pcm par défaut non garanti)
            fmt = (ex.req.json or {}).get("response_format") or (ex.req.json or {}).get("audio", {}).get("format")
            if fmt in ("pcm", "pcm16", None):
                write_pcm_wav(d / "response.audio.wav", pcm)
                extra["audio_file"] = "response.audio.wav"
            else:
                (d / f"response.audio.{fmt}").write_bytes(pcm)
                extra["audio_file"] = f"response.audio.{fmt}"
            extra["audio_bytes"] = len(pcm)
            extra["audio_transcript"] = tr or None
    elif ct == "application/json" or body[:1] in (b"{", b"["):
        parsed = ex.json()
        resp["kind"] = "json"
        resp["body"] = shrink(parsed) if parsed is not None else body.decode("utf-8", "replace")
        if isinstance(parsed, dict):
            pcm, tr = _chat_audio_from_message(parsed)
            if pcm:
                fmt = (ex.req.json or {}).get("audio", {}).get("format", "wav")
                if fmt == "pcm16":
                    write_pcm_wav(d / "response.audio.wav", pcm)
                    extra["audio_file"] = "response.audio.wav"
                else:
                    (d / f"response.audio.{fmt}").write_bytes(pcm)
                    extra["audio_file"] = f"response.audio.{fmt}"
                extra["audio_bytes"] = len(pcm)
                extra["audio_detected"] = sniff_audio(pcm[:16])
                extra["audio_transcript"] = tr
    elif ct.startswith("audio/") or ct in ("application/octet-stream", "binary/octet-stream"):
        det = sniff_audio(body[:16])
        ext = AUDIO_EXT.get(det, "bin")
        (d / f"response.audio.{ext}").write_bytes(body)
        resp["kind"] = "binary"
        extra = {"audio_file": f"response.audio.{ext}", "audio_bytes": len(body), "audio_detected": det}
    else:
        resp["kind"] = "text"
        resp["body"] = body.decode("utf-8", "replace")[:20000]
    if extra:
        resp["extracted"] = extra
    (d / "response.json").write_text(json.dumps(resp, indent=2, ensure_ascii=False))
    return {"status": ex.status, "kind": resp.get("kind"), "content_type": ct, "ttfb_ms": ex.ttfb_ms,
            "total_ms": ex.total_ms, "bytes": len(body), "extracted": extra or None, "transport_error": ex.error}


# ====================================================================== boto3 (Bedrock)
def jsonable(obj: Any) -> Any:
    """Rend une structure boto3 sérialisable : bytes -> descripteur, datetime -> str, gros blobs raccourcis."""
    import datetime

    if isinstance(obj, (bytes, bytearray)):
        b = bytes(obj)
        magic = sniff_audio(b[:16])
        if b[:8] == b"\x89PNG\r\n\x1a\n": magic = "png"
        elif b[:3] == b"\xff\xd8\xff": magic = "jpeg"
        elif b[:6] in (b"GIF87a", b"GIF89a"): magic = "gif"
        elif b[:4] == b"RIFF" and b[8:12] == b"WEBP": magic = "webp"
        return f"<bytes {len(b)}, sha256:{sha(b)}, magic={magic}>"
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, str):
        return shrink(obj)
    if hasattr(obj, "read"):
        return "<stream>"
    return obj


def to_wire(obj: Any) -> Any:
    """Pour request.raw.json : les bytes sont encodés {"__bytes_b64__": ...} (rejouable via replay.py)."""
    if isinstance(obj, (bytes, bytearray)):
        return {"__bytes_b64__": base64.b64encode(bytes(obj)).decode()}
    if isinstance(obj, dict):
        return {k: to_wire(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_wire(v) for v in obj]
    return obj


REPLAY_PY = '''#!/usr/bin/env python3
"""Rejoue cet appel boto3. Identifiants/région : environnement AWS habituel (ou AWS_PROFILE / AWS_REGION)."""
import base64, json, pathlib, sys
import boto3

def dec(o):
    if isinstance(o, dict):
        if set(o) == {"__bytes_b64__"}:
            return base64.b64decode(o["__bytes_b64__"])
        return {k: dec(v) for k, v in o.items()}
    return [dec(v) for v in o] if isinstance(o, list) else o

req = json.loads((pathlib.Path(__file__).parent / "request.raw.json").read_text())
client = boto3.client(req["service"], region_name=req.get("region"))
resp = getattr(client, req["operation"])(**dec(req["params"]))
for k in ("stream", "body"):
    if k in resp and hasattr(resp[k], "read"):
        resp[k] = json.loads(resp[k].read())
    elif k in resp and k == "stream":
        resp[k] = list(resp[k])
print(json.dumps(resp, default=str, indent=2)[:20000])
'''


def stream_summary_boto(events: list[dict]) -> dict:
    text, stop, usage, types, tool = "", None, None, {}, None
    for e in events:
        for k, v in e.items():
            types[k] = types.get(k, 0) + 1
            if k == "contentBlockDelta":
                dl = v.get("delta", {})
                text += dl.get("text", "")
                if "toolUse" in dl:
                    tool = tool or "toolUse"
            elif k == "contentBlockStart" and "toolUse" in v.get("start", {}):
                tool = v["start"]["toolUse"].get("name")
            elif k == "messageStop":
                stop = v.get("stopReason")
            elif k == "metadata":
                usage = v.get("usage")
    return {"events": len(events), "event_types": types, "stop_reason": stop, "usage": usage, "text": text or None, "tool_use": tool}


def save_boto(ex: Exchange, d: Path) -> dict:
    call = ex.req
    params = call.final_params()
    req_dump = {"service": call.service, "region": ex.url.split(":", 1)[1].split("/")[0], "operation": call.operation,
                "bad_credentials": call.bad_credentials or None, "params": jsonable(params)}
    if call.body is not None:
        req_dump["params"]["body"] = jsonable(call.body)  # JSON lisible plutôt que bytes opaques
    (d / "request.json").write_text(json.dumps(req_dump, indent=2, ensure_ascii=False, default=str))
    (d / "request.raw.json").write_text(json.dumps({"service": call.service, "region": req_dump["region"], "operation": call.operation,
                                                    "params": to_wire(params)}, ensure_ascii=False))
    (d / "replay.py").write_text(REPLAY_PY)
    if ex.dry_run:
        return {"status": None, "dry_run": True, "client_side_error": ex.error if ex.client_side else None}

    resp: dict[str, Any] = {"status": ex.status, "reason": ex.reason, "operation": call.operation, "headers": ex.resp_headers,
                            "timing": {"ttfb_ms": ex.ttfb_ms, "total_ms": ex.total_ms, "events": ex.chunks, "retries_throttling": ex.retries}}
    if ex.client_side:
        resp["kind"] = "client-side-error"
    elif ex.events is not None:
        resp["kind"] = "boto-stream"
        resp["stream_summary"] = stream_summary_boto(ex.events)
        resp["events"] = jsonable(ex.events)
    elif ex.err_code:
        resp["kind"] = "boto-error"
    elif ex.status is None:
        resp["kind"] = "transport-error"
    else:
        resp["kind"] = "boto-json"
    if ex.error:
        resp["error"] = ex.error
    if ex.err_code:
        resp["error_code"] = ex.err_code
    if ex.data is not None:
        resp["data"] = jsonable(ex.data)
    (d / "response.json").write_text(json.dumps(resp, indent=2, ensure_ascii=False, default=str))
    return {"status": ex.status, "kind": resp["kind"], "error_code": ex.err_code, "ttfb_ms": ex.ttfb_ms, "total_ms": ex.total_ms,
            "transport_error": ex.error if resp["kind"] in ("transport-error", "client-side-error") else None}
