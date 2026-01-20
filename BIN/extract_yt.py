# Version: 3.16
# Description: RESTORED working logic + Sync with 02_TXT and Metadata headers

import sys, os, configparser, re
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def load_config():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "config.txt")
    config = configparser.ConfigParser()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = '[DEFAULT]\n' + f.read()
        config.read_string(content)
        return config['DEFAULT'], base_dir
    except:
        return {}, base_dir

CONF, BASE_DIR = load_config()
# Целевая папка теперь строго 02_TXT
TARGET_DIR = os.path.join(BASE_DIR, "02_TXT")

def get_video_metadata(vid):
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            upload_date = info.get('upload_date', '00000000')
            formatted_date = f"{upload_date[2:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            author = info.get('uploader', 'Unknown').replace(" ", "_")
            title = info.get('title', 'Untitled_Video')
            return formatted_date, author, title
    except:
        return "00-00-00", "Unknown", "Untitled_Video"

def main():
    if len(sys.argv) < 2:
        print("Ошибка: Введите ID видео или ссылку")
        return
    
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    try:
        print(f"[*] Запрашиваю данные ролика {vid}...")
        upload_date, author, title = get_video_metadata(vid)
        
        # ТВОЯ РАБОЧАЯ ЛОГИКА СУБТИТРОВ
        api = YouTubeTranscriptApi()
        data = api.list(vid).find_transcript(['he', 'iw', 'en']).fetch()
        
        full_text_list = []
        for t in data:
            if isinstance(t, dict):
                full_text_list.append(t.get('text', ''))
            else:
                full_text_list.append(getattr(t, 'text', ''))
        
        text = " ".join(full_text_list).replace('\n', ' ')
        
        # Формирование имени файла (твой формат + префикс времени для сортировки)
        now_time = datetime.now().strftime("%y%m%d_%H%M")
        file_name = f"{now_time}-{author}-{upload_date}-{vid}.txt"
        path = os.path.join(TARGET_DIR, file_name)
        
        # Запись с шапкой (Линк и Название)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\n")
            f.write(f"LINK: https://www.youtube.com/watch?v={vid}\n")
            f.write(f"AUTHOR: {author}\n")
            f.write("-" * 50 + "\n\n")
            f.write(text)
            
        print(f"--- УСПЕХ ---")
        print(f"Файл создан в 02_TXT: {file_name}")
        print(f"Объем: {len(text)} символов.")
        
    except Exception as e:
        print(f"Ошибка YouTube: {e}")

if __name__ == "__main__":
    main()