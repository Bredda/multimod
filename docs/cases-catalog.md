# Catalogue des cas de test

_Généré par `python -m mmprobe catalog` — ne pas éditer à la main._

317 cas. « Attente » = ce que la doc laisse prévoir (`2xx`, `4xx`, `any` = indéterminé / à découvrir). Tags : `heavy` = gros payloads (opt-in `--heavy`), `security` = SSRF (opt-in, ta gateway uniquement), `probe` = paramètre récent/non documenté dans la spec publique, `neg` = cas négatif. Un même id (`chat-image/multi_images`) dans les deux cibles = même scénario, comparable avec `report --compare`.

# Cible HTTP — OpenAI / LiteLLM (HTTP brut, sans SDK) — 218 cas

## POST /audio/speech

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `default` | 2xx |  | Appel minimal (model, input, voice) : format par défaut attendu = mp3 |
| `legacy_tts1` | 2xx |  | Modèle historique tts-1 |
| `format_mp3` | 2xx | format | response_format=mp3 : content-type, conteneur réel et taille du binaire renvoyé |
| `format_opus` | 2xx | format | response_format=opus : content-type, conteneur réel et taille du binaire renvoyé |
| `format_aac` | 2xx | format | response_format=aac : content-type, conteneur réel et taille du binaire renvoyé |
| `format_flac` | 2xx | format | response_format=flac : content-type, conteneur réel et taille du binaire renvoyé |
| `format_wav` | 2xx | format | response_format=wav : content-type, conteneur réel et taille du binaire renvoyé |
| `format_pcm` | 2xx | format | response_format=pcm : content-type, conteneur réel et taille du binaire renvoyé |
| `voice_alloy` | 2xx | voice | Voix intégrée `alloy` |
| `voice_ash` | 2xx | voice | Voix intégrée `ash` |
| `voice_ballad` | any | voice | Voix intégrée `ballad` — absente de tts-1 selon les modèles |
| `voice_coral` | 2xx | voice | Voix intégrée `coral` |
| `voice_echo` | 2xx | voice | Voix intégrée `echo` |
| `voice_fable` | 2xx | voice | Voix intégrée `fable` |
| `voice_onyx` | 2xx | voice | Voix intégrée `onyx` |
| `voice_nova` | 2xx | voice | Voix intégrée `nova` |
| `voice_sage` | 2xx | voice | Voix intégrée `sage` |
| `voice_shimmer` | 2xx | voice | Voix intégrée `shimmer` |
| `voice_verse` | any | voice | Voix intégrée `verse` — absente de tts-1 selon les modèles |
| `voice_custom_object` | 4xx | neg, probe | Voix custom sous forme d'objet {"id": ...} (voix personnalisées OpenAI) |
| `voice_unknown` | 4xx | neg | Voix inconnue |
| `speed_min` | 2xx | params | speed=0.25 (borne basse) |
| `speed_max` | 2xx | params | speed=4.0 (borne haute) |
| `speed_too_low` | 4xx | neg, params | speed=0.1 (< min) |
| `speed_too_high` | 4xx | neg, params | speed=5 (> max) |
| `speed_string` | 4xx | neg, params | speed="fast" (mauvais type) |
| `instructions` | 2xx | params | instructions sur gpt-4o-mini-tts |
| `instructions_tts1` | any | params | instructions sur tts-1 (doc : sans effet) — ignoré ou rejeté ? |
| `stream_format_sse` | 2xx | stream, probe | stream_format=sse : événements speech.audio.delta/done au lieu d'un binaire |
| `stream_format_audio` | 2xx | stream, probe | stream_format=audio (défaut explicite) |
| `stream_format_invalid` | 4xx | neg, stream, probe | stream_format invalide |
| `stream_format_sse_tts1` | any | stream, probe | stream_format=sse sur tts-1 (non supporté d'après la doc) |
| `input_french` | 2xx |  | Texte français accentué |
| `input_unicode_emoji` | any |  | Unicode + emoji + caractères non latins |
| `input_4096` | 2xx | long | input = 4096 caractères exactement (limite) |
| `input_4097` | 4xx | neg, long | input = 4097 caractères (> limite) |
| `input_empty` | 4xx | neg | input vide |
| `input_whitespace` | any | neg | input = espaces seulement |
| `input_not_string` | 4xx | neg | input = liste de chaînes |
| `missing_model` | 4xx | neg | model absent |
| `missing_voice` | 4xx | neg | voice absent |
| `missing_input` | 4xx | neg | input absent |
| `model_unknown` | 4xx | neg | model inexistant |
| `model_wrong_type` | 4xx | neg | model d'un autre type (chat) sur /audio/speech |
| `format_invalid` | 4xx | neg | response_format=ogg (hors liste) |
| `format_uppercase` | any | neg | response_format=MP3 (casse) |
| `unknown_param` | any | neg | paramètre inconnu `foo` : le schéma est additionalProperties=false — rejet ou ignoré ? |
| `content_type_urlencoded` | 4xx | neg, transport | Corps application/x-www-form-urlencoded au lieu de JSON |
| `content_type_multipart` | 4xx | neg, transport | Corps multipart/form-data au lieu de JSON |
| `malformed_json` | 4xx | neg, transport | JSON invalide |
| `auth_invalid` | 4xx | neg, auth | Clé API invalide |
| `auth_missing` | 4xx | neg, auth | Pas de header Authorization |

## POST /audio/transcriptions

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `model_whisper` | 2xx |  | whisper-1, format json par défaut |
| `model_4o_transcribe` | 2xx |  | gpt-4o-transcribe, format json par défaut |
| `model_4o_mini_transcribe` | 2xx |  | gpt-4o-mini-transcribe |
| `input_mp3` | 2xx | input-format | Fichier d'entrée mp3 |
| `input_wav` | 2xx | input-format | Fichier d'entrée wav |
| `input_flac` | 2xx | input-format | Fichier d'entrée flac |
| `input_ogg` | 2xx | input-format | Fichier d'entrée ogg — Ogg/Opus produit par response_format=opus |
| `input_opus` | any | input-format | Fichier d'entrée opus — extension .opus : listée ou non ? |
| `input_aac` | any | input-format | Fichier d'entrée aac — AAC ADTS brut : extension .aac absente de la liste doc |
| `input_wav_from_pcm` | 2xx | input-format | Fichier d'entrée wav_from_pcm — PCM 24 kHz s16le mono reconditionné en WAV |
| `input_m4a` | 2xx | input-format, user-fixture | Fichier d'entrée m4a (à fournir : fixtures/sample.m4a) |
| `input_mp4` | 2xx | input-format, user-fixture | Fichier d'entrée mp4 (à fournir : fixtures/sample.mp4) |
| `input_webm` | 2xx | input-format, user-fixture | Fichier d'entrée webm (à fournir : fixtures/sample.webm) |
| `input_mpga` | 2xx | input-format, user-fixture | Fichier d'entrée mpga (à fournir : fixtures/sample.mpga) |
| `input_mpeg` | 2xx | input-format, user-fixture | Fichier d'entrée mpeg (à fournir : fixtures/sample.mpeg) |
| `input_fr` | 2xx |  | Audio français sans `language` (détection auto) |
| `input_tone_no_speech` | any |  | Son sans parole (sinus 440 Hz) : texte vide ou hallucination ? |
| `input_silence` | any |  | Silence 3 s |
| `fmt_json_whisper` | 2xx | response_format | response_format=json sur whisper-1 |
| `fmt_text_whisper` | 2xx | response_format | response_format=text sur whisper-1 |
| `fmt_srt_whisper` | 2xx | response_format | response_format=srt sur whisper-1 |
| `fmt_vtt_whisper` | 2xx | response_format | response_format=vtt sur whisper-1 |
| `fmt_verbose_json_whisper` | 2xx | response_format | response_format=verbose_json sur whisper-1 |
| `fmt_json_4o` | 2xx | response_format | response_format=json sur gpt-4o-transcribe (doc : json seulement) |
| `fmt_text_4o` | any | response_format | response_format=text sur gpt-4o-transcribe (doc : json seulement) |
| `fmt_srt_4o` | 4xx | response_format | response_format=srt sur gpt-4o-transcribe (doc : json seulement) |
| `fmt_vtt_4o` | 4xx | response_format | response_format=vtt sur gpt-4o-transcribe (doc : json seulement) |
| `fmt_verbose_json_4o` | 4xx | response_format | response_format=verbose_json sur gpt-4o-transcribe (doc : json seulement) |
| `fmt_diarized_json` | any | response_format, probe | diarized_json sur le modèle diarize (segments par locuteur) |
| `fmt_invalid` | 4xx | neg, response_format | response_format invalide |
| `ts_segment` | 2xx | timestamps | verbose_json + timestamp_granularities[]=segment |
| `ts_word` | 2xx | timestamps | verbose_json + timestamp_granularities[]=word |
| `ts_word_and_segment` | 2xx | timestamps | verbose_json + word ET segment (clé répétée) |
| `ts_without_verbose` | any | timestamps, neg | timestamp_granularities sans verbose_json (doc : requis) — rejet ou ignoré ? |
| `ts_invalid` | 4xx | timestamps, neg | timestamp_granularities[]=sentence |
| `ts_4o` | any | timestamps | timestamp_granularities sur gpt-4o-transcribe |
| `language_en` | 2xx | params | language=en |
| `language_fr_on_fr` | 2xx | params | language=fr sur audio français |
| `language_wrong` | any | params | language=fr forcé sur audio anglais : traduit, transcrit en français phonétique, erreur ? |
| `language_invalid` | any | params, neg | language=english (pas un code ISO-639-1) |
| `prompt` | 2xx | params | prompt de guidage (vocabulaire) |
| `temperature_0_5` | 2xx | params | temperature=0.5 |
| `temperature_out_of_range` | 4xx | params, neg | temperature=2 (> 1) |
| `temperature_string` | 4xx | params, neg | temperature=hot |
| `logprobs_4o` | 2xx | params | include[]=logprobs (json, gpt-4o-transcribe) |
| `logprobs_whisper` | any | params | include[]=logprobs sur whisper-1 (non supporté) |
| `logprobs_text_format` | any | params | include[]=logprobs avec response_format=text (doc : json seulement) |
| `include_invalid` | 4xx | params, neg | include[]=foo |
| `chunking_auto` | any | params, probe | chunking_strategy=auto |
| `chunking_server_vad` | any | params, probe | chunking_strategy JSON {type: server_vad} |
| `stream_4o` | 2xx | stream | stream=true sur gpt-4o-transcribe : flux SSE transcript.text.delta/done |
| `stream_whisper` | any | stream | stream=true sur whisper-1 (doc : ignoré) — réponse JSON classique ? |
| `stream_text_format` | any | stream | stream=true avec response_format=text |
| `missing_file` | 4xx | neg | Pas de partie `file` |
| `missing_model` | 4xx | neg | Pas de champ `model` |
| `file_as_text_field` | 4xx | neg | `file` envoyé comme champ texte (pas une partie fichier) |
| `unsupported_ext_txt` | 4xx | neg, input-format | Fichier texte nommé notes.txt |
| `empty_file` | 4xx | neg, input-format | Fichier vide (0 octet) |
| `corrupt_mp3` | 4xx | neg, input-format | Octets aléatoires nommés .mp3 |
| `ext_mismatch` | any | neg, input-format | Contenu mp3 déclaré .wav : l'extension prime-t-elle sur le contenu ? |
| `no_extension` | any | neg, input-format | Nom de fichier sans extension |
| `content_type_octet_stream` | any | input-format | Partie fichier en application/octet-stream avec nom .mp3 |
| `model_unknown` | 4xx | neg | Modèle inexistant |
| `model_wrong_type` | 4xx | neg | Modèle TTS sur /audio/transcriptions |
| `json_body` | 4xx | neg, transport | Corps JSON au lieu de multipart (le fichier ne peut pas y être) |
| `auth_invalid` | 4xx | neg, auth | Clé API invalide |
| `too_large_26mb` | 4xx | neg, heavy | Fichier > 25 Mo (limite documentée) : code attendu 413 ou 400 |

## POST /chat/completions — content part `image_url`

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `url_https` | 2xx | source, network | Image par URL https publique (le fetch est fait côté provider) — nécessite que la cible puisse joindre l'URL |
| `data_url_png` | 2xx | source | Data URL base64 PNG — scène : carré rouge, cercle bleu, triangle vert sur fond gris clair |
| `data_url_jpg` | 2xx | source, format | Data URL JPG (même scène) |
| `data_url_webp` | 2xx | source, format | Data URL WEBP (même scène) |
| `data_url_gif` | 2xx | source, format | Data URL GIF (même scène) |
| `data_url_bmp` | 4xx | source, format, neg | Data URL BMP (hors liste png/jpeg/webp/gif) |
| `data_url_tiff` | 4xx | source, format, neg | Data URL TIFF (hors liste png/jpeg/webp/gif) |
| `data_url_svg` | 4xx | source, format, neg | Data URL SVG (non supporté) |
| `data_url_animated_gif` | any | source, format | GIF animé (doc : seuls les GIF non animés) |
| `data_url_wrong_mime` | any | source, format, neg | PNG déclaré image/jpeg dans le data URL : le MIME déclaré prime-t-il sur le contenu ? |
| `data_url_no_mime` | any | source, neg | data:;base64,... sans type MIME |
| `raw_base64_no_prefix` | any | source, neg | Base64 brut sans préfixe `data:` (le champ doc dit « URL or base64 ») |
| `detail_low` | 2xx | detail | detail=low : impact sur usage.prompt_tokens |
| `detail_high` | 2xx | detail | detail=high : impact sur usage.prompt_tokens |
| `detail_auto` | 2xx | detail | detail=auto : impact sur usage.prompt_tokens |
| `detail_ultra` | 4xx | detail, neg | detail=ultra (valeur invalide) : impact sur usage.prompt_tokens |
| `multi_images` | 2xx | compose | Deux images dans le même message + question comparative |
| `interleaved` | 2xx | compose | text, image, text, image : l'ordre des parts est-il préservé ? |
| `image_only` | any | compose | Message avec une seule image et AUCUNE part text |
| `text_as_string_plus_image_msg` | 2xx | compose | Historique mixte : message 1 en content string, message 2 en parts avec image |
| `history_image_then_text` | 2xx | compose | Image dans un tour précédent, question de suivi en texte seul (l'image reste-t-elle dans le contexte ?) |
| `system_prompt_plus_image` | 2xx | compose | Message system texte + user image |
| `developer_role_plus_image` | any | compose | Rôle `developer` (nouveau) + user image |
| `ocr_text` | 2xx | quality | OCR : image contenant « HELLO 42 » |
| `image_in_system` | 4xx | neg, placement | Part image dans un message system (doc : texte seulement) |
| `image_in_assistant` | 4xx | neg, placement | Part image dans un message assistant (doc : text/refusal seulement) |
| `image_in_tool_result` | 4xx | neg, placement, tools | Part image dans un message role=tool (résultat de fonction) |
| `model_without_vision` | any | neg, model | Image envoyée à un modèle texte-seul : erreur explicite ou image ignorée en silence ? |
| `stream` | 2xx | stream | stream=true + stream_options.include_usage avec image |
| `structured_output` | 2xx | compose | response_format json_schema + image (extraction structurée) |
| `tool_call_with_image` | 2xx | compose, tools | Function calling déclenché depuis une image |
| `url_unreachable` | 4xx | neg, source, network | URL qui ne résout pas (host .invalid) |
| `url_not_an_image` | 4xx | neg, source, network | URL valide mais contenu text/html |
| `url_http_plain` | any | neg, source, network | URL http:// non TLS |
| `url_file_scheme` | 4xx | neg, source, security | URL file:///etc/hostname (SSRF / schéma local) — doit être refusée |
| `url_internal_ip` | 4xx | neg, source, security | URL vers 169.254.169.254 (metadata cloud) — doit être refusée/injoignable |
| `url_empty` | 4xx | neg | image_url.url = chaîne vide |
| `base64_corrupt` | 4xx | neg | Data URL avec base64 tronqué/corrompu |
| `not_an_image_bytes` | 4xx | neg | Data URL image/png dont le contenu est du HTML |
| `image_url_as_string` | 4xx | neg, schema | image_url donné comme chaîne au lieu d'un objet {url} (erreur client fréquente) |
| `missing_image_url` | 4xx | neg, schema | Part {type: image_url} sans clé image_url |
| `unknown_part_type` | 4xx | neg, schema | Part de type inconnu (`image`) |
| `tiny_1x1` | any | limits | Image 1×1 px |
| `large_6000x4000` | any | limits | Image 6000×4000 px (PNG uni, peu d'octets) : redimensionnement côté provider ? |
| `huge_8200x8200` | any | limits | Image 8200×8200 px (> 8000 px, limite de certains providers) |
| `too_large_22mb` | 4xx | neg, limits, heavy | Image ≈ 22 Mo (doc : max 20 Mo par image) |
| `many_images_12` | any | limits | 12 images dans un seul message (pas de limite documentée à ce niveau côté OpenAI ; certains providers limitent à ~20) |
| `auth_invalid` | 4xx | neg, auth | Clé API invalide |

## POST /chat/completions — content part `input_audio` & sortie audio

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `in_wav_text_out` | 2xx | audio-in | input_audio wav + consigne texte, modalities=[text] |
| `in_mp3_text_out` | 2xx | audio-in | input_audio mp3 |
| `in_wav_no_modalities` | 2xx | audio-in | input_audio sans `modalities` (défaut = [text]) |
| `in_audio_only` | any | audio-in | input_audio sans aucune part text (le modèle répond à l'audio) |
| `in_french` | 2xx | audio-in | Audio français |
| `in_tone_no_speech` | any | audio-in | Audio sans parole (sinus) |
| `in_two_audios` | any | audio-in, compose | Deux input_audio dans le même message (wav + mp3) |
| `in_text_interleaved` | 2xx | audio-in, compose | text, audio, text |
| `in_stream_text_out` | 2xx | audio-in, stream | input_audio + stream=true + include_usage (sortie texte) |
| `in_tool_call` | any | audio-in, tools | input_audio + tools (tool_choice=required) |
| `in_format_flac` | 4xx | audio-in, neg, format | input_audio.format=flac (enum doc : wav, mp3) |
| `in_format_pcm16` | 4xx | audio-in, neg, format | input_audio.format=pcm16 avec PCM brut |
| `in_format_uppercase` | any | audio-in, neg, format | format=WAV (casse) |
| `in_format_mismatch` | any | audio-in, neg, format | Contenu mp3 déclaré format=wav : le format déclaré prime-t-il ? |
| `in_format_missing` | 4xx | audio-in, neg, schema | input_audio sans `format` |
| `in_data_as_data_url` | 4xx | audio-in, neg, schema | input_audio.data = data URL (confusion fréquente avec image_url) |
| `in_data_corrupt_base64` | 4xx | audio-in, neg | input_audio.data = base64 invalide |
| `in_data_not_audio` | 4xx | audio-in, neg | input_audio.data = base64 d'un fichier texte |
| `in_data_empty` | 4xx | audio-in, neg | input_audio.data = chaîne vide |
| `in_audio_as_string` | 4xx | audio-in, neg, schema | input_audio donné comme chaîne au lieu d'un objet |
| `in_audio_in_system` | 4xx | audio-in, neg, placement | input_audio dans un message system |
| `in_audio_in_assistant` | 4xx | audio-in, neg, placement | input_audio dans un message assistant |
| `in_audio_on_text_model` | 4xx | audio-in, neg, model | input_audio envoyé à un modèle texte-seul |
| `in_audio_on_vision_model` | 4xx | audio-in, neg, model | input_audio envoyé à un modèle vision (non audio) |
| `out_text_prompt_wav` | 2xx | audio-out | Prompt texte seul -> réponse texte + audio wav (chat comme TTS) |
| `out_format_mp3` | 2xx | audio-out, format | audio.format=mp3 (non-stream) : conteneur réel de message.audio.data |
| `out_format_flac` | 2xx | audio-out, format | audio.format=flac (non-stream) : conteneur réel de message.audio.data |
| `out_format_opus` | 2xx | audio-out, format | audio.format=opus (non-stream) : conteneur réel de message.audio.data |
| `out_format_pcm16` | 2xx | audio-out, format | audio.format=pcm16 (non-stream) : conteneur réel de message.audio.data |
| `out_format_aac` | any | audio-out, format | audio.format=aac (non-stream) : conteneur réel de message.audio.data — aac figure dans l'enum de la spec OpenAPI mais pas dans la description |
| `out_voice_verse` | any | audio-out, voice | audio.voice=verse |
| `out_voice_coral` | any | audio-out, voice | audio.voice=coral |
| `out_voice_marin` | any | audio-out, voice | audio.voice=marin |
| `out_voice_cedar` | any | audio-out, voice | audio.voice=cedar |
| `in_wav_audio_out` | 2xx | audio-in, audio-out | input_audio + sortie audio : conversation vocale complète (usage audio_tokens in/out) |
| `in_mp3_audio_out_mp3` | 2xx | audio-in, audio-out | input_audio mp3 -> sortie audio mp3 |
| `out_modalities_audio_only` | any | audio-out | modalities=[audio] seul (la doc le mentionne ; le modèle exige souvent [text, audio]) |
| `out_modalities_with_text_model` | 4xx | audio-out, neg, model | modalities=[text,audio] sur modèle texte-seul |
| `out_missing_audio_param` | 4xx | audio-out, neg | modalities contient audio mais pas de paramètre `audio` |
| `out_audio_param_without_modality` | any | audio-out, neg | paramètre `audio` fourni mais modalities=[text] |
| `out_voice_invalid` | 4xx | audio-out, neg | audio.voice inconnue |
| `out_format_invalid` | 4xx | audio-out, neg | audio.format=ogg |
| `out_modalities_invalid` | 4xx | audio-out, neg | modalities=[video] |
| `out_stream_pcm16` | 2xx | audio-out, stream | Streaming audio : delta.audio {id, data, transcript} en pcm16 |
| `out_stream_wav` | 4xx | audio-out, stream, neg | Streaming audio avec format=wav (doc : pcm16 requis en streaming) |
| `out_n2` | any | audio-out, neg | n=2 avec sortie audio |
| `multi_turn_audio_id` | 2xx | multi-turn, audio-out | Tour 2 : on référence la réponse audio précédente par assistant.audio.id (pas de ré-upload) |
| `multi_turn_audio_id_text_fallback` | 2xx | multi-turn, audio-out | Tour 2 : assistant référencé par son transcript texte (pas d'id audio) |
| `multi_turn_audio_id_unknown` | 4xx | multi-turn, neg | assistant.audio.id inexistant |
| `multi_turn_input_audio_then_text` | 2xx | multi-turn, audio-in | Tour 1 : audio utilisateur ; tour 2 : question texte de suivi (l'audio reste-t-il en contexte ?) |
| `auth_invalid` | 4xx | neg, auth | Clé API invalide |

# Cible Bedrock — boto3 / bedrock-runtime — 99 cas

## Images — Converse / ConverseStream / InvokeModel

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `bytes_png` | 2xx | source, format | Image PNG en octets (format déclaré 'png') |
| `bytes_jpg` | 2xx | source, format | Image JPG en octets (format déclaré 'jpeg') |
| `bytes_webp` | 2xx | source, format | Image WEBP en octets (format déclaré 'webp') |
| `bytes_gif` | 2xx | source, format | Image GIF en octets (format déclaré 'gif') |
| `declared_png_actual_bmp` | 4xx | source, format, neg | Octets BMP déclarés 'png' (formats hors liste png/jpeg/gif/webp) |
| `declared_png_actual_tiff` | 4xx | source, format, neg | Octets TIFF déclarés 'png' (formats hors liste png/jpeg/gif/webp) |
| `declared_png_actual_svg` | 4xx | source, format, neg | Octets SVG déclarés 'png' (formats hors liste png/jpeg/gif/webp) |
| `declared_jpeg_actual_png` | any | source, format, neg | PNG déclaré 'jpeg' : le format déclaré prime-t-il sur le contenu ? |
| `declared_png_actual_jpeg` | any | source, format, neg | JPEG déclaré 'png' |
| `format_invalid_value` | 4xx | source, format, neg | format='bmp' (hors enum ImageFormat) : rejet botocore ou serveur ? |
| `animated_gif` | any | source, format | GIF animé : accepté ? quelles images sont vues ? |
| `not_an_image_bytes` | 4xx | source, neg | Octets HTML déclarés 'png' |
| `empty_bytes` | 4xx | source, neg | Image de 0 octet |
| `corrupt_bytes` | 4xx | source, neg | PNG tronqué (octets de tête valides, reste corrompu) |
| `s3_location_unreachable` | 4xx | source, neg | source s3Location vers un bucket inexistant (voie alternative aux octets pour les gros fichiers) |
| `png_vision_nova` | 2xx | model-family | PNG sur le rôle 'vision_nova' (autre famille de modèles : comportements/limites différents ?) |
| `png_vision_other` | 2xx | model-family | PNG sur le rôle 'vision_other' (autre famille de modèles : comportements/limites différents ?) |
| `multi_images` | 2xx | compose | Deux images + question comparative |
| `interleaved` | 2xx | compose | text, image, text, image : l'ordre est-il préservé ? |
| `image_only` | any | compose | Une image, aucun bloc texte (OpenAI l'accepte) |
| `system_prompt_plus_image` | 2xx | compose | system=[{text}] + user image |
| `history_image_then_text` | 2xx | compose | Image au tour 1, question texte au tour 3 (l'image reste-t-elle en contexte ?) |
| `ocr_text` | 2xx | quality | OCR : image « HELLO 42 » |
| `image_in_assistant` | 4xx | neg, placement | Bloc image dans un message assistant (doc : images réservées au rôle user) |
| `first_message_assistant` | 4xx | neg, placement | Premier message de rôle assistant (Converse impose user en premier) |
| `image_in_tool_result` | any | placement, tools | Image dans un toolResult (OpenAI : refusé pour role=tool) |
| `size_3_60mb` | 2xx | limits | Image de 3,60 Mo (sous 3,75 Mo) |
| `size_3_85mb` | any | limits | Image de 3,85 Mo (entre 3,75 Mo décimal et 3,75 MiB = 3,93 Mo : quelle unité ?) |
| `size_4_10mb` | 4xx | limits, neg | Image de 4,10 Mo (au-dessus de 3,75 MiB) |
| `tiny_1x1` | any | limits | Image 1×1 px (certains modèles imposent un minimum) |
| `large_6000x4000` | any | limits | 6000×4000 px (sous 8000 px) |
| `huge_8200x8200` | 4xx | limits, neg | 8200×8200 px (> 8000 px) |
| `images_20` | any | limits | 20 images dans un message (limite documentée) |
| `images_21` | 4xx | limits, neg | 21 images (> limite documentée) |
| `model_without_vision` | any | neg, model | Image envoyée à un modèle texte-seul : erreur explicite ? |
| `too_large_22mb` | 4xx | neg, limits, heavy | Image ≈ 22 Mo (bien au-delà de 3,75 Mo ; limite de taille de requête Converse) |
| `stream` | 2xx | stream | ConverseStream avec image : types d'événements, usage dans l'événement metadata |
| `tool_call_with_image` | 2xx | compose, tools | toolConfig (toolChoice=any) déclenché depuis une image |
| `structured_output_via_tool` | 2xx | compose, tools | Extraction structurée = outil forcé (équivalent de response_format json_schema d'OpenAI) |
| `count_tokens_image` | any | quota | CountTokens (Converse) avec image : estimer le coût avant l'appel (quotas) |
| `invoke_claude_native_base64` | 2xx | invoke | InvokeModel format natif Anthropic (source base64) |
| `invoke_claude_native_url` | any | invoke, source | InvokeModel format natif Anthropic avec source {type:url} (l'API Anthropic directe le permet ; Bedrock ?) |
| `invoke_nova_native` | 2xx | invoke | InvokeModel format natif Nova (messages-v1, image en base64) |
| `auth_invalid` | 4xx | neg, auth | Identifiants AWS invalides |

## Transcription — Converse + AudioBlock (pas d'endpoint dédié)

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `model_small` | 2xx |  | Transcription WAV (rôle audio_in, ex. Voxtral Small) |
| `model_mini` | 2xx |  | Transcription WAV (rôle audio_in_mini, ex. Voxtral Mini) |
| `input_mp3` | 2xx | input-format | Fichier d'entrée mp3 |
| `input_wav` | 2xx | input-format | Fichier d'entrée wav — en-tête WAV correct |
| `input_flac` | 2xx | input-format | Fichier d'entrée flac |
| `input_ogg` | 2xx | input-format | Fichier d'entrée ogg — Ogg/Opus |
| `input_opus` | any | input-format | Fichier d'entrée opus — déclaré 'opus' (octets Ogg/Opus) |
| `input_aac` | any | input-format | Fichier d'entrée aac — AAC ADTS brut |
| `input_pcm` | any | input-format | Fichier d'entrée pcm — PCM brut 24 kHz s16le mono, déclaré 'pcm' |
| `input_wav_streaming_header` | any | input-format | Fichier d'entrée wav_streaming_header — WAV tel que renvoyé par OpenAI : tailles d'en-tête = 0xFFFFFFFF |
| `input_wav_stereo` | any | input-format | Fichier d'entrée wav_stereo — stéréo (certains modèles : mono seulement) |
| `input_wav_12khz` | any | input-format | Fichier d'entrée wav_12khz — échantillonnage 12 kHz |
| `input_m4a` | any | input-format, user-fixture | Fichier d'entrée m4a (à fournir : fixtures/sample.m4a) |
| `input_mp4` | any | input-format, user-fixture | Fichier d'entrée mp4 (à fournir : fixtures/sample.mp4) |
| `input_webm` | any | input-format, user-fixture | Fichier d'entrée webm (à fournir : fixtures/sample.webm) |
| `input_mpga` | any | input-format, user-fixture | Fichier d'entrée mpga (à fournir : fixtures/sample.mpga) |
| `input_mpeg` | any | input-format, user-fixture | Fichier d'entrée mpeg (à fournir : fixtures/sample.mpeg) |
| `input_fr` | 2xx |  | Audio français, sans indication de langue |
| `input_tone_no_speech` | any |  | Sinus sans parole : texte vide, refus ou hallucination ? |
| `input_silence` | any |  | Silence 3 s |
| `size_1_5mb` | any | limits | WAV de silence ≈ 1,5 Mo : où se situe la limite de taille d'entrée ? |
| `size_2_5mb` | any | limits | WAV de silence ≈ 2,5 Mo : où se situe la limite de taille d'entrée ? |
| `size_10mb` | any | limits | WAV de silence ≈ 10 Mo : où se situe la limite de taille d'entrée ? |
| `size_26mb` | 4xx | limits, neg, heavy | WAV de 26 Mo (équivalent du cas OpenAI too_large_26mb) |
| `prompt_language_hint` | 2xx |  | Indication de langue dans le prompt (équivalent de `language`) |
| `prompt_srt` | any | response_format | Demander des sous-titres SRT horodatés (équivalent de response_format=srt) |
| `prompt_json` | any | response_format | Demander {"text": ...} en JSON (équivalent de response_format=json) |
| `prompt_diarize` | any | response_format | Demander les locuteurs (équivalent diarized_json) |
| `stream` | 2xx | stream | ConverseStream sur une transcription (équivalent stream=true) |
| `input_empty` | 4xx | neg | AudioBlock de 0 octet |
| `input_corrupt_mp3` | 4xx | neg | Octets aléatoires déclarés 'mp3' |
| `input_text_file` | 4xx | neg | Fichier texte déclaré 'wav' |
| `ext_mismatch` | any | neg, input-format | MP3 déclaré 'wav' : le format déclaré prime-t-il ? |
| `format_invalid_value` | 4xx | neg, input-format | format='wmv' (hors enum AudioFormat) |
| `model_without_audio` | 4xx | neg, model | AudioBlock envoyé à un modèle sans modalité SPEECH (rôle vision) |
| `auth_invalid` | 4xx | neg, auth | Identifiants AWS invalides |

## Audio en entrée — Converse AudioBlock

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `in_wav_text_out` | 2xx | audio-in | AudioBlock wav + consigne texte |
| `in_mp3_text_out` | 2xx | audio-in | AudioBlock mp3 |
| `in_audio_only` | any | audio-in | AudioBlock sans bloc texte |
| `in_french` | 2xx | audio-in | Audio français |
| `in_two_audios` | any | audio-in, compose | Deux AudioBlock dans le même message |
| `in_text_interleaved` | 2xx | audio-in, compose | text, audio, text |
| `in_stream_text_out` | 2xx | audio-in, stream | ConverseStream avec audio en entrée |
| `in_history_audio_then_text` | 2xx | multi-turn, audio-in | Audio au tour 1, question texte au tour 3 (l'audio reste-t-il en contexte ?) |
| `in_format_mismatch` | any | audio-in, neg, format | MP3 déclaré 'wav' |
| `in_data_empty` | 4xx | audio-in, neg | AudioBlock de 0 octet |
| `in_data_not_audio` | 4xx | audio-in, neg | Fichier texte déclaré 'wav' |
| `in_audio_in_assistant` | 4xx | audio-in, neg, placement | AudioBlock dans un message assistant |
| `in_audio_on_text_model` | 4xx | audio-in, neg, model | AudioBlock envoyé à un modèle texte-seul |
| `in_audio_on_vision_model` | 4xx | audio-in, neg, model | AudioBlock envoyé à un modèle vision (sans SPEECH) |
| `in_tool_call` | any | audio-in, tools | AudioBlock + toolConfig (toolChoice=any) |
| `auth_invalid` | 4xx | neg, auth | Identifiants AWS invalides |
| `nova_sonic_converse` | 4xx | audio-out, neg, model | Nova Sonic via Converse (sortie audio) : refus attendu, Sonic = flux bidirectionnel uniquement |

## Synthèse vocale / audio en sortie — ce qui existe sur bedrock-runtime

| cas | attente | tags | ce que ça teste |
|---|---|---|---|
| `nova_sonic_converse` | 4xx | neg, model | Synthèse vocale via Nova Sonic + Converse : refus attendu |
| `nova_sonic_invoke_model` | 4xx | neg, model | Nova Sonic via InvokeModel (non streaming) : refus attendu |
