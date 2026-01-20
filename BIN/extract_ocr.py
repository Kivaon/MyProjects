import requests, os, base64, time
from datetime import datetime

# v1.4-stable - 2026-01-19
# Цепочка: IMG2TXT -> TXT2DOC
# Имя: [YYMMDD_HHMMSS]_[FirstFile].txt

# --- НАСТРОЙКИ ---
KEY = "AIzaSyDSC5bHwhxRHKIF3waY2sNJSR22PeSVnaU"
IMG_FOLDER = os.path.expanduser("~/Documents/AI_Lab/IMG2TXT")
RAW_DIR = os.path.expanduser("~/Documents/AI_Lab/TXT2DOC")

def get_now():
    """Время для лога в консоли"""
    return datetime.now().strftime("%H:%M:%S")

def ocr_image(image_path, attempt=1):
    """Функция запроса к Gemini с логикой повторов"""
    with open(image_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={KEY}"
    
    prompt = "Перепиши весь текст с этой картинки на иврите. Сохраняй структуру абзацев. Не добавляй свои комментарии."
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_data}}
            ]
        }]
    }

    try:
        r = requests.post(url, json=payload, timeout=120)
        
        # Если превышен лимит (429) или сервер устал (503)
        if r.status_code == 429:
            wait = 30 * attempt
            print(f"[{get_now()}] [!] Лимит API. Ждем {wait} сек...")
            time.sleep(wait)
            return ocr_image(image_path, attempt + 1) if attempt < 5 else ""
            
        if r.status_code == 503:
            print(f"[{get_now()}] [!] Сервер Google занят. Ждем 15 сек...")
            time.sleep(15)
            return ocr_image(image_path, attempt + 1) if attempt < 5 else ""

        r.raise_for_status()
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"[{get_now()}] Ошибка на файле {os.path.basename(image_path)}: {e}")
        return ""

def main():
    # Создаем папки, если их нет
    if not os.path.exists(IMG_FOLDER):
        os.makedirs(IMG_FOLDER)
        print(f"[{get_now()}] Создана папка: {IMG_FOLDER}. Положите туда картинки.")
        return
    
    os.makedirs(RAW_DIR, exist_ok=True)

    # Собираем список файлов (JPG, PNG, WEBP)
    valid_ext = ('.jpg', '.jpeg', '.png', '.webp')
    files = sorted([f for f in os.listdir(IMG_FOLDER) if f.lower().endswith(valid_ext)])
    
    if not files:
        print(f"[{get_now()}] В папке IMG2TXT нет подходящих файлов {valid_ext}")
        return

    # --- ФОРМИРУЕМ ИМЯ ВЫХОДНОГО ФАЙЛА ---
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    first_file_name = os.path.splitext(files[0])[0] # Имя без расширения
    file_name = f"{time_tag}_{first_file_name}.txt"
    final_output_path = os.path.join(RAW_DIR, file_name)

    print(f"[{get_now()}] --- ЗАПУСК OCR (Всего: {len(files)} страниц) ---")
    print(f"[{get_now()}] Результат будет в: {file_name}")
    
    full_text = ""
    
    # Обработка каждой картинки
    for i, filename in enumerate(files, 1):
        print(f"[{get_now()}] [{i}/{len(files)}] Обработка: {filename}...")
        path = os.path.join(IMG_FOLDER, filename)
        
        text = ocr_image(path)
        
        if text:
            full_text += f"\n\n--- СТРАНИЦА {i}: {filename} ---\n\n" + text
            print(f"[{get_now()}] Готово.")
        else:
            print(f"[{get_now()}] ОШИБКА: Не удалось получить текст с {filename}")
            
        # Пауза 5 сек, чтобы не "злить" API частыми тяжелыми запросами
        time.sleep(5)

    # Сохраняем итоговый файл
    if full_text.strip():
        with open(final_output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"\n[{get_now()}] --- ЗАВЕРШЕНО УСПЕШНО ---")
        print(f"[{get_now()}] Файл создан: {final_output_path}")
    else:
        print(f"\n[{get_now()}] --- ОШИБКА: Текст не был получен. Файл не сохранен. ---")

if __name__ == "__main__":
    main()