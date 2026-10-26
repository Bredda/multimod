#!/usr/bin/env bash
# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet
curl -sS -i -X POST "$MM_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $MM_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @/home/bredda/workspace/multimod/captures/openai/chat-audio/multi_turn_audio_id_unknown/request.raw.json
