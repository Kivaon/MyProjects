import os, sys, re
from datetime import datetime
from faster_whisper import WhisperModel
import tbox_utils as utils

# Попытка импорта рефайнера
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# --- ПАСПОРТ ---
VERSION = "v1.0.whisper"
DATE    = "2026-01-26"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def extract_audio():
    # 1. Сбор путей и конфига
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    CONF = utils.load_local_config()
    if not CONF: return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR   = CONF.get('TXT_RAW')

    # 2. Поиск аудиофайла (mp3, wav, m4a, ogg)
    target_path = None
    extensions = ('.mp3', '.wav', '.m4a', '.ogg', '.flac')
    
    if user_arg and os.path.exists(user_arg):
        target_path = os.path.abspath(user_arg)
    else:
        files = [os.path.join(INBOX_DIR, f) for f in os.listdir(INBOX_DIR) if f.lower().endswith(extensions)]
        if files:
            target_path = max(files, key=os.path.getmtime)

    if not target_path:
        utils.tbox_log("Аудиофайлы не найдены в INBOX.", META, "ERROR")
        return

    # 3. Инициализация модели Whisper
    utils.tbox_log("Загрузка модели Whisper (Medium)... Это может занять время при первом запуске.", META, "INFO")
    # На Mac используем CPU (модели M1/M2/M3 справляются отлично)
    model = WhisperModel("medium", device="cpu", compute_type="int8")

    # 4. Транскрибация
    utils.tbox_log(f"Старт транскрибации: {os.path.basename(target_path)}", META, "START")
    
    segments, info = model.transcribe(target_path, beam_size=5)
    
    # Собираем текст по сегментам
    full_text = []
    utils.tbox_log(f"Язык определен как: {info.language} (вероятность {info.language_probability:.2f})", META, "INFO")
    
    for segment in segments:
        # Пишем в консоль прогресс (по времени аудио)
        sys.stdout.write(f"\rОбработано: {segment.end:.1f} сек.")
        sys.stdout.flush()
        full_text.append(segment.text)
    
    print("\n") # Перенос после прогресс-бара

    # 5. Сохранение RAW
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    clean_name = os.path.basename(target_path).rsplit('.', 1)[0]
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_name}_audio_raw.txt")

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {clean_name}\n")
        f.write(f"SOURCE: AUDIO_TRANSCRIPT ({info.language})\n")
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 30 + "\n\n")
        f.write(" ".join(full_text))

    utils.tbox_log(f"Транскрипт готов: {os.path.basename(output_txt)}", META, "DONE")

    # 6. Передача в Refinery
    if refinery:
        utils.tbox_log("Запуск Refinery (режим AUDIO)...", META, "INFO")
        refinery.run_refining(output_txt, mode="AUDIO")

if __name__ == "__main__":
    extract_audio()