import sys, os, configparser
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def load_config():
    config = configparser.ConfigParser()
    path = os.path.expanduser("~/Documents/AI_Lab/config.txt")
    with open(path, 'r', encoding='utf-8') as f:
        # Читаем конфиг, игнорируя комментарии и пустые строки
        config_string = '[DEFAULT]\n' + f.read()
    config.read_string(config_string)
    return config['DEFAULT']

CONF = load_config()
LOG_FILE = CONF.get('LOG_FILE').split('#')[0].strip()
TARGET_DIR = CONF.get('TEMP_TXT_DIR').split('#')[0].strip()

def write_log(event_type, message):
    ts = datetime.now().strftime("%y%m%d_%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{event_type}] {message}\n")

def get_video_metadata(vid):
    """Безопасное получение автора"""
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            author = info.get('uploader', 'Unknown')
            return "".join([c for c in author if c.isalnum() or c=='_'])
    except:
        return "UnknownAuthor"

def main():
    if len(sys.argv) < 2: return
    
    raw_input = sys.argv[1]
    vid = raw_input.split('v=')[-1].split('&')[0] if 'v=' in raw_input else raw_input
    
    os.makedirs(TARGET_DIR, exist_ok=True)
    write_log("YT_START", f"ID: {vid}")
    
    try:
        author = get_video_metadata(vid)
        
        # Получаем данные
        api = YouTubeTranscriptApi()
        transcript_list = api.list(vid).find_transcript(['he', 'iw']).fetch()
        
        # --- ФИНАЛЬНЫЙ FIX ДЛЯ ТЕКСТА ---
        full_text = []
        for segment in transcript_list:
            # Пробуем все варианты: как словарь, как объект или как атрибут
            if isinstance(segment, dict):
                val = segment.get('text', '')
            else:
                # Пытаемся достать атрибут 'text' напрямую
                val = getattr(segment, 'text', str(segment))
            full_text.append(val)
        
        text = " ".join(full_text)
        
        if not text.strip() or text == "[]":
            raise Exception("Получен пустой массив вместо текста")

        time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
        file_name = f"{time_tag}_{author}_{vid}.txt"
        path = os.path.join(TARGET_DIR, file_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Успех: {file_name}")
        write_log("YT_DONE", f"Saved: {file_name}")
        
    except Exception as e:
        error_msg = f"Video {vid} Error: {str(e)}"
        print(f"ОШИБКА: {error_msg}")
        write_log("YT_ERROR", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()