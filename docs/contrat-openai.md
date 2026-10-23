# Contrat OpenAI — audio & multimodalité (référence)

> **Statut des informations.** Source : spec OpenAPI officielle `openai/openai-openapi` (branche `manual_spec`, v2.3.0, téléchargée le 2026-10-23) + doc publique OpenAI.
> Légende : **[spec]** = présent dans la spec OpenAPI · **[doc]** = affirmé par la doc/guides mais absent de la spec · **[?]** = à trancher par un run (cas `any` ou `probe` du [catalogue](cases-catalog.md)).
> **[obs]** = confirmé par le run de référence du 2026-10-23, voir [observations-openai.md](observations-openai.md) (qui fait foi en cas de désaccord avec ce fichier).
> La spec est en retard sur l'API réelle (ex. `stream_format`, `diarized_json`, `chunking_strategy` y sont absents ou partiels) : le run de référence fait foi, pas ce fichier.

---

## 1. `POST /audio/speech` — texte → audio

**Requête** : `application/json`, schéma `additionalProperties: false` [spec].

| champ | type | contrainte | |
|---|---|---|---|
| `model` | string | `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts` | requis |
| `input` | string | ≤ 4096 caractères | requis |
| `voice` | string | `alloy ash ballad coral echo fable onyx nova sage shimmer verse` ; objet `{id}` pour voix custom [?] | requis |
| `response_format` | string | `mp3`(défaut) `opus` `aac` `flac` `wav` `pcm` | |
| `speed` | number | 0.25 – 4.0 (défaut 1) | |
| `instructions` | string | ≤ 4096 ; **sans effet sur `tts-1`/`tts-1-hd`** | |
| `stream_format` | string | `sse` \| `audio` [doc][?] | absent de la spec |

**Réponse** : **corps binaire**, pas JSON. `Content-Type` dépend du format (`audio/mpeg`, `audio/opus`, `audio/aac`, `audio/flac`, `audio/wav`, `audio/pcm`) [doc][?]. Livré en `Transfer-Encoding: chunked` : l'audio peut être lu avant la fin de la génération. `opus` = conteneur Ogg [?]. `pcm` = brut 24 kHz, 16 bit signé LE, mono [doc].
Avec `stream_format=sse` : flux `text/event-stream` d'événements `speech.audio.delta` (`audio` en base64) puis `speech.audio.done` (avec `usage`) [doc][?].
**Pas d'`usage` dans la réponse binaire** → toute comptabilisation (caractères, durée) est à faire côté gateway [?].

## 2. `POST /audio/transcriptions` — audio → texte

**Requête** : `multipart/form-data` [spec].

| champ | type | contrainte |
|---|---|---|
| `file` | fichier | flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm ; **≤ 25 Mo** [doc] (un WAV de 26 MiB est pourtant accepté [obs]) ; extension du nom de fichier obligatoire et déterminante [obs] — requis |
| `model` | string | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` ; `gpt-4o-transcribe-diarize` [doc][?] — requis |
| `language` | string | ISO-639-1 (`en`, `fr`) |
| `prompt` | string | guidage de style/vocabulaire |
| `response_format` | string | `json`(défaut) `text` `srt` `verbose_json` `vtt` ; `diarized_json` [doc][?]. **`gpt-4o-*-transcribe` : `json` et `text` [obs]** (la spec dit `json` seulement) ; `diarized_json` confirmé [obs] |
| `temperature` | number | 0 – 1 |
| `include[]` | string, répétable | `logprobs` (json + modèles gpt-4o-transcribe uniquement) |
| `timestamp_granularities[]` | string, répétable | `word`, `segment` ; **exige `verbose_json`** ; whisper-1 seulement [spec][?] |
| `stream` | bool | SSE ; **ignoré par `whisper-1`** [spec] |
| `chunking_strategy` | `auto` \| objet | [doc][?] |

**Réponse** : **le type dépend de `response_format`** :

| `response_format` | Content-Type | corps |
|---|---|---|
| `json` | application/json | `{"text": "..."}` (+ `usage`, `logprobs` selon modèle/include [?]) |
| `text` | text/plain | texte brut |
| `srt`, `vtt` | text/plain [?] | sous-titres |
| `verbose_json` | application/json | `{task, language, duration, text, segments[], words[]}` (`segments[]` : id, seek, start, end, text, tokens, temperature, avg_logprob, compression_ratio, no_speech_prob) [spec] |
| `diarized_json` | application/json | segments avec locuteur [?] |
| `stream=true` | text/event-stream | `transcript.text.delta` … `transcript.text.done` [doc][?] |

## 3. `POST /chat/completions` — parts multimodales

### 3.1 Parts autorisées par rôle [spec]

| rôle | `text` | `image_url` | `input_audio` | `file` | autre |
|---|:-:|:-:|:-:|:-:|---|
| `system` / `developer` | ✅ | ❌ | ❌ | ❌ | |
| `user` | ✅ | ✅ | ✅ | ✅ | |
| `assistant` | ✅ | ❌ | ❌ | ❌ | `refusal` ; champ `audio: {id}` (voir 3.3) |
| `tool` | ✅ | ❌ | ❌ | ❌ | |

Le *rejet effectif* (400 vs ignoré en silence) de chaque case ❌ est testé par les cas `neg`/`placement`.

### 3.2 Image — `image_url`

```json
{"type": "image_url", "image_url": {"url": "<https URL | data:image/png;base64,...>", "detail": "auto|low|high"}}
```
- `url` : URL publique **ou** data URL base64 [spec]. Le base64 *nu* (sans `data:`) est-il accepté ? [?]
- `detail` : `auto`(défaut) / `low` / `high` — pilote la résolution et le coût en tokens [spec].
- Formats : PNG, JPEG, WEBP, GIF non animé ; ≤ 20 Mo/image ; ≤ 500 images/requête [doc][?].
- Pour une URL, **c'est OpenAI qui télécharge l'image**.

### 3.3 Audio — entrée et sortie

Entrée :
```json
{"type": "input_audio", "input_audio": {"data": "<base64 SANS préfixe data:>", "format": "wav|mp3"}}
```
Sortie audio — requête :
```json
{"model": "gpt-4o-audio-preview", "modalities": ["text", "audio"], "audio": {"voice": "alloy", "format": "wav"}, "messages": [...]}
```
- `audio.format` : `wav mp3 flac opus pcm16` (+ `aac` dans l'enum de la spec) ; **`pcm16` seul en streaming** [doc][?].
- `audio.voice` : mêmes voix que TTS [spec] ; voix plus récentes (`marin`, `cedar`) [?].
- Modèles : `gpt-4o-audio-preview`, `gpt-4o-mini-audio-preview` [spec] ; `gpt-4o-audio-preview` est introuvable (404) avec la clé testée ; `gpt-audio`, `gpt-audio-mini`, `gpt-audio-1.5` existent [obs] → alias `MM_MODEL_AUDIO_CHAT` (défaut `gpt-audio`).

Sortie audio — réponse (non-stream) [spec] :
```json
{"choices":[{"message":{"role":"assistant","content":null,
  "audio":{"id":"audio_...","expires_at":1700000000,"data":"<base64>","transcript":"..."}}}],
 "usage":{"prompt_tokens":..,"completion_tokens":..,
   "prompt_tokens_details":{"audio_tokens":..,"cached_tokens":..},
   "completion_tokens_details":{"audio_tokens":..,"reasoning_tokens":..}}}
```
En streaming : `choices[0].delta.audio = {id, data, transcript, expires_at}` par chunk, `data` = PCM16 base64 [doc][?].

**Multi-tours** : le message assistant précédent peut être référencé **par id seul** `{"role":"assistant","audio":{"id":"audio_..."}}` — l'audio est conservé *côté OpenAI* jusqu'à `expires_at` [spec]. Alternative sans état : renvoyer le `transcript` en `content` texte.

## 4. Erreurs

Format OpenAI [doc] : `{"error": {"message", "type", "param", "code"}}`, typiquement `400 invalid_request_error`, `401`, `404 model_not_found`, `413`, `429`. Les cas `neg` capturent `param`/`code` réels pour chaque situation — c'est la table de correspondance dont la gateway aura besoin pour reproduire les erreurs.
