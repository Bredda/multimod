"""Serveur factice minimal (stdlib) pour valider les scripts sans clé API.
Ne reproduit PAS fidèlement OpenAI : sert uniquement à exercer le pipeline de capture.
Usage: python tools/mock_server.py [port]  puis MM_BASE_URL=http://127.0.0.1:8099/v1 MM_API_KEY=x
"""
import base64, io, json, struct, sys, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def wav_bytes(n=2400):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\x00\x01" * n)
    return b.getvalue()

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body, ct="application/json"):
        if not isinstance(body, bytes): body = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _err(self, msg, code=400, param=None):
        self._send(code, {"error": {"message": msg, "type": "invalid_request_error", "param": param, "code": None}})
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n)
        if "invalid" in (self.headers.get("Authorization") or ""): return self._err("Incorrect API key provided", 401)
        ct = self.headers.get("Content-Type", "")
        if self.path.endswith("/audio/speech"):
            if "json" not in ct: return self._err("expected json")
            try: b = json.loads(raw)
            except Exception: return self._err("bad json")
            if "voice" not in b or "input" not in b or not b["input"]: return self._err("missing field")
            if b.get("stream_format") == "sse":
                ev = lambda t, **k: f"data: {json.dumps({'type': t, **k})}\n\n".encode()
                return self._send(200, ev("speech.audio.delta", audio=base64.b64encode(b"\x00\x01" * 100).decode()) + ev("speech.audio.done", usage={"input_tokens": 5}), "text/event-stream")
            fmt = b.get("response_format", "mp3")
            body = {"wav": wav_bytes(), "mp3": b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" * 50, "flac": b"fLaC" + b"\0" * 40,
                    "opus": b"OggS" + b"\0" * 40, "aac": b"\xff\xf1\x50\x80" + b"\0" * 40, "pcm": b"\x00\x01" * 400}.get(fmt)
            if body is None: return self._err(f"bad format {fmt}", param="response_format")
            return self._send(200, body, "audio/mpeg" if fmt == "mp3" else "audio/" + fmt)
        if self.path.endswith("/audio/transcriptions"):
            if "multipart" not in ct: return self._err("expected multipart")
            if b'name="file"' not in raw: return self._err("missing file", param="file")
            if b"stream" in raw and b"true" in raw:
                ev = lambda t, **k: f"data: {json.dumps({'type': t, **k})}\n\n".encode()
                return self._send(200, ev("transcript.text.delta", delta="Hello ") + ev("transcript.text.done", text="Hello world"), "text/event-stream")
            if b"srt" in raw: return self._send(200, b"1\n00:00:00,000 --> 00:00:02,000\nHello world\n", "text/plain")
            return self._send(200, {"text": "Hello world"})
        if self.path.endswith("/chat/completions"):
            try: b = json.loads(raw)
            except Exception: return self._err("bad json")
            msgs = b.get("messages") or []
            for m in msgs:
                for p in (m["content"] if isinstance(m.get("content"), list) else []):
                    if p.get("type") == "image_url" and not isinstance(p.get("image_url"), dict): return self._err("image_url must be object", param="messages")
            mods = b.get("modalities") or ["text"]
            if "audio" in mods and not b.get("audio"): return self._err("audio param required", param="audio")
            if b.get("stream"):
                def ch(delta, fin=None, usage=None):
                    d = {"id": "c1", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": delta, "finish_reason": fin}]}
                    if usage: d["usage"] = usage; d["choices"] = []
                    return f"data: {json.dumps(d)}\n\n".encode()
                out = ch({"role": "assistant", "content": ""})
                if "audio" in mods:
                    out += ch({"audio": {"id": "audio_1", "data": base64.b64encode(b"\x00\x01" * 200).decode(), "transcript": "Hello"}})
                else:
                    out += ch({"content": "A red "}) + ch({"content": "square."})
                out += ch({}, "stop") + ch({}, usage={"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}) + b"data: [DONE]\n\n"
                return self._send(200, out, "text/event-stream")
            msg = {"role": "assistant", "content": "A red square."}
            if "audio" in mods:
                msg = {"role": "assistant", "content": None, "audio": {"id": "audio_1", "expires_at": 0, "data": base64.b64encode(wav_bytes()).decode(), "transcript": "Hello"}}
            return self._send(200, {"id": "c1", "object": "chat.completion", "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
                                    "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13, "prompt_tokens_details": {"audio_tokens": 0}}})
        self._err("not found", 404)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
