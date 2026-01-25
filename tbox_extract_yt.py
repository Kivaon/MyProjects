import sys, os, configparser, re
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Импорт унифицированной утилиты вывода
from tbox_utils import tbox_log

# --- MANIFEST ---
VERSION = "v3.42"
DATE    = "2026-01-23"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def load_tbox_config():
    """Индивидуальный парсинг конфига с поддержкой ${BASE_DIR}"""
    # Определяем корень проекта относительно bin/
    base_dir_script = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir_script, "config.txt")
    conf_data = {}

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    conf_data[key.strip()] = value.strip()

        # Интерполяция переменной ${BASE_DIR}
        # Если в конфиге нет BASE_DIR, используем путь по умолчанию
        actual_base = conf_data.get('BASE_DIR', base_dir_script)
        for key in conf_data:
            if '${BASE_DIR}' in conf_data[key]:
                conf_data[key] = conf_data[key].replace('${BASE_DIR}', actual_base)
        
        return conf_data
    except:
        return None

def clean_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_video_metadata(vid, conf):
    """Запрос метаданных видео с имитацией браузера"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'logger': None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={vid}"
            tbox_log("Попытка запроса метаданных через yt-dlp...", META, "INFO", conf)
            
            info = ydl.extract_info(url, download=False)
            
            upload_date = info.get('upload_date', '00000000')
            formatted_date = f"{upload_date[2:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            author = clean_filename(info.get('uploader', 'Unknown'))
            title = info.get('title', 'Untitled_Video')
            
            tbox_log("Метаданные успешно получены", META, "DONE", conf)
            return formatted_date, author, title

    except Exception as e:
        error_msg = str(e).split('.')[0]
        tbox_log(f"YouTube block (403). Причина: {error_msg}", META, "WARN", conf)
        return "00-00-00", "Unknown", "Untitled_Video"

def main():
    # 1. Загрузка конфигурации
    CONF = load_tbox_config()
    
    if not CONF:
        # Если конфиг не найден, tbox_log выведет ошибку только в терминал
        tbox_log("FATAL: config.txt не найден или пуст.", META, "ERROR")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"\n--- [ TranslateBox: YT Extractor {VERSION} ] ---")
        tbox_log("Использование: tbox_extract_yt [ID или Ссылка]", META, "INFO", CONF)
        return
    
    # 2. Обработка ввода и путей
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    target_dir = CONF.get('TEMP_TXT_DIR', '02_TXT')
    os.makedirs(target_dir, exist_ok=True)
    
    tbox_log(f"Начало обработки ролика: {vid}", META, "START", CONF)
    
    try:
        # 3. Получение данных
        upload_date, author, title = get_video_metadata(vid, CONF)
        tbox_log(f"Канал: {author} | Название: {title[:30]}...", META, "INFO", CONF)
        
        # 4. Загрузка субтитров
        tbox_log("Загрузка субтитров...", META, "INFO", CONF)
        api = YouTubeTranscriptApi()
        transcript_data = api.list(vid).find_transcript(['he', 'iw', 'en']).fetch()
        
        # Безопасное извлечение текста (учитываем структуру API)
        full_text_list = []
        for segment in transcript_data:
            if isinstance(segment, dict):
                full_text_list.append(segment.get('text', ''))
            else:
                full_text_list.append(getattr(segment, 'text', ''))
        
        text = " ".join(full_text_list).replace('\n', ' ')
        
        # 5. Сохранение файла
        now_time = datetime.now().strftime("%y%m%d_%H%M")
        file_name = f"{now_time}-{author}-{upload_date}-{vid}.txt"
        path = os.path.join(target_dir, file_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\nLINK: https://www.youtube.com/watch?v={vid}\nAUTHOR: {author}\n")
            f.write("-" * 50 + "\n\n" + text)
            
        tbox_log(f"УСПЕХ: Файл создан {file_name} ({len(text)} симв.)", META, "DONE", CONF)
        
    except Exception as e:
        tbox_log(f"Ошибка выполнения: {e}", META, "ERROR", CONF)

if __name__ == "__main__":
    main()