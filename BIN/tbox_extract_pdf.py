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
VERSION = "v2.2.column-aware"
DATE    = "2026-01-30"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def extract_columns_from_page(page, has_hebrew=False, conf=None):
    """Извлекает текст из колонок с учетом направления чтения"""
    try:
        # Получаем все текстовые блоки с координатами
        words = page.extract_words()
        if not words:
            return page.extract_text() or ""
        
        # Определяем границы колонок
        x_coords = [w['x0'] for w in words]
        min_x, max_x = min(x_coords), max(x_coords)
        page_width = max_x - min_x
        
        # Если страница слишком узкая - вероятно одна колонка
        if page_width < 300:
            if conf:
                utils.tbox_log("Обнаружено 1 колонка, читаем последовательно", META, "INFO", conf)
            return page.extract_text() or ""
        
        # Определяем середину страницы для разделения колонок
        mid_x = min_x + page_width / 2
        
        # Разделяем на левую и правую колонки
        left_column = []
        right_column = []
        
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            if word_center < mid_x:
                left_column.append(word)
            else:
                right_column.append(word)
        
        # Проверяем, есть ли текст в обеих колонках
        if not left_column or not right_column:
            if conf:
                utils.tbox_log("Обнаружено 1 колонка, читаем последовательно", META, "INFO", conf)
            return page.extract_text() or ""
        
        # Логируем обнаружение двух колонок и порядок чтения
        if conf:
            if has_hebrew:
                utils.tbox_log("Обнаружено 2 колонки, порядок: правая → левая (RTL)", META, "INFO", conf)
            else:
                utils.tbox_log("Обнаружено 2 колонки, порядок: левая → правая (LTR)", META, "INFO", conf)
        
        # Сортируем слова в каждой колонке по Y (сверху вниз)
        left_column.sort(key=lambda w: (w['top'], w['x0']))
        right_column.sort(key=lambda w: (w['top'], w['x0']))
        
        # Собираем текст из колонок
        def column_to_text(column):
            if not column:
                return ""
            
            lines = []
            current_line = []
            current_y = None
            tolerance = 5  # допуск для объединения в одну строку
            
            for word in column:
                if current_y is None or abs(word['top'] - current_y) > tolerance:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word['text']]
                    current_y = word['top']
                else:
                    current_line.append(word['text'])
            
            if current_line:
                lines.append(" ".join(current_line))
            
            return "\n".join(lines)
        
        left_text = column_to_text(left_column)
        right_text = column_to_text(right_column)
        
        # Для RTL: сначала правая колонка, потом левая
        # Для LTR: сначала левая колонка, потом правая
        if has_hebrew:
            combined = right_text + "\n\n" + left_text
        else:
            combined = left_text + "\n\n" + right_text
        
        return combined.strip()
        
    except Exception as e:
        # Если анализ колонок не удался, возвращаем обычный текст
        return page.extract_text() or ""

def extract_pdf():
    # 1. Сбор вводных
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.dirname(script_dir)
    
    # Загружаем конфиг через утилиты (чтобы не дублировать код чтения)
    CONF = utils.load_local_config()
    if not CONF:
        utils.tbox_log("Критическая ошибка: Конфиг не найден.", META, "ERROR", CONF)
        return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR   = CONF.get('TXT_RAW')

    if not INBOX_DIR or not RAW_DIR:
        utils.tbox_log("В конфиге не заданы INBOX_DIR или TXT_RAW", META, "ERROR", CONF)
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
        utils.tbox_log("Целевой файл не определен.", META, "ERROR", CONF)
        return

    # 3. ПОДГОТОВКА СОХРАНЕНИЯ
    os.makedirs(RAW_DIR, exist_ok=True)
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_name = os.path.basename(target_path)
    # Создаем имя файла, которое Refinery легко превратит в название документа
    clean_base_name = original_name.replace('.pdf', '').replace('.PDF', '')
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_base_name}_raw.txt")

    # 4. ЭКСТРАКЦИЯ С УЧЕТОМ КОЛОНОК
    utils.tbox_log(f"Старт экстракции: {original_name}", META, "START", CONF)
    
    try:
        full_text = []
        with pdfplumber.open(target_path) as pdf:
            total = len(pdf.pages)
            utils.tbox_log(f"Всего страниц: {total}", META, "INFO", CONF)
            
            for i, page in enumerate(pdf.pages, 1):
                utils.tbox_log(f"Обработка страницы {i}/{total}", META, "INFO", CONF)
                
                # Проверяем наличие иврита на странице
                page_text_sample = page.extract_text() or ""
                has_hebrew = bool(re.search(r'[\u0590-\u05FF]', page_text_sample))
                
                # Используем новый алгоритм извлечения колонок
                txt = extract_columns_from_page(page, has_hebrew, CONF)
                
                if txt:
                    # Применяем bidi обработку для RTL текста
                    full_text.append(get_display(txt) if has_hebrew else txt)
                
                if i % 10 == 0:
                    utils.tbox_log(f"Прогресс: {i}/{total} страниц", META, "INFO", CONF)
        
        # Записываем файл с метками для Refinery
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {clean_base_name}\n")
            f.write(f"SOURCE: PDF_EXTRACTOR\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write("\n\n".join(full_text))
            
        utils.tbox_log(f"Текст извлечен: {os.path.basename(output_txt)}", META, "DONE", CONF)

        # 5. АВТО-ПЕРЕДАЧА В REFINERY
        # --- УМНЫЙ ВЫБОР РЕЖИМА ---
        
        # Проверяем весь извлеченный текст на наличие иврита
        is_really_hebrew = bool(re.search(r'[\u0590-\u05FF]', "\n".join(full_text)))
        
        chosen_mode = "PDF_HE" if is_really_hebrew else "PDF"
        if refinery:
            utils.tbox_log(f"Передача в Refinery (Режим: {chosen_mode})...", META, "INFO", CONF)
            refinery.run_refining(output_txt, mode=chosen_mode)
        else:
            utils.tbox_log("Refinery не найден, автоматическая верстка пропущена.", META, "WARNING", CONF)
        
    except Exception as e:
        utils.tbox_log(f"Ошибка процесса: {e}", META, "ERROR", CONF)

if __name__ == "__main__":
    extract_pdf()