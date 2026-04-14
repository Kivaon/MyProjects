# Транскрипция аудио: локальная и облачная обработка

## 📋 Быстрый старт

### По умолчанию (локальная обработка):
```bash
python tbox_extract_audio.py
# или с конкретным файлом:
python tbox_extract_audio.py /path/to/audio.mp3
```

### С облачной обработкой:
```bash
# OpenAI Whisper API
python tbox_extract_audio.py --provider=openai

# Google Cloud Speech
python tbox_extract_audio.py --provider=google

# Azure Speech Services
python tbox_extract_audio.py --provider=azure
```

---

## ⚙️ Конфигурация

Отредактируйте `config.txt`:

```ini
# По умолчанию локальная
TRANSCRIBE_PROVIDER=local

# Для OpenAI
OPENAI_API_KEY=sk-...your-key...

# Для Google Cloud
GOOGLE_CLOUD_KEY_FILE=/path/to/credentials.json

# Для Azure
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
```

---

## 🔄 Восстановление после сбоя

Все чанки сохраняются **сразу же** после обработки. При сбое:

1. Скрипт создаёт `.progress.json` файл
2. При переапуске автоматически продолжит с последнего обработанного чанка
3. После успеха файл прогресса удаляется

**Пример:**
```
260129_1234-audio_audio_raw.txt       ← основной файл
260129_1234-audio_audio_raw.progress.json  ← прогресс (удалится при завершении)
```

---

## 📊 Сравнение провайдеров

| Провайдер | Качество | Цена | Про | Против |
|-----------|----------|------|-----|--------|
| **LOCAL** | ⭐⭐⭐⭐ | Бесплатно | Без интернета, быстро | Требует CPU |
| **OPENAI** | ⭐⭐⭐⭐⭐ | $0.006/мин | Лучшее для иврита/русского | Нужен API ключ, интернет |
| **GOOGLE** | ⭐⭐⭐⭐ | $1.44/ч | Хорошее качество | Сложнее настроить |
| **AZURE** | ⭐⭐⭐⭐ | $1/ч | Интеграция с MS | Дороже |

---

## 🔑 Получение API ключей

### OpenAI Whisper API
1. Перейди на https://platform.openai.com/api-keys
2. Создай новый ключ
3. Скопируй в `config.txt`
4. Установи: `pip install openai`

**Пример использования:**
```bash
# Первая транскрипция
python tbox_extract_audio.py --provider=openai

# Если прервалась - просто переапусти, продолжит с того же места
python tbox_extract_audio.py --provider=openai
```

### Google Cloud Speech
1. Создай проект в Google Cloud Console
2. Скачай JSON с ключом
3. Скопируй путь в `config.txt`
4. Установи: `pip install google-cloud-speech`

### Azure Speech
1. Перейди на Azure Portal
2. Создай ресурс "Speech Services"
3. Скопируй ключ и регион в `config.txt`
4. Установи: `pip install azure-cognitiveservices-speech`

---

## 📝 Формат вывода

Все провайдеры дают одинаковый формат файла:

```
TITLE: audio_name
SOURCE: AUDIO_TRANSCRIBE (OPENAI) (v1.3.cloud-ready)
DATE: 2026-01-29 15:23:45
STATUS: Completed
----------------------------------------

[CHUNK 1 | 0:00 → 0:15]
Текст первого сегмента...

[CHUNK 2 | 0:15 → 0:31]
Текст второго сегмента...

[CHUNK 3 | 0:31 → 0:47]
Текст третьего сегмента...
```

---

## 🚨 Обработка ошибок

### Таймауты и I/O ошибки
- Автоматически повторяет **3 раза** с задержкой 2 сек
- Все повторы логируются

### Memory Error
- **Не повторяет** (это критическая ошибка)
- Сохранённые чанки остаются в файле

### API ошибки (OpenAI, Google, Azure)
- Если ключ неверный → ошибка при первой попытке
- Если лимит превышен → попытается 3 раза

### Disk Full
- Скрипт остановится с ошибкой
- Все обработанные чанки сохранены

---

## 💡 Советы

1. **Для надёжности** — используй `--provider=local` для автономной работы
2. **Для качества на иврите/русском** — используй `--provider=openai`
3. **Для больших файлов** — облачные провайдеры безопаснее (не зависит от RAM)
4. **Для тестирования** — используй локальную обработку

---

## 🔧 Технические детали

### Локальная обработка
- **Модель**: Faster-Whisper Medium
- **Вычисления**: CPU
- **Формат**: int8 (быстро и экономно)
- **Метод**: beam_size=5 (высокая точность)

### Облачные API
- **OpenAI**: v1 Audio API (latest)
- **Google**: Speech-to-Text v1p1beta1
- **Azure**: Unified Speech Service

### Восстановление
- Сохраняет прогресс в JSON после каждого чанка
- При сбое возобновляет без пересчёта уже обработанного
- Максимум 3 попытки на каждый чанк
