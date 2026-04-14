#!/bin/bash
# Полный цикл: Gemini предобработка + TTS озвучка

# 1. Подготовка текста через Gemini
echo "🤖 Подготовка текста через Gemini..."
PYTHONPATH=/Users/kivaonmac/Documents/AI_Lab/BIN/TBOX python3 /Users/kivaonmac/Documents/AI_Lab/BIN/ABOX/gemini_preprocessor.py "$1" --output=prepared_text.txt

# 2. Озвучка подготовленного текста
echo "🎤 Озвучка подготовленного текста..."
PYTHONPATH=/Users/kivaonmac/Documents/AI_Lab/BIN/TBOX python3 /Users/kivaonmac/Documents/AI_Lab/BIN/ABOX/tbox_tts.py --male prepared_text.txt

echo "✅ Готово!"
