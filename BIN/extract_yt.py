# Version: 3.20
# Description: Synchronized Logging (Terminal + Single Factory Log)

import sys, os, configparser, re
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

VERSION = "v3.20"
SCRIPT_NAME = os.path.basename(__file__)

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
TARGET_DIR = os.path.join(BASE_DIR, "02_TXT")

# ПРАВИЛЬНЫЙ ПУТЬ К ЛОГУ (Берем из конфига ключ LOG_FILE)
# Если в конфиге LOG_FILE = factory.log, то пишем в него.
log_name = CONF.get('LOG_FILE', 'factory.log').split('#')[0].strip()
LOG_FILE_PATH = os.path.join(BASE_DIR, log_name)

def log(message, level="INFO"):
    """Единая точка логирования: Терминал + Файл + Версия"""
    now = datetime.now()
    time_t = now.strftime("%H:%M:%S")
    time_f = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Добавляем [VERSION] в строку
    msg_terminal = f"[{time_t}] [{SCRIPT_NAME} {VERSION}] [{level}] {message}"
    msg_file = f"[{time_f}] [{SCRIPT_NAME} {VERSION}] [{level}] {message}"
    
    print(msg_terminal)
    
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(msg_file + "\n")
    except Exception as e:
        print(f"!!! Ошибка записи в лог: {e}")
        
def clean_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_video_metadata(vid):
    # Настройки для имитации реального браузера
    ydl_opts = {
        'quiet': True,              # Подавляет обычные сообщения
        'no_warnings': True,        # Уберет те самые желтые WARNING про SABR
        'noplaylist': True,
        'nocheckcertificate': True,
        'logger': None,             # Полностью отключает внутренний вывод библиотеки в консоль
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={vid}"
            log(f"Попытка запроса метаданных через yt-dlp...")
            
            info = ydl.extract_info(url, download=False)
            
            # Если мы дошли сюда, значит запрос УДАЛСЯ
            upload_date = info.get('upload_date', '00000000')
            formatted_date = f"{upload_date[2:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            author = info.get('uploader', 'Unknown').replace(" ", "_")
            title = info.get('title', 'Untitled_Video')
            
            log(f"Метаданные успешно получены с первой попытки", "DONE")
            return formatted_date, author, title

    except Exception as e:
        # Теперь ошибка 403 попадет в лог!
        error_msg = str(e).split('.')[0] # Берем только первую часть ошибки для краткости
        log(f"YouTube заблокировал запрос метаданных (403). Причина: {error_msg}", "WARN")
        return "00-00-00", "Unknown", "Untitled_Video"

def main():
    if len(sys.argv) < 2:
        print("\n--- [ v3.17 YT Extractor ] ---")
        print("Использование: yt [ID или Ссылка]")
        return
    
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    log(f"Начало обработки ролика: {vid}")
    
    try:
        log("Запрос данных ролика...")
        upload_date, author, title = get_video_metadata(vid)
        
        log(f"Канал: {author} | Название: {title[:30]}...")
        
        log("Загрузка субтитров...")
        api = YouTubeTranscriptApi()
        data = api.list(vid).find_transcript(['he', 'iw', 'en']).fetch()
        
        full_text_list = []
        for t in data:
            if isinstance(t, dict):
                full_text_list.append(t.get('text', ''))
            else:
                full_text_list.append(getattr(t, 'text', ''))
        
        text = " ".join(full_text_list).replace('\n', ' ')
        
        now_time = datetime.now().strftime("%y%m%d_%H%M")
        file_name = f"{now_time}-{author}-{upload_date}-{vid}.txt"
        path = os.path.join(TARGET_DIR, file_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\n")
            f.write(f"LINK: https://www.youtube.com/watch?v={vid}\n")
            f.write(f"AUTHOR: {author}\n")
            f.write("-" * 50 + "\n\n")
            f.write(text)
            
        log(f"УСПЕХ: Файл создан {file_name} ({len(text)} симв.)", "DONE")
        
    except Exception as e:
        log(f"Ошибка выполнения: {e}", "ERROR")

if __name__ == "__main__":
    main()