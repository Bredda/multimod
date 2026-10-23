"""POST /audio/speech — synthèse vocale (texte -> audio binaire)."""
from __future__ import annotations

from ..http import DROP, Req
from . import case
from .util import json_req

EP = "speech"
SENT = "Hello! This is a test of the text to speech endpoint."
P = "/audio/speech"


def body(ctx, model_key: str = "tts", **over) -> dict:
    return {"model": ctx.model(model_key), "input": SENT, "voice": "alloy", **over}


def simple(name, title, expect="2xx", tags=(), notes="", model_key="tts", **over):
    """Cas à un seul appel JSON : body de base + surcharges (DROP retire une clé)."""
    def fn(ctx):
        ctx.call(json_req(P, body(ctx, model_key, **over)))
    case(EP, name, title, expect, tags, notes)(fn)


# ---- nominal
simple("default", "Appel minimal (model, input, voice) : format par défaut attendu = mp3")
simple("legacy_tts1", "Modèle historique tts-1", model_key="tts_legacy")
for fmt in ("mp3", "opus", "aac", "flac", "wav", "pcm"):
    simple(f"format_{fmt}", f"response_format={fmt} : content-type, conteneur réel et taille du binaire renvoyé",
           tags=("format",), response_format=fmt)

# ---- voix
for v in ("alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"):
    simple(f"voice_{v}", f"Voix intégrée `{v}`", tags=("voice",), voice=v,
           expect="any" if v in ("ballad", "verse") else "2xx",
           notes="absente de tts-1 selon les modèles" if v in ("ballad", "verse") else "")
simple("voice_custom_object", "Voix custom sous forme d'objet {\"id\": ...} (voix personnalisées OpenAI)", "4xx", ("neg", "probe"),
       voice={"id": "voice_does_not_exist"})
simple("voice_unknown", "Voix inconnue", "4xx", ("neg",), voice="bogus")

# ---- speed
simple("speed_min", "speed=0.25 (borne basse)", tags=("params",), speed=0.25)
simple("speed_max", "speed=4.0 (borne haute)", tags=("params",), speed=4.0)
simple("speed_too_low", "speed=0.1 (< min)", "4xx", ("neg", "params"), speed=0.1)
simple("speed_too_high", "speed=5 (> max)", "4xx", ("neg", "params"), speed=5)
simple("speed_string", "speed=\"fast\" (mauvais type)", "4xx", ("neg", "params"), speed="fast")

# ---- instructions / streaming
simple("instructions", "instructions sur gpt-4o-mini-tts", tags=("params",), instructions="Speak slowly, in a calm and warm tone.")
simple("instructions_tts1", "instructions sur tts-1 (doc : sans effet) — ignoré ou rejeté ?", "any", ("params",),
       model_key="tts_legacy", instructions="Speak slowly.")
simple("stream_format_sse", "stream_format=sse : événements speech.audio.delta/done au lieu d'un binaire", tags=("stream", "probe"),
       stream_format="sse")
simple("stream_format_audio", "stream_format=audio (défaut explicite)", tags=("stream", "probe"), stream_format="audio")
simple("stream_format_invalid", "stream_format invalide", "4xx", ("neg", "stream", "probe"), stream_format="ndjson")
simple("stream_format_sse_tts1", "stream_format=sse sur tts-1 (non supporté d'après la doc)", "any", ("stream", "probe"),
       model_key="tts_legacy", stream_format="sse")

# ---- input
simple("input_french", "Texte français accentué", input="Bonjour, ça va très bien ? Où est l'été — là-bas.")
simple("input_unicode_emoji", "Unicode + emoji + caractères non latins", "any", input="Hello 👋 こんにちは 你好 مرحبا")
simple("input_4096", "input = 4096 caractères exactement (limite)", tags=("long",), input=("word " * 820)[:4096])
simple("input_4097", "input = 4097 caractères (> limite)", "4xx", ("neg", "long"), input=("word " * 820)[:4097])
simple("input_empty", "input vide", "4xx", ("neg",), input="")
simple("input_whitespace", "input = espaces seulement", "any", ("neg",), input="   ")
simple("input_not_string", "input = liste de chaînes", "4xx", ("neg",), input=["a", "b"])

# ---- champs manquants / invalides
simple("missing_model", "model absent", "4xx", ("neg",), model=DROP)
simple("missing_voice", "voice absent", "4xx", ("neg",), voice=DROP)
simple("missing_input", "input absent", "4xx", ("neg",), input=DROP)
simple("model_unknown", "model inexistant", "4xx", ("neg",), model="tts-does-not-exist")
simple("model_wrong_type", "model d'un autre type (chat) sur /audio/speech", "4xx", ("neg",), model_key="vision")
simple("format_invalid", "response_format=ogg (hors liste)", "4xx", ("neg",), response_format="ogg")
simple("format_uppercase", "response_format=MP3 (casse)", "any", ("neg",), response_format="MP3")
simple("unknown_param", "paramètre inconnu `foo` : le schéma est additionalProperties=false — rejet ou ignoré ?", "any", ("neg",), foo="bar")


# ---- transport / auth
@case(EP, "content_type_urlencoded", "Corps application/x-www-form-urlencoded au lieu de JSON", "4xx", ("neg", "transport"))
def _(ctx):
    ctx.call(Req(path=P, urlencoded={"model": ctx.model("tts"), "input": SENT, "voice": "alloy"}))


@case(EP, "content_type_multipart", "Corps multipart/form-data au lieu de JSON", "4xx", ("neg", "transport"))
def _(ctx):
    ctx.call(Req(path=P, fields=[("model", ctx.model("tts")), ("input", SENT), ("voice", "alloy")], is_multipart=True))


@case(EP, "malformed_json", "JSON invalide", "4xx", ("neg", "transport"))
def _(ctx):
    ctx.call(Req(path=P, raw_body=b'{"model": ', headers={"Content-Type": "application/json"}))


@case(EP, "auth_invalid", "Clé API invalide", "4xx", ("neg", "auth"))
def _(ctx):
    ctx.call(Req(path=P, json=body(ctx), headers={"Authorization": "Bearer sk-invalid-mmprobe"}))


@case(EP, "auth_missing", "Pas de header Authorization", "4xx", ("neg", "auth"))
def _(ctx):
    ctx.call(Req(path=P, json=body(ctx), headers={"Authorization": None}))
