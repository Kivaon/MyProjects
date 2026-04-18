#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TBox OCR Extractor - Извлечение текста из изображений с нумерацией
Работает по той же логике, что и PDF extractor
"""

import os
import sys
import re
from datetime import datetime

# Добавляем путь к родительской директории для импорта утилит
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    import tconfig as utils
except ImportError:
    print("Ошибка: tconfig не найден. Проверьте наличие файла tconfig.py в:", parent_dir)
    sys.exit(1)

# Импортируем наш универсальный Refinery
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# Импортируем OCR библиотеки
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("ВНИМАНИЕ: pytesseract или PIL не установлены. OCR не будет работать.")

# --- PASSPORT ---
VERSION = "v1.1.ocr-stable"
DATE    = "2026-04-18"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def find_ocr_files(base_name, ocr_dir, conf=None):
    """Находит все OCR файлы с указанным базовым именем и нумерацией"""
    if not os.path.exists(ocr_dir):
        if conf:
            utils.tbox_log(f"Директория OCR не найдена: {ocr_dir}", META, "ERROR", conf)
        return []
    
    # Ищем файлы по шаблонам: base_name.jpg, base_name1.jpg, base_name2.jpg, base_name_001.jpg...
    patterns = [
        re.compile(rf"{re.escape(base_name)}\.(jpg|jpeg|png|tiff|tif)$", re.IGNORECASE),  # agreement.jpg
        re.compile(rf"{re.escape(base_name)}(\d+)\.(jpg|jpeg|png|tiff|tif)$", re.IGNORECASE),  # agreement1.jpg
        re.compile(rf"{re.escape(base_name)}_(\d+)\.(jpg|jpeg|png|tiff|tif)$", re.IGNORECASE)  # agreement_001.jpg
    ]
    
    found_files = []
    
    # Сначала ищем базовый файл без номера
    for ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif']:
        base_file = os.path.join(ocr_dir, f"{base_name}.{ext}")
        if os.path.exists(base_file):
            found_files.append((0, base_file, f"{base_name}.{ext}"))
            break  # Нашли базовый файл, выходим из цикла
    
    # Затем ищем пронумерованные файлы (все паттерны)
    numbered_files = []
    for filename in os.listdir(ocr_dir):
        for pattern in patterns[1:]:  # Пропускаем первый паттерн (базовый файл)
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                filepath = os.path.join(ocr_dir, filename)
                # Избегаем дубликатов
                if not any(f[1] == filepath for f in numbered_files):
                    numbered_files.append((num, filepath, filename))
                break  # Нашли совпадение, переходим к следующему файлу
    
    # Сортируем пронумерованные файлы по номеру
    numbered_files.sort(key=lambda x: x[0])
    
    # Объединяем: сначала базовый, потом пронумерованные
    all_files = found_files + numbered_files
    
    if conf:
        utils.tbox_log(f"Найдено OCR файлов: {len(all_files)} для '{base_name}'", META, "INFO", conf)
        for num, filepath, filename in all_files:
            utils.tbox_log(f"  {num if num > 0 else 'base'}: {filename}", META, "INFO", conf)
    
    return all_files

def detect_image_language(text):
    """Автоматически определяет язык текста из OCR"""
    if not text or not text.strip():
        return 'unknown'
    
    text_sample = text[:500]  # Анализируем первые 500 символов
    
    # Иврит
    hebrew_pattern = r'[\u0590-\u05FF\uFB1D-\uFB4F]'
    hebrew_chars = len(re.findall(hebrew_pattern, text_sample))
    if hebrew_chars > 5:
        return 'hebrew'
    
    # Китайский
    chinese_pattern = r'[\u4e00-\u9fff]'
    chinese_chars = len(re.findall(chinese_pattern, text_sample))
    if chinese_chars > 5:
        return 'chinese'
    
    # Русский
    russian_chars = len(re.findall(r'[а-яёА-ЯЁ]', text_sample))
    if russian_chars > 10:
        return 'russian'
    
    # Арабский
    arabic_pattern = r'[\u0600-\u06FF]'
    arabic_chars = len(re.findall(arabic_pattern, text_sample))
    if arabic_chars > 5:
        return 'arabic'
    
    # Японский
    japanese_pattern = r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]'
    japanese_chars = len(re.findall(japanese_pattern, text_sample))
    if japanese_chars > 5:
        return 'japanese'
    
    # Корейский
    korean_pattern = r'[\uac00-\ud7af]'
    korean_chars = len(re.findall(korean_pattern, text_sample))
    if korean_chars > 5:
        return 'korean'
    
    # Испанский
    spanish_chars = len(re.findall(r'[ñÑáÁéÉíÍóÓúÚüÜ¿¡]', text_sample))
    if spanish_chars > 2:
        return 'spanish'
    
    # Французский
    french_chars = len(re.findall(r'[àâäéèêëïîôöùûüÿç]', text_sample))
    if french_chars > 2:
        return 'french'
    
    # Немецкий
    german_chars = len(re.findall(r'[äöüßÄÖÜ]', text_sample))
    if german_chars > 2:
        return 'german'
    
    # По умолчанию - английский
    latin_chars = len(re.findall(r'[a-zA-Z]', text_sample))
    if latin_chars > 20:
        return 'english'
    
    return 'unknown'

def get_ocr_language_code(detected_lang):
    """Возвращает код языка для tesseract"""
    lang_codes = {
        'hebrew': 'heb',
        'chinese': 'chi_sim+chi_tra',  # Упрощенный и традиционный
        'russian': 'rus',
        'arabic': 'ara',
        'japanese': 'jpn',
        'korean': 'kor',
        'spanish': 'spa',
        'french': 'fra',
        'german': 'deu',
        'english': 'eng',
        'unknown': 'eng+rus+heb+chi_sim+chi_tra'  # Все основные языки
    }
    return lang_codes.get(detected_lang, 'eng+rus+heb')

def extract_text_from_images(image_files, conf=None):
    """Извлекает и объединяет текст из изображений через OCR с автоопределением языка"""
    if not image_files:
        if conf:
            utils.tbox_log("Изображения не найдены", META, "ERROR", conf)
        return ""
    
    if not OCR_AVAILABLE:
        error_msg = "OCR библиотеки не доступны. Установите pytesseract и Pillow"
        if conf:
            utils.tbox_log(error_msg, META, "ERROR", conf)
        else:
            print(error_msg)
        return ""
    
    combined_text = []
    language_stats = {}
    
    for num, filepath, filename in image_files:
        try:
            # Сначала пробуем многоязычный OCR
            print(f"Обработка изображения: {filename}...")
            text = pytesseract.image_to_string(Image.open(filepath), lang='eng+rus+heb+chi_sim+chi_tra')
            
            # Определяем основной язык текста
            detected_lang = detect_image_language(text)
            ocr_lang = get_ocr_language_code(detected_lang)
            
            # Если язык определен, делаем повторное распознавание с правильным языком
            if detected_lang != 'unknown':
                print(f"  Обнаружен язык: {detected_lang}, повторное распознавание...")
                text = pytesseract.image_to_string(Image.open(filepath), lang=ocr_lang)
            
            # Статистика языков
            language_stats[detected_lang] = language_stats.get(detected_lang, 0) + 1
            
            if text and text.strip():
                # Добавляем заголовок части с указанием языка
                if num == 0:
                    part_header = f"--- ОСНОВНОЙ ФАЙЛ (ЯЗЫК: {detected_lang.upper()}) ---\n"
                else:
                    part_header = f"--- ЧАСТЬ {num} (ЯЗЫК: {detected_lang.upper()}) ---\n"
                combined_text.append(part_header)
                combined_text.append(text.strip())
                combined_text.append("\n\n")
                
                if conf:
                    utils.tbox_log(f"Добавлена часть {num if num > 0 else 'base'}: {len(text)} символов (язык: {detected_lang})", META, "INFO", conf)
            else:
                print(f"Текст не найден в {filename}")
                
        except Exception as e:
            error_msg = f"Ошибка OCR {filename}: {e}"
            if conf:
                utils.tbox_log(error_msg, META, "ERROR", conf)
            else:
                print(error_msg)
    
    # Выводим статистику языков
    print(f"\n📊 Статистика языков:")
    for lang, count in language_stats.items():
        print(f"  {lang.upper()}: {count} файлов")
    
    return "\n".join(combined_text)

def main():
    """Главная функция"""
    # 1. Сбор вводных
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.dirname(script_dir)
    
    # Загружаем конфиг через утилиты (как в PDF)
    CONF = utils.load_local_config()
    if not CONF:
        print("Критическая ошибка: Конфиг не найден.")
        return
    
    # 2. Пути из конфигурации (как в PDF)
    OCR_DIR = CONF.get('OCR_DIR', '01_INBOX')
    RAW_DIR = CONF.get('TXT_RAW', '02_TXT/raw')
    
    if not OCR_DIR or not RAW_DIR:
        print("В конфиге не заданы OCR_DIR или TXT_RAW")
        return
    
    # 3. ЛОГИКА ПОИСКА ФАЙЛА (как в PDF)
    base_name = None
    if user_arg:
        base_name = user_arg
    else:
        # Берем имя по умолчанию из конфига
        base_name = CONF.get('DEFAULT_OCR_NAME', 'document')
    
    if not base_name:
        print("Ошибка: укажите имя файла или настройте DEFAULT_OCR_NAME в конфиге")
        return
    
    # 4. ПОДГОТОВКА СОХРАНЕНИЯ (как в PDF)
    os.makedirs(RAW_DIR, exist_ok=True)
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_name = base_name
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{original_name}_ocr_raw.txt")

    # Логирование
    print(f"[{time_tag}] [{NAME} {VERSION}] [START] Обработка OCR: {base_name}")
    utils.tbox_log(f"Начало обработки OCR: {base_name}", META, "START", CONF)
    
    try:
        # 5. ПОИСК ИЗОБРАЖЕНИЙ
        image_files = find_ocr_files(base_name, OCR_DIR, CONF)
        
        if not image_files:
            error_msg = f"Изображения для '{base_name}' не найдены в {OCR_DIR}"
            print(error_msg)
            utils.tbox_log(error_msg, META, "ERROR", CONF)
            return
        
        # 6. OCR ИЗВЛЕЧЕНИЕ ТЕКСТА
        print("\nOCR извлечение текста из изображений...")
        combined_text = extract_text_from_images(image_files, CONF)
        
        if not combined_text:
            error_msg = "Текст не извлечен из изображений"
            print(error_msg)
            utils.tbox_log(error_msg, META, "ERROR", CONF)
            return
        
        # 7. СОХРАНЕНИЕ RAW ФАЙЛА (как в PDF)
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {original_name}\n")
            f.write(f"SOURCE: OCR_EXTRACTOR\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write(combined_text)
        
        print(f"\n✅ Сырой текст сохранен: {os.path.basename(output_txt)}")
        utils.tbox_log(f"Сырой текст сохранен: {os.path.basename(output_txt)}", META, "DONE", CONF)
        
        # 8. АВТО-ПЕРЕДАЧА В REFINERY (как в PDF)
        # Проверяем весь извлеченный текст на наличие языков
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', combined_text))
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', combined_text))
        has_russian = bool(re.search(r'[а-яёА-ЯЁ]', combined_text))
        
        # Умный выбор режима
        if has_hebrew or has_chinese or has_russian:
            chosen_mode = "MULTILANG"
        else:
            chosen_mode = "CONTRACT"  # Для договоров
            
        if refinery:
            utils.tbox_log(f"Передача в Refinery (Режим: {chosen_mode})...", META, "INFO", CONF)
            refinery.run_refining(output_txt, mode=chosen_mode)
        else:
            utils.tbox_log("Refinery не найден, автоматическая верстка пропущена.", META, "WARNING", CONF)
        
        # 9. ЗАВЕРШЕНИЕ
        print(f"\n--- ЗАВЕРШЕНО: {base_name} ---")
        utils.tbox_log(f"--- ЗАВЕРШЕНО: {base_name} ---", META, "DONE", CONF)
        
    except Exception as e:
        error_msg = f"Критический сбой в работе OCR экстрактора: {e}"
        print(error_msg)
        utils.tbox_log(error_msg, META, "ERROR", CONF)

if __name__ == "__main__":
    main()
