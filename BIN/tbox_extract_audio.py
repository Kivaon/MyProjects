import os, sys, re, time
from datetime import datetime
from faster_whisper import WhisperModel
import tbox_utils as utils

# Попытка импорта универсального рефайнера
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# --- ПАСПОРТ ---
VERSION = "v1.1.stable"
DATE    = "2026-01-26"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def extract_audio():
    # 1. Загрузка конфигурации
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
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

    # 3. Инициализация нейросети (Whisper)
    # Используем 'medium' для лучшего качества иврита и русского
    # compute_type="int8" ускоряет работу на CPU в 2 раза
    utils.tbox_log("Загрузка модели AI (Medium)...", META, "INFO")
    try:
        model = WhisperModel("medium", device="cpu", compute_type="int8")
    except Exception as e:
        utils.tbox_log(f"Ошибка загрузки модели: {e}", META, "ERROR")
        return

    # 4. Транскрибация с логированием времени
    start_time = time.perf_counter()
    utils.tbox_log(f"СТАРТ: {os.path.basename(target_path)}", META, "START")
    
    # beam_size=5 дает высокую точность
    segments, info = model.transcribe(target_path, beam_size=5, vad_filter=True)
    
    utils.tbox_log(f"Аудио: {info.duration/60:.1f} мин. Язык: {info.language}", META, "INFO")
    
    full_text = []
    for segment in segments:
        # Рисуем прогресс в консоли
        percent = (segment.end / info.duration) * 100
        sys.stdout.write(f"\rПрогресс: {percent:.1f}% | {segment.end:.1f}/{info.duration:.1f} сек.")
        sys.stdout.flush()
        full_text.append(segment.text)
    
    print("\n") # Сброс строки после прогресс-бара

    # Расчет скорости
    end_time = time.perf_counter()
    duration_total = end_time - start_time
    speed_x = info.duration / duration_total

    utils.tbox_log(f"ГОТОВО за {duration_total:.1f} сек. (Скорость: {speed_x:.1f}x)", META, "DONE")

    # 5. Сохранение результата в RAW_DIR
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    clean_name = os.path.basename(target_path).rsplit('.', 1)[0]
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_name}_audio_raw.txt")

    # Формируем структуру файла для Refinery
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {clean_name}\n")
        f.write(f"SOURCE: AUDIO_LOCAL_WHISPER ({VERSION})\n")
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 30 + "\n\n")
        f.write(" ".join(full_text).strip())

    # 6. Авто-передача в Refinery
    if refinery:
        utils.tbox_log(f"Передаю в Refinery (режим AUDIO)...", META, "INFO")
        refinery.run_refining(output_txt, mode="AUDIO")
    else:
        utils.tbox_log("Refinery не найден, верстка пропущена.", META, "WARNING")

if __name__ == "__main__":
    extract_audio()