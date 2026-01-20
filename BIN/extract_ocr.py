# Version: 3.4
# Description: YouTube Transcript Extractor with absolute path resolving

import sys, os, configparser
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def load_config():
    """
    Определяет корень проекта относительно местоположения скрипта.
    Позволяет запускать скрипт через алиасы из любой директории.
    """
    # Вычисляем путь к папке AI_Lab (на один уровень выше папки bin)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "config.txt")
    
    config = configparser.ConfigParser()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            # Добавляем фиктивную секцию для работы с простым списком ключей
            config_string = '[DEFAULT]\n' + f.read()
        config.read_string(config_string)
        return config['DEFAULT'], base_dir
    except Exception as e:
        print(f"[v3.4] Ошибка чтения конфигурации: {e}")
        sys.exit(1)

# Глобальные переменные на основе конфига
CONF, BASE_DIR = load_config()
LOG_FILE = os.path.join(BASE_DIR, CONF.get('LOG_FILE').split('#')[0].strip())
TARGET_DIR = os.path.join(BASE_DIR, CONF.get('TEMP_TXT_DIR').split('#')[0].strip())

def write_log(event_type, message):
    ts = datetime.now().strftime("%y%m%d_%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [v3.4] [{event_type}] {message}\n")

def get_video_metadata(vid):
    """Безопасно извлекает имя автора видео через yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True, 
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            author = info.get('uploader', 'Unknown')
            # Оставляем только буквы, цифры и подчеркивание для имени файла
            return "".join([c for c in author if c.isalnum() or c=='_'])
    except:
        return "UnknownAuthor"

def main():
    if len(sys.argv) < 2:
        print("Использование: yt https://id.com/")
        return
    
    raw_input = sys.argv[1]
    # Извлекаем ID видео из ссылки или берем как есть
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    os.makedirs(TARGET_DIR, exist_ok=True)
    write_log("YT_START", f"ID: {vid}")
    
    try:
        author = get_video_metadata(vid)
        
        # Работа с API субтитров
        api = YouTubeTranscriptApi()
        # Ищем субтитры на иврите (коды he или iw)
        transcript_list = api.list(vid).find_transcript(['he', 'iw']).fetch()
        
        # Сбор текста из объектов любого типа (dict или object)
        full_text = []
        for segment in transcript_list:
            text_chunk = getattr(segment, 'text', None) 
            if text_chunk is None and isinstance(segment, dict):
                text_chunk = segment.get('text', '')
            if text_chunk:
                full_text.append(text_chunk)
        
        text = " ".join(full_text)
        
        if not text.strip():
            raise Exception("Текст пуст после извлечения")

        # Формируем имя файла: ТАЙМШТАМП_АВТОР_ID.txt
        time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
        file_name = f"{time_tag}_{author}_{vid}.txt"
        path = os.path.join(TARGET_DIR, file_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [v3.4] Успех: {file_name}")
        write_log("YT_DONE", f"Saved: {file_name}")
        
    except Exception as e:
        error_msg = f"Video {vid} failed: {str(e)}"
        print(f"ОШИБКА [v3.4]: {error_msg}")
        write_log("YT_ERROR", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()