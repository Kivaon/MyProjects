import sys, os, re
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# --- ИМПОРТЫ И ПУТИ ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import tbox_utils as utils
    from tbox_utils import tbox_log
    # Импортируем твой автономный рефайнер для автоматизации
    import tbox_refine_standalone as refiner
except ImportError as e:
    print(f"ОШИБКА ИМПОРТА: {e}")
    sys.exit(1)

# --- MANIFEST ---
VERSION = "v4.4.final"
DATE    = "2026-01-25"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def clean_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_video_metadata(vid, conf):
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True, 
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={vid}"
            tbox_log(f"Запрос метаданных для {vid}...", META, "INFO", conf)
            info = ydl.extract_info(url, download=False)
            upload_date = info.get('upload_date', '00000000')
            formatted_date = f"{upload_date[2:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            author = clean_filename(info.get('uploader', 'Unknown'))
            title = info.get('title', 'Untitled_Video')
            tbox_log(f"Получено: '{title[:40]}...' | Автор: {author}", META, "INFO", conf)
            return formatted_date, author, title
    except Exception as e:
        tbox_log(f"Предупреждение по метаданным: {str(e)[:50]}", META, "WARN", conf)
        return "00-00-00", "Unknown", "Untitled_Video"

def main():
    # Загружаем конфиг через утилиту, которую мы поправили
    CONF = utils.load_local_config()
    if not CONF:
        print("КРИТИЧЕСКАЯ ОШИБКА: config.txt не найден.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"\n--- [ TranslateBox: YT Extractor {VERSION} ] ---")
        return
    
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    tbox_log(f"--- СТАРТ ОБРАБОТКИ РОЛИКА {vid} ---", META, "START", CONF)

    try:
        # 1. Сбор данных (ТВОЙ ДВИЖОК 4.1)
        upload_date, author, title = get_video_metadata(vid, CONF)
        
        tbox_log("Запрос субтитров через YouTube Transcript API...", META, "INFO", CONF)
        api = YouTubeTranscriptApi()
        transcript_data = api.list(vid).find_transcript(['he', 'iw', 'en']).fetch()
        
        # Твой надежный парсинг из 4.1
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
        
        raw_path = os.path.join(CONF.get('TXT_RAW'), f"{base_name}_raw.txt")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\nAUTHOR: {author}\nLINK: https://youtu.be/{vid}\n\n{text}")
        
        tbox_log(f"Сырой текст сохранен: {os.path.basename(raw_path)}", META, "INFO", CONF)

        # 3. REFINERY (Вызов обновленного процесса)
        tbox_log("Запуск процесса ОБЛАГОРАЖИВАНИЯ (Refinery)...", META, "INFO", CONF)
        
        # Передаем путь к файлу в новый рефайнер, который умеет делать паузы
        refiner.run_refining(raw_path, mode="YT")
        
        tbox_log(f"--- ЗАВЕРШЕНО: {base_name} ---", META, "DONE", CONF)

    except Exception as e:
        tbox_log(f"Критический сбой в работе экстрактора: {e}", META, "ERROR", CONF)

if __name__ == "__main__":
    main()