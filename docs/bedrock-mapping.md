# Mapping OpenAI → Bedrock Runtime (boto3) — hypothèses de conception à valider par les sondes

> **Statut.** Rien de ce document n'a encore été observé en vrai : les sondes Bedrock (`--provider bedrock`) sont écrites et validées hors-ligne (paramètres vérifiés contre le modèle de service botocore, transport testé avec un faux client), **mais n'ont pas tourné contre AWS** (aucun identifiant AWS dans l'environnement de travail).
> Les lignes marquées **[AWS]** viennent de la documentation AWS (liens en bas) ; **[tiers]** = passerelle open source équivalente (stdapi.ai) citée comme *prior art* ; **[hyp]** = ma déduction. La colonne « vérifié par » donne le cas qui tranchera ; après le run, `captures/<label>/REPORT.md` fait foi.
> Rappel du contexte : la gateway reçoit du format OpenAI ; le worker transforme (templates Jinja2) puis appelle Bedrock avec **boto3** (Converse ou InvokeModel selon le modèle) ou LLMaaS/LiteLLM en HTTP.

## 1. Ce qui existe sur `bedrock-runtime` (et ce qui n'existe pas)

| Besoin OpenAI | Bedrock Runtime | |
|---|---|---|
| `image_url` dans le chat | `Converse` / `ConverseStream` : bloc `image` (`png jpeg gif webp`, source `bytes` ou `s3Location`) ; ou `InvokeModel` au format natif du modèle | [AWS] |
| `input_audio` dans le chat | bloc `audio` de Converse (`mp3 opus wav aac flac mp4 ogg mkv mka x-aac m4a mpeg mpga pcm webm`, source `bytes`/`s3Location`), **uniquement pour les modèles à modalité SPEECH** (ex. Voxtral Mini/Small) | [AWS] formats · [tiers] modèles |
| `/audio/transcriptions` | **pas d'endpoint dédié**. Émulable : bloc audio + prompt de transcription sur un modèle SPEECH. Amazon Transcribe est un **autre service** (hors bedrock-runtime) | [tiers] |
| `/audio/speech` (TTS) | **aucun modèle TTS sur bedrock-runtime**. Amazon Polly = autre service | [AWS] (pas de modèle listé) · [hyp] |
| sortie audio du chat (`modalities:["audio"]`) | uniquement Nova (2) Sonic, via `InvokeModelWithBidirectionalStream` (flux HTTP/2 bidirectionnel ; l'AWS indique que ni Converse ni InvokeModel ne conviennent, et que les clés API Bedrock ne fonctionnent pas pour ce mode) | [AWS] |
| boto3 et ce flux bidirectionnel | boto3 expose l'opération dans son modèle de service ; à ma connaissance botocore ne sait pas tenir ce flux (les exemples AWS utilisent le SDK `aws_sdk_bedrock_runtime`). **Non vérifié ici.** | [hyp] |

→ Conséquence directe : **côté Bedrock, le périmètre faisable avec boto3 est « image en entrée » et « audio en entrée (STT émulé) » ; TTS et audio en sortie n'ont pas de chemin boto3**. À confirmer avec les cas `speech/nova_sonic_*` et `chat-audio/nova_sonic_converse` (ils s'attendent à un refus).

## 2. Chat avec image : `image_url` → bloc `image` Converse

| OpenAI | Converse | Écart / décision à prendre | Vérifié par |
|---|---|---|---|
| `image_url.url = data:image/png;base64,…` | `image.source.bytes` (octets décodés) + `format` | décoder ; **déduire le format du contenu, pas du MIME** (OpenAI aussi ignore le MIME déclaré) | `bytes_*`, `declared_*` |
| `image_url.url = https://…` | **aucune source URL** (`bytes` ou `s3Location`) | le worker doit **télécharger** : SSRF, taille, timeout, allow-list ; ou refuser | `s3_location_unreachable`, `invoke_claude_native_url` |
| formats png/jpeg/webp/gif | `png jpeg gif webp` | identiques ; bmp/tiff/svg refusés des deux côtés ? | `declared_png_actual_*` |
| taille : OpenAI a accepté 22 Mo | **3,75 Mo par image** [AWS, à confirmer] | redimensionner/recompresser, ou 400 ? unité : 3,75 Mo ou MiB ? | `size_3_60mb`, `size_3_85mb`, `size_4_10mb`, `too_large_22mb` |
| dimensions : OpenAI a accepté 8200 px | **8000 px** [AWS, à confirmer] | idem | `huge_8200x8200`, `large_6000x4000` |
| nb d'images : OpenAI a accepté ≥ 12 | **20 par message** [AWS, à confirmer] | | `images_20`, `images_21`, `multi_images` |
| `detail: low/high/auto/original` | **aucun équivalent** [hyp] | ignorer (et le documenter) | — |
| image dans `system`/`assistant`/`tool` : OpenAI → 400 | `system` = texte seul ; images réservées au rôle `user` [AWS] ; image **dans un `toolResult` possible** | différence de comportement à décider | `image_in_assistant`, `image_in_tool_result` |
| `developer` / plusieurs `system` | `system: [{"text"}…]` | fusionner | `system_prompt_plus_image` |
| partie `image_url` seule, sans texte | ? | OpenAI l'accepte | `image_only` |
| `response_format: json_schema` | outil forcé (`toolChoice: {tool}`) ou sortie structurée native selon modèle [hyp] | | `structured_output_via_tool` |
| `tools` + `tool_choice:"required"` | `toolConfig` + `toolChoice: {any:{}}` | | `tool_call_with_image` |
| `stream: true` | `ConverseStream` : événements `messageStart / contentBlockDelta / messageStop / metadata` (usage dans `metadata`) | **à retraduire** en chunks `chat.completion.chunk` ; pas de `[DONE]` natif | `stream` |
| `max_completion_tokens` | `inferenceConfig.maxTokens` | | tous |
| `usage.prompt/completion_tokens` | `usage.inputTokens / outputTokens` | mapping direct ; estimation préalable possible via `CountTokens` | `count_tokens_image` |
| `finish_reason` | `stopReason` : `end_turn→stop`, `max_tokens→length`, `tool_use→tool_calls`, `content_filtered`/`guardrail_intervened→content_filter` [AWS/hyp] | | tous |
| modèle sans vision → OpenAI : 500 (!) | `ValidationException` attendue | gating par capacités du modèle côté gateway | `model_without_vision` |
| erreurs | `ClientError` boto3 : `Error.Code` (`ValidationException`, `ThrottlingException`, `AccessDeniedException`, `ModelErrorException`…), statut HTTP | table de traduction vers `{error:{message,type,param,code}}` | cas `neg` |
| InvokeModel natif | Anthropic : `anthropic_version` + `content[].source.base64` ; Nova : `messages-v1` + `image.source.bytes` en base64 | 2 templates distincts de plus | `invoke_claude_native_*`, `invoke_nova_native` |

## 3. Audio en entrée : `input_audio` / `/audio/transcriptions` → bloc `audio` Converse

| OpenAI | Converse | Écart / décision à prendre | Vérifié par |
|---|---|---|---|
| `input_audio {data(b64), format: wav\|mp3}` | `audio {format, source.bytes}` | décoder ; **le modèle doit avoir la modalité SPEECH** → gating | `chat-audio/in_*` |
| formats d'entrée : OpenAI chat = wav/mp3 ; STT = flac mp3 mp4 mpeg mpga m4a ogg wav webm | liste AudioBlock plus large (`opus aac flac ogg pcm …`) | l'API Bedrock est **plus permissive** que le chat OpenAI, mais le support effectif dépend du modèle | `transcriptions/input_*` |
| fichier multipart `file` (nom + octets) | octets + `format` | OpenAI déduit le type de l'**extension du nom** ; Bedrock demande un `format` explicite → le déduire de l'extension/du contenu | `ext_mismatch`, `in_format_mismatch` |
| limites : OpenAI 25 Mo (≥ 26 MiB accepté) | ~2 Mo et mono pour Voxtral [tiers, à confirmer] | découpage (chunking) côté gateway, ou 413 | `size_1_5mb`, `size_2_5mb`, `size_10mb`, `input_wav_stereo` |
| `response_format` json/text | texte libre du modèle → à encapsuler en `{"text": …}` | | `prompt_json` |
| `verbose_json`, `srt`, `vtt`, `diarized_json`, `timestamp_granularities[]` | pas de paramètre ; au mieux demandé par prompt, sans garantie [tiers : non supportés hors Transcribe] | refuser (400) ou émuler ? | `prompt_srt`, `prompt_diarize` |
| `language`, `prompt` | à injecter dans le prompt de transcription | | `prompt_language_hint` |
| `include[]=logprobs` | n/a ([tiers] : renvoyer `null`) | | — |
| `stream=true` (SSE `transcript.text.delta/done`) | `ConverseStream` | retraduire les événements | `transcriptions/stream` |
| silence / bruit → OpenAI : texte halluciné | à mesurer | | `input_tone_no_speech`, `input_silence` |
| `usage` : tokens ou durée selon modèle (OpenAI) | `usage.inputTokens/outputTokens` du modèle | quotas à définir en tokens ou durée | tous |
| WAV avec en-tête « streaming » (0xFFFFFFFF) renvoyé par OpenAI | ? | un client qui rejoue une sortie OpenAI vers la gateway l'enverra tel quel | `input_wav_streaming_header` |

## 4. Ce qui n'a pas de chemin Bedrock/boto3 (à trancher côté produit)

- `/audio/speech` et la sortie audio du chat : pas de TTS sur bedrock-runtime. Options (hors périmètre boto3-seul) : un autre service AWS (Polly), un LLMaaS (LiteLLM → provider TTS), ou ne pas exposer l'endpoint pour les modèles Bedrock.
- Nova Sonic : seulement en flux bidirectionnel ; nécessiterait un autre SDK et un transport (WebSocket) que la gateway n'a pas aujourd'hui.

## 5. Sources

- [ImageBlock — API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html) · [Message — API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html) (limites 3,75 Mo / 8000 px / 20 images : relevées via un résumé de recherche, pas sur la page ouverte → **à confirmer**, c'est précisément ce que mesurent les cas `size_*`, `huge_*`, `images_*`).
- [AudioBlock — API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_AudioBlock.html) (lu : liste des formats, union `bytes`/`s3Location`).
- [Nova 2 Sonic — model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-sonic.html) · [API compatibility](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html) (Sonic : `InvokeModelWithBidirectionalStream` seul).
- [Models at a glance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html) (liste des modèles : Voxtral Mini 3B / Small 24B 2507, Nova 2 Lite/Sonic, Claude, Llama 4, Pixtral, Qwen3-VL…).
- [stdapi.ai — Speech to Text](https://stdapi.ai/api_openai_audio_transcriptions/) : passerelle OpenAI-compatible qui émule `/audio/transcriptions` avec Voxtral via Converse (limites ~2 Mo / mono, `json`/`text` seulement, pas de timestamps hors Transcribe).
