import os, sys, re, pdfplumber
from datetime import datetime
from bidi.algorithm import get_display
import tbox_utils as utils

# Импортируем наш универсальный Refinery
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# --- ПАСПОРТ ---
VERSION = "v2.1.final"
DATE    = "2026-01-25"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def extract_pdf():
    # 1. Сбор вводных
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.dirname(script_dir)
    
    # Загружаем конфиг через утилиты (чтобы не дублировать код чтения)
    CONF = utils.load_local_config()
    if not CONF:
        utils.tbox_log("Критическая ошибка: Конфиг не найден.", META, "ERROR")
        return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR   = CONF.get('TXT_RAW')

    if not INBOX_DIR or not RAW_DIR:
        utils.tbox_log("В конфиге не заданы INBOX_DIR или TXT_RAW", META, "ERROR")
        return

    # 2. ЛОГИКА ПОИСКА ФАЙЛА
    target_path = None
    if user_arg:
        if os.path.exists(user_arg):
            target_path = os.path.abspath(user_arg)
        else:
            files = [f for f in os.listdir(INBOX_DIR) if f.lower().endswith('.pdf')]
            matches = [f for f in files if user_arg.lower() in f.lower()]
            if matches:
                full_matches = [os.path.join(INBOX_DIR, f) for f in matches]
                target_path = max(full_matches, key=os.path.getmtime)
    else:
        files = [os.path.join(INBOX_DIR, f) for f in os.listdir(INBOX_DIR) if f.lower().endswith('.pdf')]
        if files:
            target_path = max(files, key=os.path.getmtime)

    if not target_path:
        utils.tbox_log("Целевой файл не определен.", META, "ERROR")
        return

    # 3. ПОДГОТОВКА СОХРАНЕНИЯ
    os.makedirs(RAW_DIR, exist_ok=True)
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_name = os.path.basename(target_path)
    # Создаем имя файла, которое Refinery легко превратит в название документа
    clean_base_name = original_name.replace('.pdf', '').replace('.PDF', '')
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_base_name}_raw.txt")

    # 4. ЭКСТРАКЦИЯ
    utils.tbox_log(f"Старт экстракции: {original_name}", META, "START")
    
    try:
        full_text = []
        with pdfplumber.open(target_path) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                txt = page.extract_text()
                if txt:
                    # Простая проверка на иврит для bidi
                    has_hebrew = bool(re.search(r'[\u0590-\u05FF]', txt))
                    full_text.append(get_display(txt) if has_hebrew else txt)
                if i % 10 == 0:
                    utils.tbox_log(f"Прогресс: {i}/{total} страниц", META, "INFO")
        
        # Записываем файл с метками для Refinery
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {clean_base_name}\n")
            f.write(f"SOURCE: PDF_EXTRACTOR\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write("\n\n".join(full_text))
            
        utils.tbox_log(f"Текст извлечен: {os.path.basename(output_txt)}", META, "DONE")

        # 5. АВТО-ПЕРЕДАЧА В REFINERY
        # --- УМНЫЙ ВЫБОР РЕЖИМА ---
        
        # Проверяем весь извлеченный текст на наличие иврита
        is_really_hebrew = bool(re.search(r'[\u0590-\u05FF]', "\n".join(full_text)))
        
        chosen_mode = "PDF_HE" if is_really_hebrew else "PDF"
        if refinery:
            utils.tbox_log(f"Передача в Refinery (Режим: {chosen_mode})...", META, "INFO")
            refinery.run_refining(output_txt, mode=chosen_mode)
        else:
            utils.tbox_log("Refinery не найден, автоматическая верстка пропущена.", META, "WARNING")
        
    except Exception as e:
        utils.tbox_log(f"Ошибка процесса: {e}", META, "ERROR")

if __name__ == "__main__":
    extract_pdf()