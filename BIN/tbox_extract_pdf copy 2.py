import os, sys, re, pdfplumber
from datetime import datetime
from bidi.algorithm import get_display
import tbox_utils as utils

# --- ПАСПОРТ ---
VERSION = "v2.0.stable"
DATE    = "2026-01-25"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def extract_pdf():
    # 1. Сбор вводных
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.dirname(script_dir)
    config_path = os.path.join(base_project_dir, "config.txt")
    
    CONF = {}
    if not os.path.exists(config_path):
        utils.tbox_log(f"Критическая ошибка: Конфиг не найден {config_path}", META, "ERROR")
        return

    # 2. Чтение конфига
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    CONF[key.strip()] = val.strip()
        
        actual_base = CONF.get('BASE_DIR', base_project_dir)
        for k in CONF:
            if isinstance(CONF[k], str) and '${BASE_DIR}' in CONF[k]:
                CONF[k] = CONF[k].replace('${BASE_DIR}', actual_base)
    except Exception as e:
        utils.tbox_log(f"Ошибка чтения конфига: {e}", META, "ERROR")
        return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR   = CONF.get('TXT_RAW')

    if not INBOX_DIR or not RAW_DIR:
        utils.tbox_log("В конфиге не заданы INBOX_DIR или TXT_RAW", META, "ERROR")
        return

    # 3. ЛОГИКА ПОИСКА ФАЙЛА (Target Selection)
    target_path = None

    if user_arg:
        # Вариант А: Прямой путь
        if os.path.exists(user_arg):
            target_path = os.path.abspath(user_arg)
        # Вариант Б: Часть имени в INBOX
        else:
            if os.path.exists(INBOX_DIR):
                files = [f for f in os.listdir(INBOX_DIR) if f.lower().endswith('.pdf')]
                matches = [f for f in files if user_arg.lower() in f.lower()]
                if matches:
                    full_matches = [os.path.join(INBOX_DIR, f) for f in matches]
                    target_path = max(full_matches, key=os.path.getmtime)
                    utils.tbox_log(f"Найдено по метке '{user_arg}': {os.path.basename(target_path)}", META, "INFO")
                else:
                    utils.tbox_log(f"Файл с меткой '{user_arg}' не найден в {INBOX_DIR}", META, "ERROR")
                    return
    else:
        # Вариант В: Последний файл (Автопилот)
        if os.path.exists(INBOX_DIR):
            files = [os.path.join(INBOX_DIR, f) for f in os.listdir(INBOX_DIR) if f.lower().endswith('.pdf')]
            if files:
                target_path = max(files, key=os.path.getmtime)
                utils.tbox_log(f"Автопилот: берем последний файл {os.path.basename(target_path)}", META, "INFO")
            else:
                utils.tbox_log(f"Папка INBOX_DIR пуста: {INBOX_DIR}", META, "ERROR")
                return

    if not target_path:
        utils.tbox_log("Целевой файл не определен.", META, "ERROR")
        return

    # 4. ПОДГОТОВКА СОХРАНЕНИЯ
    os.makedirs(RAW_DIR, exist_ok=True)
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_name = os.path.basename(target_path)
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{original_name}.txt")

    # 5. ЭКСТРАКЦИЯ
    utils.tbox_log(f"Старт: {original_name}", META, "START")
    
    try:
        full_text = []
        with pdfplumber.open(target_path) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                txt = page.extract_text()
                if txt:
                    has_hebrew = bool(re.search(r'[\u0590-\u05FF]', txt))
                    # get_display() разворачивает иврит для ИИ, оставляя латиницу как есть
                    full_text.append(get_display(txt) if has_hebrew else txt)
                if i % 10 == 0:
                    utils.tbox_log(f"Прогресс: {i}/{total}", META, "INFO")
        
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {original_name}\n")
            f.write(f"SOURCE: PDF_EXTRACTOR {VERSION}\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write("\n\n".join(full_text))
            
        utils.tbox_log(f"ГОТОВО: {os.path.abspath(output_txt)}", META, "DONE")
        
    except Exception as e:
        utils.tbox_log(f"Ошибка экстракции: {e}", META, "ERROR")

if __name__ == "__main__":
    extract_pdf()