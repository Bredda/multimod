"""POST /chat/completions — audio en entrée (`input_audio`) et audio en sortie (`modalities` + `audio`)."""
from __future__ import annotations

from ..http import Req
from . import case
from .util import chat_req, input_audio, text, user

EP = "chat-audio"
Q = "Answer the question asked in the audio message, and tell me the speaker's name. Be brief."
WAV, MP3 = "speech_en.wav", "speech_en.mp3"
AM = "audio_chat"


def aud(c, fixture=WAV, fmt=None):
    return input_audio(c.fx.b64(fixture), fmt or fixture.rsplit(".", 1)[-1])


def one(name, title, build, expect="2xx", tags=(), notes="", model=AM, tokens=300, **extra):
    def fn(ctx):
        ctx.call(chat_req(ctx, model, build(ctx), tokens=tokens, **extra))
    case(EP, name, title, expect, tags, notes)(fn)


TXT = {"modalities": ["text"]}
AUDIO_OUT = lambda fmt="wav", voice="alloy": {"modalities": ["text", "audio"], "audio": {"voice": voice, "format": fmt}}  # noqa: E731

# ======================================================= audio en ENTRÉE (sortie texte)
one("in_wav_text_out", "input_audio wav + consigne texte, modalities=[text]", lambda c: [user(text(Q), aud(c))], tags=("audio-in",), **TXT)
one("in_mp3_text_out", "input_audio mp3", lambda c: [user(text(Q), aud(c, MP3))], tags=("audio-in",), **TXT)
one("in_wav_no_modalities", "input_audio sans `modalities` (défaut = [text])", lambda c: [user(text(Q), aud(c))], tags=("audio-in",))
one("in_audio_only", "input_audio sans aucune part text (le modèle répond à l'audio)", lambda c: [user(aud(c))], "any", ("audio-in",), **TXT)
one("in_french", "Audio français", lambda c: [user(text("Réponds à la question posée dans l'audio, en une phrase."), aud(c, "speech_fr.wav"))],
    tags=("audio-in",), **TXT)
one("in_tone_no_speech", "Audio sans parole (sinus)", lambda c: [user(text("What do you hear?"), aud(c, "tone_440hz.wav"))], "any", ("audio-in",), **TXT)
one("in_two_audios", "Deux input_audio dans le même message (wav + mp3)", lambda c: [user(text("Are the two audio clips identical in content?"), aud(c), aud(c, MP3))],
    "any", ("audio-in", "compose"), **TXT)
one("in_text_interleaved", "text, audio, text", lambda c: [user(text("Listen carefully."), aud(c), text("Now answer the question you heard."))],
    tags=("audio-in", "compose"), **TXT)
one("in_stream_text_out", "input_audio + stream=true + include_usage (sortie texte)", lambda c: [user(text(Q), aud(c))], tags=("audio-in", "stream"),
    stream=True, stream_options={"include_usage": True}, **TXT)


@case(EP, "in_tool_call", "input_audio + tools (tool_choice=required)", "any", ("audio-in", "tools"))
def _(ctx):
    tools = [{"type": "function", "function": {"name": "add", "description": "Add two integers", "parameters": {
        "type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}}]
    ctx.call(chat_req(ctx, AM, [user(text("Use the add tool to answer the question in the audio."), aud(ctx))], tools=tools, tool_choice="required", **TXT))


# ---- formats d'entrée / erreurs
one("in_format_flac", "input_audio.format=flac (enum doc : wav, mp3)", lambda c: [user(text(Q), aud(c, "speech_en.flac"))], "4xx", ("audio-in", "neg", "format"), **TXT)
one("in_format_pcm16", "input_audio.format=pcm16 avec PCM brut", lambda c: [user(text(Q), input_audio(c.fx.b64("speech_en.pcm"), "pcm16"))], "4xx", ("audio-in", "neg", "format"), **TXT)
one("in_format_uppercase", "format=WAV (casse)", lambda c: [user(text(Q), input_audio(c.fx.b64(WAV), "WAV"))], "any", ("audio-in", "neg", "format"), **TXT)
one("in_format_mismatch", "Contenu mp3 déclaré format=wav : le format déclaré prime-t-il ?", lambda c: [user(text(Q), input_audio(c.fx.b64(MP3), "wav"))],
    "any", ("audio-in", "neg", "format"), **TXT)
one("in_format_missing", "input_audio sans `format`", lambda c: [user(text(Q), {"type": "input_audio", "input_audio": {"data": c.fx.b64(WAV)}})],
    "4xx", ("audio-in", "neg", "schema"), **TXT)
one("in_data_as_data_url", "input_audio.data = data URL (confusion fréquente avec image_url)", lambda c: [user(text(Q), input_audio(c.fx.data_url(WAV), "wav"))],
    "4xx", ("audio-in", "neg", "schema"), **TXT)
one("in_data_corrupt_base64", "input_audio.data = base64 invalide", lambda c: [user(text(Q), input_audio("%%%not-base64%%%", "wav"))], "4xx", ("audio-in", "neg"), **TXT)
one("in_data_not_audio", "input_audio.data = base64 d'un fichier texte", lambda c: [user(text(Q), input_audio(c.fx.b64("notes.txt"), "wav"))], "4xx", ("audio-in", "neg"), **TXT)
one("in_data_empty", "input_audio.data = chaîne vide", lambda c: [user(text(Q), input_audio("", "wav"))], "4xx", ("audio-in", "neg"), **TXT)
one("in_audio_as_string", "input_audio donné comme chaîne au lieu d'un objet", lambda c: [user(text(Q), {"type": "input_audio", "input_audio": c.fx.b64(WAV)})],
    "4xx", ("audio-in", "neg", "schema"), **TXT)
one("in_audio_in_system", "input_audio dans un message system", lambda c: [{"role": "system", "content": [aud(c)]}, {"role": "user", "content": "Hi"}],
    "4xx", ("audio-in", "neg", "placement"), **TXT)
one("in_audio_in_assistant", "input_audio dans un message assistant", lambda c: [user(text("Hi")), {"role": "assistant", "content": [aud(c)]}, user(text("ok?"))],
    "4xx", ("audio-in", "neg", "placement"), **TXT)
one("in_audio_on_text_model", "input_audio envoyé à un modèle texte-seul", lambda c: [user(text(Q), aud(c))], "4xx", ("audio-in", "neg", "model"),
    model="text_only", **TXT)
one("in_audio_on_vision_model", "input_audio envoyé à un modèle vision (non audio)", lambda c: [user(text(Q), aud(c))], "4xx", ("audio-in", "neg", "model"),
    model="vision", **TXT)

# ======================================================= audio en SORTIE
one("out_text_prompt_wav", "Prompt texte seul -> réponse texte + audio wav (chat comme TTS)", lambda c: [user(text("Say hello in one short sentence."))],
    tags=("audio-out",), **AUDIO_OUT("wav"))
for fmt in ("mp3", "flac", "opus", "pcm16", "aac"):
    one(f"out_format_{fmt}", f"audio.format={fmt} (non-stream) : conteneur réel de message.audio.data", lambda c: [user(text("Say hello in one short sentence."))],
        "any" if fmt == "aac" else "2xx", ("audio-out", "format"), "aac figure dans l'enum de la spec OpenAPI mais pas dans la description" if fmt == "aac" else "", **AUDIO_OUT(fmt))
for v in ("verse", "coral", "marin", "cedar"):
    one(f"out_voice_{v}", f"audio.voice={v}", lambda c: [user(text("Say hello."))], "any", ("audio-out", "voice"), **AUDIO_OUT("wav", v))
one("in_wav_audio_out", "input_audio + sortie audio : conversation vocale complète (usage audio_tokens in/out)", lambda c: [user(aud(c))],
    tags=("audio-in", "audio-out"), **AUDIO_OUT("wav"))
one("in_mp3_audio_out_mp3", "input_audio mp3 -> sortie audio mp3", lambda c: [user(aud(c, MP3))], tags=("audio-in", "audio-out"), **AUDIO_OUT("mp3"))
one("out_modalities_audio_only", "modalities=[audio] seul (la doc le mentionne ; le modèle exige souvent [text, audio])", lambda c: [user(text("Say hello."))],
    "any", ("audio-out",), modalities=["audio"], audio={"voice": "alloy", "format": "wav"})
one("out_modalities_with_text_model", "modalities=[text,audio] sur modèle texte-seul", lambda c: [user(text("Say hello."))], "4xx", ("audio-out", "neg", "model"),
    model="text_only", **AUDIO_OUT("wav"))
one("out_missing_audio_param", "modalities contient audio mais pas de paramètre `audio`", lambda c: [user(text("Say hello."))], "4xx", ("audio-out", "neg"),
    modalities=["text", "audio"])
one("out_audio_param_without_modality", "paramètre `audio` fourni mais modalities=[text]", lambda c: [user(text("Say hello."))], "any", ("audio-out", "neg"),
    modalities=["text"], audio={"voice": "alloy", "format": "wav"})
one("out_voice_invalid", "audio.voice inconnue", lambda c: [user(text("Say hello."))], "4xx", ("audio-out", "neg"), **AUDIO_OUT("wav", "bogus"))
one("out_format_invalid", "audio.format=ogg", lambda c: [user(text("Say hello."))], "4xx", ("audio-out", "neg"), **AUDIO_OUT("ogg"))
one("out_modalities_invalid", "modalities=[video]", lambda c: [user(text("Say hello."))], "4xx", ("audio-out", "neg"), modalities=["video"])
one("out_stream_pcm16", "Streaming audio : delta.audio {id, data, transcript} en pcm16", lambda c: [user(text("Say hello in one short sentence."))],
    tags=("audio-out", "stream"), stream=True, stream_options={"include_usage": True}, **AUDIO_OUT("pcm16"))
one("out_stream_wav", "Streaming audio avec format=wav (doc : pcm16 requis en streaming)", lambda c: [user(text("Say hello."))],
    "4xx", ("audio-out", "stream", "neg"), stream=True, **AUDIO_OUT("wav"))
one("out_n2", "n=2 avec sortie audio", lambda c: [user(text("Say hello."))], "any", ("audio-out", "neg"), n=2, **AUDIO_OUT("wav"))


# ======================================================= multi-tours avec audio
@case(EP, "multi_turn_audio_id", "Tour 2 : on référence la réponse audio précédente par assistant.audio.id (pas de ré-upload)", "2xx", ("multi-turn", "audio-out"))
def _(ctx):
    first = [user(text("Say a short sentence about Paris."))]
    ex = ctx.call(chat_req(ctx, AM, first, **AUDIO_OUT("wav")), step="turn1")
    j = ex.json() or {}
    try:
        aid = j["choices"][0]["message"]["audio"]["id"]
    except Exception:
        if not ctx.dry_run:
            ctx.skip("turn1 n'a pas renvoyé message.audio.id")
        aid = "audio_<id-from-turn1>"
    msgs = first + [{"role": "assistant", "audio": {"id": aid}}, user(text("Now say it again in one word."))]
    ctx.call(chat_req(ctx, AM, msgs, **AUDIO_OUT("wav")), step="turn2")


@case(EP, "multi_turn_audio_id_text_fallback", "Tour 2 : assistant référencé par son transcript texte (pas d'id audio)", "2xx", ("multi-turn", "audio-out"))
def _(ctx):
    ex = ctx.call(chat_req(ctx, AM, [user(text("Say a short sentence about Paris."))], **AUDIO_OUT("wav")), step="turn1")
    try:
        tr = ex.json()["choices"][0]["message"]["audio"]["transcript"]
    except Exception:
        if not ctx.dry_run:
            ctx.skip("turn1 sans transcript")
        tr = "<transcript-from-turn1>"
    msgs = [user(text("Say a short sentence about Paris.")), {"role": "assistant", "content": tr}, user(text("Translate it to French."))]
    # NB : gpt-audio refuse un tour 100 % texte (ni audio en entrée ni en sortie) -> on redemande de l'audio en sortie
    ctx.call(chat_req(ctx, AM, msgs, **AUDIO_OUT("wav")), step="turn2")


@case(EP, "multi_turn_audio_id_unknown", "assistant.audio.id inexistant", "4xx", ("multi-turn", "neg"))
def _(ctx):
    msgs = [user(text("Hi")), {"role": "assistant", "audio": {"id": "audio_does_not_exist"}}, user(text("Again please."))]
    ctx.call(chat_req(ctx, AM, msgs, **AUDIO_OUT("wav")))


@case(EP, "multi_turn_input_audio_then_text", "Tour 1 : audio utilisateur ; tour 2 : question texte de suivi (l'audio reste-t-il en contexte ?)", "2xx", ("multi-turn", "audio-in"))
def _(ctx):
    ex = ctx.call(chat_req(ctx, AM, [user(text(Q), aud(ctx))], **TXT), step="turn1")
    try:
        reply = ex.json()["choices"][0]["message"]["content"]
    except Exception:
        if not ctx.dry_run:
            ctx.skip("turn1 sans contenu")
        reply = "<reply-from-turn1>"
    msgs = [user(text(Q), aud(ctx)), {"role": "assistant", "content": reply}, user(text("What city did the speaker mention?"))]
    ctx.call(chat_req(ctx, AM, msgs, **TXT), step="turn2")


@case(EP, "auth_invalid", "Clé API invalide", "4xx", ("neg", "auth"))
def _(ctx):
    r = chat_req(ctx, AM, [user(text("hi"))], **TXT)
    r.headers = {"Authorization": "Bearer sk-invalid-mmprobe"}
    ctx.call(r)
