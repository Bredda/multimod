#!/usr/bin/env bash
# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet
curl -sS -i -X POST "$MM_BASE_URL/audio/speech" \
  -H "Content-Type: application/json" \
  --data-binary @/home/bredda/workspace/multimod/captures/openai/speech/auth_missing/request.raw.json
