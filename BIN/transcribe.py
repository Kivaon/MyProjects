import os
import whisper
import shutil
import sys
from datetime import datetime

# --- ЗАГРУЗКА КОНФИГА ---
def load_config():
    path = os.path.expanduser("~/Documents/AI_Lab/config.txt")
    cfg = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                cfg[k] = os.path.expanduser(v)
    return cfg

CFG = load_config()
AUDIO_DIR = CFG.get("AUDIO_DIR")
TXT_DIR = CFG.get("TXT_DIR")

def get_now():
    return datetime.now().strftime("%H:%M:%S")

def main():
    # Создаем папки
    archive_dir = os.path.join(AUDIO_DIR, "ARCHIVE")
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(archive_dir, exist_ok=True)

    # Ищем mp3 или wav
    files = [f for f in os.listdir(AUDIO_DIR) if f.endswith((".mp3", ".wav", ".m4a"))]
    if not files:
        print("В папке AUDIO нет новых файлов.")
        return

    # Берем самый свежий файл
    file_name = max(files, key=lambda x: os.path.getmtime(os.path.join(AUDIO_DIR, x)))
    audio_path = os.path.join(AUDIO_DIR, file_name)

    print(f"[{get_now()}] >>> ЗАГРУЗКА МОДЕЛИ WHISPER...")
    # 'base' - быстро, 'medium' или 'large' - качественнее для иврита
    model = whisper.load_model("medium") 

    print(f"[{get_now()}] >>> РАСПОЗНАВАНИЕ: {file_name}")
    result = model.transcribe(audio_path, language="he") # Указываем иврит

    # Сохраняем результат в TXT
    txt_name = f"{os.path.splitext(file_name)[0]}.txt"
    txt_path = os.path.join(TXT_DIR, txt_name)
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])

    print(f"[{get_now()}] ✅ Текст сохранен: {txt_name}")

    # Архивация тяжелого аудио
    shutil.move(audio_path, os.path.join(archive_dir, file_name))
    print(f"[{get_now()}] 📦 Аудио перемещено в архив.")

if __name__ == "__main__":
    main()