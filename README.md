# multimod — sondes pour la multimodalité (OpenAI, LiteLLM, Bedrock)

Cadrage de la multimodalité de la gateway : on sonde **ce que le worker rencontrera côté provider**, sans passer par la gateway (ses endpoints n'existent pas encore). Chaque sonde capture la requête et la réponse exactes.

| Cible | Transport | Pourquoi |
|---|---|---|
| **OpenAI** (référence du contrat d'entrée de la gateway) | HTTP brut (`httpx`, pas de SDK) | définit le format que la gateway reçoit |
| **LLMaaS / LiteLLM** | HTTP brut, mêmes sondes que OpenAI (autre `.env`) | le worker fait du quasi-passthrough HTTP |
| **Bedrock** | **boto3** `bedrock-runtime` (Converse, ConverseStream, InvokeModel, CountTokens) | le worker appelle Bedrock avec boto3 |

Côté HTTP (OpenAI/LiteLLM) :

| Endpoint | Cas |
|---|---|
| `POST /audio/speech` | formats, voix, speed, instructions, `stream_format`, limites d'`input`, erreurs |
| `POST /audio/transcriptions` | modèles, formats de fichier, `response_format`, timestamps, langue, logprobs, streaming, fichiers invalides |
| `POST /chat/completions` + `image_url` | URL / data-URL, formats, `detail`, multi-images, placement par rôle, limites, URL invalides |
| `POST /chat/completions` + `input_audio` / sortie audio | wav/mp3, `modalities` + `audio`, formats de sortie, streaming PCM16, multi-tours par `audio.id` |

Côté Bedrock, les cas sont écrits en paramètres boto3 (`messages`, blocs `image`/`audio`…). Quand un scénario existe des deux côtés il garde le **même id** (`chat-image/multi_images`), ce qui permet `report --compare openai litellm bedrock-eu-west-3`. Les scénarios sans équivalent Bedrock (TTS, audio en sortie) sont sondés pour constater le refus — voir [docs/bedrock-mapping.md](docs/bedrock-mapping.md).

> **Reprise du projet par un agent / sur un autre poste : [docs/HANDOFF.md](docs/HANDOFF.md)** (décisions closes, interdits, runbooks Bedrock et LiteLLM, livrables). `AGENTS.md` en est le résumé impératif.

> Documentation : [docs/bedrock-mapping.md](docs/bedrock-mapping.md) (mapping OpenAI → Converse, hypothèses à valider) · [docs/synthese.md](docs/synthese.md) (cadrage + points d'architecture + questions ouvertes) · [docs/observations-openai.md](docs/observations-openai.md) (constats du run de référence OpenAI) · [docs/contrat-openai.md](docs/contrat-openai.md) (contrat de référence) · [docs/cases-catalog.md](docs/cases-catalog.md) (tous les cas des deux cibles, généré).

## Démarrage

```bash
# Cible OpenAI : un .env avec OPENAI_API_KEY suffit (MM_BASE_URL vaut https://api.openai.com/v1 par défaut).
# Autre cible : cp .env.example .env.<cible>, renseigner MM_BASE_URL / MM_API_KEY / MM_MODEL_*, puis --env-file .env.<cible>
uv run python -m mmprobe fixtures              # images/audio + parole générée via /audio/speech (~10 appels TTS)
uv run python -m mmprobe run -k 'speech/*'     # premier essai à bas coût
uv run python -m mmprobe run                   # tout (hors heavy/security)
```

`run` génère les fixtures manquantes tout seul. Prérequis : [uv](https://docs.astral.sh/uv/) (dépendances : `httpx`, `pillow`).

### Cibles Bedrock et LiteLLM

```bash
# Bedrock (boto3) : identifiants AWS = chaîne standard (profil, SSO, variables, ou clé API Bedrock)
cp .env.example.bedrock .env.bedrock        # région + rôles de modèles
uv run python -m mmprobe --env-file .env.bedrock bedrock-models     # liste les modèles/profils (IMAGE, SPEECH…) → ids pour le .env
uv run python -m mmprobe --env-file .env.bedrock run --dry-run      # valide tous les paramètres contre botocore, sans appel ni identifiants
uv run python -m mmprobe --env-file .env.bedrock run -k 'chat-image/bytes_*'   # premier essai
# LiteLLM : même code que OpenAI, autre .env (MM_BASE_URL, MM_API_KEY, MM_MODEL_* = alias exposés, MM_MAX_TOKENS_PARAM)
uv run python -m mmprobe --env-file .env.litellm --label litellm run
```
Les fixtures de parole (`speech_en.*`) sont produites par `/audio/speech` : les générer une fois avec la cible OpenAI (`fixtures`), elles sont ensuite partagées avec Bedrock (dossier `fixtures/` commun). Aucun id de modèle Bedrock n'est présumé : un rôle non renseigné fait **ignorer** les cas concernés (« skipped ») au lieu de viser un modèle au hasard.

### Commandes

| Commande | Rôle |
|---|---|
| `list [-k ..] [--tags ..]` | liste les cas sélectionnés |
| `fixtures [--local-only]` | génère `fixtures/` (images Pillow, audio synthétique, parole via TTS de la cible) |
| `run [-k ..] [--tags ..] [--skip-tags ..] [--heavy] [--security] [--dry-run] [--delay s] [--fresh]` | exécute, écrit `captures/<label>/`, génère `REPORT.md` |
| `bedrock-models [--modality X] [--all]` | (Bedrock) liste modèles + inference profiles et leurs modalités, écrit `captures/<label>/models.json` |
| `report [--compare LABEL…]` | `REPORT.md` d'une cible, ou `COMPARE_a_vs_b.md` entre cibles |
| `catalog` | régénère `docs/cases-catalog.md` |

Options globales : `--env-file`, `--label` (nom du dossier de captures), `--base-url`, `--provider http|bedrock` (défaut `MM_PROVIDER` ou `http`).
Sélection : `-k` accepte un glob ou une sous-chaîne sur l'id (`speech/*`, `image`, `format_wav`), répétable. Un run partiel **fusionne** dans l'index existant (`--fresh` pour repartir de zéro).
Tags : `neg` (négatif) · `probe` (param récent, absent de la spec publique) · `heavy` (payloads > 20 Mo, opt-in) · `security` (SSRF, opt-in — à réserver à la future gateway, jamais à un provider tiers) · `stream` · `format` · `compose` · …

### Comparer plusieurs cibles

```bash
uv run python -m mmprobe --env-file .env.openai  --label openai  run
uv run python -m mmprobe --env-file .env.litellm --label litellm run
uv run python -m mmprobe --env-file .env.bedrock run                 # label bedrock-<région>
uv run python -m mmprobe report --compare openai litellm bedrock-eu-west-3   # → captures/COMPARE_*.md
```
Les alias de modèles se règlent via `MM_MODEL_*` (HTTP, voir `.env.example`) ou `MM_BEDROCK_MODEL_*` (Bedrock, voir `.env.example.bedrock`). Pour LiteLLM, vérifier aussi `MM_MAX_TOKENS_PARAM` (`max_tokens` vs `max_completion_tokens`). La gateway elle-même n'est pas sondée : ses endpoints sont ce qu'on cadre.

## Ce qui est capturé

```
captures/<label>/
├── index.json              # tous les cas : statut, attente, match, résumé, fichiers extraits
├── REPORT.md               # tableau par endpoint, écarts vs attente en évidence
└── <endpoint>/<cas>[/<étape>]/
    ├── request.json        # requête telle qu'envoyée (blobs base64 résumés, clé API masquée)
    ├── request.raw.json    # corps JSON complet, rejouable
    ├── curl.sh             # rejeu : MM_BASE_URL et MM_API_KEY définis, depuis la racine du projet
    ├── response.json       # statut, headers, timings (TTFB, chunks), corps ou événements SSE
    ├── response.sse.txt    # flux brut si SSE
    └── response.audio.*    # audio extrait (binaire TTS, message.audio.data, deltas PCM16 → wav)
```
- **Attente** (`2xx`/`4xx`/`any`) = ce que la doc OpenAI laisse prévoir. Un `✗ ÉCART` n'est pas un échec du script : c'est une information sur la cible.
- Les cas multi-étapes (multi-tours audio) ont un sous-dossier par étape (`turn1/`, `turn2/`).
- Un 429 est ré-essayé (3 fois max, tracé dans `retries_429`) ; aucune autre relance, pour ne pas masquer un comportement.

Cas Bedrock : `request.json` = paramètres boto3 (octets résumés `<bytes N, sha256, magic=png>`), `request.raw.json` = complet (octets en `{"__bytes_b64__"}`), `replay.py` = rejoue l'appel avec boto3, `response.json` = statut HTTP, headers `x-amzn-*`, `data` (réponse ou `ClientError.response` avec `Error.Code`), `events` + `stream_summary` pour les flux. Un rejet **côté client** par botocore (avant tout appel réseau) est tracé `client-side-error`. Retries botocore désactivés ; seul `ThrottlingException` est ré-essayé (3 fois max, tracé).

## Limites connues

- **Les sondes Bedrock n'ont jamais tourné contre AWS** (pas d'identifiants dans l'environnement de développement). Elles sont validées hors-ligne : paramètres de chacun des 97 cas contre le modèle de service botocore (`run --dry-run`), et transport/capture/rapports via `tools/selftest_bedrock.py` (faux client boto3 : ne reproduit pas Bedrock). Les `expect` Bedrock viennent de la doc AWS, de sources tierces ou d'hypothèses — beaucoup sont `any`.
- Nova Sonic (`InvokeModelWithBidirectionalStream`) n'est pas sondable avec boto3 ; seuls ses refus par Converse/InvokeModel le sont.
- Les cas ont tourné une fois contre l'API OpenAI (2026-10-23, résultats dans `docs/observations-openai.md`) ; pas encore contre LiteLLM ni la gateway. `tools/mock_server.py` est un serveur factice pour tester la mécanique sans clé : il ne reproduit pas OpenAI.
- Les attentes `expect` viennent de la doc OpenAI ; 5 divergent de la réalité observée (limites non appliquées) — ce sont des informations, pas des bugs.
- Formats d'entrée `m4a`, `mp4`, `webm`, `mpga`, `mpeg` non générables sans ffmpeg : déposer `fixtures/sample.<ext>` pour activer les cas (sinon « skipped »).
- `text_only` (`gpt-3.5-turbo` par défaut) doit être un modèle réellement sans vision ni audio ; s'il est retiré, régler `MM_MODEL_TEXT_ONLY`.
- Le cas `url_https` dépend d'une URL d'image publique (`MM_IMAGE_URL`, défaut : logo python.org) joignable par la cible.
- Les captures contiennent des réponses de modèles et de l'audio : ne pas les committer sans relecture (`captures/` et `fixtures/` sont dans `.gitignore`).
