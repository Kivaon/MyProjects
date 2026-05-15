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
# Previous: v2.2.column-aware (2026-01-30) - Added column detection
VERSION = "v3.0.smart-segments"
DATE    = "2026-04-18"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# Smart column detection for mixed page layouts
def segment_page_vertically(page, band_height=50):
    """Divide page into horizontal bands for analysis"""
    bands = []
    all_words = page.extract_words()
    
    if not all_words:
        return bands
    
    page_height = page.height
    
    for y_start in range(0, int(page_height), band_height):
        y_end = min(y_start + band_height, page_height)
        band_words = [w for w in all_words 
                     if w['top'] >= y_start and w['top'] < y_end]
        bands.append({
            'y_start': y_start,
            'y_end': y_end, 
            'words': band_words
        })
    
    return bands

def analyze_band_structure(band):
    """Determine if band has 1 or 2 columns"""
    if not band['words']:
        return 'empty'
    
    # Analyze word distribution
    x_coords = [w['x0'] for w in band['words']]
    min_x, max_x = min(x_coords), max(x_coords)
    width = max_x - min_x
    
    # Check for centered content vs columns
    left_zone = [w for w in band['words'] if w['x0'] < min_x + width * 0.3]
    right_zone = [w for w in band['words'] if w['x0'] > min_x + width * 0.7]
    middle_zone = [w for w in band['words'] if min_x + width * 0.3 <= w['x0'] <= min_x + width * 0.7]
    
    left_text = sum(len(w['text']) for w in left_zone)
    right_text = sum(len(w['text']) for w in right_zone)
    middle_text = sum(len(w['text']) for w in middle_zone)
    total_text = left_text + right_text + middle_text
    
    if total_text == 0:
        return 'empty'
    
    # Determine structure with very strict criteria
    if middle_text > total_text * 0.7:
        return 'single_centered'
    elif left_text > total_text * 0.35 and right_text > total_text * 0.35:
        # Additional check: ensure both columns have substantial content
        min_column_size = min(left_text, right_text)
        if min_column_size > total_text * 0.25:  # Both columns must be substantial (25%+ each)
            return 'double_column'
        else:
            return 'single_column'
    else:
        return 'single_column'

def group_similar_bands(bands):
    """Group consecutive bands with same structure"""
    if not bands:
        return []
    
    segments = []
    
    # Analyze structure for each band
    for band in bands:
        band['structure'] = analyze_band_structure(band)
    
    # Group similar bands
    current_segment = {
        'structure': bands[0]['structure'],
        'y_start': bands[0]['y_start'],
        'y_end': bands[0]['y_end'],
        'words': bands[0]['words']
    }
    
    for band in bands[1:]:
        if band['structure'] == current_segment['structure']:
            # Extend current segment
            current_segment['y_end'] = band['y_end']
            current_segment['words'].extend(band['words'])
        else:
            # Start new segment
            if current_segment['words']:  # Only add non-empty segments
                segments.append(current_segment)
            current_segment = {
                'structure': band['structure'],
                'y_start': band['y_start'],
                'y_end': band['y_end'],
                'words': band['words']
            }
    
    if current_segment['words']:  # Add final segment
        segments.append(current_segment)
    
    return segments

def extract_text_from_mixed_segments(segments, has_hebrew, conf):
    """Extract text using appropriate method for each segment"""
    full_text = []
    
    for i, segment in enumerate(segments):
        if segment['structure'] == 'empty' or not segment['words']:
            continue
        
        if conf:
            utils.tbox_log(f"Segment {i+1}: {segment['structure']} ({len(segment['words'])} words, Y:{segment['y_start']}-{segment['y_end']})", META, "INFO", conf)
        
        if segment['structure'] in ['single_column', 'single_centered']:
            # Use single column extraction
            text = extract_single_column_from_words(segment['words'], has_hebrew)
        elif segment['structure'] == 'double_column':
            # Use double column extraction
            text = extract_double_column_from_words(segment['words'], has_hebrew)
        
        if text:
            full_text.append(text)
    
    return '\n'.join(full_text)

def extract_single_column_from_words(words, has_hebrew):
    """Extract text from words as single column"""
    if not words:
        return ""
    
    # Sort by Y coordinate, then by X
    words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
    
    # Build lines
    lines = []
    current_line = []
    current_y = None
    
    for word in words_sorted:
        if current_y is None or abs(word['top'] - current_y) > 5:  # New line
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word['text']]
            current_y = word['top']
        else:
            current_line.append(word['text'])
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)

def extract_double_column_from_words(words, has_hebrew):
    """Extract text from words as double column"""
    if not words:
        return ""
    
    # Find column boundary
    x_coords = [w['x0'] for w in words]
    min_x, max_x = min(x_coords), max(x_coords)
    mid_x = min_x + (max_x - min_x) / 2
    
    # Split into columns
    left_column = [w for w in words if w['x0'] < mid_x]
    right_column = [w for w in words if w['x0'] >= mid_x]
    
    # Sort each column
    left_sorted = sorted(left_column, key=lambda w: (w['top'], w['x0']))
    right_sorted = sorted(right_column, key=lambda w: (w['top'], w['x0']))
    
    # Extract text from each column
    left_text = extract_single_column_from_words(left_sorted, has_hebrew)
    right_text = extract_single_column_from_words(right_sorted, has_hebrew)
    
    # Combine based on reading direction
    if has_hebrew:
        # RTL: right column first, then left
        combined = right_text + '\n' + left_text if left_text and right_text else right_text + left_text
    else:
        # LTR: left column first, then right
        combined = left_text + '\n' + right_text if left_text and right_text else left_text + right_text
    
    return combined

def extract_single_column_text(page, has_hebrew=False, conf=None):
    """Улучшенное извлечение текста для одноколоночных документов"""
    try:
        # Получаем слова с координатами
        words = page.extract_words()
        if not words:
            return page.extract_text() or ""
        
        # Сортируем слова по координатам (сверху вниз, слева направо)
        words.sort(key=lambda w: (w['top'], w['x0']))
        
        # Собираем текст с учетом строк
        lines = []
        current_line = []
        current_y = None
        tolerance = 3  # допуск для объединения в одну строку
        
        for word in words:
            if current_y is None or abs(word['top'] - current_y) > tolerance:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word['text']]
                current_y = word['top']
            else:
                current_line.append(word['text'])
        
        if current_line:
            lines.append(" ".join(current_line))
        
        text = "\n".join(lines)
        
        if conf:
            utils.tbox_log(f"Извлечено {len(lines)} строк из одноколоночного документа", META, "INFO", conf)
        
        return text.strip()
        
    except Exception as e:
        # Если улучшенное извлечение не удалось, возвращаем обычный текст
        if conf:
            utils.tbox_log(f"Ошибка улучшенного извлечения: {e}, используем стандартный метод", META, "WARNING", conf)
        return page.extract_text() or ""

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
                utils.tbox_log("Обнаружено 1 колонка (узкая страница), используем улучшенное извлечение", META, "INFO", conf)
            return extract_single_column_text(page, has_hebrew, conf)
        
        # Additional check: if page is not very wide, be conservative
        if page_width < 450:
            if conf:
                utils.tbox_log(f"Page width {page_width:.0f}px - conservative: 1 column", META, "INFO", conf)
            return extract_single_column_text(page, has_hebrew, conf)
        
        # Анализируем распределение текста по горизонтали
        # Разделяем страницу на 3 вертикальные зоны
        left_zone = []
        middle_zone = []
        right_zone = []
        
        mid_x = min_x + page_width / 2
        left_boundary = min_x + page_width * 0.3
        right_boundary = min_x + page_width * 0.7
        
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            if word_center < left_boundary:
                left_zone.append(word)
            elif word_center > right_boundary:
                right_zone.append(word)
            else:
                middle_zone.append(word)
        
        # Проверяем, есть ли текст в левой и правой зонах
        left_text_len = sum(len(w['text']) for w in left_zone)
        right_text_len = sum(len(w['text']) for w in right_zone)
        middle_text_len = sum(len(w['text']) for w in middle_zone)
        
        total_text = left_text_len + right_text_len + middle_text_len
        
        # Check for single column with centered headers
        # If both side zones have similar amounts and middle zone is significant, 
        # it's likely single column with centered content
        side_balance = abs(left_text_len - right_text_len) / max(left_text_len, right_text_len) if max(left_text_len, right_text_len) > 0 else 0
        
        # Single column if:
        # 1. Middle zone has significant text (centered headers)
        # 2. Side zones are balanced (similar amounts)  
        # 3. One side zone is very small
        if middle_text_len > total_text * 0.3 and side_balance < 0.3:
            if conf:
                utils.tbox_log(f"Detected 1 column with centered content (balance: {side_balance:.2f}, center: {middle_text_len/total_text:.1%})", META, "INFO", conf)
            return extract_single_column_text(page, has_hebrew, conf)
        elif left_text_len < total_text * 0.15 or right_text_len < total_text * 0.15:
            if conf:
                utils.tbox_log(f"Detected 1 column (unbalanced sides: left: {left_text_len/total_text:.1%}, right: {right_text_len/total_text:.1%})", META, "INFO", conf)
            return extract_single_column_text(page, has_hebrew, conf)
        
        # Если дошли сюда - у нас действительно две колонки
        # Дополнительная проверка: анализируем плотность текста
        left_density = len(left_zone) / (page_width * 0.5) if left_zone else 0
        right_density = len(right_zone) / (page_width * 0.5) if right_zone else 0
        
        # Если плотность текста очень неравномерная - вероятно одноколоночный документ
        if left_density > 0 and right_density > 0:
            density_ratio = min(left_density, right_density) / max(left_density, right_density)
            if density_ratio < 0.4:  # One column has significantly less text
                if conf:
                    utils.tbox_log(f"Detected 1 column (uneven density: {density_ratio:.2f}), using enhanced extraction", META, "INFO", conf)
                return extract_single_column_text(page, has_hebrew, conf)
        
        # Разделяем на левую и правую колонки
        left_column = []
        right_column = []
        
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            if word_center < mid_x:
                left_column.append(word)
            else:
                right_column.append(word)
        
        # Логируем обнаружение двух колонок и порядок чтения с отладочной информацией
        if conf:
            if has_hebrew:
                utils.tbox_log(f"Detected 2 columns, order: right -> left (RTL) | Width: {page_width:.0f}px | Left: {left_text_len/total_text:.1%} | Middle: {middle_text_len/total_text:.1%} | Right: {right_text_len/total_text:.1%}", META, "INFO", conf)
            else:
                utils.tbox_log(f"Detected 2 columns, order: left -> right (LTR) | Width: {page_width:.0f}px | Left: {left_text_len/total_text:.1%} | Middle: {middle_text_len/total_text:.1%} | Right: {right_text_len/total_text:.1%}", META, "INFO", conf)
        
        # Проверяем, есть ли текст в обеих колонках
        if not left_column or not right_column:
            if conf:
                utils.tbox_log("Обнаружено 1 колонку (пустая колонка), используем улучшенное извлечение", META, "INFO", conf)
            return extract_single_column_text(page, has_hebrew, conf)
        
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
        # Если анализ колонок не удался, используем улучшенное извлечение
        if conf:
            utils.tbox_log(f"Ошибка анализа колонок: {e}, используем улучшенное извлечение", META, "WARNING", conf)
        return extract_single_column_text(page, has_hebrew, conf)

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
                
                # Use new smart mixed layout detection
                bands = segment_page_vertically(page)
                segments = group_similar_bands(bands)
                txt = extract_text_from_mixed_segments(segments, has_hebrew, CONF)
                
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