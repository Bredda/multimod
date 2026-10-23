# multimod — sondes HTTP pour la multimodalité OpenAI

Exerce, **en HTTP brut (httpx, pas de SDK)**, les endpoints multimodaux compatibles OpenAI et capture pour chaque cas la requête et la réponse exactes :

| Endpoint | Cas |
|---|---|
| `POST /audio/speech` | formats, voix, speed, instructions, `stream_format`, limites d'`input`, erreurs |
| `POST /audio/transcriptions` | modèles, formats de fichier, `response_format`, timestamps, langue, logprobs, streaming, fichiers invalides |
| `POST /chat/completions` + `image_url` | URL / data-URL, formats, `detail`, multi-images, placement par rôle, limites, URL invalides |
| `POST /chat/completions` + `input_audio` / sortie audio | wav/mp3, `modalities` + `audio`, formats de sortie, streaming PCM16, multi-tours par `audio.id` |

Même jeu de cas pour **n'importe quelle cible** (OpenAI, LiteLLM, la gateway) → on compare ensuite les captures.

> Documentation : [docs/synthese.md](docs/synthese.md) (cadrage + points d'architecture + questions ouvertes) · [docs/observations-openai.md](docs/observations-openai.md) (constats du run de référence OpenAI) · [docs/contrat-openai.md](docs/contrat-openai.md) (contrat de référence) · [docs/cases-catalog.md](docs/cases-catalog.md) (les 218 cas, généré).

## Démarrage

```bash
# Cible OpenAI : un .env avec OPENAI_API_KEY suffit (MM_BASE_URL vaut https://api.openai.com/v1 par défaut).
# Autre cible : cp .env.example .env.<cible>, renseigner MM_BASE_URL / MM_API_KEY / MM_MODEL_*, puis --env-file .env.<cible>
uv run python -m mmprobe fixtures              # images/audio + parole générée via /audio/speech (~10 appels TTS)
uv run python -m mmprobe run -k 'speech/*'     # premier essai à bas coût
uv run python -m mmprobe run                   # tout (hors heavy/security)
```

`run` génère les fixtures manquantes tout seul. Prérequis : [uv](https://docs.astral.sh/uv/) (dépendances : `httpx`, `pillow`).

### Commandes

| Commande | Rôle |
|---|---|
| `list [-k ..] [--tags ..]` | liste les cas sélectionnés |
| `fixtures [--local-only]` | génère `fixtures/` (images Pillow, audio synthétique, parole via TTS de la cible) |
| `run [-k ..] [--tags ..] [--skip-tags ..] [--heavy] [--security] [--dry-run] [--delay s] [--fresh]` | exécute, écrit `captures/<label>/`, génère `REPORT.md` |
| `report [--compare LABEL…]` | `REPORT.md` d'une cible, ou `COMPARE_a_vs_b.md` entre cibles |
| `catalog` | régénère `docs/cases-catalog.md` |

Options globales : `--env-file`, `--label` (nom du dossier de captures), `--base-url`.
Sélection : `-k` accepte un glob ou une sous-chaîne sur l'id (`speech/*`, `image`, `format_wav`), répétable. Un run partiel **fusionne** dans l'index existant (`--fresh` pour repartir de zéro).
Tags : `neg` (négatif) · `probe` (param récent, absent de la spec publique) · `heavy` (payloads > 20 Mo, opt-in) · `security` (SSRF, opt-in — **uniquement contre ta propre gateway**, pas un provider tiers) · `stream` · `format` · `compose` · …

### Comparer plusieurs cibles

```bash
uv run python -m mmprobe --env-file .env.openai  --label openai  run
uv run python -m mmprobe --env-file .env.litellm --label litellm run
uv run python -m mmprobe --env-file .env.gateway --label gateway run
uv run python -m mmprobe report --compare openai litellm gateway    # → captures/COMPARE_openai_vs_litellm_vs_gateway.md
```
Les alias de modèles propres à chaque cible se règlent via `MM_MODEL_*` dans son `.env` (voir `.env.example`). Pour une gateway/LiteLLM, vérifier aussi `MM_MAX_TOKENS_PARAM` (`max_tokens` vs `max_completion_tokens`).

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

## Limites connues

- Les cas ont tourné une fois contre l'API OpenAI (2026-10-23, résultats dans `docs/observations-openai.md`) ; pas encore contre LiteLLM ni la gateway. `tools/mock_server.py` est un serveur factice pour tester la mécanique sans clé : il ne reproduit pas OpenAI.
- Les attentes `expect` viennent de la doc OpenAI ; 5 divergent de la réalité observée (limites non appliquées) — ce sont des informations, pas des bugs.
- Formats d'entrée `m4a`, `mp4`, `webm`, `mpga`, `mpeg` non générables sans ffmpeg : déposer `fixtures/sample.<ext>` pour activer les cas (sinon « skipped »).
- `text_only` (`gpt-3.5-turbo` par défaut) doit être un modèle réellement sans vision ni audio ; s'il est retiré, régler `MM_MODEL_TEXT_ONLY`.
- Le cas `url_https` dépend d'une URL d'image publique (`MM_IMAGE_URL`, défaut : logo python.org) joignable par la cible.
- Les captures contiennent des réponses de modèles et de l'audio : ne pas les committer sans relecture (`captures/` et `fixtures/` sont dans `.gitignore`).
