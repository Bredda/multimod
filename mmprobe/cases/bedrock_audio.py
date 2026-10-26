"""Bedrock (boto3, bedrock-runtime) — audio.

* Entrée audio : bloc `audio` de Converse, réservé aux modèles à modalité SPEECH (ex. Voxtral). Il n'existe pas
  d'endpoint de transcription sur bedrock-runtime : une « transcription » = un prompt + un AudioBlock.
* Sortie audio / TTS : rien dans Converse. Nova Sonic n'est joignable que par InvokeModelWithBidirectionalStream
  (flux HTTP/2 bidirectionnel, non pris en charge par boto3) : on ne sonde que le refus de Converse/InvokeModel.
"""
from __future__ import annotations

from ..bedrock import BCall
from ..fixtures import Skip, ensure_silence_wav, ensure_speech_variants
from . import bcase
from .bedrock_util import assistant, aud, converse, fmt_of, img, model, txt, user

TR = "Transcribe this audio verbatim. Output only the transcript."
CH = "Answer the question asked in the audio message, and tell me the speaker's name. Be brief."
WAV, MP3 = "speech_en_clean.wav", "speech_en.mp3"


def variants(ctx):
    try:
        ensure_speech_variants(ctx.cfg.fixtures_dir)
    except Skip as s:
        ctx.skip(str(s))


def make(ep):
    def one(name, title, build, expect="2xx", tags=(), notes="", role="audio_in", **extra):
        def fn(ctx):
            variants(ctx)
            ctx.call(converse(ctx, role, build(ctx), **extra))
        bcase(ep, name, title, expect, tags, notes)(fn)
    return one


# ================================================================ transcriptions (prompt de transcription + AudioBlock)
t = make("transcriptions")
t("model_small", "Transcription WAV (rôle audio_in, ex. Voxtral Small)", lambda c: [user(txt(TR), aud(c, WAV))])
t("model_mini", "Transcription WAV (rôle audio_in_mini, ex. Voxtral Mini)", lambda c: [user(txt(TR), aud(c, WAV))], role="audio_in_mini")
for ext, fx, exp, note in [
    ("mp3", "speech_en.mp3", "2xx", ""), ("wav", WAV, "2xx", "en-tête WAV correct"), ("flac", "speech_en.flac", "2xx", ""),
    ("ogg", "speech_en.ogg", "2xx", "Ogg/Opus"), ("opus", "speech_en.opus", "any", "déclaré 'opus' (octets Ogg/Opus)"),
    ("aac", "speech_en.aac", "any", "AAC ADTS brut"), ("pcm", "speech_en.pcm", "any", "PCM brut 24 kHz s16le mono, déclaré 'pcm'"),
    ("wav_streaming_header", "speech_en.wav", "any", "WAV tel que renvoyé par OpenAI : tailles d'en-tête = 0xFFFFFFFF"),
    ("wav_stereo", "speech_en_stereo.wav", "any", "stéréo (certains modèles : mono seulement)"),
    ("wav_12khz", "speech_en_12k.wav", "any", "échantillonnage 12 kHz"),
]:
    t(f"input_{ext}", f"Fichier d'entrée {ext}" + (f" — {note}" if note else ""), lambda c, f=fx, e=ext: [user(txt(TR), aud(c, f, {"wav_streaming_header": "wav", "wav_stereo": "wav", "wav_12khz": "wav"}.get(e)))],
      exp, ("input-format",))
for ext in ("m4a", "mp4", "webm", "mpga", "mpeg"):
    t(f"input_{ext}", f"Fichier d'entrée {ext} (à fournir : fixtures/sample.{ext})", lambda c, e=ext: [user(txt(TR), aud(c, f"sample.{e}", e))], "any", ("input-format", "user-fixture"))
t("input_fr", "Audio français, sans indication de langue", lambda c: [user(txt(TR), aud(c, "speech_fr.wav"))])
t("input_tone_no_speech", "Sinus sans parole : texte vide, refus ou hallucination ?", lambda c: [user(txt(TR), aud(c, "tone_440hz.wav"))], "any")
t("input_silence", "Silence 3 s", lambda c: [user(txt(TR), aud(c, "silence_3s.wav"))], "any")
# tailles (Voxtral : ~2 Mo d'après un tiers — à confirmer)
for mb, nbytes, exp in [("1_5", 1_500_000, "any"), ("2_5", 2_500_000, "any"), ("10", 10_000_000, "any")]:
    t(f"size_{mb}mb", f"WAV de silence ≈ {mb.replace('_', ',')} Mo : où se situe la limite de taille d'entrée ?",
      lambda c, n=nbytes, m=mb: [user(txt(TR), aud(c, c.fx.ensure(ensure_silence_wav, f"silence_{m}mb.wav", n).name, "wav"))], exp, ("limits",))


def _heavy(ctx):
    from ..fixtures import build_heavy
    build_heavy(ctx.cfg.fixtures_dir)
    ctx.call(converse(ctx, "audio_in", [user(txt(TR), aud(ctx, "silence_26mb.wav", "wav"))]))


bcase("transcriptions", "size_26mb", "WAV de 26 Mo (équivalent du cas OpenAI too_large_26mb)", "4xx", ("limits", "neg", "heavy"))(_heavy)
# options de transcription demandées par prompt (pas de paramètre dédié dans Converse)
t("prompt_language_hint", "Indication de langue dans le prompt (équivalent de `language`)", lambda c: [user(txt("The audio is in English. " + TR), aud(c, WAV))])
t("prompt_srt", "Demander des sous-titres SRT horodatés (équivalent de response_format=srt)", lambda c: [user(txt("Transcribe this audio as SRT subtitles with timestamps."), aud(c, WAV))], "any", ("response_format",))
t("prompt_json", "Demander {\"text\": ...} en JSON (équivalent de response_format=json)", lambda c: [user(txt('Transcribe this audio. Reply with JSON only: {"text": "..."}'), aud(c, WAV))], "any", ("response_format",))
t("prompt_diarize", "Demander les locuteurs (équivalent diarized_json)", lambda c: [user(txt("Transcribe this audio and label each speaker."), aud(c, WAV))], "any", ("response_format",))
t("stream", "ConverseStream sur une transcription (équivalent stream=true)", lambda c: [user(txt(TR), aud(c, WAV))], tags=("stream",), stream=True)
# négatifs
t("input_empty", "AudioBlock de 0 octet", lambda c: [user(txt(TR), {"audio": {"format": "wav", "source": {"bytes": b""}}})], "4xx", ("neg",))
t("input_corrupt_mp3", "Octets aléatoires déclarés 'mp3'", lambda c: [user(txt(TR), aud(c, "corrupt.mp3"))], "4xx", ("neg",))
t("input_text_file", "Fichier texte déclaré 'wav'", lambda c: [user(txt(TR), aud(c, "notes.txt", "wav"))], "4xx", ("neg",))
t("ext_mismatch", "MP3 déclaré 'wav' : le format déclaré prime-t-il ?", lambda c: [user(txt(TR), aud(c, MP3, "wav"))], "any", ("neg", "input-format"))
t("format_invalid_value", "format='wmv' (hors enum AudioFormat)", lambda c: [user(txt(TR), aud(c, MP3, "wmv"))], "4xx", ("neg", "input-format"))
t("model_without_audio", "AudioBlock envoyé à un modèle sans modalité SPEECH (rôle vision)", lambda c: [user(txt(TR), aud(c, WAV))], "4xx", ("neg", "model"), role="vision")


@bcase("transcriptions", "auth_invalid", "Identifiants AWS invalides", "4xx", ("neg", "auth"))
def _(ctx):
    variants(ctx)
    c = converse(ctx, "audio_in", [user(txt(TR), aud(ctx, WAV))])
    c.bad_credentials = True
    ctx.call(c)


# ================================================================ chat-audio (input_audio OpenAI -> AudioBlock)
a = make("chat-audio")
a("in_wav_text_out", "AudioBlock wav + consigne texte", lambda c: [user(txt(CH), aud(c, WAV))], tags=("audio-in",))
a("in_mp3_text_out", "AudioBlock mp3", lambda c: [user(txt(CH), aud(c, MP3))], tags=("audio-in",))
a("in_audio_only", "AudioBlock sans bloc texte", lambda c: [user(aud(c, WAV))], "any", ("audio-in",))
a("in_french", "Audio français", lambda c: [user(txt("Réponds à la question posée dans l'audio, en une phrase."), aud(c, "speech_fr.wav"))], tags=("audio-in",))
a("in_two_audios", "Deux AudioBlock dans le même message", lambda c: [user(txt("Are the two audio clips identical in content?"), aud(c, WAV), aud(c, MP3))], "any", ("audio-in", "compose"))
a("in_text_interleaved", "text, audio, text", lambda c: [user(txt("Listen carefully."), aud(c, WAV), txt("Now answer the question you heard."))], tags=("audio-in", "compose"))
a("in_stream_text_out", "ConverseStream avec audio en entrée", lambda c: [user(txt(CH), aud(c, WAV))], tags=("audio-in", "stream"), stream=True)
a("in_history_audio_then_text", "Audio au tour 1, question texte au tour 3 (l'audio reste-t-il en contexte ?)",
  lambda c: [user(txt(CH), aud(c, WAV)), assistant(txt("The answer is 4.")), user(txt("What city did the speaker mention?"))], tags=("multi-turn", "audio-in"))
a("in_format_mismatch", "MP3 déclaré 'wav'", lambda c: [user(txt(CH), aud(c, MP3, "wav"))], "any", ("audio-in", "neg", "format"))
a("in_data_empty", "AudioBlock de 0 octet", lambda c: [user(txt(CH), {"audio": {"format": "wav", "source": {"bytes": b""}}})], "4xx", ("audio-in", "neg"))
a("in_data_not_audio", "Fichier texte déclaré 'wav'", lambda c: [user(txt(CH), aud(c, "notes.txt", "wav"))], "4xx", ("audio-in", "neg"))
a("in_audio_in_assistant", "AudioBlock dans un message assistant", lambda c: [user(txt("Hi")), assistant(aud(c, WAV)), user(txt("ok?"))], "4xx", ("audio-in", "neg", "placement"))
a("in_audio_on_text_model", "AudioBlock envoyé à un modèle texte-seul", lambda c: [user(txt(CH), aud(c, WAV))], "4xx", ("audio-in", "neg", "model"), role="text_only")
a("in_audio_on_vision_model", "AudioBlock envoyé à un modèle vision (sans SPEECH)", lambda c: [user(txt(CH), aud(c, WAV))], "4xx", ("audio-in", "neg", "model"), role="vision")


@bcase("chat-audio", "in_tool_call", "AudioBlock + toolConfig (toolChoice=any)", "any", ("audio-in", "tools"))
def _(ctx):
    variants(ctx)
    tools = {"tools": [{"toolSpec": {"name": "add", "description": "Add two integers", "inputSchema": {"json": {
        "type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}}}], "toolChoice": {"any": {}}}
    ctx.call(converse(ctx, "audio_in", [user(txt("Use the add tool to answer the question in the audio."), aud(ctx, WAV))], toolConfig=tools))


@bcase("chat-audio", "auth_invalid", "Identifiants AWS invalides", "4xx", ("neg", "auth"))
def _(ctx):
    variants(ctx)
    c = converse(ctx, "audio_in", [user(txt(CH), aud(ctx, WAV))], tokens=20)
    c.bad_credentials = True
    ctx.call(c)


# ================================================================ sortie audio / TTS : ce qui existe (ou pas)
@bcase("chat-audio", "nova_sonic_converse", "Nova Sonic via Converse (sortie audio) : refus attendu, Sonic = flux bidirectionnel uniquement", "4xx", ("audio-out", "neg", "model"))
def _(ctx):
    ctx.call(converse(ctx, "sonic", [user(txt("Say hello in one short sentence."))], tokens=50))


@bcase("speech", "nova_sonic_converse", "Synthèse vocale via Nova Sonic + Converse : refus attendu", "4xx", ("neg", "model"))
def _(ctx):
    ctx.call(converse(ctx, "sonic", [user(txt("Please read this aloud: Hello, this is a test."))], tokens=50))


@bcase("speech", "nova_sonic_invoke_model", "Nova Sonic via InvokeModel (non streaming) : refus attendu", "4xx", ("neg", "model"))
def _(ctx):
    body = {"schemaVersion": "messages-v1", "messages": [{"role": "user", "content": [{"text": "Say hello."}]}]}
    ctx.call(BCall("invoke_model", {"modelId": model(ctx, "sonic")}, body=body))
