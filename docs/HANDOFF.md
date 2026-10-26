# HANDOFF — reprise du projet par un agent de code (poste pro, environnement bancaire)

> **Lecteur visé : un agent de code (GitHub Copilot) qui reprend ce dépôt sans avoir assisté aux échanges précédents.**
> Ce document est la source de vérité sur le *pourquoi*, les *décisions closes*, les *interdits* et la *suite*. Le *comment* du code est dans [README.md](../README.md). En cas de doute entre ce document et ton intuition : suis ce document, puis demande à l'humain (§12).

## 0. En 12 lignes

1. Équipe produit : une **gateway IA générative d'entreprise** exposant une API **compatible OpenAI** devant **Bedrock** et un **LLMaaS** (LiteLLM). Elle sait déjà faire `chat/completions` (parts `text` et `file`), `embeddings`, `rerank`.
2. Design : la gateway gère auth, contrôles (quotas…), infos modèle/provider ; elle envoie à un **worker** qui transforme le payload OpenAI en payload provider via des **templates Jinja2** — Bedrock (Converse **ou** InvokeModel selon le modèle) via **boto3**, LLMaaS en quasi-passthrough via **client HTTP** — puis retransforme la réponse en OpenAI.
3. Sprint en cours : **explorer et cadrer la multimodalité** : `/audio/speech`, `/audio/transcriptions`, `/chat/completions` avec parts **image** et **audio**.
4. Ce dépôt (`mmprobe`) = des **sondes** qui appellent les providers (pas la gateway, dont les endpoints n'existent pas — c'est ce qu'on cadre) et **capturent l'entrée et la sortie exactes de chaque cas**. Livrable final : ces captures + une documentation/synthèse.
5. **Fait** : sondes OpenAI (référence du contrat d'entrée) exécutées, documentées → `captures/openai/`, [observations-openai.md](observations-openai.md). **Sondes Bedrock (boto3)** et **LiteLLM (HTTP)** écrites mais **jamais exécutées**.
6. **À faire, par toi, depuis le poste pro** : exécuter les sondes **Bedrock** et **LiteLLM**, puis rédiger les observations et mettre à jour la synthèse (§9, §10).
7. Le poste pro **n'a pas accès à OpenAI** (domaine bloqué) : tu ne peux ni rejouer ni compléter `captures/openai/` — elle est **figée** (§4).
8. Tu n'es pas là pour « faire passer » les cas : **un échec est un résultat**, à capturer et documenter tel quel (§8).
9. Données **synthétiques uniquement** dans les requêtes (§3). Aucun secret dans le dépôt.
10. Aucun `push` de résultats hors du poste sans accord explicite de l'humain (§11).
11. Les cas `security` (SSRF) et `heavy` ne se lancent **jamais** sans accord explicite (§11).
12. Toute affirmation écrite dans la doc doit être traçable à un cas ou à une source, et étiquetée (§9).

---

## 1. Décisions déjà prises — ne pas les rouvrir

| # | Décision | Pourquoi |
|---|---|---|
| D1 | OpenAI et LiteLLM sont sondés en **HTTP brut** (`httpx`), **jamais avec le SDK OpenAI/LiteLLM**. | On veut le fil exact (headers, corps, SSE), car le worker LLMaaS fait du HTTP sans SDK. |
| D2 | Bedrock est sondé **uniquement avec boto3** (`bedrock-runtime`), **jamais en HTTP signé à la main**. | Le worker appelle Bedrock avec boto3 ; ce qui compte est ce que boto3 reçoit/renvoie (dict, `ClientError`, événements de flux). |
| D3 | On ne sonde **pas la gateway**. | Ses endpoints multimodaux n'existent pas encore. |
| D4 | **OpenAI = référence du contrat d'entrée** de la future gateway ; Bedrock et LiteLLM = cibles de sortie du worker. | Les clients enverront du format OpenAI. |
| D5 | Un **même id de cas** (`chat-image/multi_images`) désigne le **même scénario** dans toutes les cibles. | Permet `report --compare`. Ne renomme pas un id existant. |
| D6 | Les cas Bedrock sont écrits **en paramètres boto3**, pas en JSON HTTP. Les cas HTTP en JSON/multipart. | Voir D1/D2. |
| D7 | Les rôles de modèles Bedrock n'ont **aucun défaut** ; un rôle absent ⇒ cas « skipped ». | Les ids/inference profiles dépendent du compte et de la région ; ne jamais viser un modèle au hasard. |
| D8 | Les retries sont **désactivés** (botocore `max_attempts=1`) ; seuls 429 (HTTP) / `ThrottlingException` (boto3) sont relancés ≤ 3 fois, **et tracés**. | Ne pas masquer un comportement. |
| D9 | `expect` (`2xx`/`4xx`/`any`) = ce que la **doc** laisse prévoir ; un écart n'est ni un bug ni à « corriger » : c'est de l'information. | Voir §8. |
| D10 | TTS (`/audio/speech`) et sortie audio du chat n'ont **pas de chemin boto3/Bedrock** (Nova Sonic = flux bidirectionnel seul). On sonde seulement le **refus**. | Voir [bedrock-mapping.md](bedrock-mapping.md) §1 — *à confirmer* par les cas `nova_sonic_*`. Le choix produit qui en découle appartient à l'humain (§12). |
| D11 | Langue : **français** pour la doc et les commentaires, comme l'existant. | Cohérence. |
| D12 | `fixtures/` est **partagé** entre cibles ; la parole (`speech_*`) a été générée par OpenAI TTS et **est versionnée**. | OpenAI est inaccessible ici (§4). |

## 2. État d'avancement

| Élément | État | Preuve / où |
|---|---|---|
| Sondes OpenAI (HTTP) — 214 cas par défaut (+4 opt-in) | ✅ exécutées le 2026-10-23 | `captures/openai/`, `REPORT.md` (5 écarts / 214 échanges) |
| Observations OpenAI | ✅ rédigées | [observations-openai.md](observations-openai.md) |
| Contrat OpenAI | ✅ | [contrat-openai.md](contrat-openai.md), spec dans `captures/openai/openapi.yaml` |
| Sondes **Bedrock** (boto3) — 97 cas (+2 `heavy`) | ✅ écrites ; ✅ paramètres validés contre botocore (`run --dry-run`) ; ✅ transport testé avec faux client (`tools/selftest_bedrock.py`) ; ❌ **jamais exécutées sur AWS** | `mmprobe/cases/bedrock_*.py`, `mmprobe/bedrock.py` |
| Sondes **LiteLLM** (HTTP) | ✅ ce sont les cas OpenAI (même code) ; ❌ **jamais exécutées sur LiteLLM** ; rôles de modèles à mapper | §6 |
| Mapping OpenAI→Bedrock | 📝 hypothèses ; lignes `[AWS]` (doc), `[tiers]`, `[hyp]` | [bedrock-mapping.md](bedrock-mapping.md) |
| Synthèse | ✅ pour OpenAI ; section Bedrock = « ce que la doc laisse prévoir » (non observé) | [synthese.md](synthese.md) |
| `docs/observations-bedrock.md`, `observations-litellm.md` | ❌ **à écrire** | §9 |
| Comparaison inter-cibles | ❌ à produire (`report --compare`) | §6, §7 |

## 3. Cadre « environnement bancaire » — contraintes à respecter

- **Données** : n'envoie à un modèle que des données **synthétiques** (les fixtures le sont : formes géométriques, parole générée « Hello, my name is Laurent… », bruit). **N'ajoute jamais** de document, image, audio ou texte réel/interne, même « pour tester ». Si un cas exige un fichier réel (ex. `sample.m4a`), demande à l'humain un fichier **synthétique/public**.
- **Secrets** : jamais dans le dépôt, les captures, les logs ou les docs. `.env*` est ignoré (sauf `.env.example*`). Les clés sont masquées dans `request.json`, mais **vérifie** avant tout commit (`grep -rF "<valeur>"`). Ne colle pas de clé dans un message/prompt.
- **Identifiants indirects dans les captures** : `x-amzn-requestid`, ARNs d'inference profiles (contiennent l'ID de compte AWS), noms d'organisation/projet, noms d'hôtes internes (LiteLLM). Ils **ne sont pas** des secrets, mais ce sont des informations internes : signale-les à l'humain avant toute sortie des captures du poste (§11).
- **Réseau** : proxy/inspection TLS probables. HTTP : `HTTPS_PROXY`/`NO_PROXY` sont lus ; certificat d'entreprise via `MM_CA_BUNDLE=/chemin/ca.pem`. boto3 : `AWS_CA_BUNDLE`, mêmes variables proxy. **Ne désactive pas la vérification TLS** (`MM_VERIFY_TLS=false`) sans accord de l'humain.
- **Coût / quotas** : un run Bedrock complet fait ~100 appels courts (`maxTokens` 100–300), des images jusqu'à ~4 Mo et des audios jusqu'à 10 Mo. Utilise `--delay 2` si tu rencontres du throttling. Lance d'abord un sous-ensemble (§6).
- **Modèles autorisés** : n'utilise que des modèles que l'organisation autorise ; en cas de doute sur un modèle, demande.

## 4. Ce que tu ne peux pas faire depuis le poste pro (et la conduite à tenir)

- **OpenAI est bloqué.** Conséquences :
  - `captures/openai/` est **la référence figée** : ne la régénère pas, ne la modifie pas, ne l'« améliore » pas. `report` peut la relire.
  - La commande `fixtures` appelle `/audio/speech` de la cible HTTP configurée : **ne l'utilise pas** pour « réparer » des fixtures de parole manquantes (elles sont versionnées). Si elles manquent, c'est que le transfert est incomplet → demande à l'humain.
  - Les fixtures **lourdes** (`silence_*mb.wav`, `noise_*`) ne sont pas versionnées : elles se **régénèrent à la demande** (les cas les créent) — c'est normal.
- **Nova Sonic** (`InvokeModelWithBidirectionalStream`) n'est pas sondable avec boto3 ; ne tente pas d'ajouter un autre SDK sans accord (§12).

## 5. Installation

```bash
uv sync                      # httpx, pillow, boto3 (voir pyproject.toml ; Python ≥ 3.11)
uv run python -m mmprobe --provider bedrock list | tail -1     # 97 cas Bedrock
uv run python -m mmprobe --provider http    list | tail -1     # 214 cas HTTP
```
Si `uv` n'est pas disponible ou si l'index de paquets est un miroir interne : `python -m venv .venv && pip install httpx pillow boto3` puis `python -m mmprobe …` ; signale-le à l'humain.
Pour `tools/selftest_bedrock.py` : `PYTHONPATH=. python tools/selftest_bedrock.py`.
⚠ Si aucun `--env-file` n'est donné, le programme charge `./.env` **s'il existe** : sur le poste pro passe **toujours** `--env-file` explicitement pour ne pas viser la mauvaise cible.

## 6. Runbook — Bedrock (boto3)

1. `cp .env.example.bedrock .env.bedrock` ; renseigne la région et l'authentification (profil/SSO/variables standard AWS, ou clé API Bedrock `AWS_BEARER_TOKEN_BEDROCK`). *Une clé API Bedrock peut fonctionner pour Converse/InvokeModel mais pas pour le plan de contrôle (`bedrock-models`) : dans ce cas renseigne les ids à la main.*
2. **Découverte** : `uv run python -m mmprobe --env-file .env.bedrock bedrock-models` → liste les modèles avec modalités (IMAGE, SPEECH…) et inference profiles ; écrit `captures/<label>/models.json`.
   Remplis `MM_BEDROCK_MODEL_*` : `VISION` (ex. un Claude), `VISION_NOVA` (un Nova avec image), `VISION_OTHER` (Llama 4/Pixtral/Qwen3-VL…), `AUDIO_IN` et `AUDIO_IN_MINI` (modèles **SPEECH**, ex. Voxtral Small/Mini), `TEXT_ONLY` (sans image/audio, ex. Nova Micro), `SONIC` (`amazon.nova-2-sonic-v1:0`). Si un modèle n'est servi que par **inference profile**, mets l'**id du profil** (préfixe de zone, ex. `eu.…`). Un rôle laissé vide ⇒ cas « skipped » (c'est voulu).
3. **Validation sans appel** : `… --env-file .env.bedrock run --dry-run` (vérifie les paramètres contre botocore ; ne contacte pas AWS). Doit afficher `0 erreur(s) de script`.
4. **Premier essai, bas coût** : `… run -k 'chat-image/bytes_png' -k 'chat-image/auth_invalid'`. Vérifie dans `captures/<label>/chat-image/bytes_png/response.json` que la réponse décrit bien « carré rouge, cercle bleu, triangle vert ».
5. **Par endpoint** : `-k 'chat-image/*'` puis `-k 'transcriptions/*'` puis `-k 'chat-audio/*'` puis `-k 'speech/*'` (les deux derniers : refus attendus de Sonic). Lis `REPORT.md` après chaque étape.
6. Run partiel ⇒ **fusion** dans l'index ; `--fresh` repart de zéro. Le label par défaut est `bedrock-<région>`.
7. Rapport : `… report` ; comparaison : `report --compare openai litellm bedrock-<région>` (dans `captures/COMPARE_*.md`).

## 7. Runbook — LiteLLM (HTTP, sans SDK)

1. `cp .env.example .env.litellm` ; `MM_BASE_URL=https://<litellm>/v1`, `MM_API_KEY=<clé LiteLLM>`, `MM_LABEL=litellm`, `MM_MAX_TOKENS_PARAM=max_tokens` (LiteLLM/providers historiques ; teste `max_completion_tokens` si rejeté — note lequel marche), `MM_CA_BUNDLE` si besoin. Ajoute `MM_EXTRA_HEADERS` seulement si l'infra l'exige.
2. **Découverte** : `uv run python -m mmprobe --env-file .env.litellm http-models` → `GET /models` (+ `/model/info` si LiteLLM l'expose : `mode` par alias, p. ex. `chat`, `audio_transcription`, `audio_speech`). Écrit `captures/litellm/models.json`.
3. **Mappe les rôles** dans `.env.litellm` : `MM_MODEL_TTS`, `_TTS_LEGACY`, `_STT`, `_STT_MINI`, `_STT_WHISPER`, `_STT_DIARIZE`, `_VISION`, `_TEXT_ONLY`, `_AUDIO_CHAT` = alias LiteLLM correspondants. **Pour un rôle que LiteLLM n'expose pas, mets `-`** (ex. `MM_MODEL_STT_DIARIZE=-`) : les cas sont « skipped » au lieu de produire des 404 parasites. Les défauts OpenAI (`gpt-4o-mini-tts`, `whisper-1`…) n'ont de sens que si l'alias existe.
4. Essai : `… run -k 'chat-image/data_url_png' -k 'chat-image/auth_invalid'`. Puis `-k 'chat-image/*'`, `transcriptions/*`, `chat-audio/*`, `speech/*`.
5. **Ce qu'il faut noter en plus** (dans `observations-litellm.md`) : pour chaque alias, **quel provider/modèle sous-jacent** (via `/model/info`, headers `x-litellm-*` de `response.json` : `x-litellm-model-id`, `x-litellm-call-id`…) — le comportement observé est celui de LiteLLM **+** du provider derrière ; distingue-les quand c'est possible (message d'erreur du provider repris tel quel ou normalisé par LiteLLM ?).
6. Version de LiteLLM : si `/health/readiness` ou une page d'admin la donne, **note-la** dans l'observation (avec la date). `index.json` enregistre déjà les versions de `python/httpx/boto3/botocore`.
7. ⚠ Les cas `security` (SSRF) ciblent le fetch d'URL d'image côté serveur : **jamais sans accord explicite de l'humain** (§11) — ils ressemblent à une attaque pour une équipe sécurité.
8. TTS/STT : si LiteLLM renvoie 404 sur `/audio/*`, c'est un résultat (« non exposé »), pas un échec de script.

## 8. Lire les résultats sans se tromper

- `index.json` / `REPORT.md` : une ligne par échange (`cas › étape`), HTTP, `attente`, ✓ / `✗ ÉCART` / `·` (attente `any`), résumé.
- **Trois natures d'échec — ne les confonds pas** :
  1. `SCRIPT-ERROR` (bug du script : mauvaise construction, fixture, import…) → **corrige le script**, relance le cas.
  2. `client-side-error` (Bedrock : rejeté par **botocore avant l'envoi**) → c'est un **résultat** (le worker aurait la même exception) ; ne contourne pas.
  3. Réponse d'erreur du provider (4xx/5xx, `Error.Code`) → **résultat** ; recopie le message/code dans l'observation. Ne « répare » un cas que si l'erreur prouve un **mauvais paramètre de ton cas** (ex. schéma de body InvokeModel erroné d'après la doc AWS) — dans ce cas corrige **après avoir lu la doc du provider**, relance, et dis-le dans l'observation (« premier essai invalide car… »).
- Un `✗ ÉCART` n'est **pas** à effacer en modifiant `expect`. Après avoir observé, tu peux *ajouter* à l'observation « la doc dit X, la réalité est Y ». Ne change `expect` que pour corriger une attente **objectivement fausse d'après la doc** (rare) et mentionne-le.
- 429/Throttling : relances tracées (`retries_*`). Un cas qui échoue par throttling **n'est pas un résultat** : relance-le plus tard avec `--delay`.
- Non-déterminisme des modèles : ne compare jamais le **texte** des réponses entre runs ; compare statuts, structure, champs, tokens, erreurs.
- Chaque dossier de cas contient `request.json`, `response.json`, et pour boto3 un `replay.py` (rejouable avec ses propres identifiants) ; pour HTTP un `curl.sh`.

## 9. Livrables attendus (définition de « fini »)

1. `captures/<label>/` pour **Bedrock** et **LiteLLM**, `REPORT.md` générés par l'outil (ne les édite pas à la main).
2. `captures/COMPARE_openai_vs_litellm_vs_bedrock-<région>.md` (via `report --compare`).
3. **`docs/observations-bedrock.md`** et **`docs/observations-litellm.md`**, sur le modèle exact de [observations-openai.md](observations-openai.md) : en-tête (cible, date, modèles résolus, versions clients, portée chiffrée issue de `index.json`, réserve « un run/un compte »), puis sections par endpoint, **faits seulement**, chaque point renvoyant à un id de cas.
4. Mise à jour de [bedrock-mapping.md](bedrock-mapping.md) : pour chaque ligne, remplace `[hyp]`/« à confirmer » par `[obs]` + id de cas, ou par `[infirmé]` + explication. Ne supprime pas les hypothèses infirmées, barre-les.
5. Mise à jour de [synthese.md](synthese.md) §0 (état), §3 (questions ouvertes → tranchées/restantes) et la partie Bedrock ; ajoute la partie LiteLLM.
6. `python -m mmprobe catalog` relancé si des cas ont changé.
7. Liste explicite de ce qui **n'a pas pu être testé** et pourquoi (modèle absent, accès refusé, quota).

**Règles de rédaction (strictes)** : (a) étiquettes de source : `[obs]` observé (avec id de cas), `[AWS]`/`[LiteLLM]` documentation officielle (avec lien), `[tiers]`, `[hyp]` ; (b) chiffres tirés de `index.json`/`response.json`, jamais de mémoire ; (c) distinguer ce qui est dû à LiteLLM de ce qui est dû au provider derrière ; (d) pas de généralisation (« Bedrock ne supporte pas X ») à partir d'un seul modèle : écrire « le modèle `<id>` … » ; (e) noter région et date ; (f) si tu n'as pas observé, n'écris pas.

## 10. Points probables à ajuster au premier run (liés à du code non éprouvé)

À traiter avec la méthode du §8 (script vs résultat) :
- **Ids de modèles** : `ValidationException … on-demand throughput isn't supported` ⇒ utiliser l'id d'**inference profile**. `AccessDeniedException` ⇒ accès au modèle non activé : c'est un fait à noter, pas un cas à contourner.
- **Voxtral / audio** : l'acceptation d'un `AudioBlock` par Converse pour ces modèles est **une affirmation de source tierce**. Si tous les cas audio échouent, vérifie dans `models.json` les `inputModalities` ; essaie un petit WAV **mono** (`transcriptions/input_wav`) avant de conclure ; les cas `size_*` et `input_wav_stereo` mesurent précisément ces limites.
- **`count_tokens`** : forme `input={"converse": {...}}`, support limité à certains modèles ⇒ un refus est un résultat.
- **InvokeModel natif** (`invoke_claude_native_*`, `invoke_nova_native`) : les corps (`anthropic_version: bedrock-2023-05-31` ; `schemaVersion: messages-v1`) sont écrits d'après ma connaissance, **non validés par AWS**. Un 400 de schéma ⇒ relis la doc AWS du modèle avant de conclure « non supporté ».
- **`inferenceConfig`** : certains modèles rejettent des paramètres ; on n'envoie que `maxTokens`. Ne rajoute pas de `temperature` globalement.
- **Limites image** (3,75 Mo / 8000 px / 20 images) : annoncées par la doc AWS (relevées via un résumé de recherche, **non confirmées sur la page**). Les cas `size_3_60mb`/`3_85mb`/`4_10mb`, `huge_8200x8200`, `images_20/21` servent à les mesurer ; ne les présente comme faits qu'après run.
- **Streaming** : `ConverseStream` lève parfois des exceptions en cours de flux ; `execute_bedrock` les conserve dans `events` + `error`.
- **LiteLLM** : peut normaliser/transformer (ex. conversion d'URL d'image en base64 dans le proxy, remappage de paramètres) ; l'erreur observée peut être celle de LiteLLM, pas du provider.

## 11. Interdits et accords préalables

**Interdit** (sauf accord explicite et écrit de l'humain dans la conversation) :
- lancer `--security` (SSRF) ou `--heavy` ;
- `git push`, ou tout envoi des captures hors du poste (mail, ticket, gist, service externe, outil d'IA externe) — les captures peuvent contenir des identifiants internes (§3). Commit **local** autorisé, sans secrets ;
- utiliser un autre SDK que boto3 (Bedrock) / httpx (HTTP) ; ajouter une dépendance non listée sans le dire ;
- désactiver la vérification TLS ; stocker des identifiants dans le dépôt ;
- modifier ou supprimer `captures/openai/` ; renommer des ids de cas existants ; supprimer des cas pour « faire vert » ;
- mocker un résultat, éditer un `response.json`, ou écrire dans une observation un comportement non observé ;
- contourner un refus/une erreur en changeant de modèle sans le dire (si tu changes de modèle, c'est un **autre résultat**, à noter).

**Autorisé sans demander** : tout appel des cas par défaut sur les cibles configurées par l'humain ; corriger des bugs de script ; ajouter des cas **supplémentaires** (nouveau nom) ; régénérer `catalog` et `REPORT.md` ; compléter la documentation conformément au §9.

## 12. À demander à l'humain (ne décide pas seul)

- Quels **modèles Bedrock** utiliser par rôle, et dans **quelle région**.
- Quels **alias LiteLLM** mapper à quels rôles ; lesquels sont autorisés.
- Accord pour `--security` / `--heavy`, et pour tout dépassement raisonnable de coût/quota.
- Que faire de **TTS / audio en sortie** côté Bedrock (autre service AWS ? LiteLLM vers un autre provider ? ne pas exposer ?) — choix produit.
- **Politique de limites** de la gateway (taille image/audio, nombre d'images, formats acceptés) — les constats OpenAI (22 Mo / 8200 px acceptés) et Bedrock (3,75 Mo annoncé) divergent ; la décision est produit, pas technique.
- Comment les résultats sortent du poste pro (§11), et s'il faut **caviarder** les identifiants avant.
- Tout besoin d'un fichier audio/image d'exemple réel (`sample.m4a|mp4|webm|mpga|mpeg`) : fournis-toi-en un synthétique/public ou demande.

## 13. Constats OpenAI à garder en tête pour interpréter les autres cibles

Détail et preuves : [observations-openai.md](observations-openai.md). Ceux qui structurent la comparaison :
- OpenAI **ignore** les champs inconnus et plusieurs bornes (4097 caractères TTS, `temperature=2`, `voice` absent) ; accepte **26 MiB d'audio**, **22 Mo d'image**, **8200 px**, ≥ 12 images → les limites documentées ne sont pas appliquées.
- Image : URL http/https (téléchargée par OpenAI) **et** data-URL ; format détecté sur le **contenu**, MIME ignoré ; base64 nu refusé ; bmp/tiff/svg refusés ; GIF animé → 1ʳᵉ image.
- STT : le type de fichier est déduit de l'**extension du nom** ; `.opus`/`.aac`/sans extension refusés ; `usage` = durée (`whisper-1`) ou tokens (`gpt-4o-*`) ; silence/bruit ⇒ **texte halluciné**.
- Audio chat (`gpt-audio`) : `input_audio` wav|mp3 minuscules, format déclaré = contenu ; sortie `message.audio{id,data,transcript,expires_at}` ; **streaming sans `finish_reason`, un chunk sans `choices`, `usage` non terminal** ; WAV de sortie à en-tête « streaming » (`0xFFFFFFFF`) ; l'audio du tour précédent est re-facturé.
- Erreurs hors norme : 431 HTML (`/audio/speech` + modèle de chat), 500 (image sur modèle texte, `n=2` audio), messages = `repr` Python.

## 14. Carte du code (si tu dois le modifier)

| Fichier | Rôle |
|---|---|
| `mmprobe/cli.py` | commandes : `list`, `catalog`, `fixtures`, `run`, `report`, `bedrock-models`, `http-models` ; option globale `--provider http\|bedrock`, `--env-file`, `--label` |
| `mmprobe/config.py` | `Config` ; env `MM_*`, rôles HTTP (`DEFAULT_MODELS`, `-` = désactivé), rôles Bedrock (`BEDROCK_ROLES`, `MM_BEDROCK_MODEL_*`) |
| `mmprobe/http.py` | transport HTTP brut + `Exchange` (objet commun HTTP/boto3) |
| `mmprobe/bedrock.py` | transport boto3 : `BCall`, `execute_bedrock`, validation hors-ligne, `CLIENT_FACTORY` (injection de test) |
| `mmprobe/capture.py` | écrit `request.json`, `response.json`, `curl.sh`/`replay.py`, audio extrait, résumés de flux |
| `mmprobe/runner.py` | `Ctx.call` (dispatch HTTP/boto3), sélection (`-k`, tags, provider), `index.json` |
| `mmprobe/report.py` | résumés, `REPORT.md`, `COMPARE_*.md`, catalogue |
| `mmprobe/cases/{speech,transcriptions,chat_image,chat_audio}.py` | cas **HTTP** (`@case`) |
| `mmprobe/cases/bedrock_{image,audio,util}.py` | cas **Bedrock** (`@bcase`) |
| `mmprobe/fixtures.py` | fixtures locales, parole via TTS, variantes calibrées générées à la demande |
| `tools/mock_server.py`, `tools/selftest_bedrock.py` | tests hors-ligne de la mécanique (ne reproduisent pas les providers) |

Conventions : un cas = une fonction décorée ; `ctx.call(req, step=…)` pour chaque appel (multi-étapes ⇒ `step`) ; `ctx.skip(raison)` pour ignorer ; `DROP` retire une clé du body ; tags `neg`, `heavy`, `security`, `probe`… Pour ajouter un cas : copie un voisin, garde un **id parallèle** si le scénario existe dans l'autre cible, relance `catalog`, vérifie avec `run --dry-run`.

## 15. Pièges connus de l'environnement de développement

- Développé sous WSL ; chemins POSIX. Les captures contiennent des octets (audio/images) : ne les ouvre pas comme du texte.
- `-k` accepte un glob **ou une sous-chaîne** de l'id (`-k transcriptions/model_` sélectionne tous les `model_*`) ; plusieurs `-k` = OU. `--tags` / `--skip-tags` filtrent par tags.
- Le module `wave` de Python lit mal les WAV d'OpenAI (tailles d'en-tête = `0xFFFFFFFF`) : utiliser `speech_en_clean.wav` (en-tête corrigé, généré à la demande) pour les cas Bedrock ; `speech_en.wav` reste pour tester précisément ce cas (`input_wav_streaming_header`).
- La valeur d'une variable déjà exportée dans le shell **prime** sur le fichier `.env` passé en `--env-file`.
- `report` sans `--label`/`--env-file` cible le label déduit de la config ; ajoute `--label` explicitement quand tu relis une autre cible.
