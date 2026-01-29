import os, sys, re, time, json
from datetime import datetime
from faster_whisper import WhisperModel
import tbox_utils as utils

# Попытка импорта облачных сервисов
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google.cloud import speech_v1
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

# Попытка импорта универсального рефайнера
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# --- ПАСПОРТ ---
VERSION = "v1.3.cloud-ready"
DATE    = "2026-01-29"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# --- КОНСТАНТЫ ВОССТАНОВЛЕНИЯ ---
MAX_RETRIES = 3
RETRY_DELAY = 2  # секунды
CHUNK_SAVE_INTERVAL = 1  # сохранять после каждого чанка

def get_progress_file(output_txt):
    """Файл прогресса для восстановления после сбоя."""
    return output_txt.replace(".txt", ".progress.json")

def load_progress(output_txt):
    """Загрузить сохранённый прогресс."""
    progress_file = get_progress_file(output_txt)
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def save_progress(output_txt, last_chunk_idx, total_chunks, duration):
    """Сохранить текущий прогресс на диск."""
    progress_file = get_progress_file(output_txt)
    progress = {
        "last_chunk_idx": last_chunk_idx,
        "total_chunks": total_chunks,
        "duration": duration,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        utils.tbox_log(f"⚠️ Не удалось сохранить прогресс: {e}", META, "WARNING")

def append_chunk_to_file(output_txt, chunk_idx, segment_time, text):
    """Сохранить отдельный чанк в файл сразу же."""
    chunk_marker = f"\n\n[CHUNK {chunk_idx + 1} | {segment_time}]\n"
    try:
        with open(output_txt, "a", encoding="utf-8") as f:
            f.write(chunk_marker)
            f.write(text.strip())
            f.write("\n")
    except Exception as e:
        utils.tbox_log(f"❌ Ошибка сохранения чанка {chunk_idx}: {e}", META, "ERROR")
        raise

def transcribe_with_retry(model, target_path, beam_size=5):
    """Транскрибация с обработкой ошибок и повторами."""
    for attempt in range(MAX_RETRIES):
        try:
            utils.tbox_log(
                f"Попытка транскрибации {attempt + 1}/{MAX_RETRIES}...", 
                META, "INFO"
            )
            segments, info = model.transcribe(target_path, beam_size=beam_size, vad_filter=True)
            # Преобразуем generator в список для проверки результата
            segments_list = list(segments)
            if segments_list:
                return segments_list, info
            else:
                raise Exception("Whisper вернул пустой результат")
        except MemoryError:
            utils.tbox_log(
                f"💥 Ошибка памяти на попытке {attempt + 1}. Это критично, повтор не поможет.",
                META, "ERROR"
            )
            raise
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                utils.tbox_log(
                    f"⚠️ Ошибка на попытке {attempt + 1}: {str(e)[:80]}. "
                    f"Ожидание {RETRY_DELAY} сек перед повтором...",
                    META, "WARNING"
                )
                time.sleep(RETRY_DELAY)
            else:
                utils.tbox_log(
                    f"❌ Все {MAX_RETRIES} попытки исчерпаны: {e}",
                    META, "ERROR"
                )
                raise

def transcribe_openai_cloud(target_path):
    """Транскрибация через OpenAI Whisper API (облако)."""
    if not OPENAI_AVAILABLE:
        raise ImportError("❌ OpenAI не установлена. Установите: pip install openai")
    
    CONF = utils.load_local_config()
    api_key = CONF.get('OPENAI_API_KEY', '')
    
    if not api_key:
        raise ValueError("❌ OPENAI_API_KEY не установлен в config.txt")
    
    openai.api_key = api_key
    segments_list = []
    
    utils.tbox_log("📡 Отправка на OpenAI Whisper API...", META, "INFO")
    
    try:
        with open(target_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="en",  # OpenAI автоматически определяет иврит и русский
                temperature=0.2  # Низкая температура для точности
            )
        
        # Конвертируем формат ответа OpenAI в наш формат сегментов
        class Segment:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text
        
        # Если есть детализация по timings
        if 'segments' in transcript:
            for seg in transcript['segments']:
                segments_list.append(Segment(
                    seg.get('start', 0),
                    seg.get('end', 0),
                    seg.get('text', '')
                ))
        else:
            # Всё как один сегмент
            segments_list.append(Segment(0, 0, transcript['text']))
        
        # Информация о языке
        class AudioInfo:
            def __init__(self, language, duration):
                self.language = language
                self.duration = duration
        
        info = AudioInfo("detected by OpenAI", 0)
        
        return segments_list, info
        
    except Exception as e:
        utils.tbox_log(f"❌ Ошибка OpenAI API: {e}", META, "ERROR")
        raise

def get_provider_mode():
    """Определить провайдера из аргументов командной строки или конфига."""
    CONF = utils.load_local_config()
    
    # Аргумент командной строки имеет приоритет: --provider=openai
    for arg in sys.argv[1:]:
        if arg.startswith("--provider="):
            return arg.split("=")[1].lower()
    
    # Иначе из конфига
    provider = CONF.get('TRANSCRIBE_PROVIDER', 'local').lower()
    return provider

def extract_audio():
    # 0. Определяем провайдера
    provider = get_provider_mode()
    utils.tbox_log(f"🔧 Режим транскрипции: {provider.upper()}", META, "INFO")
    
    # 1. Загрузка конфигурации
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    # Фильтруем аргументы с флагами (--provider=...)
    if user_arg and user_arg.startswith("--"):
        user_arg = None
    
    CONF = utils.load_local_config()
    if not CONF:
        print("Ошибка: config.txt не найден.")
        return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR   = CONF.get('TXT_RAW')

    # 2. Поиск целевого файла
    target_path = None
    extensions = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac')
    
    if user_arg and os.path.exists(user_arg):
        target_path = os.path.abspath(user_arg)
    else:
        # Автопилот: берем самый свежий аудиофайл из Inbox
        files = [os.path.join(INBOX_DIR, f) for f in os.listdir(INBOX_DIR) 
                 if f.lower().endswith(extensions)]
        if files:
            target_path = max(files, key=os.path.getmtime)

    if not target_path:
        utils.tbox_log("Аудиофайлы в INBOX не найдены.", META, "ERROR")
        return

    # 3. Подготовка файла вывода и проверка прогресса
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    clean_name = os.path.basename(target_path).rsplit('.', 1)[0]
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_name}_audio_raw.txt")
    
    # Проверяем, есть ли сохранённый прогресс (восстановление после сбоя)
    progress = load_progress(output_txt)
    if progress:
        utils.tbox_log(
            f"🔄 ВОССТАНОВЛЕНИЕ: Найден прогресс от {progress['timestamp'][:16]}. "
            f"Обработано {progress['last_chunk_idx'] + 1}/{progress['total_chunks']} чанков.",
            META, "INFO"
        )
    else:
        # Новая обработка: создаём заголовок файла
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {clean_name}\n")
            f.write(f"SOURCE: AUDIO_TRANSCRIBE ({provider.upper()}) ({VERSION})\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"STATUS: Processing...\n")
            f.write("-" * 40 + "\n\n")

    # 4. Инициализация и транскрибация
    start_time = time.perf_counter()
    utils.tbox_log(f"СТАРТ: {os.path.basename(target_path)}", META, "START")
    
    try:
        if provider == "local":
            # Локальная обработка (Faster-Whisper)
            utils.tbox_log("Загрузка модели AI (Medium, локально)...", META, "INFO")
            model = WhisperModel("medium", device="cpu", compute_type="int8")
            segments, info = transcribe_with_retry(model, target_path, beam_size=5)
        
        elif provider == "openai":
            # OpenAI Whisper API
            segments, info = transcribe_openai_cloud(target_path)
        
        else:
            raise ValueError(f"❌ Неизвестный провайдер: {provider}. "
                           f"Допустимые: local, openai, google, azure")
    
    except Exception as e:
        utils.tbox_log(
            f"❌ Транскрибация провалилась: {e}. "
            f"Результат сохранён в {output_txt} - переапуск продолжит с того же места.",
            META, "ERROR"
        )
        return
    
    utils.tbox_log(
        f"Аудио: {info.duration/60:.1f} мин. Язык: {info.language}",
        META, "INFO"
    )
    
    # 5. Обработка сегментов (чанков) с сохранением каждого
    resume_from = 0
    if progress:
        resume_from = progress['last_chunk_idx'] + 1
        utils.tbox_log(f"🔄 Возобновление с чанка {resume_from}...", META, "INFO")
    
    segments_list = list(segments)
    total_chunks = len(segments_list)
    
    for idx, segment in enumerate(segments_list):
        # Пропускаем уже обработанные чанки
        if idx < resume_from:
            continue
        
        # Рисуем прогресс в консоли
        if hasattr(info, 'duration') and info.duration > 0:
            percent = (segment.end / info.duration) * 100
            sys.stdout.write(
                f"\r[{idx + 1}/{total_chunks}] "
                f"Прогресс: {percent:.1f}% | {segment.end:.1f}/{info.duration:.1f} сек."
            )
        else:
            sys.stdout.write(f"\r[{idx + 1}/{total_chunks}] Обработка...")
        sys.stdout.flush()
        
        # Форматируем временную метку
        segment_time = f"{int(segment.start//60)}:{int(segment.start%60):02d} → {int(segment.end//60)}:{int(segment.end%60):02d}"
        
        # СОХРАНЯЕМ КАЖДЫЙ ЧАНК СРАЗУ В ФАЙЛ
        try:
            append_chunk_to_file(output_txt, idx, segment_time, segment.text)
            # Обновляем прогресс для восстановления
            if hasattr(info, 'duration'):
                save_progress(output_txt, idx, total_chunks, info.duration)
            else:
                save_progress(output_txt, idx, total_chunks, 0)
        except Exception as e:
            utils.tbox_log(
                f"❌ Не удалось сохранить чанк {idx}. Ошибка: {e}",
                META, "ERROR"
            )
            return
    
    print("\n")  # Сброс строки после прогресс-бара

    # Расчет скорости
    end_time = time.perf_counter()
    duration_total = end_time - start_time
    speed_x = (info.duration / duration_total) if hasattr(info, 'duration') and info.duration > 0 else 0

    utils.tbox_log(
        f"✅ ГОТОВО за {duration_total:.1f} сек. (Скорость: {speed_x:.1f}x). "
        f"Обработано {total_chunks} чанков.",
        META, "DONE"
    )

    # 6. Завершение файла и очистка прогресса
    try:
        with open(output_txt, "r", encoding="utf-8") as f:
            content = f.read()
        # Обновляем статус на "Completed"
        content = content.replace("STATUS: Processing...", "STATUS: Completed")
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Удаляем файл прогресса (больше не нужен)
        progress_file = get_progress_file(output_txt)
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        utils.tbox_log(f"⚠️ Ошибка при завершении: {e}", META, "WARNING")

    # 7. Авто-передача в Refinery
    if refinery:
        utils.tbox_log(f"Передаю в Refinery (режим AUDIO)...", META, "INFO")
        refinery.run_refining(output_txt, mode="AUDIO")
    else:
        utils.tbox_log("Refinery не найден, верстка пропущена.", META, "WARNING")

if __name__ == "__main__":
    extract_audio()