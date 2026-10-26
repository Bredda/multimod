#!/usr/bin/env bash
# Rejeu : MM_BASE_URL et MM_API_KEY doivent être définis ; lancer depuis la racine du projet
curl -sS -i -X POST "$MM_BASE_URL/audio/transcriptions" \
  -H "Authorization: Bearer $MM_API_KEY" \
  -F 'model=gpt-4o-transcribe' \
  -F 'response_format=verbose_json' \
  -F 'timestamp_granularities[]=word' \
  -F 'file=@fixtures/speech_en.mp3;filename=speech_en.mp3;type=audio/mpeg'
