#!/usr/bin/env bash
# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet
curl -sS -i -X POST "$MM_BASE_URL/audio/transcriptions" \
  -H "Authorization: Bearer $MM_API_KEY" \
  -F 'model=gpt-4o-transcribe' \
  -F 'file=@fixtures/corrupt.mp3;filename=corrupt.mp3;type=audio/mpeg'
