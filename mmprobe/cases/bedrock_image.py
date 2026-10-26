"""Bedrock (boto3, bedrock-runtime) — images : ce que le worker enverra pour un `image_url` OpenAI.

Converse n'accepte pas d'URL : `bytes` ou `s3Location`. Les cas mesurent formats, tailles, nombre d'images,
placement par rôle, et ce que renvoie Bedrock en erreur (ValidationException, etc.).
"""
from __future__ import annotations

from ..bedrock import BCall
from ..fixtures import ensure_noise_png
from . import bcase
from .bedrock_util import assistant, converse, fmt_of, img, model, need_family, txt, user
import base64

EP = "chat-image"
Q = "Describe this image in one short sentence, naming each shape and its color."


def one(name, title, build, expect="2xx", tags=(), notes="", role="vision", **extra):
    def fn(ctx):
        ctx.call(converse(ctx, role, build(ctx), **extra))
    bcase(EP, name, title, expect, tags, notes)(fn)


# ---- formats (octets réels)
for ext in ("png", "jpg", "webp", "gif"):
    one(f"bytes_{ext}", f"Image {ext.upper()} en octets (format déclaré '{fmt_of('x.' + ext)}')", lambda c, e=ext: [user(txt(Q), img(c, f"scene.{e}"))], tags=("source", "format"))
for ext in ("bmp", "tiff", "svg"):
    one(f"declared_png_actual_{ext}", f"Octets {ext.upper()} déclarés 'png' (formats hors liste png/jpeg/gif/webp)", lambda c, e=ext: [user(txt(Q), img(c, f"scene.{e}", "png"))],
        "4xx", ("source", "format", "neg"))
one("declared_jpeg_actual_png", "PNG déclaré 'jpeg' : le format déclaré prime-t-il sur le contenu ?", lambda c: [user(txt(Q), img(c, "scene.png", "jpeg"))], "any", ("source", "format", "neg"))
one("declared_png_actual_jpeg", "JPEG déclaré 'png'", lambda c: [user(txt(Q), img(c, "scene.jpg", "png"))], "any", ("source", "format", "neg"))
one("format_invalid_value", "format='bmp' (hors enum ImageFormat) : rejet botocore ou serveur ?", lambda c: [user(txt(Q), img(c, "scene.png", "bmp"))], "4xx", ("source", "format", "neg"))
one("animated_gif", "GIF animé : accepté ? quelles images sont vues ?", lambda c: [user(txt(Q), img(c, "animated.gif"))], "any", ("source", "format"))
one("not_an_image_bytes", "Octets HTML déclarés 'png'", lambda c: [user(txt(Q), img(c, "not_an_image.html", "png"))], "4xx", ("source", "neg"))
one("empty_bytes", "Image de 0 octet", lambda c: [user(txt(Q), {"image": {"format": "png", "source": {"bytes": b""}}})], "4xx", ("source", "neg"))
one("corrupt_bytes", "PNG tronqué (octets de tête valides, reste corrompu)", lambda c: [user(txt(Q), {"image": {"format": "png", "source": {"bytes": c.fx.bytes("scene.png")[:200]}}})],
    "4xx", ("source", "neg"))


@bcase(EP, "s3_location_unreachable", "source s3Location vers un bucket inexistant (voie alternative aux octets pour les gros fichiers)", "4xx", ("source", "neg"))
def _(ctx):
    msgs = [user(txt(Q), {"image": {"format": "png", "source": {"s3Location": {"uri": "s3://mmprobe-bucket-does-not-exist-0000/scene.png"}}}})]
    ctx.call(converse(ctx, "vision", msgs))


# ---- autres familles de modèles (mêmes octets)
for role in ("vision_nova", "vision_other"):
    one(f"png_{role}", f"PNG sur le rôle '{role}' (autre famille de modèles : comportements/limites différents ?)", lambda c: [user(txt(Q), img(c, "scene.png"))],
        tags=("model-family",), role=role)

# ---- composition
one("multi_images", "Deux images + question comparative", lambda c: [user(txt("What is the color and shape in the first image, and in the second image?"),
                                                                           img(c, "red_square.png"), img(c, "blue_circle.png"))], tags=("compose",))
one("interleaved", "text, image, text, image : l'ordre est-il préservé ?", lambda c: [user(txt("Image A:"), img(c, "red_square.png"), txt("Image B:"), img(c, "blue_circle.png"),
                                                                                           txt("Which image (A or B) contains a circle?"))], tags=("compose",))
one("image_only", "Une image, aucun bloc texte (OpenAI l'accepte)", lambda c: [user(img(c, "scene.png"))], "any", ("compose",))
one("system_prompt_plus_image", "system=[{text}] + user image", lambda c: [user(txt(Q), img(c, "scene.png"))], tags=("compose",),
    system="You answer in French, in one sentence.")
one("history_image_then_text", "Image au tour 1, question texte au tour 3 (l'image reste-t-elle en contexte ?)",
    lambda c: [user(txt("Remember this picture."), img(c, "red_square.png")), assistant(txt("Understood, I see a picture.")), user(txt("What color was the shape in the picture?"))],
    tags=("compose",))
one("ocr_text", "OCR : image « HELLO 42 »", lambda c: [user(txt("What text is written in the image? Reply with the text only."), img(c, "text_hello42.png"))], tags=("quality",))
one("image_in_assistant", "Bloc image dans un message assistant (doc : images réservées au rôle user)", lambda c: [user(txt("Hi")), assistant(img(c, "scene.png")), user(txt("Describe it."))],
    "4xx", ("neg", "placement"))
one("first_message_assistant", "Premier message de rôle assistant (Converse impose user en premier)", lambda c: [assistant(txt("Hello")), user(txt(Q), img(c, "scene.png"))], "4xx", ("neg", "placement"))


@bcase(EP, "image_in_tool_result", "Image dans un toolResult (OpenAI : refusé pour role=tool)", "any", ("placement", "tools"))
def _(ctx):
    tools = {"tools": [{"toolSpec": {"name": "get_picture", "description": "Returns a picture", "inputSchema": {"json": {"type": "object", "properties": {}}}}}]}
    msgs = [user(txt("Call get_picture then describe it.")),
            assistant({"toolUse": {"toolUseId": "tool_1", "name": "get_picture", "input": {}}}),
            user({"toolResult": {"toolUseId": "tool_1", "content": [img(ctx, "scene.png")]}})]
    ctx.call(converse(ctx, "vision", msgs, toolConfig=tools))


# ---- limites (documentées pour Converse : 3,75 Mo / 8000 px / 20 images par message)
one("size_3_60mb", "Image de 3,60 Mo (sous 3,75 Mo)", lambda c: [user(txt("Is there a visible pattern? One sentence."), img(c, c.fx.ensure(ensure_noise_png, "noise_3_60mb.png", 3_600_000).name))],
    tags=("limits",), tokens=100)
one("size_3_85mb", "Image de 3,85 Mo (entre 3,75 Mo décimal et 3,75 MiB = 3,93 Mo : quelle unité ?)", lambda c: [user(txt("Is there a visible pattern? One sentence."),
    img(c, c.fx.ensure(ensure_noise_png, "noise_3_85mb.png", 3_850_000).name))], "any", ("limits",), tokens=100)
one("size_4_10mb", "Image de 4,10 Mo (au-dessus de 3,75 MiB)", lambda c: [user(txt("Is there a visible pattern? One sentence."), img(c, c.fx.ensure(ensure_noise_png, "noise_4_10mb.png", 4_100_000).name))],
    "4xx", ("limits", "neg"), tokens=100)
one("tiny_1x1", "Image 1×1 px (certains modèles imposent un minimum)", lambda c: [user(txt("What color is this image?"), img(c, "tiny_1x1.png"))], "any", ("limits",))
one("large_6000x4000", "6000×4000 px (sous 8000 px)", lambda c: [user(txt("What color is this image?"), img(c, "large_6000x4000.png"))], "any", ("limits",))
one("huge_8200x8200", "8200×8200 px (> 8000 px)", lambda c: [user(txt("What color is this image?"), img(c, "huge_8200x8200.png"))], "4xx", ("limits", "neg"))
one("images_20", "20 images dans un message (limite documentée)", lambda c: [user(txt("How many images did I send? Number only."), *[img(c, "scene.png") for _ in range(20)])], "any", ("limits",), tokens=20)
one("images_21", "21 images (> limite documentée)", lambda c: [user(txt("How many images did I send? Number only."), *[img(c, "scene.png") for _ in range(21)])], "4xx", ("limits", "neg"), tokens=20)
one("model_without_vision", "Image envoyée à un modèle texte-seul : erreur explicite ?", lambda c: [user(txt(Q), img(c, "scene.png"))], "any", ("neg", "model"), role="text_only")


@bcase(EP, "too_large_22mb", "Image ≈ 22 Mo (bien au-delà de 3,75 Mo ; limite de taille de requête Converse)", "4xx", ("neg", "limits", "heavy"))
def _(ctx):
    from ..fixtures import build_heavy
    build_heavy(ctx.cfg.fixtures_dir)
    ctx.call(converse(ctx, "vision", [user(txt(Q), img(ctx, "noise_big.png"))], tokens=100))


# ---- fonctionnalités combinées
@bcase(EP, "stream", "ConverseStream avec image : types d'événements, usage dans l'événement metadata", tags=("stream",))
def _(ctx):
    ctx.call(converse(ctx, "vision", [user(txt(Q), img(ctx, "scene.png"))], stream=True))


@bcase(EP, "tool_call_with_image", "toolConfig (toolChoice=any) déclenché depuis une image", tags=("compose", "tools"))
def _(ctx):
    tools = {"tools": [{"toolSpec": {"name": "report_shapes", "description": "Report the shape count",
                                     "inputSchema": {"json": {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}}}}],
             "toolChoice": {"any": {}}}
    ctx.call(converse(ctx, "vision", [user(txt("Count the shapes in the image and call report_shapes."), img(ctx, "scene.png"))], toolConfig=tools))


@bcase(EP, "structured_output_via_tool", "Extraction structurée = outil forcé (équivalent de response_format json_schema d'OpenAI)", tags=("compose", "tools"))
def _(ctx):
    schema = {"type": "object", "required": ["shapes"], "properties": {"shapes": {"type": "array", "items": {
        "type": "object", "required": ["shape", "color"], "properties": {"shape": {"type": "string"}, "color": {"type": "string"}}}}}}
    tools = {"tools": [{"toolSpec": {"name": "shapes", "description": "List shapes", "inputSchema": {"json": schema}}}], "toolChoice": {"tool": {"name": "shapes"}}}
    ctx.call(converse(ctx, "vision", [user(txt("List the shapes and their colors."), img(ctx, "scene.png"))], toolConfig=tools))


@bcase(EP, "count_tokens_image", "CountTokens (Converse) avec image : estimer le coût avant l'appel (quotas)", "any", ("quota",))
def _(ctx):
    ctx.call(BCall("count_tokens", {"modelId": model(ctx, "vision"), "input": {"converse": {"messages": [user(txt(Q), img(ctx, "scene.png"))]}}}))


# ---- InvokeModel natif (le worker choisit « converse ou invoke selon modèle »)
@bcase(EP, "invoke_claude_native_base64", "InvokeModel format natif Anthropic (source base64)", tags=("invoke",))
def _(ctx):
    m = need_family(ctx, "vision", "anthropic")
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 300, "messages": [{"role": "user", "content": [
        {"type": "text", "text": Q}, {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(ctx.fx.bytes("scene.png")).decode()}}]}]}
    ctx.call(BCall("invoke_model", {"modelId": m}, body=body))


@bcase(EP, "invoke_claude_native_url", "InvokeModel format natif Anthropic avec source {type:url} (l'API Anthropic directe le permet ; Bedrock ?)", "any", ("invoke", "source"))
def _(ctx):
    m = need_family(ctx, "vision", "anthropic")
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 300, "messages": [{"role": "user", "content": [
        {"type": "text", "text": Q}, {"type": "image", "source": {"type": "url", "url": ctx.cfg.image_url}}]}]}
    ctx.call(BCall("invoke_model", {"modelId": m}, body=body))


@bcase(EP, "invoke_nova_native", "InvokeModel format natif Nova (messages-v1, image en base64)", tags=("invoke",))
def _(ctx):
    m = need_family(ctx, "vision_nova", "nova")
    body = {"schemaVersion": "messages-v1", "inferenceConfig": {"max_new_tokens": 300}, "messages": [{"role": "user", "content": [
        {"text": Q}, {"image": {"format": "png", "source": {"bytes": base64.b64encode(ctx.fx.bytes("scene.png")).decode()}}}]}]}
    ctx.call(BCall("invoke_model", {"modelId": m}, body=body))


@bcase(EP, "auth_invalid", "Identifiants AWS invalides", "4xx", ("neg", "auth"))
def _(ctx):
    c = converse(ctx, "vision", [user(txt("hi"))], tokens=20)
    c.bad_credentials = True
    ctx.call(c)
