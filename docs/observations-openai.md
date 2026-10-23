# Observations — run de référence contre l'API OpenAI

> **Ce que c'est.** Constats tirés de `captures/openai/` (run du 2026-10-23, `https://api.openai.com/v1`, clé de l'équipe). Chaque ligne renvoie à un cas : le détail brut (requête, réponse, headers, audio) est dans `captures/openai/<endpoint>/<cas>/`, le tableau complet dans `captures/openai/REPORT.md`.
> **Portée.** 216 cas, 214 échanges HTTP, dont 156 conformes à l'attente tirée de la doc, **5 écarts**, 53 « attente indéterminée », 5 ignorés (fixtures m4a/mp4/webm/mpga/mpeg non fournies). Les cas `security` n'ont pas été lancés.
> **Réserve.** Un seul run, un seul compte : les comportements sont ceux observés ce jour pour ces modèles (`gpt-4o-mini-tts`, `tts-1`, `whisper-1`, `gpt-4o-(mini-)transcribe`, `gpt-4o-transcribe-diarize`, `gpt-4o-mini`, `gpt-audio` → résolu en `gpt-audio-2025-08-28`). Les modèles évoluent ; les limites « acceptées » ne sont pas des limites garanties.

## 1. Les 5 écarts avec la documentation

| Cas | Doc | Observé |
|---|---|---|
| `speech/input_4097` | `input` ≤ 4096 caractères | **200** : 4097 caractères acceptés sur `gpt-4o-mini-tts` (2,1 Mo d'audio). La limite n'est pas appliquée sur ce modèle (non testé sur `tts-1`). |
| `speech/missing_voice` | `voice` requis | **200** : une voix par défaut est utilisée. |
| `transcriptions/temperature_out_of_range` | 0 ≤ temperature ≤ 1 | **200** avec `temperature=2` : texte aberrant en sortie (`Helloight ruditud ka mag…`). Aucune validation de plage. |
| `transcriptions/too_large_26mb` | fichier ≤ 25 Mo | **200** pour un WAV de 26 MiB (≈ 27,3 Mo). Plafond réel inconnu. |
| `chat-image/too_large_22mb` | image ≤ 20 Mo | **200** pour un PNG de 22 Mo (≈ 36 857 tokens facturés). Plafond réel inconnu. |

→ Conséquence : **on ne peut pas se reposer sur les limites documentées pour dimensionner ou valider côté gateway.** Soit on les impose nous-mêmes (choix produit), soit on mesure les vraies bornes.

## 2. `POST /audio/speech`

- **Réponse binaire chunked** (31 à 77 chunks selon le format ; TTFB 0,5 à 2,7 s). Content-Types réels :

  | `response_format` | Content-Type | contenu réel |
  |---|---|---|
  | mp3 | `audio/mpeg` | MP3 (24 kHz mono) |
  | opus | `audio/opus` | **Ogg** contenant Opus |
  | aac | `audio/aac` | AAC ADTS brut (pas de conteneur m4a) |
  | flac | `audio/flac` | FLAC |
  | wav | `audio/wav` | WAV PCM 16 bit 24 kHz mono, **en-tête « streaming » : tailles RIFF et `data` = `0xFFFFFFFF`** |
  | pcm | `audio/pcm` | brut, sans en-tête |

- **`stream_format=sse`** (modèle `gpt-4o-mini-tts`) : `text/event-stream`, 105 événements `{"type":"speech.audio.delta","audio":"<base64>"}`, puis `{"type":"speech.audio.done","usage":{"input_tokens","output_tokens","total_tokens"}}`, puis `data: [DONE]`. `stream_format=audio` → binaire classique. Valeur inconnue → 400 `invalid_value` (« Supported values are: 'audio' and 'sse' »). Sur `tts-1`, `sse` est **ignoré** (200, binaire).
- **`usage` : absent de la réponse binaire**, présent uniquement dans l'événement `done` en SSE.
- **Tolérance** : paramètre inconnu (`foo`) → ignoré (200) ; `instructions` sur `tts-1` → ignoré (200) ; `input` d'espaces → 200 ; voix `ballad` et `verse` acceptées sur `gpt-4o-mini-tts`.
- **Rejets** : `speed` hors [0.25, 4] → 400 `decimal_below_min_value` / `decimal_above_max_value`, `param: speed` ; `input` vide → 400 `empty_string` ; `response_format` en majuscules (`MP3`) → 400 ; voix inconnue ou objet `{id}` inexistant → 400 (`param: voice_id` pour l'objet) ; corps urlencoded → 400 « you must provide a model parameter », multipart → 400 (message = `repr` de validation), JSON invalide → 400 (message long avec « HINT » sur la bibliothèque HTTP) ; sans `Authorization` → 401.
- ⚠ **`model` = modèle de chat (`gpt-4o-mini`) → HTTP 431, corps `text/html`** (« Request Header Fields Too Large »), reproduit avec `curl` nu : c'est OpenAI, pas notre script. Un modèle inexistant donne en revanche un 404 JSON `model_not_found`.

## 3. `POST /audio/transcriptions`

**Fichier d'entrée.** L'**extension du nom de fichier est requise et fait foi** :
- acceptés : `.mp3`, `.wav`, `.flac`, `.ogg` (Opus dans Ogg), WAV reconstruit depuis du PCM ; `Content-Type` de la partie = `application/octet-stream` accepté si l'extension est bonne.
- refusés (400 `unsupported_value`, `param: file`, « Unsupported file format opus/aac/txt ») : `.opus`, `.aac`, `.txt`, **nom sans extension**.
- contenu MP3 nommé `.wav` → 400 `unsupported_format` avec `param: "messages"` (paramètre trompeur : il n'y a pas de `messages` ici). Fichier vide → même erreur. Octets aléatoires `.mp3` → 400 `invalid_value` « Audio file might be corrupted or unsupported ».

**`response_format` par modèle.**

| modèle | json | text | srt / vtt | verbose_json | diarized_json |
|---|:-:|:-:|:-:|:-:|:-:|
| `whisper-1` | ✅ | ✅ (`text/plain`) | ✅ (`text/plain`) | ✅ | — |
| `gpt-4o-transcribe` | ✅ | ✅ | ❌ 400 | ❌ 400 | — |
| `gpt-4o-transcribe-diarize` | — | — | — | — | ✅ |

Le message d'erreur (« not compatible with model **'gpt-4o-transcribe-api-ev3'**. Use 'json' or 'text' instead ») laisse échapper un nom de modèle interne : à ne pas répercuter tel quel.

**Corps de réponse.**
- `json` → `{"text", "usage"}`. **`usage` est toujours présent mais de forme différente selon le modèle** : `whisper-1` → `{"type":"duration","seconds":8}` (audio de 7,1 s) ; `gpt-4o-*-transcribe` → `{"type":"tokens","total_tokens","input_tokens","input_token_details":{"text_tokens","audio_tokens"},"output_tokens"}`.
- `verbose_json` (whisper) → `{task, language, duration, text, segments[], usage}` ; avec `timestamp_granularities[]=word` → `words[]` (`{word,start,end}`) ; les deux ensemble → `segments[]` + `words[]`.
- `diarized_json` → `{task, duration, text, segments[], usage}`, segments `{"type":"transcript.text.segment","id","speaker":"A","text","start","end"}` (pas de `language`).
- `include[]=logprobs` (gpt-4o, `json`) → clé `logprobs: [{token, logprob, bytes}]` ; sur `whisper-1` → **ignoré** (200, pas de `logprobs`) ; avec `response_format=text` → 400.

**Paramètres.** `timestamp_granularities[]` sans `verbose_json` → 400 `timestamp_granularities_format` ; valeur hors enum → 400 dont le *message est un `repr` Python de la liste d'erreurs de validation* (sans `code`) ; `language=english` → 400 `invalid_value` ; `language=fr` forcé sur de l'anglais → 200, transcrit en anglais (non forcé) ; `chunking_strategy` (`auto` ou objet `server_vad`) accepté sur `gpt-4o-transcribe` ; `temperature=hot` → 400, `temperature=2` → 200 (voir §1).

**Streaming.** `stream=true` sur `gpt-4o-transcribe` → SSE : 21 × `{"type":"transcript.text.delta","delta"}`, 1 × `transcript.text.done`, puis `[DONE]`. **Reste en SSE même avec `response_format=text`.** Sur `whisper-1`, `stream=true` est ignoré → JSON classique.

**Silence / bruit.** Un sinus de 2 s et 3 s de silence renvoient **200 avec du texte halluciné dans une langue sans rapport** (`পাপ্পু`, `هیچوقت`) : on ne peut pas supposer un texte vide.

**Autres erreurs.** Pas de `file` → 400 (message = repr de validation) ; pas de `model` → 400 « you must provide a model parameter » ; modèle TTS (`tts-1`) sur cet endpoint → **404 « Invalid URL (POST /v1/audio/transcriptions) »** ; corps JSON → 400.

## 4. `POST /chat/completions` avec images (`gpt-4o-mini`)

**Sources.**
- URL https **et http://** publiques acceptées (OpenAI télécharge de son côté). Échecs de téléchargement → 400 `invalid_image_url` (« Error while downloading file. Upstream status code: 404 » / « Failed to download file »). URL vide → 400. Contenu HTML derrière l'URL → 400 `invalid_image_format`.
- data-URL `png`, `jpeg`, `webp`, `gif` acceptés. `bmp`, `tiff`, `svg`, ou HTML déguisé en PNG → 400 `invalid_image_format` (« …one of the following formats: ['png','jpeg','gif','webp'] »). Base64 corrompu → 400 `image_parse_error`.
- **Le MIME déclaré n'est pas fiable ni vérifié** : un PNG déclaré `image/jpeg` passe (le format est détecté sur le contenu). `data:;base64,…` sans MIME → 400 « Invalid MIME type » ; **base64 nu sans `data:` → 400** `invalid_image_url`.
- **GIF animé accepté mais seule la 1ʳᵉ image est vue** (le modèle décrit « un carré rouge », 1ʳᵉ frame).

**`detail`** : `low` → 2 855 tokens d'entrée contre 8 522 pour `auto`/`high` (même image, `gpt-4o-mini`). Valeur invalide → 400 *sans `code`* ; le message liste `['low','auto','high','original']` : **`original` est une valeur valide récente**.

**Dimensions et volume** (tokens d'entrée, `gpt-4o-mini`) : 1×1 px → 8 513 ; 512×320 → 8 522 ; 6000×4000 → 36 848 ; **8200×8200 accepté** (25 514) — pas de rejet au-delà de 8000 px ; 12 images 1×1 dans un message → 102 020 tokens, accepté.

**Composition.** Texte avant/après/entre images, plusieurs images, image seule sans texte, rôle `developer`, historique avec image puis question de suivi, JSON schema strict et function calling (`finish_reason: tool_calls`), streaming + `include_usage` : tous OK. L'ordre des parts est préservé (`interleaved`).

**Rôles.** Image dans `system`, `assistant` ou `tool` → 400 `invalid_value`, `param: messages[i]` (« Image URLs are only allowed for messages with role 'user' »).

**Schéma.** `image_url` donné comme chaîne → 400 `invalid_type` avec chemin précis (`messages[0].content[1].image_url`) ; part `{"type":"image"}` → 400 listant les types valides (`text, image_url, input_audio, refusal, audio, file`) ; `{"type":"image_url"}` sans objet → 400 au **message trompeur** (« image_url is only supported by certain models »).

⚠ **Image envoyée à `gpt-3.5-turbo` → 500 `server_error`** (reproduit deux fois), pas un 400 : un modèle sans vision ne produit pas d'erreur propre côté OpenAI.

## 5. `POST /chat/completions` avec audio (`gpt-audio`)

**Disponibilité.** `gpt-4o-audio-preview` → 404 `model_not_found` pour cette clé ; `gpt-audio` (résolu `gpt-audio-2025-08-28`), `gpt-audio-mini`, `gpt-audio-1.5` listés par `GET /v1/models`.

**Entrée `input_audio`.**
- `format` : **`wav` ou `mp3` uniquement, en minuscules** (`flac`, `pcm16`, `WAV` → 400 `invalid_value`). **Le format déclaré doit correspondre au contenu** (MP3 déclaré `wav` → 400 `unsupported_format`, `param: messages`).
- `data` : base64 sans préfixe ; data-URL, base64 invalide ou vide → 400 `invalid_value` avec chemin exact ; texte encodé → 400 `unsupported_format`. `input_audio` en chaîne → 400 `invalid_type`. `format` absent → 400 `missing_required_parameter`.
- Rôle : audio dans `system`/`assistant` → 400 (« Audio URLs are only allowed for messages with role 'user' »). Sur un modèle texte ou vision → 400 « Content blocks are expected to be either text or image_url type ».
- Plusieurs `input_audio`, audio seul sans texte, audio + texte entrelacés, français, tonalité sans parole : OK.
- **Usage** : `prompt_tokens_details.audio_tokens` (63 pour le WAV de ≈ 6,3 s ; 71 pour le MP3 de même contenu), et `prompt_tokens_details` contient aussi `text_tokens` et `image_tokens`.

**Sortie audio.**
- `modalities:["text","audio"]` + `audio:{voice,format}` obligatoires ensemble. `["audio"]` seul → 400 (« Only ['text'] and ['text','audio'] are supported »). `audio` sans `modalities` audio → 400.
- **`gpt-audio` refuse un appel sans audio ni en entrée ni en sortie** (400 `invalid_value`, `param: model` : « This model requires that either input content or output modality contain audio »). Il ne remplace donc pas un modèle texte.
- Réponse : `message.content = null`, `message.audio = {id, data(base64), transcript, expires_at}` ; `expires_at` ≈ **+1 h**.
- **Le WAV de sortie a lui aussi un en-tête « streaming » (`0xFFFFFFFF`)** : la durée se calcule sur le nombre d'octets, pas dans l'en-tête.
- Formats de sortie tous acceptés : `wav`, `mp3`, `flac`, `opus` (Ogg/Opus), `aac` (ADTS), `pcm16` (brut). Voix valides : `alloy echo fable onyx nova shimmer coral verse ballad ash sage marin cedar`. `n=2` → **500** `model_error`.
- `usage.completion_tokens_details.audio_tokens` renseigné (ex. 37 sur 52).

**Streaming audio** (`stream:true`, `audio.format=pcm16` obligatoire ; `wav` → 400 `unsupported_value`).
- 56 chunks pour une phrase. Le transcript arrive par morceaux (`delta.audio.transcript`) et l'audio par d'autres chunks (`delta.audio.data`), `id` dans le 1ᵉʳ chunk audio.
- **Particularités à connaître** : (a) **aucun `finish_reason`** n'est émis ; (b) **un chunk n'a pas de clé `choices`** (seulement `id`, `usage:null`, …) ; (c) le chunk `usage` (`choices: []`) n'est **pas le dernier** : un chunk final `{"delta":{"audio":{"expires_at":…}}}` le suit, avant `[DONE]` ; (d) chaque chunk porte une clé `usage` (null sauf le chunk usage) et un champ `obfuscation`.

**Multi-tours.**
- Référence par id : `{"role":"assistant","audio":{"id":"audio_…"}}` → OK ; **l'audio précédent est re-facturé en entrée** (tour 2 : `prompt_tokens_details.audio_tokens: 98`). Id inconnu → 400 `audio_not_found` (`param: content.messages[1].audio.id`).
- Repli par `transcript` en texte (`{"role":"assistant","content":"…"}`) → OK (à condition de redemander de l'audio en sortie, cf. ci-dessus).
- L'audio d'un tour utilisateur précédent reste dans le contexte (« Le locuteur a mentionné Paris »).

**Function calling avec audio en entrée** : `tool_calls` renvoyés mais `finish_reason: "stop"` (contre `tool_calls` observé avec `gpt-4o-mini` + image).

## 6. Transverse

- **Format d'erreur** : `{"error":{"message","type","param","code"}}` dans l'immense majorité des cas, mais : (1) HTTP 431 en `text/html` (`speech` + modèle de chat) ; (2) erreurs de validation des endpoints audio dont `message` est un `repr` Python et `code`/`param` absents ; (3) `param` parfois trompeur (`messages` pour des erreurs de fichier audio) ; (4) 500 `server_error`/`model_error` pour des combinaisons non supportées (`gpt-3.5-turbo`+image, `n=2` audio).
- **Headers utiles** à relayer/ignorer : `x-request-id`, `openai-processing-ms`, `openai-version`, `x-ratelimit-limit-requests` / `-remaining-requests` / `-reset-requests`.
- **Non déterminisme** : la langue de réponse d'un modèle audio peut dériver (un cas a répondu en italien à un prompt anglais) — les tests de non-régression ne doivent pas comparer le texte.
- **Non couverts** : formats `m4a`/`mp4`/`webm`/`mpga`/`mpeg` en STT ; cas `security` (SSRF) ; plafonds réels de taille ; `/audio/translations` ; Responses API.
