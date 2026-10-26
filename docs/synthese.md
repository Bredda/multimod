# Cadrage multimodalité — synthèse (étape 1 : comportement des endpoints OpenAI)

## 0. Où on en est

| | état |
|---|---|
| Sondes HTTP brutes (218 cas dont 4 opt-in `heavy`/`security`) | ✅ écrites ; 216 exécutés contre OpenAI |
| Run de référence OpenAI | ✅ fait le 2026-10-23 → `captures/openai/` · détail : [observations-openai.md](observations-openai.md) |
| Run contre LiteLLM (LLMaaS) | ⏳ à faire (mêmes sondes HTTP, autre `--env-file`) |
| Sondes **Bedrock** (boto3, 97 cas) | ✅ écrites et validées hors-ligne · ⏳ **jamais exécutées sur AWS** (pas d'identifiants) |
| Mapping OpenAI → Bedrock | 📝 hypothèses dans [bedrock-mapping.md](bedrock-mapping.md), chaque ligne reliée au cas qui la vérifiera |
| Contrat documenté | ✅ [contrat-openai.md](contrat-openai.md) (spec OpenAPI) — complété par les observations |

Résultat du run : 214 échanges, 156 conformes à la doc, **5 écarts**, 53 cas à attente indéterminée désormais tranchés, 5 ignorés (fixtures `m4a/mp4/webm/mpga/mpeg` à fournir). Les cas `security` (SSRF) n'ont volontairement pas été lancés contre OpenAI.

---

## 1. Trois surfaces, trois natures de payload

| Endpoint | Entrée | Sortie | Streaming |
|---|---|---|---|
| `/chat/completions` + `image_url` | JSON, image en **URL (http/https) ou data-URL base64** | JSON (comme aujourd'hui) | SSE (comme aujourd'hui) |
| `/chat/completions` + `input_audio` / sortie audio | JSON, audio en **base64 brut** (wav/mp3) | JSON : `message.audio = {id, data, transcript, expires_at}`, `content: null` | SSE, `delta.audio` PCM16 base64 — **forme atypique**, voir §2.6 |
| `/audio/transcriptions` | **multipart/form-data** (fichier binaire) | **JSON *ou* `text/plain`** selon `response_format`, ou SSE | SSE (`gpt-4o-*` seulement) |
| `/audio/speech` | JSON | **binaire** chunked (Content-Type = format), ou SSE | chunked natif / SSE |

Aujourd'hui la gateway ne manipule que du JSON-in/JSON-out (+ SSE de chat). Les deux endpoints `/audio/*` cassent cette hypothèse **dans les deux sens**, et la complétion avec image/audio la met sous tension (taille, SSE atypique).

## 2. Points d'architecture (contrat + observations)

1. **Transport du binaire jusqu'au worker.** `transcriptions` arrive en multipart ; `speech` repart en binaire. Les templates Jinja2 transforment des *dicts JSON* : ils ne portent pas un fichier. À décider : le worker reçoit-il le fichier brut (stockage objet intermédiaire / enveloppe base64) et le template ne traite-t-il que les champs ? C'est le point de design le plus structurant du lot. *Observé en plus :* **chez OpenAI le type du fichier est déduit de l'extension du nom** (sans extension → 400 ; contenu MP3 nommé `.wav` → 400) : le **nom de fichier doit traverser** la gateway et le worker intact.
2. **La réponse n'est pas toujours du JSON.** Transcription `text/srt/vtt` → `text/plain` ; TTS → binaire (ou SSE). Le pipeline « worker retransforme en JSON OpenAI puis la gateway forwarde » doit connaître le `response_format`/`stream_format` demandé pour rendre le bon Content-Type. *Observé :* le TTS fait du chunked (TTFB 0,5–2,7 s) : bufferiser toute la réponse dégrade la latence perçue ; et le WAV renvoyé (TTS **et** chat) a un **en-tête « streaming » (tailles `0xFFFFFFFF`)** → toute durée/validation doit se calculer sur les octets.
3. **Limites de taille.** Base64 = +33 %. OpenAI a accepté **26 MiB d'audio et 22 Mo d'image** malgré les 25 Mo / 20 Mo documentés : les bornes réelles ne sont pas connues, donc **nos propres limites sont un choix produit à poser**, pas une copie de la doc. À recenser composant par composant (reverse proxy, API gateway, file entre gateway et worker). Les payloads de test existent (`--heavy`).
4. **Image par URL ⇒ qui télécharge ?** Chez OpenAI, le provider (http et https acceptés ; erreurs `invalid_image_url` avec le code HTTP amont). Si un provider cible n'accepte que des octets (hypothèse à vérifier pour Bedrock), la gateway/le worker devra télécharger : **SSRF** (schémas `file:`, IP internes/metadata), taille max, timeout, allow-list. Les cas `url_file_scheme` / `url_internal_ip` (tag `security`) servent à vérifier que **notre** gateway les refuse — *à ne pas lancer contre un provider tiers*. Autre point : OpenAI **détecte le format sur le contenu** et ignore le MIME déclaré ; ne valider que le MIME serait plus laxiste ou plus strict qu'eux selon les cas.
5. **L'audio de sortie en chat est un état côté provider.** `assistant.audio.id` (valide ≈ 1 h) référence l'audio du tour précédent ; **il est re-facturé en tokens d'entrée à chaque tour** (98 tokens audio re-comptés au tour 2). Les autres providers n'ont pas cet état : via la gateway, soit on rejette ce champ, soit on le remplace par le `transcript` (**le repli par transcript fonctionne** chez OpenAI, mais `gpt-audio` exige de l'audio en entrée *ou* en sortie à chaque appel).
6. **Le streaming audio de chat n'est pas du SSE chat classique.** Pas de `finish_reason` ; un chunk **sans clé `choices`** ; le chunk `usage` n'est **pas le dernier** (un chunk `expires_at` le suit) ; chaque chunk porte `usage:null` et `obfuscation`. Un forwarder SSE qui suppose `choices[0]` ou « usage = dernier chunk » casse. Idem le SSE de transcription (`transcript.text.delta/done`) et de TTS (`speech.audio.delta/done`) : trois dialectes SSE, tous terminés par `data: [DONE]`.
7. **Comptabilisation des quotas hétérogène (confirmé).** Chat : `usage.prompt_tokens_details.audio_tokens` / `completion_tokens_details.audio_tokens`. Transcription : **`whisper-1` → `{"type":"duration","seconds":8}`**, **`gpt-4o-*` → `{"type":"tokens",…}`**. TTS : binaire **sans `usage`** (présent uniquement dans l'événement `done` en SSE) → caractères/durée à calculer nous-mêmes. Image : tokens très variables (`detail=low` 2 855 contre 8 522 ; 6000×4000 → 36 848 ; 12 images → 102 020) : le contrôle de quotas doit se baser sur l'`usage` renvoyé, pas sur une estimation.
8. **Matrice de capacités par modèle.** Les modèles de vision ou d'audio ne remplacent pas les modèles texte (`gpt-audio` refuse un appel sans audio). Côté erreurs, OpenAI n'est pas fiable pour décider à notre place : image sur `gpt-3.5-turbo` → **500**, audio sur modèle texte/vision → 400 au libellé générique, `speech` avec un modèle de chat → **431 HTML**, `transcriptions` avec `tts-1` → 404 « Invalid URL ». La gateway doit donc **connaître les capacités de chaque modèle** (entrées/sorties, formats, limites) et produire elle-même des erreurs propres avant l'appel provider.
9. **Format d'erreur.** Cible : `{"error":{message,type,param,code}}`. Pièges observés à *ne pas* reproduire tels quels : `message` = `repr` Python de la validation (endpoints audio), `param` trompeur (`messages` pour une erreur de fichier audio), nom de modèle interne dans un message (`gpt-4o-transcribe-api-ev3`), réponse HTML. La table `param`/`code` complète est dans les captures `neg`.
10. **Validation stricte ou tolérante ?** OpenAI **ignore** les champs inconnus (`foo`), `instructions` sur `tts-1`, `logprobs` sur `whisper-1`, `stream` sur `whisper-1`, et **ne valide pas toutes les bornes** (`temperature=2`, `input` 4097 car., `voice` absent). À positionner : la gateway valide-t-elle plus strictement qu'OpenAI, ou laisse-t-elle passer ? (Sa réponse conditionne la compatibilité client.)

## 3. Questions encore ouvertes

| Question | Où regarder / comment trancher |
|---|---|
| Bornes réelles de taille (audio > 26 MiB, image > 22 Mo, nb d'images/message) | relancer `--heavy` avec des fichiers plus gros |
| Formats STT `m4a`, `mp4`, `webm`, `mpga`, `mpeg` | déposer `fixtures/sample.<ext>` puis `run -k 'input_'` |
| Comportement de **LiteLLM** sur chaque cas (formats, passthrough, SSE, erreurs) | `run --env-file .env.litellm --label litellm` puis `report --compare openai litellm` |
| Refus SSRF de la future gateway (`file://`, `169.254.169.254`) | `run --security -k security` **sur la gateway uniquement**, une fois ses endpoints exposés (non sondable avant) |
| **Bedrock** : limites réelles (3,75 Mo ? 8000 px ? 20 images ?), formats effectivement acceptés, comportement de Voxtral en transcription, erreurs `ValidationException` | `bedrock-models` puis `run --env-file .env.bedrock` (voir [bedrock-mapping.md](bedrock-mapping.md)) |
| TTS / audio en sortie sur Bedrock : confirmer l'absence de chemin boto3 | `speech/nova_sonic_*`, `chat-audio/nova_sonic_converse` |
| Variabilité entre modèles/versions (`gpt-audio-mini`, `gpt-audio-1.5`, `gpt-transcribe`, `gpt-live-transcribe` listés par `/v1/models`) | `MM_MODEL_*` puis relance partielle |

### Ce que la doc AWS laisse déjà prévoir pour Bedrock (à confirmer par les sondes)

- **Image** : Converse n'accepte pas d'URL (octets ou `s3Location`) → le worker télécharge (SSRF, §2.4) ; plafonds annoncés 3,75 Mo / 8000 px / 20 images par message, **bien en dessous de ce qu'OpenAI a accepté** (22 Mo, 8200 px, ≥ 12 images) → recompression/redimensionnement ou refus à décider.
- **Audio en entrée** : seulement via les modèles à modalité SPEECH (Voxtral) ; pas d'endpoint de transcription ; `verbose_json`/`srt`/`vtt`/timestamps/diarisation sans équivalent.
- **TTS et audio en sortie** : aucun chemin avec boto3 (Nova Sonic = flux bidirectionnel uniquement). Le périmètre faisable côté Bedrock se réduit donc à *image en entrée* et *audio en entrée*.

## 4. Protocole pour les cibles suivantes

```bash
uv run python -m mmprobe --env-file .env.litellm --label litellm run
uv run python -m mmprobe --env-file .env.bedrock bedrock-models      # ids de modèles disponibles → .env.bedrock
uv run python -m mmprobe --env-file .env.bedrock run                  # sondes boto3, label bedrock-<région>
uv run python -m mmprobe report --compare openai litellm bedrock-eu-west-3   # captures/COMPARE_*.md
```
Les alias de modèles se règlent via `MM_MODEL_*` (HTTP) ou `MM_BEDROCK_MODEL_*` (Bedrock, aucun défaut) dans le `.env` de la cible. La gateway elle-même n'est pas sondée (ses endpoints sont ce qu'on cadre). Lire en priorité les lignes `**DIFF**` du COMPARE : ce sont les endroits où la cible ne se comporte pas comme OpenAI sur la classe de statut.

## 5. Hors périmètre de cette étape

- `/audio/translations`, voix personnalisées, Realtime API, Responses API (`input_image`, `input_audio` y portent d'autres noms).
- Input `file` (déjà géré) combiné à image/audio.
- Qualité des réponses (OCR, transcription) : les cas la capturent mais ne la notent pas.
- Non-déterminisme : le texte des réponses de modèle change d'un run à l'autre ; ne pas s'en servir comme oracle de non-régression.
