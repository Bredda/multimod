# AGENTS.md — lis `docs/HANDOFF.md` AVANT toute action

Ce dépôt (`mmprobe`) sonde des providers (OpenAI, LiteLLM en HTTP brut ; Bedrock en boto3) pour cadrer la multimodalité d'une gateway IA d'entreprise, et **capture l'entrée/sortie exacte de chaque cas**. Le document de reprise complet est [docs/HANDOFF.md](docs/HANDOFF.md) (décisions closes, interdits, runbooks, livrables).

Règles non négociables (détail et exceptions : HANDOFF §1, §3, §8, §11) :

1. **Un échec est un résultat** : ne jamais mocker, éditer une réponse, changer un `expect` pour « faire vert », ni écrire un comportement non observé. Distinguer `SCRIPT-ERROR` (à corriger) d'une erreur du provider (à documenter).
2. **OpenAI/LiteLLM : HTTP brut `httpx`, pas de SDK. Bedrock : boto3 uniquement.** Ne pas sonder la gateway.
3. **`captures/openai/` est figée** (OpenAI est bloqué ici) : ne pas la régénérer ni la modifier. Ne pas utiliser `fixtures` pour refaire la parole.
4. **Données synthétiques uniquement** dans les requêtes ; **aucun secret** dans le dépôt, les captures ou les docs ; toujours passer `--env-file` explicitement.
5. **Sans accord explicite de l'humain** : pas de `--security`, pas de `--heavy`, pas de `git push` ni d'envoi des captures hors du poste, pas de TLS désactivé, pas de nouveau SDK/dépendance.
6. **Ne pas renommer ni supprimer d'id de cas** (un même id = un même scénario entre cibles) ; on ajoute des cas, on n'en retire pas.
7. Documentation en **français**, chaque affirmation étiquetée (`[obs]` + id de cas, `[AWS]`/`[LiteLLM]` + lien, `[tiers]`, `[hyp]`) ; pas de généralisation à partir d'un seul modèle.
8. En cas de doute sur un choix produit (limites, TTS côté Bedrock, modèles, accès) : **demander** (HANDOFF §12).
