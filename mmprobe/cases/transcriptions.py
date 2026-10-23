"""POST /audio/transcriptions — parole -> texte (multipart/form-data)."""
from __future__ import annotations

from ..fixtures import Skip
from ..http import FilePart, Req
from . import case
from .util import file_part, multipart

EP = "transcriptions"
P = "/audio/transcriptions"
EN = "speech_en.mp3"  # généré par `fixtures` via /audio/speech


def stt(ctx, model_key="stt", audio=EN, fields=(), as_name=None, ctype=None) -> Req:
    return multipart(P, [("model", ctx.model(model_key)), *fields], [file_part(ctx, audio, as_name, ctype)])


def simple(name, title, expect="2xx", tags=(), notes="", model_key="stt", audio=EN, fields=(), as_name=None, ctype=None):
    def fn(ctx):
        ctx.call(stt(ctx, model_key, audio, fields, as_name, ctype))
    case(EP, name, title, expect, tags, notes)(fn)


# ---- modèles
simple("model_whisper", "whisper-1, format json par défaut", model_key="stt_whisper")
simple("model_4o_transcribe", "gpt-4o-transcribe, format json par défaut")
simple("model_4o_mini_transcribe", "gpt-4o-mini-transcribe", model_key="stt_mini")

# ---- formats de fichier d'entrée (générés par /audio/speech)
for ext, fname, exp, note in [
    ("mp3", "speech_en.mp3", "2xx", ""), ("wav", "speech_en.wav", "2xx", ""), ("flac", "speech_en.flac", "2xx", ""),
    ("ogg", "speech_en.ogg", "2xx", "Ogg/Opus produit par response_format=opus"),
    ("opus", "speech_en.opus", "any", "extension .opus : listée ou non ?"),
    ("aac", "speech_en.aac", "any", "AAC ADTS brut : extension .aac absente de la liste doc"),
    ("wav_from_pcm", "speech_en_from_pcm.wav", "2xx", "PCM 24 kHz s16le mono reconditionné en WAV"),
]:
    simple(f"input_{ext}", f"Fichier d'entrée {ext}", exp, ("input-format",), note, audio=fname)
for ext in ("m4a", "mp4", "webm", "mpga", "mpeg"):  # non générables sans ffmpeg : à déposer dans fixtures/
    simple(f"input_{ext}", f"Fichier d'entrée {ext} (à fournir : fixtures/sample.{ext})", "2xx", ("input-format", "user-fixture"),
           audio=f"sample.{ext}")
simple("input_fr", "Audio français sans `language` (détection auto)", audio="speech_fr.mp3")
simple("input_tone_no_speech", "Son sans parole (sinus 440 Hz) : texte vide ou hallucination ?", "any", audio="tone_440hz.wav")
simple("input_silence", "Silence 3 s", "any", audio="silence_3s.wav")

# ---- response_format
for fmt in ("json", "text", "srt", "vtt", "verbose_json"):
    simple(f"fmt_{fmt}_whisper", f"response_format={fmt} sur whisper-1", tags=("response_format",),
           model_key="stt_whisper", fields=[("response_format", fmt)])
for fmt, exp in [("json", "2xx"), ("text", "any"), ("srt", "4xx"), ("vtt", "4xx"), ("verbose_json", "4xx")]:
    simple(f"fmt_{fmt}_4o", f"response_format={fmt} sur gpt-4o-transcribe (doc : json seulement)", exp, ("response_format",),
           fields=[("response_format", fmt)])
simple("fmt_diarized_json", "diarized_json sur le modèle diarize (segments par locuteur)", "any", ("response_format", "probe"),
       model_key="stt_diarize", fields=[("response_format", "diarized_json"), ("chunking_strategy", "auto")])
simple("fmt_invalid", "response_format invalide", "4xx", ("neg", "response_format"), fields=[("response_format", "yaml")])

# ---- timestamps
simple("ts_segment", "verbose_json + timestamp_granularities[]=segment", tags=("timestamps",), model_key="stt_whisper",
       fields=[("response_format", "verbose_json"), ("timestamp_granularities[]", "segment")])
simple("ts_word", "verbose_json + timestamp_granularities[]=word", tags=("timestamps",), model_key="stt_whisper",
       fields=[("response_format", "verbose_json"), ("timestamp_granularities[]", "word")])
simple("ts_word_and_segment", "verbose_json + word ET segment (clé répétée)", tags=("timestamps",), model_key="stt_whisper",
       fields=[("response_format", "verbose_json"), ("timestamp_granularities[]", "word"), ("timestamp_granularities[]", "segment")])
simple("ts_without_verbose", "timestamp_granularities sans verbose_json (doc : requis) — rejet ou ignoré ?", "any", ("timestamps", "neg"),
       model_key="stt_whisper", fields=[("timestamp_granularities[]", "word")])
simple("ts_invalid", "timestamp_granularities[]=sentence", "4xx", ("timestamps", "neg"), model_key="stt_whisper",
       fields=[("response_format", "verbose_json"), ("timestamp_granularities[]", "sentence")])
simple("ts_4o", "timestamp_granularities sur gpt-4o-transcribe", "any", ("timestamps",),
       fields=[("response_format", "verbose_json"), ("timestamp_granularities[]", "word")])

# ---- paramètres
simple("language_en", "language=en", fields=[("language", "en")], tags=("params",))
simple("language_fr_on_fr", "language=fr sur audio français", audio="speech_fr.mp3", fields=[("language", "fr")], tags=("params",))
simple("language_wrong", "language=fr forcé sur audio anglais : traduit, transcrit en français phonétique, erreur ?", "any", ("params",),
       fields=[("language", "fr")])
simple("language_invalid", "language=english (pas un code ISO-639-1)", "any", ("params", "neg"), fields=[("language", "english")])
simple("prompt", "prompt de guidage (vocabulaire)", fields=[("prompt", "Laurent, Paris, gateway")], tags=("params",))
simple("temperature_0_5", "temperature=0.5", fields=[("temperature", "0.5")], tags=("params",), model_key="stt_whisper")
simple("temperature_out_of_range", "temperature=2 (> 1)", "4xx", ("params", "neg"), fields=[("temperature", "2")], model_key="stt_whisper")
simple("temperature_string", "temperature=hot", "4xx", ("params", "neg"), fields=[("temperature", "hot")], model_key="stt_whisper")
simple("logprobs_4o", "include[]=logprobs (json, gpt-4o-transcribe)", tags=("params",), fields=[("include[]", "logprobs")])
simple("logprobs_whisper", "include[]=logprobs sur whisper-1 (non supporté)", "any", ("params",), model_key="stt_whisper",
       fields=[("include[]", "logprobs")])
simple("logprobs_text_format", "include[]=logprobs avec response_format=text (doc : json seulement)", "any", ("params",),
       fields=[("include[]", "logprobs"), ("response_format", "text")])
simple("include_invalid", "include[]=foo", "4xx", ("params", "neg"), fields=[("include[]", "foo")])
simple("chunking_auto", "chunking_strategy=auto", "any", ("params", "probe"), fields=[("chunking_strategy", "auto")])
simple("chunking_server_vad", "chunking_strategy JSON {type: server_vad}", "any", ("params", "probe"),
       fields=[("chunking_strategy", '{"type":"server_vad","silence_duration_ms":500}')])

# ---- streaming
simple("stream_4o", "stream=true sur gpt-4o-transcribe : flux SSE transcript.text.delta/done", tags=("stream",), fields=[("stream", "true")])
simple("stream_whisper", "stream=true sur whisper-1 (doc : ignoré) — réponse JSON classique ?", "any", ("stream",),
       model_key="stt_whisper", fields=[("stream", "true")])
simple("stream_text_format", "stream=true avec response_format=text", "any", ("stream",), fields=[("stream", "true"), ("response_format", "text")])


# ---- négatifs : formulaire / fichier / transport
@case(EP, "missing_file", "Pas de partie `file`", "4xx", ("neg",))
def _(ctx):
    ctx.call(multipart(P, [("model", ctx.model("stt"))], []))


@case(EP, "missing_model", "Pas de champ `model`", "4xx", ("neg",))
def _(ctx):
    ctx.call(multipart(P, [], [file_part(ctx, EN)]))


@case(EP, "file_as_text_field", "`file` envoyé comme champ texte (pas une partie fichier)", "4xx", ("neg",))
def _(ctx):
    ctx.call(multipart(P, [("model", ctx.model("stt")), ("file", "speech_en.mp3")], []))


@case(EP, "unsupported_ext_txt", "Fichier texte nommé notes.txt", "4xx", ("neg", "input-format"))
def _(ctx):
    ctx.call(stt(ctx, audio="notes.txt"))


@case(EP, "empty_file", "Fichier vide (0 octet)", "4xx", ("neg", "input-format"))
def _(ctx):
    ctx.call(stt(ctx, audio="empty.wav"))


@case(EP, "corrupt_mp3", "Octets aléatoires nommés .mp3", "4xx", ("neg", "input-format"))
def _(ctx):
    ctx.call(stt(ctx, audio="corrupt.mp3"))


@case(EP, "ext_mismatch", "Contenu mp3 déclaré .wav : l'extension prime-t-elle sur le contenu ?", "any", ("neg", "input-format"))
def _(ctx):
    ctx.call(stt(ctx, audio="speech_en.mp3", as_name="speech.wav", ctype="audio/wav"))


@case(EP, "no_extension", "Nom de fichier sans extension", "any", ("neg", "input-format"))
def _(ctx):
    ctx.call(stt(ctx, audio="speech_en.mp3", as_name="audio", ctype="application/octet-stream"))


@case(EP, "content_type_octet_stream", "Partie fichier en application/octet-stream avec nom .mp3", "any", ("input-format",))
def _(ctx):
    ctx.call(stt(ctx, audio="speech_en.mp3", ctype="application/octet-stream"))


@case(EP, "model_unknown", "Modèle inexistant", "4xx", ("neg",))
def _(ctx):
    r = stt(ctx); r.fields[0] = ("model", "stt-does-not-exist"); ctx.call(r)


@case(EP, "model_wrong_type", "Modèle TTS sur /audio/transcriptions", "4xx", ("neg",))
def _(ctx):
    r = stt(ctx); r.fields[0] = ("model", ctx.model("tts_legacy")); ctx.call(r)


@case(EP, "json_body", "Corps JSON au lieu de multipart (le fichier ne peut pas y être)", "4xx", ("neg", "transport"))
def _(ctx):
    ctx.call(Req(path=P, json={"model": ctx.model("stt"), "file": "speech_en.mp3"}))


@case(EP, "auth_invalid", "Clé API invalide", "4xx", ("neg", "auth"))
def _(ctx):
    r = stt(ctx); r.headers = {"Authorization": "Bearer sk-invalid-mmprobe"}; ctx.call(r)


@case(EP, "too_large_26mb", "Fichier > 25 Mo (limite documentée) : code attendu 413 ou 400", "4xx", ("neg", "heavy"))
def _(ctx):
    from ..fixtures import build_heavy
    build_heavy(ctx.cfg.fixtures_dir)
    ctx.call(stt(ctx, audio="silence_26mb.wav"))
