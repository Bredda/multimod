"""Fixtures de test : images (Pillow), audio synthétique (stdlib), parole (via /audio/speech)."""
from __future__ import annotations

import base64
import io
import math
import os
import random
import struct
import wave
from pathlib import Path

from .config import Config

SPEECH_EN = "Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two plus two?"
SPEECH_FR = "Bonjour, je m'appelle Laurent. Aujourd'hui, il fait beau à Paris. Combien font deux plus deux ?"

MIME = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif",
    "bmp": "image/bmp", "tiff": "image/tiff", "svg": "image/svg+xml",
    "mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac", "ogg": "audio/ogg", "opus": "audio/opus",
    "aac": "audio/aac", "m4a": "audio/mp4", "mp4": "video/mp4", "webm": "audio/webm", "mpga": "audio/mpeg",
    "mpeg": "audio/mpeg", "pcm": "application/octet-stream", "txt": "text/plain",
}


class Skip(Exception):
    pass


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


class Fixtures:
    def __init__(self, directory: Path):
        self.dir = directory

    def path(self, name: str) -> Path:
        p = self.dir / name
        if not p.exists():
            raise Skip(f"fixture manquante: fixtures/{name} (lancer `fixtures`, ou fournir le fichier)")
        return p

    def bytes(self, name: str) -> bytes:
        return self.path(name).read_bytes()

    def b64(self, name: str) -> str:
        return base64.b64encode(self.bytes(name)).decode()

    def data_url(self, name: str, mime: str | None = None) -> str:
        return f"data:{mime or MIME[ext_of(name)]};base64,{self.b64(name)}"

    def ensure(self, fn, *args, **kw) -> Path:
        return fn(self.dir, *args, **kw)

    def mime(self, name: str) -> str:
        return MIME.get(ext_of(name), "application/octet-stream")


# ---------------------------------------------------------------- audio local
def _write_wav(path: Path, samples: bytes, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples)


def _tone(seconds: float, hz: float = 440.0, rate: int = 24000) -> bytes:
    n = int(seconds * rate)
    return b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * hz * i / rate))) for i in range(n))


def build_local(d: Path) -> list[str]:
    """Génère les fixtures qui ne dépendent d'aucune API. Retourne la liste des fichiers créés."""
    from PIL import Image, ImageDraw, ImageFont

    d.mkdir(parents=True, exist_ok=True)
    made: list[str] = []

    def done(name: str):
        made.append(name)

    # --- images : scène simple et vérifiable (carré rouge, cercle bleu, triangle vert sur fond gris clair)
    scene = Image.new("RGB", (512, 320), (235, 235, 235))
    dr = ImageDraw.Draw(scene)
    dr.rectangle((40, 60, 200, 220), fill=(220, 30, 30))
    dr.ellipse((230, 60, 390, 220), fill=(30, 60, 220))
    dr.polygon([(420, 220), (500, 220), (460, 90)], fill=(30, 170, 60))
    scene.save(d / "scene.png"); done("scene.png")
    scene.save(d / "scene.jpg", quality=90); done("scene.jpg")
    scene.save(d / "scene.webp"); done("scene.webp")
    scene.save(d / "scene.gif"); done("scene.gif")
    scene.save(d / "scene.bmp"); done("scene.bmp")
    scene.save(d / "scene.tiff"); done("scene.tiff")

    a = Image.new("RGB", (256, 256), "white"); ImageDraw.Draw(a).rectangle((48, 48, 208, 208), fill=(220, 30, 30))
    a.save(d / "red_square.png"); done("red_square.png")
    b = Image.new("RGB", (256, 256), "white"); ImageDraw.Draw(b).ellipse((48, 48, 208, 208), fill=(30, 60, 220))
    b.save(d / "blue_circle.png"); done("blue_circle.png")

    try:
        font = ImageFont.load_default(size=72)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    t = Image.new("RGB", (480, 140), "white")
    ImageDraw.Draw(t).text((20, 30), "HELLO 42", fill="black", font=font)
    t.save(d / "text_hello42.png"); done("text_hello42.png")

    f1 = Image.new("RGB", (128, 128), (220, 30, 30)); f2 = Image.new("RGB", (128, 128), (30, 60, 220))
    f1.save(d / "animated.gif", save_all=True, append_images=[f2], duration=500, loop=0); done("animated.gif")

    Image.new("RGB", (1, 1), (255, 0, 0)).save(d / "tiny_1x1.png"); done("tiny_1x1.png")
    Image.new("RGB", (6000, 4000), (200, 120, 40)).save(d / "large_6000x4000.png", optimize=True); done("large_6000x4000.png")
    Image.new("L", (8200, 8200), 128).save(d / "huge_8200x8200.png", optimize=True); done("huge_8200x8200.png")

    (d / "scene.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
        '<rect width="200" height="100" fill="red"/></svg>'); done("scene.svg")
    (d / "not_an_image.html").write_text("<html><body>hello</body></html>"); done("not_an_image.html")

    # --- audio synthétique
    _write_wav(d / "tone_440hz.wav", _tone(2.0)); done("tone_440hz.wav")
    _write_wav(d / "silence_3s.wav", b"\x00\x00" * 24000 * 3); done("silence_3s.wav")
    random.seed(1)
    (d / "corrupt.mp3").write_bytes(bytes(random.randrange(256) for _ in range(4096))); done("corrupt.mp3")
    (d / "empty.wav").write_bytes(b""); done("empty.wav")
    (d / "notes.txt").write_text("not audio"); done("notes.txt")
    return made


def build_heavy(d: Path) -> list[str]:
    """Gros fichiers (opt-in, cas taggés `heavy`)."""
    made = []
    if not (d / "silence_26mb.wav").exists():
        _write_wav(d / "silence_26mb.wav", b"\x00\x00" * (26 * 1024 * 1024 // 2)); made.append("silence_26mb.wav")
    if not (d / "noise_big.png").exists():
        from PIL import Image
        w, h = 3300, 2300  # ~22 Mo de bruit incompressible
        Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(d / "noise_big.png", compress_level=0); made.append("noise_big.png")
    return made


# ------------------------------------------------------- parole via /audio/speech
def build_speech(cfg: Config, d: Path, log=print) -> list[str]:
    """Génère les fichiers de parole en appelant l'endpoint /audio/speech de la cible configurée."""
    from .http import Req, execute

    model = cfg.models["tts"]
    if model == "-":
        log("  rôle tts désactivé (MM_MODEL_TTS=-) : parole non générée")
        return []
    made: list[str] = []

    def tts(text: str, fmt: str, name: str):
        if (d / name).exists():
            return
        ex = execute(cfg, Req(path="/audio/speech", json={"model": model, "input": text, "voice": "alloy", "response_format": fmt}))
        from .capture import sniff_audio
        if ex.status != 200 or not ex.body:
            log(f"  ! {name}: HTTP {ex.status} {ex.error or ex.body[:200]!r}")
            return
        if fmt != "pcm" and sniff_audio(ex.body[:16]) in ("json?", "unknown/raw"):
            log(f"  ! {name}: la réponse ne ressemble pas à de l'audio ({ex.content_type}, {ex.body[:60]!r}) — ignorée")
            return
        (d / name).write_bytes(ex.body); made.append(name)

    d.mkdir(parents=True, exist_ok=True)
    for fmt in ("mp3", "wav", "flac", "opus", "aac", "pcm"):
        tts(SPEECH_EN, fmt, f"speech_en.{fmt}")
    tts(SPEECH_FR, "mp3", "speech_fr.mp3")
    tts(SPEECH_FR, "wav", "speech_fr.wav")
    # opus (OpenAI) = conteneur Ogg ; on expose aussi l'extension .ogg
    if (d / "speech_en.opus").exists() and not (d / "speech_en.ogg").exists():
        (d / "speech_en.ogg").write_bytes((d / "speech_en.opus").read_bytes()); made.append("speech_en.ogg")
    # pcm brut (24 kHz s16le mono) => wav valide, pour tester l'upload d'un wav reconstruit
    if (d / "speech_en.pcm").exists() and not (d / "speech_en_from_pcm.wav").exists():
        _write_wav(d / "speech_en_from_pcm.wav", (d / "speech_en.pcm").read_bytes()); made.append("speech_en_from_pcm.wav")
    return made


# ------------------------------------------------ fixtures calibrées (générées à la demande par les cas Bedrock)
def ensure_noise_png(d: Path, name: str, target_bytes: int) -> Path:
    """PNG de bruit incompressible dont la taille ≈ target_bytes (compress_level=0)."""
    p = d / name
    if not p.exists():
        import math
        from PIL import Image
        side = int(math.sqrt(target_bytes / 3))
        rnd = random.Random(7)
        Image.frombytes("RGB", (side, side), rnd.randbytes(side * side * 3)).save(p, compress_level=0)
    return p


def ensure_silence_wav(d: Path, name: str, nbytes: int, rate: int = 24000) -> Path:
    """WAV mono s16 de silence, en-tête correct, `nbytes` ≈ taille du fichier."""
    p = d / name
    if not p.exists():
        _write_wav(p, b"\x00\x00" * ((nbytes - 44) // 2), rate)
    return p


def _pcm_of_streaming_wav(path: Path) -> bytes:
    b = path.read_bytes()
    return b[44:] if b[:4] == b"RIFF" else b  # l'en-tête OpenAI (tailles 0xFFFFFFFF) fait mentir le module wave


def ensure_speech_variants(d: Path) -> None:
    """Variantes dérivées de speech_en.wav : en-tête corrigé, stéréo, 12 kHz (décimation naïve, suffisant pour une sonde)."""
    src = d / "speech_en.wav"
    if not src.exists():
        raise Skip("fixture manquante: fixtures/speech_en.wav (lancer `fixtures`, nécessite /audio/speech)")
    pcm = _pcm_of_streaming_wav(src)
    if not (d / "speech_en_clean.wav").exists():
        _write_wav(d / "speech_en_clean.wav", pcm, 24000)
    if not (d / "speech_en_stereo.wav").exists():
        samples = [pcm[i:i + 2] for i in range(0, len(pcm) - 1, 2)]
        with wave.open(str(d / "speech_en_stereo.wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(b"".join(s + s for s in samples))
    if not (d / "speech_en_12k.wav").exists():
        samples = [pcm[i:i + 2] for i in range(0, len(pcm) - 1, 2)]
        _write_wav(d / "speech_en_12k.wav", b"".join(samples[::2]), 12000)
