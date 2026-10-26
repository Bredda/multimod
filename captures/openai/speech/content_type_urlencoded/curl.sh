#!/usr/bin/env bash
# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet
curl -sS -i -X POST "$MM_BASE_URL/audio/speech" \
  -H "Authorization: Bearer $MM_API_KEY" \
  --data-urlencode 'model=gpt-4o-mini-tts' \
  --data-urlencode 'input=Hello! This is a test of the text to speech endpoint.' \
  --data-urlencode 'voice=alloy'
