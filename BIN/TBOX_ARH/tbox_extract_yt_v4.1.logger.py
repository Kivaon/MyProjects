import sys, os, configparser, re
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Импорт унифицированной утилиты вывода и рефайнера
from tbox_utils import tbox_log #, tbox_refine_and_save

# --- MANIFEST ---
VERSION = "v4.1.logger"
DATE    = "2026-01-24"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def load_tbox_config():
    base_dir_script = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir_script, "config.txt")
    conf_data = {}
    if not os.path.exists(config_path): return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    conf_data[key.strip()] = value.strip()
        actual_base = conf_data.get('BASE_DIR', base_dir_script)
        for key in conf_data:
            if '${BASE_DIR}' in conf_data[key]:
                conf_data[key] = conf_data[key].replace('${BASE_DIR}', actual_base)
        return conf_data
    except: return None

def clean_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_video_metadata(vid, conf):
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True, 
        'nocheckcertificate': True, 'logger': None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={vid}"
            tbox_log(f"Запрос метаданных для {vid} через yt-dlp...", META, "INFO", conf)
            info = ydl.extract_info(url, download=False)
            
            upload_date = info.get('upload_date', '00000000')
            formatted_date = f"{upload_date[2:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            author = clean_filename(info.get('uploader', 'Unknown'))
            title = info.get('title', 'Untitled_Video')
            
            tbox_log(f"Получено: '{title[:40]}...' | Автор: {author} | Дата: {formatted_date}", META, "INFO", conf)
            return formatted_date, author, title
    except Exception as e:
        tbox_log(f"Предупреждение по метаданным: {str(e)[:60]}", META, "WARN", conf)
        return "00-00-00", "Unknown", "Untitled_Video"

def main():
    CONF = load_tbox_config()
    if not CONF:
        tbox_log("КРИТИЧЕСКАЯ ОШИБКА: config.txt не найден или поврежден.", META, "ERROR")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"\n--- [ TranslateBox: YT Extractor {VERSION} ] ---")
        return
    
    # Извлечение ID
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    # Логируем начало работы
    tbox_log(f"--- СТАРТ ОБРАБОТКИ РОЛИКА {vid} ---", META, "START", CONF)

    try:
        # 1. Сбор данных
        upload_date, author, title = get_video_metadata(vid, CONF)
        
        tbox_log("Запрос субтитров через YouTube Transcript API...", META, "INFO", CONF)
        api = YouTubeTranscriptApi()
        transcript_data = api.list(vid).find_transcript(['he', 'iw', 'en']).fetch()
        
        # Парсинг транскрипта
        full_text_list = []
        for segment in transcript_data:
            if isinstance(segment, dict):
                full_text_list.append(segment.get('text', ''))
            else:
                full_text_list.append(getattr(segment, 'text', ''))
        
        text = " ".join(full_text_list).replace('\n', ' ')
        tbox_log(f"Субтитры выкачаны успешно. Объем: {len(text)} симв.", META, "INFO", CONF)
        
        # 2. Пути и сохранение RAW
        now_time = datetime.now().strftime("%y%m%d_%H%M")
        base_name = f"{now_time}-{author}-{upload_date}-{vid}"
        
        raw_dir = CONF.get('TXT_RAW')
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(raw_dir, f"{base_name}_raw.txt")
        
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\nAUTHOR: {author}\nLINK: https://youtu.be/{vid}\n\n{text}")
        
        tbox_log(f"Сырой текст сохранен: 02_TXT/raw/{os.path.basename(raw_path)}", META, "INFO", CONF)

        # 3. Refinery (AI)
        tbox_log("Запуск процесса ОБЛАГОРАЖИВАНИЯ (Refinery)...", META, "INFO", CONF)
        
        # Функция внутри tbox_utils должна сама логировать свои этапы ( Gemini, Save MD, Save DOCX )
        md_file, doc_file = tbox_refine_and_save(text, base_name, CONF, title=title)
        
        # Финальный отчет
        tbox_log(f"УСПЕХ: Сформирован MD-файл: {os.path.basename(md_file)}", META, "DONE", CONF)
        tbox_log(f"УСПЕХ: Сформирован DOCX-оригинал: {os.path.basename(doc_file)}", META, "DONE", CONF)
        tbox_log(f"--- ЗАВЕРШЕНО: {base_name} ---", META, "DONE", CONF)
    except Exception as e:
        tbox_log(f"Критический сбой в работе экстрактора: {e}", META, "ERROR", CONF)

  
if __name__ == "__main__":
    main()