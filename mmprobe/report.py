"""Résumés courts par échange, REPORT.md par cible, COMPARE.md entre cibles, catalogue des cas."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import capture


def _clip(s: Any, n: int = 110) -> str:
    s = str(s).replace("\n", " ⏎ ").replace("|", "\\|")
    return s if len(s) <= n else s[: n - 1] + "…"


def _err(body: Any, raw: bytes) -> str:
    if isinstance(body, dict):
        e = body.get("error", body.get("detail", body))
        if isinstance(e, dict):
            bits = [str(e.get(k)) for k in ("type", "code", "param") if e.get(k)]
            return f"{'/'.join(bits)}: {e.get('message', '')}" if bits else str(e.get("message", e))
        return str(e)
    return raw[:200].decode("utf-8", "replace")


def _converse_text(out: dict) -> tuple[str, list[str]]:
    parts = (out.get("message") or {}).get("content") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict)), [p["toolUse"].get("name", "?") for p in parts if isinstance(p, dict) and "toolUse" in p]


def summarize_boto(endpoint: str, ex) -> str:
    if ex.client_side:
        return _clip(f"CLIENT-SIDE (botocore, avant envoi) {ex.error}", 240)
    if ex.err_code or (ex.status is None):
        return _clip(f"ERR {ex.error}", 260)
    if ex.events is not None:
        s = capture.stream_summary_boto(ex.events)
        u = s["usage"] or {}
        return _clip(f"STREAM events={s['events']} stop={s['stop_reason']} tok={u.get('inputTokens')}/{u.get('outputTokens')} tool={s['tool_use']} text={s['text']!r}", 240)
    d = ex.data or {}
    if ex.req.operation == "converse":
        text, tools = _converse_text(d.get("output") or {})
        u = d.get("usage") or {}
        return _clip(f"stop={d.get('stopReason')} tok={u.get('inputTokens')}/{u.get('outputTokens')} lat={ (d.get('metrics') or {}).get('latencyMs')}ms tools={tools or None} text={text!r}", 260)
    if ex.req.operation == "count_tokens":
        return _clip(f"inputTokens={d.get('inputTokens')}")
    if ex.req.operation == "invoke_model":
        return _clip(f"invoke body={json.dumps(d.get('body'), ensure_ascii=False)[:200]}", 260)
    return _clip(json.dumps({k: v for k, v in d.items() if k != "ResponseMetadata"}, default=str, ensure_ascii=False), 260)


def summarize(endpoint: str, ex) -> str:
    """Une ligne qui dit l'essentiel de la réponse (utilisée dans l'index et les rapports)."""
    if ex.kind == "boto":
        return summarize_boto(endpoint, ex)
    if ex.error and ex.status is None:
        return _clip(f"TRANSPORT {ex.error}")
    body = ex.json()
    if ex.status is None or ex.status >= 400:
        return _clip("ERR " + _err(body, ex.body), 220)
    ct = ex.content_type

    if endpoint == "speech":
        if ct == "text/event-stream" or ex.body.startswith(b"data:"):
            s = capture.stream_summary(capture.parse_sse(ex.body.decode("utf-8", "replace")))
            return _clip(f"SSE events={s['events']} types={s['event_types']} usage={s['usage']}")
        return _clip(f"audio ct={ct} detected={capture.sniff_audio(ex.body[:16])} {len(ex.body)}B chunks={ex.chunks} ttfb={ex.ttfb_ms}ms")

    if endpoint == "transcriptions":
        if ct == "text/event-stream" or ex.body.startswith(b"data:"):
            s = capture.stream_summary(capture.parse_sse(ex.body.decode("utf-8", "replace")))
            return _clip(f"SSE events={s['events']} types={s['event_types']} text={s['text']!r}")
        if isinstance(body, dict):
            keys = sorted(body.keys())
            extra = ""
            if "segments" in body or "words" in body:
                extra = f" lang={body.get('language')} dur={body.get('duration')} segs={len(body.get('segments') or [])} words={len(body.get('words') or [])}"
            return _clip(f"json keys={keys}{extra} text={body.get('text')!r}")
        return _clip(f"{ct or 'text'}: {ex.body[:90].decode('utf-8', 'replace')}")

    # chat-image / chat-audio
    if ct == "text/event-stream" or ex.body.startswith(b"data:"):
        s = capture.stream_summary(capture.parse_sse(ex.body.decode("utf-8", "replace")))
        u = s["usage"] or {}
        return _clip(f"SSE chunks={s['events']} done={s['ends_with_done']} finish={s['finish_reason']} usage={u.get('prompt_tokens')}/{u.get('completion_tokens')} text={s['text']!r}", 200)
    if isinstance(body, dict) and body.get("choices"):
        ch = body["choices"][0]
        m = ch.get("message") or {}
        u = body.get("usage") or {}
        pd, cd = u.get("prompt_tokens_details") or {}, u.get("completion_tokens_details") or {}
        a = m.get("audio")
        bits = [f"finish={ch.get('finish_reason')}", f"tok={u.get('prompt_tokens')}/{u.get('completion_tokens')}"]
        if pd.get("audio_tokens") or cd.get("audio_tokens"):
            bits.append(f"audio_tok={pd.get('audio_tokens')}/{cd.get('audio_tokens')}")
        if a:
            bits.append(f"audio(id={str(a.get('id'))[:14]}, {len(a.get('data') or '')}b64, transcript={_clip(a.get('transcript'), 50)!r})")
        bits.append(f"content={m.get('content')!r}")
        return _clip(" ".join(bits), 240)
    return _clip(f"{ct}: {ex.body[:120].decode('utf-8', 'replace')}")


# ------------------------------------------------------------------ rapports
def _load_index(out_dir: Path) -> dict:
    p = out_dir / "index.json"
    if not p.exists():
        raise SystemExit(f"pas d'index dans {out_dir} : lancer `run` d'abord")
    return json.loads(p.read_text())


def _cls(status: int | None) -> str:
    return "—" if status is None else f"{status // 100}xx"


def _spec_lines(out_dir: Path) -> list[str]:
    """Lignes d'intro décrivant la spec OpenAPI de référence, si `openapi.source.json` est présent à côté de l'index."""
    p = out_dir / "openapi.source.json"
    if not p.exists():
        return []
    m = json.loads(p.read_text())
    return [
        f"- spec de référence : **{m['title']} v{m['version']}** — branche `{m['branch']}` du dépôt [{m['repo'].split('github.com/')[1]}]({m['repo']}), "
        f"téléchargée le {m['downloaded_at']} ([source]({m['url']}))",
        f"  - copie locale : `{m['file']}` ({m['bytes'] / 1e6:.1f} Mo, sha256 `{m['sha256'][:16]}…`). "
        "Elle est en retard sur l'API réelle (absents : `diarized_json`, `detail=original`, `gpt-4o-transcribe` en `text`…) : "
        "les observations font foi en cas de désaccord.",
    ]


def write_report(out_dir: Path) -> Path:
    idx = _load_index(out_dir)
    rows_by_ep: dict[str, list[str]] = {}
    totals = {"steps": 0, "match": 0, "mismatch": 0, "skipped": 0, "script_error": 0}
    for r in idx["results"]:
        ep = r["case"].split("/")[0]
        lines = rows_by_ep.setdefault(ep, [])
        if r["outcome"] == "skipped":
            totals["skipped"] += 1
            lines.append(f"| `{r['case']}` | — | {r['expect']} | skip | {_clip(r['reason'], 160)} |")
            continue
        if r["outcome"] == "script-error":
            totals["script_error"] += 1
            lines.append(f"| `{r['case']}` | — | {r['expect']} | 💥 | script: {_clip(r['reason'], 160)} |")
            continue
        for s in r["steps"]:
            totals["steps"] += 1
            m = s.get("match")
            if m is True: totals["match"] += 1
            if m is False: totals["mismatch"] += 1
            mark = {True: "✓", False: "✗ ÉCART", None: "·"}[m]
            name = r["case"] + (f" › {s['step']}" if s.get("step") else "")
            lines.append(f"| `{name}` | {s.get('status')} | {s['expect']} | {mark} | {s.get('summary') or ''} |")
    out = [f"# Rapport — `{idx['label']}`", "",
           f"- cible : `{idx['base_url']}`{' (boto3, bedrock-runtime)' if idx.get('provider') == 'bedrock' else ''}  ·  généré : {idx['generated_at']}",
           f"- modèles : " + ", ".join(f"{k}=`{v}`" for k, v in idx["models"].items()),
           *_spec_lines(out_dir),
           f"- échanges : {totals['steps']} · conformes à l'attente : {totals['match']} · **écarts : {totals['mismatch']}** · "
           f"cas ignorés : {totals['skipped']} · erreurs de script : {totals['script_error']}", "",
           "> « Attente » = comportement décrit par la doc OpenAI (2xx / 4xx / any), tirée de la spec ci-dessus et des guides publics "
           "(certaines limites, ex. 25 Mo audio / 20 Mo image, ne figurent que dans les guides). Un écart n'est pas un bug : "
           "c'est une information (doc imprécise, ou la cible diffère).", ""]
    names = {"speech": "POST /audio/speech", "transcriptions": "POST /audio/transcriptions",
             "chat-image": "POST /chat/completions — image_url", "chat-audio": "POST /chat/completions — input_audio / audio out"}
    if idx.get("provider") == "bedrock":
        names = {"speech": "Bedrock — synthèse vocale / audio en sortie (existe-t-il ?)", "transcriptions": "Bedrock — transcription (Converse + AudioBlock)",
                 "chat-image": "Bedrock — images (Converse / ConverseStream / InvokeModel)", "chat-audio": "Bedrock — audio en entrée (Converse AudioBlock)"}
    for ep, lines in rows_by_ep.items():
        out += [f"## {names.get(ep, ep)}", "", "| cas | HTTP | attente | | résumé |", "|---|---|---|---|---|", *lines, ""]
    p = out_dir / "REPORT.md"
    p.write_text("\n".join(out))
    return p


def write_compare(base: Path, labels: list[str]) -> Path:
    idxs = {l: _load_index(base / l) for l in labels}
    table: dict[str, dict[str, Any]] = {}
    order: dict[str, int] = {}
    for l, idx in idxs.items():
        for r in idx["results"]:
            order.setdefault(r["case"], r.get("order", 10**6))
            if r["outcome"] == "skipped":
                table.setdefault(r["case"] + "", {})[l] = [("skip", None)]
                continue
            table.setdefault(r["case"], {})[l] = [(s.get("step"), s.get("status")) for s in r.get("steps", [])] or [(None, None)]
    out = [f"# Comparaison — {' vs '.join(f'`{l}`' for l in labels)}", "",
           "Une ligne par cas/étape. **Diff** = les classes de statut (2xx/4xx/5xx) diffèrent entre cibles ; `~` = mêmes classes mais codes différents.", "",
           "| cas | " + " | ".join(labels) + " | diff |", "|---|" + "---|" * (len(labels) + 1)]
    n_diff = 0
    for cid in sorted(table, key=lambda c: order[c]):
        per = table[cid]
        steps = []
        for l in labels:
            for st, _ in per.get(l, []):
                if st not in steps:
                    steps.append(st)
        for st in steps:
            cells, codes = [], []
            for l in labels:
                found = [s for s in per.get(l, []) if s[0] == st]
                code = found[0][1] if found else None
                codes.append(code)
                cells.append("n/a" if not found else ("skip" if found[0][0] == "skip" else str(code)))
            real = [c for c in codes if c is not None]
            classes = {c // 100 for c in real}
            flag = "**DIFF**" if len(classes) > 1 else ("~" if len(set(real)) > 1 else "")
            n_diff += flag == "**DIFF**"
            out.append(f"| `{cid}{' › ' + st if st and st != 'skip' else ''}` | " + " | ".join(cells) + f" | {flag} |")
    out.insert(2, f"**{n_diff} divergence(s) de classe de statut.**")
    p = base / ("COMPARE_" + "_vs_".join(labels) + ".md")
    p.write_text("\n".join(out) + "\n")
    return p


def write_catalog(cases, path: Path) -> Path:
    names = {"http": {"speech": "POST /audio/speech", "transcriptions": "POST /audio/transcriptions",
                      "chat-image": "POST /chat/completions — content part `image_url`",
                      "chat-audio": "POST /chat/completions — content part `input_audio` & sortie audio"},
             "bedrock": {"speech": "Synthèse vocale / audio en sortie — ce qui existe sur bedrock-runtime",
                         "transcriptions": "Transcription — Converse + AudioBlock (pas d'endpoint dédié)",
                         "chat-image": "Images — Converse / ConverseStream / InvokeModel",
                         "chat-audio": "Audio en entrée — Converse AudioBlock"}}
    titles = {"http": "Cible HTTP — OpenAI / LiteLLM (HTTP brut, sans SDK)", "bedrock": "Cible Bedrock — boto3 / bedrock-runtime"}
    out = ["# Catalogue des cas de test", "",
           "_Généré par `python -m mmprobe catalog` — ne pas éditer à la main._", "",
           f"{len(cases)} cas. « Attente » = ce que la doc laisse prévoir (`2xx`, `4xx`, `any` = indéterminé / à découvrir). "
           "Tags : `heavy` = gros payloads (opt-in `--heavy`), `security` = SSRF (opt-in, ta gateway uniquement), `probe` = paramètre récent/non documenté dans la spec publique, `neg` = cas négatif. "
           "Un même id (`chat-image/multi_images`) dans les deux cibles = même scénario, comparable avec `report --compare`."]
    for target in ("http", "bedrock"):
        sub = [c for c in cases if c.target == target]
        if not sub:
            continue
        out += ["", f"# {titles[target]} — {len(sub)} cas"]
        cur = None
        for c in sub:
            if c.endpoint != cur:
                cur = c.endpoint
                out += ["", f"## {names[target].get(cur, cur)}", "", "| cas | attente | tags | ce que ça teste |", "|---|---|---|---|"]
            note = f" — {c.notes}" if c.notes else ""
            out.append(f"| `{c.name}` | {c.expect} | {', '.join(c.tags)} | {c.title.replace('|', '/')}{note.replace('|', '/')} |")
    path.write_text("\n".join(out) + "\n")
    return path
