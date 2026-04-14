# ABOX - Audio Box

Система озвучки текстов на русском языке с использованием Edge TTS.

## 🎤 Основные функции:
- Озвучка текстов в MP3
- Предобработка с ударениями
- Работа с голосами
- Визуализация ударений

## 📁 Структура:
- `tts/` - генерация TTS
- `voices/` - работа с голосами  
- `preprocessor/` - предобработка
- `visualizer/` - визуализация
- `data/dictionaries/` - словари ударений

## 🚀 Использование:
```bash
# Озвучка текста
speech document.txt

# Работа с голосами
list_voices

# Тренировка ударений
python3 stress_trainer.py --stats
```

## ⚙️ Конфигурация:
- `config/aconfig.txt` - настройки ABOX
- `data/dictionaries/` - словари ударений

## 📋 Список модулей:
- `tbox_tts_gen.py` - главный генератор TTS
- `tbox_tts_preprocessor.py` - предобработка текста
- `tbox_tts_ethalon.py` - эталонные голоса
- `tbox_tts_visualizer.py` - визуализация ударений
- `tbox_stress_trainer.py` - тренажер ударений
- `tbox_text_marker.py` - маркер проблемных слов
- `tbox_punctuation_ai.py` - ИИ для пунктуации
- `list_voices.py` - список доступных голосов
- `tbox_voice_trainer.py` - тренажер голосов

## 🔗 Связь с TBOX:
- TBOX обрабатывает тексты и создает словари
- ABOX использует готовые словари для озвучки
- Общие данные в `shared/` и `config/`
