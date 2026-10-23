"""POST /chat/completions — content part `image_url`."""
from __future__ import annotations

from ..http import Req
from . import case
from .util import chat_req, image, text, user

EP = "chat-image"
Q = "Describe this image in one short sentence, naming each shape and its color."
SCENE_DESC = "scène : carré rouge, cercle bleu, triangle vert sur fond gris clair"


def one(name, title, build, expect="2xx", tags=(), notes="", model="vision"):
    """build(ctx) -> liste de messages."""
    def fn(ctx):
        ctx.call(chat_req(ctx, model, build(ctx)))
    case(EP, name, title, expect, tags, notes)(fn)


# ---- sources de l'image
one("url_https", "Image par URL https publique (le fetch est fait côté provider)", lambda c: [user(text(Q), image(c.cfg.image_url))],
    tags=("source", "network"), notes="nécessite que la cible puisse joindre l'URL")
one("data_url_png", f"Data URL base64 PNG — {SCENE_DESC}", lambda c: [user(text(Q), image(c.fx.data_url("scene.png")))], tags=("source",))
for ext in ("jpg", "webp", "gif"):
    one(f"data_url_{ext}", f"Data URL {ext.upper()} (même scène)", lambda c, e=ext: [user(text(Q), image(c.fx.data_url(f"scene.{e}")))],
        tags=("source", "format"))
for ext, mime in (("bmp", "image/bmp"), ("tiff", "image/tiff")):
    one(f"data_url_{ext}", f"Data URL {ext.upper()} (hors liste png/jpeg/webp/gif)", lambda c, e=ext: [user(text(Q), image(c.fx.data_url(f"scene.{e}")))],
        "4xx", ("source", "format", "neg"))
one("data_url_svg", "Data URL SVG (non supporté)", lambda c: [user(text(Q), image(c.fx.data_url("scene.svg")))], "4xx", ("source", "format", "neg"))
one("data_url_animated_gif", "GIF animé (doc : seuls les GIF non animés)", lambda c: [user(text(Q), image(c.fx.data_url("animated.gif")))],
    "any", ("source", "format"))
one("data_url_wrong_mime", "PNG déclaré image/jpeg dans le data URL : le MIME déclaré prime-t-il sur le contenu ?",
    lambda c: [user(text(Q), image(c.fx.data_url("scene.png", "image/jpeg")))], "any", ("source", "format", "neg"))
one("data_url_no_mime", "data:;base64,... sans type MIME", lambda c: [user(text(Q), image("data:;base64," + c.fx.b64("scene.png")))],
    "any", ("source", "neg"))
one("raw_base64_no_prefix", "Base64 brut sans préfixe `data:` (le champ doc dit « URL or base64 »)",
    lambda c: [user(text(Q), image(c.fx.b64("scene.png")))], "any", ("source", "neg"))

# ---- detail
for d, exp in (("low", "2xx"), ("high", "2xx"), ("auto", "2xx"), ("ultra", "4xx")):
    one(f"detail_{d}", f"detail={d}" + (" (valeur invalide)" if exp == "4xx" else "") + " : impact sur usage.prompt_tokens",
        lambda c, d=d: [user(text(Q), image(c.fx.data_url("scene.png"), d))], exp, ("detail",) + (("neg",) if exp == "4xx" else ()))

# ---- composition des messages
one("multi_images", "Deux images dans le même message + question comparative",
    lambda c: [user(text("What is the color and shape in the first image, and in the second image?"),
                    image(c.fx.data_url("red_square.png")), image(c.fx.data_url("blue_circle.png")))], tags=("compose",))
one("interleaved", "text, image, text, image : l'ordre des parts est-il préservé ?",
    lambda c: [user(text("Image A:"), image(c.fx.data_url("red_square.png")), text("Image B:"), image(c.fx.data_url("blue_circle.png")),
                    text("Which image (A or B) contains a circle?"))], tags=("compose",))
one("image_only", "Message avec une seule image et AUCUNE part text", lambda c: [user(image(c.fx.data_url("scene.png")))], "any", ("compose",))
one("text_as_string_plus_image_msg", "Historique mixte : message 1 en content string, message 2 en parts avec image",
    lambda c: [{"role": "user", "content": "I will show you a picture next."}, {"role": "assistant", "content": "OK, please send it."},
               user(text(Q), image(c.fx.data_url("scene.png")))], tags=("compose",))
one("history_image_then_text", "Image dans un tour précédent, question de suivi en texte seul (l'image reste-t-elle dans le contexte ?)",
    lambda c: [user(text("Remember this picture."), image(c.fx.data_url("red_square.png"))),
               {"role": "assistant", "content": "Understood, I see a picture."},
               {"role": "user", "content": "What color was the shape in the picture?"}], tags=("compose",))
one("system_prompt_plus_image", "Message system texte + user image",
    lambda c: [{"role": "system", "content": "You answer in French, in one sentence."}, user(text(Q), image(c.fx.data_url("scene.png")))],
    tags=("compose",))
one("developer_role_plus_image", "Rôle `developer` (nouveau) + user image", lambda c: [
    {"role": "developer", "content": "Answer in one sentence."}, user(text(Q), image(c.fx.data_url("scene.png")))], "any", ("compose",))
one("ocr_text", "OCR : image contenant « HELLO 42 »", lambda c: [user(text("What text is written in the image? Reply with the text only."),
                                                                   image(c.fx.data_url("text_hello42.png")))], tags=("quality",))

# ---- placement interdit
one("image_in_system", "Part image dans un message system (doc : texte seulement)", lambda c: [
    {"role": "system", "content": [text("Be brief."), image(c.fx.data_url("scene.png"))]}, {"role": "user", "content": "Hi"}], "4xx", ("neg", "placement"))
one("image_in_assistant", "Part image dans un message assistant (doc : text/refusal seulement)", lambda c: [
    user(text("Hi")), {"role": "assistant", "content": [image(c.fx.data_url("scene.png"))]}, user(text("Describe it."))], "4xx", ("neg", "placement"))


@case(EP, "image_in_tool_result", "Part image dans un message role=tool (résultat de fonction)", "4xx", ("neg", "placement", "tools"))
def _(ctx):
    msgs = [user(text("Call get_picture then describe it.")),
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_picture", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "content": [image(ctx.fx.data_url("scene.png"))]}]
    tools = [{"type": "function", "function": {"name": "get_picture", "description": "Returns a picture", "parameters": {"type": "object", "properties": {}}}}]
    ctx.call(chat_req(ctx, "vision", msgs, tools=tools))


# ---- compat modèles
one("model_without_vision", "Image envoyée à un modèle texte-seul : erreur explicite ou image ignorée en silence ?",
    lambda c: [user(text(Q), image(c.fx.data_url("scene.png")))], "any", ("neg", "model"), model="text_only")

# ---- features combinées
@case(EP, "stream", "stream=true + stream_options.include_usage avec image", tags=("stream",))
def _(ctx):
    ctx.call(chat_req(ctx, "vision", [user(text(Q), image(ctx.fx.data_url("scene.png")))], stream=True,
                      stream_options={"include_usage": True}))


@case(EP, "structured_output", "response_format json_schema + image (extraction structurée)", tags=("compose",))
def _(ctx):
    schema = {"type": "object", "additionalProperties": False, "required": ["shapes"], "properties": {"shapes": {
        "type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["shape", "color"],
                                   "properties": {"shape": {"type": "string"}, "color": {"type": "string"}}}}}}
    ctx.call(chat_req(ctx, "vision", [user(text("List the shapes and their colors."), image(ctx.fx.data_url("scene.png")))],
                      response_format={"type": "json_schema", "json_schema": {"name": "shapes", "strict": True, "schema": schema}}))


@case(EP, "tool_call_with_image", "Function calling déclenché depuis une image", tags=("compose", "tools"))
def _(ctx):
    tools = [{"type": "function", "function": {"name": "report_shapes", "description": "Report the shape count",
              "parameters": {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}}}]
    ctx.call(chat_req(ctx, "vision", [user(text("Count the shapes in the image and call report_shapes."), image(ctx.fx.data_url("scene.png")))],
                      tools=tools, tool_choice="required"))


# ---- images invalides / limites
one("url_unreachable", "URL qui ne résout pas (host .invalid)", lambda c: [user(text(Q), image("https://mmprobe.invalid/x.png"))], "4xx", ("neg", "source", "network"))
one("url_not_an_image", "URL valide mais contenu text/html", lambda c: [user(text(Q), image("https://example.com/"))], "4xx", ("neg", "source", "network"))
one("url_http_plain", "URL http:// non TLS", lambda c: [user(text(Q), image(c.cfg.image_url.replace("https://", "http://")))],
    "any", ("neg", "source", "network"))
one("url_file_scheme", "URL file:///etc/hostname (SSRF / schéma local) — doit être refusée", lambda c: [user(text(Q), image("file:///etc/hostname"))],
    "4xx", ("neg", "source", "security"))
one("url_internal_ip", "URL vers 169.254.169.254 (metadata cloud) — doit être refusée/injoignable", lambda c: [user(text(Q), image("http://169.254.169.254/latest/meta-data/"))],
    "4xx", ("neg", "source", "security"))
one("url_empty", "image_url.url = chaîne vide", lambda c: [user(text(Q), image(""))], "4xx", ("neg",))
one("base64_corrupt", "Data URL avec base64 tronqué/corrompu", lambda c: [user(text(Q), image("data:image/png;base64,iVBORw0KGgo=AAAA"))], "4xx", ("neg",))
one("not_an_image_bytes", "Data URL image/png dont le contenu est du HTML", lambda c: [user(text(Q), image(c.fx.data_url("not_an_image.html", "image/png")))],
    "4xx", ("neg",))
one("image_url_as_string", "image_url donné comme chaîne au lieu d'un objet {url} (erreur client fréquente)",
    lambda c: [user(text(Q), {"type": "image_url", "image_url": c.fx.data_url("scene.png")})], "4xx", ("neg", "schema"))
one("missing_image_url", "Part {type: image_url} sans clé image_url", lambda c: [user(text(Q), {"type": "image_url"})], "4xx", ("neg", "schema"))
one("unknown_part_type", "Part de type inconnu (`image`)", lambda c: [user(text(Q), {"type": "image", "source": {"url": "x"}})], "4xx", ("neg", "schema"))
one("tiny_1x1", "Image 1×1 px", lambda c: [user(text("What color is this image?"), image(c.fx.data_url("tiny_1x1.png")))], "any", ("limits",))
one("large_6000x4000", "Image 6000×4000 px (PNG uni, peu d'octets) : redimensionnement côté provider ?",
    lambda c: [user(text("What color is this image?"), image(c.fx.data_url("large_6000x4000.png")))], "any", ("limits",))
one("huge_8200x8200", "Image 8200×8200 px (> 8000 px, limite de certains providers)",
    lambda c: [user(text("What color is this image?"), image(c.fx.data_url("huge_8200x8200.png")))], "any", ("limits",))


@case(EP, "too_large_22mb", "Image ≈ 22 Mo (doc : max 20 Mo par image)", "4xx", ("neg", "limits", "heavy"))
def _(ctx):
    from ..fixtures import build_heavy
    build_heavy(ctx.cfg.fixtures_dir)
    ctx.call(chat_req(ctx, "vision", [user(text(Q), image(ctx.fx.data_url("noise_big.png")))]))


@case(EP, "many_images_12", "12 images dans un seul message (pas de limite documentée à ce niveau côté OpenAI ; certains providers limitent à ~20)",
      "any", ("limits",))
def _(ctx):
    parts = [text("How many images did I send? Answer with a number only.")] + [image(ctx.fx.data_url("tiny_1x1.png")) for _ in range(12)]
    ctx.call(chat_req(ctx, "vision", [user(*parts)], tokens=20))


@case(EP, "auth_invalid", "Clé API invalide", "4xx", ("neg", "auth"))
def _(ctx):
    r = chat_req(ctx, "vision", [user(text(Q), image(ctx.fx.data_url("tiny_1x1.png")))])
    r.headers = {"Authorization": "Bearer sk-invalid-mmprobe"}
    ctx.call(r)
