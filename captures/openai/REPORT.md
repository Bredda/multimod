# Rapport — `openai`

- cible : `https://api.openai.com/v1`  ·  généré : 2026-10-23T10:47:08+0200
- modèles : tts=`gpt-4o-mini-tts`, tts_legacy=`tts-1`, stt=`gpt-4o-transcribe`, stt_mini=`gpt-4o-mini-transcribe`, stt_whisper=`whisper-1`, stt_diarize=`gpt-4o-transcribe-diarize`, vision=`gpt-4o-mini`, text_only=`gpt-3.5-turbo`, audio_chat=`gpt-audio`
- spec de référence : **OpenAI API (spec OpenAPI officielle) v2.3.0** — branche `manual_spec` du dépôt [openai/openai-openapi](https://github.com/openai/openai-openapi), téléchargée le 2026-10-23 ([source](https://raw.githubusercontent.com/openai/openai-openapi/manual_spec/openapi.yaml))
  - copie locale : `openapi.yaml` (1.4 Mo, sha256 `6a6c681b182002de…`). Elle est en retard sur l'API réelle (absents : `diarized_json`, `detail=original`, `gpt-4o-transcribe` en `text`…) : les observations font foi en cas de désaccord.
- échanges : 214 · conformes à l'attente : 156 · **écarts : 5** · cas ignorés : 5 · erreurs de script : 0

> « Attente » = comportement décrit par la doc OpenAI (2xx / 4xx / any), tirée de la spec ci-dessus et des guides publics (certaines limites, ex. 25 Mo audio / 20 Mo image, ne figurent que dans les guides). Un écart n'est pas un bug : c'est une information (doc imprécise, ou la cible diffère).

## POST /audio/speech

| cas | HTTP | attente | | résumé |
|---|---|---|---|---|
| `speech/default` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 75264B chunks=50 ttfb=700.6ms |
| `speech/legacy_tts1` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 51072B chunks=57 ttfb=899.7ms |
| `speech/format_mp3` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 64896B chunks=45 ttfb=853.4ms |
| `speech/format_opus` | 200 | 2xx | ✓ | audio ct=audio/opus detected=ogg 38891B chunks=31 ttfb=798.3ms |
| `speech/format_aac` | 200 | 2xx | ✓ | audio ct=audio/aac detected=aac 34164B chunks=35 ttfb=2676.1ms |
| `speech/format_flac` | 200 | 2xx | ✓ | audio ct=audio/flac detected=flac 112439B chunks=60 ttfb=599.0ms |
| `speech/format_wav` | 200 | 2xx | ✓ | audio ct=audio/wav detected=wav 184844B chunks=76 ttfb=1258.3ms |
| `speech/format_pcm` | 200 | 2xx | ✓ | audio ct=audio/pcm detected=unknown/raw 194400B chunks=77 ttfb=512.6ms |
| `speech/voice_alloy` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 66432B chunks=50 ttfb=610.0ms |
| `speech/voice_ash` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 76032B chunks=57 ttfb=838.4ms |
| `speech/voice_ballad` | 200 | any | · | audio ct=audio/mpeg detected=mp3 69888B chunks=52 ttfb=636.3ms |
| `speech/voice_coral` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 79488B chunks=51 ttfb=639.8ms |
| `speech/voice_echo` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 67200B chunks=46 ttfb=787.9ms |
| `speech/voice_fable` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 81024B chunks=55 ttfb=662.2ms |
| `speech/voice_onyx` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 64896B chunks=48 ttfb=782.2ms |
| `speech/voice_nova` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 69120B chunks=63 ttfb=578.0ms |
| `speech/voice_sage` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 70656B chunks=48 ttfb=829.5ms |
| `speech/voice_shimmer` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 56064B chunks=46 ttfb=855.1ms |
| `speech/voice_verse` | 200 | any | · | audio ct=audio/mpeg detected=mp3 72192B chunks=52 ttfb=847.8ms |
| `speech/voice_custom_object` | 400 | 4xx | ✓ | ERR invalid_request_error/voice_id: No voice found with id 'voice_does_not_exist'. |
| `speech/voice_unknown` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/voice: Invalid value: 'bogus'. Supported values are: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer', 'coral', 'verse', 'ballad', 'ash', 'sage', 'marin', and 'cedar'. |
| `speech/speed_min` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 260352B chunks=100 ttfb=729.2ms |
| `speech/speed_max` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 18048B chunks=21 ttfb=3167.3ms |
| `speech/speed_too_low` | 400 | 4xx | ✓ | ERR invalid_request_error/decimal_below_min_value/speed: Invalid 'speed': decimal below minimum value. Expected a value >= 0.25, but got 0.1 instead. |
| `speech/speed_too_high` | 400 | 4xx | ✓ | ERR invalid_request_error/decimal_above_max_value/speed: Invalid 'speed': decimal above maximum value. Expected a value <= 4.0, but got 5 instead. |
| `speech/speed_string` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_type/speed: Invalid type for 'speed': expected a decimal, but got a string instead. |
| `speech/instructions` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 64128B chunks=56 ttfb=597.6ms |
| `speech/instructions_tts1` | 200 | any | · | audio ct=audio/mpeg detected=mp3 51840B chunks=44 ttfb=1366.2ms |
| `speech/stream_format_sse` | 200 | 2xx | ✓ | SSE events=107 types={'speech.audio.delta': 105, 'speech.audio.done': 1} usage={'input_tokens': 13, 'output_t… |
| `speech/stream_format_audio` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 61056B chunks=49 ttfb=734.3ms |
| `speech/stream_format_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/stream_format: Invalid value: 'ndjson'. Supported values are: 'audio' and 'sse'. |
| `speech/stream_format_sse_tts1` | 200 | any | · | audio ct=audio/mpeg detected=mp3 51456B chunks=46 ttfb=1358.1ms |
| `speech/input_french` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 70656B chunks=49 ttfb=905.9ms |
| `speech/input_unicode_emoji` | 200 | any | · | audio ct=audio/mpeg detected=mp3 57600B chunks=45 ttfb=1001.0ms |
| `speech/input_4096` | 200 | 2xx | ✓ | audio ct=audio/mpeg detected=mp3 10147200B chunks=10280 ttfb=653.5ms |
| `speech/input_4097` | 200 | 4xx | ✗ ÉCART | audio ct=audio/mpeg detected=mp3 2141568B chunks=1351 ttfb=782.9ms |
| `speech/input_empty` | 400 | 4xx | ✓ | ERR invalid_request_error/empty_string/input: Invalid 'input': empty string. Expected a string with minimum length 1, but got an empty string instead. |
| `speech/input_whitespace` | 200 | any | · | audio ct=audio/mpeg detected=mp3 5760B chunks=8 ttfb=834.4ms |
| `speech/input_not_string` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_type/input: Invalid type for 'input': expected a string, but got an array instead. |
| `speech/missing_model` | 400 | 4xx | ✓ | ERR invalid_request_error: you must provide a model parameter |
| `speech/missing_voice` | 200 | 4xx | ✗ ÉCART | audio ct=audio/mpeg detected=mp3 56832B chunks=44 ttfb=1404.1ms |
| `speech/missing_input` | 400 | 4xx | ✓ | ERR invalid_request_error/missing_required_parameter/input: Missing required parameter: 'input'. |
| `speech/model_unknown` | 404 | 4xx | ✓ | ERR invalid_request_error/model_not_found: The model `tts-does-not-exist` does not exist or you do not have access to it. |
| `speech/model_wrong_type` | 431 | 4xx | ✓ | ERR <html> ⏎   <head> ⏎     <title>Request Header Fields Too Large</title> ⏎   </head> ⏎   <body> ⏎     <h1><p>Request Header Fields Too Large</p></h1> ⏎     Error parsing headers: &#x27;limit request headers fields& |
| `speech/format_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/response_format: Invalid value: 'ogg'. Supported values are: 'mp3', 'aac', 'opus', 'flac', 'pcm', and 'wav'. |
| `speech/format_uppercase` | 400 | any | · | ERR invalid_request_error/invalid_value/response_format: Invalid value: 'MP3'. Supported values are: 'mp3', 'aac', 'opus', 'flac', 'pcm', and 'wav'. |
| `speech/unknown_param` | 200 | any | · | audio ct=audio/mpeg detected=mp3 62592B chunks=44 ttfb=1068.8ms |
| `speech/content_type_urlencoded` | 400 | 4xx | ✓ | ERR invalid_request_error: you must provide a model parameter |
| `speech/content_type_multipart` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'dict_type', 'loc': ('body',), 'msg': 'Input should be a valid dictionary'}] |
| `speech/malformed_json` | 400 | 4xx | ✓ | ERR invalid_request_error: We could not parse the JSON body of your request. (HINT: This likely means you aren't using your HTTP library correctly. The OpenAI API expects a JSON payload, but what was sent was not valid … |
| `speech/auth_invalid` | 401 | 4xx | ✓ | ERR invalid_request_error/invalid_api_key: Incorrect API key provided: sk-inval******robe. You can find your API key at https://platform.openai.com/account/api-keys. |
| `speech/auth_missing` | 401 | 4xx | ✓ | ERR invalid_request_error: You didn't provide an API key. You need to provide your API key in an Authorization header using Bearer auth (i.e. Authorization: Bearer YOUR_KEY), or as the password field (with blank usernam… |

## POST /audio/transcriptions

| cas | HTTP | attente | | résumé |
|---|---|---|---|---|
| `transcriptions/model_whisper` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/model_4o_transcribe` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/model_4o_mini_transcribe` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/input_mp3` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/input_wav` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/input_flac` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/input_ogg` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/input_opus` | 400 | any | · | ERR invalid_request_error/unsupported_value/file: Unsupported file format opus |
| `transcriptions/input_aac` | 400 | any | · | ERR invalid_request_error/unsupported_value/file: Unsupported file format aac |
| `transcriptions/input_wav_from_pcm` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/input_m4a` | — | 2xx | skip | fixture manquante: fixtures/sample.m4a (lancer `fixtures`, ou fournir le fichier) |
| `transcriptions/input_mp4` | — | 2xx | skip | fixture manquante: fixtures/sample.mp4 (lancer `fixtures`, ou fournir le fichier) |
| `transcriptions/input_webm` | — | 2xx | skip | fixture manquante: fixtures/sample.webm (lancer `fixtures`, ou fournir le fichier) |
| `transcriptions/input_mpga` | — | 2xx | skip | fixture manquante: fixtures/sample.mpga (lancer `fixtures`, ou fournir le fichier) |
| `transcriptions/input_mpeg` | — | 2xx | skip | fixture manquante: fixtures/sample.mpeg (lancer `fixtures`, ou fournir le fichier) |
| `transcriptions/input_fr` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text="Bonjour, je m'appelle Laurent. Aujourd'hui, il fait beau à Paris. Combien f… |
| `transcriptions/input_tone_no_speech` | 200 | any | · | json keys=['text', 'usage'] text='পাপ্পু' |
| `transcriptions/input_silence` | 200 | any | · | json keys=['text', 'usage'] text='هیچوقت' |
| `transcriptions/fmt_json_whisper` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/fmt_text_whisper` | 200 | 2xx | ✓ | text/plain: Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus 2? ⏎  |
| `transcriptions/fmt_srt_whisper` | 200 | 2xx | ✓ | text/plain: 1 ⏎ 00:00:00,000 --> 00:00:06,960 ⏎ Hello, my name is Laurent. Today is a sunny Friday in Pari |
| `transcriptions/fmt_vtt_whisper` | 200 | 2xx | ✓ | text/plain: WEBVTT ⏎  ⏎ 00:00:00.000 --> 00:00:06.960 ⏎ Hello, my name is Laurent. Today is a sunny Friday i |
| `transcriptions/fmt_verbose_json_whisper` | 200 | 2xx | ✓ | json keys=['duration', 'language', 'segments', 'task', 'text', 'usage'] lang=english dur=7.099999904632568 se… |
| `transcriptions/fmt_json_4o` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/fmt_text_4o` | 200 | any | · | text/plain: Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two plus two? ⏎  |
| `transcriptions/fmt_srt_4o` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_value/response_format: response_format 'srt' is not compatible with model 'gpt-4o-transcribe-api-ev3'. Use 'json' or 'text' instead. |
| `transcriptions/fmt_vtt_4o` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_value/response_format: response_format 'vtt' is not compatible with model 'gpt-4o-transcribe-api-ev3'. Use 'json' or 'text' instead. |
| `transcriptions/fmt_verbose_json_4o` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_value/response_format: response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe-api-ev3'. Use 'json' or 'text' instead. |
| `transcriptions/fmt_diarized_json` | 200 | any | · | json keys=['duration', 'segments', 'task', 'text', 'usage'] lang=None dur=7.104 segs=4 words=0 text='Hello, m… |
| `transcriptions/fmt_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/response_format: Invalid response format: yaml. Valid values are: json, text, vtt, srt, verbose_json. |
| `transcriptions/ts_segment` | 200 | 2xx | ✓ | json keys=['duration', 'language', 'segments', 'task', 'text', 'usage'] lang=english dur=7.099999904632568 se… |
| `transcriptions/ts_word` | 200 | 2xx | ✓ | json keys=['duration', 'language', 'task', 'text', 'usage', 'words'] lang=english dur=7.099999904632568 segs=… |
| `transcriptions/ts_word_and_segment` | 200 | 2xx | ✓ | json keys=['duration', 'language', 'segments', 'task', 'text', 'usage', 'words'] lang=english dur=7.099999904… |
| `transcriptions/ts_without_verbose` | 400 | any | · | ERR invalid_request_error/timestamp_granularities_format/timestamp_granularities: Timestamp granularities are only supported with response_format=verbose_json |
| `transcriptions/ts_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'enum', 'loc': ('body', 'timestamp_granularities[]', 0), 'msg': "Input should be 'segment' or 'word'", 'ctx': {'expected': "'segment' or 'word'"}}] |
| `transcriptions/ts_4o` | 400 | any | · | ERR invalid_request_error/unsupported_value/response_format: response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe-api-ev3'. Use 'json' or 'text' instead. |
| `transcriptions/language_en` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/language_fr_on_fr` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text="Bonjour, je m'appelle Laurent. Aujourd'hui il fait beau à Paris. Combien fo… |
| `transcriptions/language_wrong` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/language_invalid` | 400 | any | · | ERR invalid_request_error/invalid_value/language: Language code 'english' is not recognized. Try adding the language name to your prompt. |
| `transcriptions/prompt` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/temperature_0_5` | 200 | 2xx | ✓ | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/temperature_out_of_range` | 200 | 4xx | ✗ ÉCART | json keys=['text', 'usage'] text='Helloight ruditud ka mag vai Joo desse Rob П theoretical    If             … |
| `transcriptions/temperature_string` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'float_parsing', 'loc': ('body', 'temperature'), 'msg': 'Input should be a valid number, unable to parse string as a number'}] |
| `transcriptions/logprobs_4o` | 200 | 2xx | ✓ | json keys=['logprobs', 'text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. Wh… |
| `transcriptions/logprobs_whisper` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/logprobs_text_format` | 400 | any | · | ERR invalid_request_error/unsupported_value/include: include=logprobs is only supported for response_format 'json' |
| `transcriptions/include_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'enum', 'loc': ('body', 'include[]', 0), 'msg': "Input should be 'logprobs'", 'ctx': {'expected': "'logprobs'"}}] |
| `transcriptions/chunking_auto` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/chunking_server_vad` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/stream_4o` | 200 | 2xx | ✓ | SSE events=23 types={'transcript.text.delta': 21, 'transcript.text.done': 1} text='Hello, my name is Laurent.… |
| `transcriptions/stream_whisper` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is 2 plus… |
| `transcriptions/stream_text_format` | 200 | any | · | SSE events=23 types={'transcript.text.delta': 21, 'transcript.text.done': 1} text='Hello, my name is Laurent.… |
| `transcriptions/missing_file` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'missing', 'loc': ('body', 'file'), 'msg': 'Field required', 'input': None}] |
| `transcriptions/missing_model` | 400 | 4xx | ✓ | ERR invalid_request_error: you must provide a model parameter |
| `transcriptions/file_as_text_field` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'value_error', 'loc': ('body', 'file'), 'msg': "Value error, Expected UploadFile, received: <class 'str'>", 'ctx': {'error': ValueError("Expected UploadFile, received: <class 'str'>"… |
| `transcriptions/unsupported_ext_txt` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_value/file: Unsupported file format txt |
| `transcriptions/empty_file` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_format/messages: This model does not support the format you provided. |
| `transcriptions/corrupt_mp3` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/file: Audio file might be corrupted or unsupported |
| `transcriptions/ext_mismatch` | 400 | any | · | ERR invalid_request_error/unsupported_format/messages: This model does not support the format you provided. |
| `transcriptions/no_extension` | 400 | any | · | ERR invalid_request_error/unsupported_value/file: Unsupported file format |
| `transcriptions/content_type_octet_stream` | 200 | any | · | json keys=['text', 'usage'] text='Hello, my name is Laurent. Today is a sunny Friday in Paris. What is two pl… |
| `transcriptions/model_unknown` | 404 | 4xx | ✓ | ERR invalid_request_error/model_not_found: The model `stt-does-not-exist` does not exist or you do not have access to it. |
| `transcriptions/model_wrong_type` | 404 | 4xx | ✓ | ERR invalid_request_error: Invalid URL (POST /v1/audio/transcriptions) |
| `transcriptions/json_body` | 400 | 4xx | ✓ | ERR invalid_request_error: [{'type': 'missing', 'loc': ('body', 'file'), 'msg': 'Field required', 'input': None}] |
| `transcriptions/auth_invalid` | 401 | 4xx | ✓ | ERR invalid_request_error/invalid_api_key: Incorrect API key provided: sk-inval******robe. You can find your API key at https://platform.openai.com/account/api-keys. |
| `transcriptions/too_large_26mb` | 200 | 4xx | ✗ ÉCART | json keys=['text', 'usage'] text='Открытое небо.' |

## POST /chat/completions — image_url

| cas | HTTP | attente | | résumé |
|---|---|---|---|---|
| `chat-image/url_https` | 200 | 2xx | ✓ | finish=stop tok=8522/26 content='The image features two intertwined snake shapes, one in blue and the other in yellow, alongside the word "python" in gray.' |
| `chat-image/data_url_png` | 200 | 2xx | ✓ | finish=stop tok=8522/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/data_url_jpg` | 200 | 2xx | ✓ | finish=stop tok=8522/21 content='The image features a red square, a blue circle, and a green triangle arranged from left to right.' |
| `chat-image/data_url_webp` | 200 | 2xx | ✓ | finish=stop tok=8522/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/data_url_gif` | 200 | 2xx | ✓ | finish=stop tok=8522/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/data_url_bmp` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_format: You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp']. |
| `chat-image/data_url_tiff` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_format: You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp']. |
| `chat-image/data_url_svg` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_format: You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp']. |
| `chat-image/data_url_animated_gif` | 200 | any | · | finish=stop tok=8522/8 content='The image features a single red square.' |
| `chat-image/data_url_wrong_mime` | 200 | any | · | finish=stop tok=8522/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/data_url_no_mime` | 400 | any | · | ERR invalid_request_error/invalid_image_format: Invalid MIME type. Only image types are supported. |
| `chat-image/raw_base64_no_prefix` | 400 | any | · | ERR invalid_request_error/invalid_image_url: Failed to download file. File URL is invalid. |
| `chat-image/detail_low` | 200 | 2xx | ✓ | finish=stop tok=2855/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/detail_high` | 200 | 2xx | ✓ | finish=stop tok=8522/16 content='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/detail_auto` | 200 | 2xx | ✓ | finish=stop tok=8522/16 content='The image contains a red square, a blue circle, and a green triangle.' |
| `chat-image/detail_ultra` | 400 | 4xx | ✓ | ERR invalid_request_error: Invalid chat format. Expected 'detail' field in image_url dict to be one of ['low', 'auto', 'high', 'original'] if specified. |
| `chat-image/multi_images` | 200 | 2xx | ✓ | finish=stop tok=17024/32 content='In the first image, the color is red and the shape is a square. In the second image, the color is blue and the shape is a circle.' |
| `chat-image/interleaved` | 200 | 2xx | ✓ | finish=stop tok=17024/12 content='Image B contains a circle. Image A contains a square.' |
| `chat-image/image_only` | 200 | any | · | finish=stop tok=8507/39 content='The image features three distinct shapes:\n\n1. A red square\n2. A blue circle\n3. A green triangle\n\nThese shapes are arranged in a horizontal line against a light gray background.' |
| `chat-image/text_as_string_plus_image_msg` | 200 | 2xx | ✓ | finish=stop tok=8544/16 content='The image contains a red square, a blue circle, and a green triangle.' |
| `chat-image/history_image_then_text` | 200 | 2xx | ✓ | finish=stop tok=8536/8 content='The shape in the picture is red.' |
| `chat-image/system_prompt_plus_image` | 200 | 2xx | ✓ | finish=stop tok=8535/15 content="L'image montre un carré rouge, un cercle bleu et un triangle vert." |
| `chat-image/developer_role_plus_image` | 200 | any | · | finish=stop tok=8531/16 content='The image contains a red square, a blue circle, and a green triangle.' |
| `chat-image/ocr_text` | 200 | 2xx | ✓ | finish=stop tok=8521/4 content='HELLO 42' |
| `chat-image/image_in_system` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0]: Invalid 'messages[0]'. Image URLs are only allowed for messages with role 'user', but this message with role 'system' contains an image URL. |
| `chat-image/image_in_assistant` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[1]: Invalid 'messages[1]'. Image URLs are only allowed for messages with role 'user', but this message with role 'assistant' contains an image URL. |
| `chat-image/image_in_tool_result` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[2]: Invalid 'messages[2]'. Image URLs are only allowed for messages with role 'user', but this message with role 'tool' contains an image URL. |
| `chat-image/model_without_vision` | 500 | any | · | ERR server_error: The server had an error processing your request. Sorry about that! You can retry your request, or contact us through our help center at help.openai.com if you keep seeing this error. (Please include th… |
| `chat-image/stream` | 200 | 2xx | ✓ | SSE chunks=20 done=True finish=stop usage=8522/16 text='The image features a red square, a blue circle, and a green triangle.' |
| `chat-image/structured_output` | 200 | 2xx | ✓ | finish=stop tok=8566/30 content='{"shapes":[{"shape":"square","color":"red"},{"shape":"circle","color":"blue"},{"shape":"triangle","color":"green"}]}' |
| `chat-image/tool_call_with_image` | 200 | 2xx | ✓ | finish=tool_calls tok=8553/14 content=None |
| `chat-image/url_unreachable` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_url: Failed to download file. |
| `chat-image/url_not_an_image` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_format: You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp']. |
| `chat-image/url_http_plain` | 200 | any | · | finish=stop tok=8522/27 content='The image features two stylized snake shapes, one in blue and one in yellow, alongside the word "python" in gray text.' |
| `chat-image/url_empty` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_url: Failed to download file. File URL is invalid. |
| `chat-image/base64_corrupt` | 400 | 4xx | ✓ | ERR invalid_request_error/image_parse_error: You uploaded an unsupported image. Please make sure your image is valid. |
| `chat-image/not_an_image_bytes` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_image_format: You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp']. |
| `chat-image/image_url_as_string` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_type/messages[0].content[1].image_url: Invalid type for 'messages[0].content[1].image_url': expected an object, but got a string instead. |
| `chat-image/missing_image_url` | 400 | 4xx | ✓ | ERR invalid_request_error/messages.[0].content.[1].type: Invalid content type. image_url is only supported by certain models. |
| `chat-image/unknown_part_type` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].type: Invalid value: 'image'. Supported values are: 'text', 'image_url', 'input_audio', 'refusal', 'audio', and 'file'. |
| `chat-image/tiny_1x1` | 200 | any | · | finish=stop tok=8513/5 content='The image is red.' |
| `chat-image/large_6000x4000` | 200 | any | · | finish=stop tok=36848/5 content='The image is orange.' |
| `chat-image/huge_8200x8200` | 200 | any | · | finish=stop tok=25514/10 content='The image appears to be a shade of blue.' |
| `chat-image/too_large_22mb` | 200 | 4xx | ✗ ÉCART | finish=stop tok=36857/38 content='The image displays a textured pattern that predominantly features a range of small dots and speckles in vibrant colors including blue, purple, and hints of green and pink, creating a visually abstract effe… |
| `chat-image/many_images_12` | 200 | any | · | finish=stop tok=102020/1 content='10' |
| `chat-image/auth_invalid` | 401 | 4xx | ✓ | ERR invalid_request_error/invalid_api_key: Incorrect API key provided: sk-inval******robe. You can find your API key at https://platform.openai.com/account/api-keys. |

## POST /chat/completions — input_audio / audio out

| cas | HTTP | attente | | résumé |
|---|---|---|---|---|
| `chat-audio/in_wav_text_out` | 200 | 2xx | ✓ | finish=stop tok=94/28 audio_tok=63/0 content="I can answer the question from the audio. The answer is 4. However, I cannot identify the speaker's name from the voice." |
| `chat-audio/in_mp3_text_out` | 200 | 2xx | ✓ | finish=stop tok=102/68 audio_tok=71/0 content='I can answer the question in the audio. The question is: "What is 2 plus 2?" The answer is 4.\n\nHowever, I’m sorry, but I can\'t identify the speaker\'s name from the voice. I can only work w… |
| `chat-audio/in_wav_no_modalities` | 200 | 2xx | ✓ | finish=stop tok=94/22 audio_tok=63/0 content='The answer to the question is 4. However, I cannot identify the speaker’s name from the voice.' |
| `chat-audio/in_audio_only` | 200 | any | · | finish=stop tok=74/42 audio_tok=63/0 content='Hello, Laurent! It sounds like a lovely day in Paris. To answer your question: 2 plus 2 equals 4. If you have any other questions or need assistance, feel free to ask.' |
| `chat-audio/in_french` | 200 | 2xx | ✓ | finish=stop tok=112/8 audio_tok=84/0 content='2 plus 2 font 4.' |
| `chat-audio/in_tone_no_speech` | 200 | any | · | finish=stop tok=36/32 audio_tok=20/0 content="It sounds like there's a tone or a beep playing in the audio. If you need more detail or have another query about the sound, feel free to ask." |
| `chat-audio/in_two_audios` | 200 | any | · | finish=stop tok=158/42 audio_tok=134/0 content='It sounds like the two audio clips are identical in content. They both have the same introduction, mention the same day and weather, and ask the same question. Based on what you provided, the… |
| `chat-audio/in_text_interleaved` | 200 | 2xx | ✓ | finish=stop tok=84/22 audio_tok=63/0 content='The question you mentioned is "What is 2 plus 2?" The answer to that is 4.' |
| `chat-audio/in_stream_text_out` | 200 | 2xx | ✓ | SSE chunks=56 done=True finish=stop usage=94/52 text='The question asked in the audio message is: What is 2 plus 2? The answer is 4.\n\nI’m sorry, but I can’t identify the speaker’s name just from th… |
| `chat-audio/in_tool_call` | 200 | any | · | finish=stop tok=126/25 audio_tok=63/0 content=None |
| `chat-audio/in_format_flac` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.format: Invalid value: 'flac'. Supported values are: 'wav' and 'mp3'. |
| `chat-audio/in_format_pcm16` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.format: Invalid value: 'pcm16'. Supported values are: 'wav' and 'mp3'. |
| `chat-audio/in_format_uppercase` | 400 | any | · | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.format: Invalid value: 'WAV'. Supported values are: 'wav' and 'mp3'. |
| `chat-audio/in_format_mismatch` | 400 | any | · | ERR invalid_request_error/unsupported_format/messages: This model does not support the format you provided. |
| `chat-audio/in_format_missing` | 400 | 4xx | ✓ | ERR invalid_request_error/missing_required_parameter/messages[0].content[1].input_audio.format: Missing required parameter: 'messages[0].content[1].input_audio.format'. |
| `chat-audio/in_data_as_data_url` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.data: Invalid input audio data: 'messages[0].content[1].input_audio.data'. Expected base64-encoded data but got an invalid base64-encoded value. |
| `chat-audio/in_data_corrupt_base64` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.data: Invalid input audio data: 'messages[0].content[1].input_audio.data'. Expected base64-encoded data but got an invalid base64-encoded value. |
| `chat-audio/in_data_not_audio` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_format/messages: This model does not support the format you provided. |
| `chat-audio/in_data_empty` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0].content[1].input_audio.data: Invalid input audio data: 'messages[0].content[1].input_audio.data'. Expected base64-encoded data but got empty base64-encoded bytes. |
| `chat-audio/in_audio_as_string` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_type/messages[0].content[1].input_audio: Invalid type for 'messages[0].content[1].input_audio': expected an object, but got a string instead. |
| `chat-audio/in_audio_in_system` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0]: Invalid 'messages[0]'. Audio URLs are only allowed for messages with role 'user', but this message with role 'system' contains an audio URL. |
| `chat-audio/in_audio_in_assistant` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[1]: Invalid 'messages[1]'. Audio URLs are only allowed for messages with role 'user', but this message with role 'assistant' contains an audio URL. |
| `chat-audio/in_audio_on_text_model` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0]: Invalid 'messages[0]'. Content blocks are expected to be either text or image_url type. |
| `chat-audio/in_audio_on_vision_model` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/messages[0]: Invalid 'messages[0]'. Content blocks are expected to be either text or image_url type. |
| `chat-audio/out_text_prompt_wav` | 200 | 2xx | ✓ | finish=stop tok=14/54 audio_tok=0/38 audio(id=audio_6adb1e42, 121660b64, transcript='Hello there, great to meet you!') content=None |
| `chat-audio/out_format_mp3` | 200 | 2xx | ✓ | finish=stop tok=14/55 audio_tok=0/39 audio(id=audio_6adb1e43, 22684b64, transcript='Hello! Great to have you here.') content=None |
| `chat-audio/out_format_flac` | 200 | 2xx | ✓ | finish=stop tok=14/81 audio_tok=0/63 audio(id=audio_6adb1e45, 94684b64, transcript="Hello, it's great to be talking with you!") content=None |
| `chat-audio/out_format_opus` | 200 | 2xx | ✓ | finish=stop tok=14/66 audio_tok=0/49 audio(id=audio_6adb1e46, 27124b64, transcript='Hello! Great to be here with you.') content=None |
| `chat-audio/out_format_pcm16` | 200 | 2xx | ✓ | finish=stop tok=14/71 audio_tok=0/54 audio(id=audio_6adb1e47, 172800b64, transcript='Ciao, che piacere sentirti!') content=None |
| `chat-audio/out_format_aac` | 200 | any | · | finish=stop tok=14/66 audio_tok=0/50 audio(id=audio_6adb1e49, 29640b64, transcript='Hello there, great to meet you!') content=None |
| `chat-audio/out_voice_verse` | 200 | any | · | finish=stop tok=10/97 audio_tok=0/73 audio(id=audio_6adb1e4b, 233660b64, transcript='Hello! Great to meet you. How can I help you toda…') content=None |
| `chat-audio/out_voice_coral` | 200 | any | · | finish=stop tok=10/68 audio_tok=0/52 audio(id=audio_6adb1e4c, 166460b64, transcript='Hello! How are you doing today?') content=None |
| `chat-audio/out_voice_marin` | 200 | any | · | finish=stop tok=10/106 audio_tok=0/80 audio(id=audio_6adb1e4e, 256060b64, transcript="Hello! It's great to connect with you. How can I …") content=None |
| `chat-audio/out_voice_cedar` | 200 | any | · | finish=stop tok=10/89 audio_tok=0/65 audio(id=audio_6adb1e4f, 208060b64, transcript='Hello! Great to meet you. How can I help you toda…') content=None |
| `chat-audio/in_wav_audio_out` | 200 | 2xx | ✓ | finish=stop tok=74/240 audio_tok=63/189 audio(id=audio_6adb1e52, 604860b64, transcript='Bonjour Laurent, ravi de parler avec toi. Aujourd…') content=None |
| `chat-audio/in_mp3_audio_out_mp3` | 200 | 2xx | ✓ | finish=length tok=82/300 audio_tok=71/231 audio(id=audio_6adb1e56, 143228b64, transcript="Hello Laurent, it's nice to meet you! Today sound…") content=None |
| `chat-audio/out_modalities_audio_only` | 400 | any | · | ERR invalid_request_error/invalid_value/modalities: Invalid value for 'modalities'. Only ['text'] and ['text', 'audio'] are supported. |
| `chat-audio/out_modalities_with_text_model` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/modalities: The selected model does not support audio modality. |
| `chat-audio/out_missing_audio_param` | 400 | 4xx | ✓ | ERR invalid_request_error/missing_audio/modalities[1]: `audio` modality requires an `audio` output configuration. |
| `chat-audio/out_audio_param_without_modality` | 400 | any | · | ERR invalid_request_error/invalid_value/model: This model requires that either input content or output modality contain audio. |
| `chat-audio/out_voice_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/audio.voice: Invalid value: 'bogus'. Supported values are: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer', 'coral', 'verse', 'ballad', 'ash', 'sage', 'marin', and 'cedar'. |
| `chat-audio/out_format_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/audio.format: Invalid value: 'ogg'. Supported values are: 'mp3', 'opus', 'aac', 'flac', 'wav', and 'pcm16'. |
| `chat-audio/out_modalities_invalid` | 400 | 4xx | ✓ | ERR invalid_request_error/invalid_value/modalities[0]: Invalid value: 'video'. Supported values are: 'text' and 'audio'. |
| `chat-audio/out_stream_pcm16` | 200 | 2xx | ✓ | SSE chunks=56 done=True finish=None usage=14/52 text=None |
| `chat-audio/out_stream_wav` | 400 | 4xx | ✓ | ERR invalid_request_error/unsupported_value/audio.format: Unsupported value: 'audio.format' does not support 'wav' when stream=true. Supported values are: 'pcm16'. |
| `chat-audio/out_n2` | 500 | any | · | ERR model_error: The model produced invalid content. Consider modifying your prompt if you are seeing this error persistently. |
| `chat-audio/multi_turn_audio_id › turn1` | 200 | 2xx | ✓ | finish=stop tok=14/125 audio_tok=0/98 audio(id=audio_6adb1e5d, 313660b64, transcript='Paris est réputée pour sa magnifique tour Eiffel …') content=None |
| `chat-audio/multi_turn_audio_id › turn2` | 200 | 2xx | ✓ | finish=stop tok=155/50 audio_tok=98/39 audio(id=audio_6adb1e5e, 124860b64, transcript='Incroyable.') content=None |
| `chat-audio/multi_turn_audio_id_text_fallback › turn1` | 200 | 2xx | ✓ | finish=stop tok=14/124 audio_tok=0/101 audio(id=audio_6adb1edd, 323260b64, transcript='Paris est célèbre pour sa tour Eiffel et son ambi…') content=None |
| `chat-audio/multi_turn_audio_id_text_fallback › turn2` | 200 | 2xx | ✓ | finish=stop tok=40/166 audio_tok=0/132 audio(id=audio_6adb1edf, 422460b64, transcript='Bien sûr. Voici la phrase en français : Paris est…') content=None |
| `chat-audio/multi_turn_audio_id_unknown` | 400 | 4xx | ✓ | ERR invalid_request_error/audio_not_found/content.messages[1].audio.id: Assistant audio audio_does_not_exist not found. |
| `chat-audio/multi_turn_input_audio_then_text › turn1` | 200 | 2xx | ✓ | finish=stop tok=94/39 audio_tok=63/0 content='I\'m sorry, but I can\'t identify the speaker\'s name from the voice. However, I can answer the question. The answer to "What is 2 plus 2?" is 4.' |
| `chat-audio/multi_turn_input_audio_then_text › turn2` | 200 | 2xx | ✓ | finish=stop tok=148/5 audio_tok=63/0 content='The speaker mentioned Paris.' |
| `chat-audio/auth_invalid` | 401 | 4xx | ✓ | ERR invalid_request_error/invalid_api_key: Incorrect API key provided: sk-inval******robe. You can find your API key at https://platform.openai.com/account/api-keys. |
