import sys, os, requests, time, re

# --- ИНИЦИАЛИЗАЦИЯ ПУТЕЙ ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import tbox_utils as utils
except ImportError:
    print(f"Критическая ошибка: tbox_utils.py не найден в {project_root}")
    sys.exit(1)

# --- ПАСПОРТ ---
VERSION = "v5.00.git-structure"
DATE    = "2026-04-14"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# --- ШАБЛОНЫ ИНСТРУКЦИЙ (ПРОМПТЫ ЗАШИТЫ ЗДЕСЬ) ---
PROMPT_TEMPLATES = {
    "PDF": (
        "ТЫ — МАСТЕР ВЕРСТКИ PDF. СЛОВА НЕ МЕНЯТЬ.\n"
        "ЗАДАЧА: Склеить разорванные строки в абзацы, убрать номера страниц и мусор.\n"
        "Оформить заголовки '#' и списки."
    ),
    "PDF_HE": (
        "ТЫ — ЭКСПЕРТ ПО ВОССТАНОВЛЕНИЮ ТЕКСТА ИЗ ГРЯЗНЫХ PDF (ИВРИТ + РУССКИЙ).\n"
            "СЛОВА НЕ МЕНЯТЬ, НО ИСПРАВИТЬ ОШИБКИ РАСПОЗНАВАНИЯ.\n\n"
            "ЗАДАЧИ:\n"
            "1. ИСПРАВИТЬ ОГЛАСОВКИ (НИКУДОТ): В исходном тексте огласовки могут стоять ПЕРЕД буквами или отдельно. "
            "Верни их на места или убери, если они мешают целостности слова. Текст должен стать читаемым.\n"
            "2. СКЛЕИТЬ СТРОКИ: PDF разорвал предложения на отдельные строки. Собери их в цельные, логические абзацы. "
            "Новый абзац — только там, где закончилась мысль или по смыслу начинается новая тема.\n"
            "3. ЧИСТКА: Удали номера страниц, колонтитулы и артефакты (странные символы вроде ).\n"
            "4. ОФОРМЛЕНИЕ: Используй заголовки '#' и списки только там, где это было в оригинале.\n"
            "\nРЕЗУЛЬТАТ ВЕРНИ В ЧИСТОМ MARKDOWN."    
    ),
    "YT": (
       "ТЫ — ФОРМАТЕР. НЕ ПЕРЕСКАЗЫВАЙ, НЕ ДОБАВЛЯЙ СЛОВА.\n"
            "ТВОЯ ЗАДАЧА: Только расставить пунктуацию и разбить на абзацы. ВСЕ СЛОВА ОСТАВЛЯТЬ БЕЗ ИЗМЕНЕНИЙ.\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. НЕ ИЗМЕНЯЯ СЛОВА И ИХ ПОСЛЕДОВАТЕЛЬНОСТЬ, ДОБАВЬ ЗНАКИ ПРЕПИНАНИЯ И РАЗБЕЙ НА АБЗАЦЫ.\n"
            "2. ДОБАВИТЬ заголовки для логических блоков и выдели их '#'.\n"
            "5. ВЫДЕЛИТЬ цитаты '**текст**'.\n\n"
            "ЗАПРЕЩЕНО: пересказ, вступления, комментарии.\n\n"
    ),
    "AUDIO": (
        "ТЫ — РЕДАКТОР-ФОРМАТЕР. ПЕРЕД ТОБОЙ ТРАНСКРИПТ АУДИОЛЕКЦИИ.\n\n"
        "ВАЖНОЕ ПРАВИЛО: НЕ ПЕРЕВОДИ ТЕКСТ! Сохраняй язык оригинала (иврит или русский).\n\n"
        "ТВОЯ ЗАДАЧА:\n"
        "1. ОФОРМЛЕНИЕ: Разбей монолог на логические абзацы. Добавь заголовки '#' для тем.\n"
        "2. ЧИСТКА: Удали слова-паразиты, повторы, ошибки распознавания.\n"
        "3. СТРУКТУРА: Объедини короткие сегменты в осмысленные абзацы.\n"
        "4. ЦИТАТЫ: Если есть цитаты из Торы/Гмары, оформи их '**текст**'.\n"
        "5. ЯЗЫК: Сохраняй оригинальный язык текста БЕЗ ИЗМЕНЕНИЙ.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN. НЕ ПЕРЕВОДИ НИЧЕГО!"
    ),
    "MULTILANG": (
        "ТЫ — МНОГОЯЗЫЧНЫЙ РЕДАКТОР-ФОРМАТЕР. ПЕРЕД ТОБОЙ ТЕКСТ НА ЛЮБОМ ЯЗЫКЕ.\n\n"
        "ВАЖНОЕ ПРАВИЛО: НЕ ПЕРЕВОДИ ТЕКСТ! Сохраняй язык оригинала БЕЗ ИЗМЕНЕНИЙ.\n\n"
        "ТВОЯ ЗАДАЧА:\n"
        "1. ОПРЕДЕЛИ ЯЗЫК: Определи язык текста (иврит, русский, английский, испанский, и т.д.).\n"
        "2. ОФОРМЛЕНИЕ: Разбей текст на логические абзацы. Добавь заголовки '#' для тем.\n"
        "3. ЧИСТКА: Удали слова-паразиты, повторы, ошибки распознавания.\n"
        "4. СТРУКТУРА: Объедини короткие сегменты в осмысленные абзацы.\n"
        "5. ЦИТАТЫ: Выделяй цитаты '**текст**'.\n"
        "6. ЯЗЫК: Сохраняй оригинальный язык текста БЕЗ ИЗМЕНЕНИЙ.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN. НЕ ПЕРЕВОДИ НИЧЕГО!"
    ),
    "CONTRACT": (
        "ТЫ — ЭКСПЕРТ ПО ЮРИДИЧЕСКИМ ДОКУМЕНТАМ И ДОГОВОРАМ. ПЕРЕД ТОБОЙ OCR-ТЕКСТ ДОГОВОРА.\n\n"
        "ВАЖНОЕ ПРАВИЛО: НЕ ПЕРЕВОДИ ТЕКСТ! Сохраняй язык оригинала БЕЗ ИЗМЕНЕНИЙ.\n\n"
        "ТВОЯ ЗАДАЧА:\n"
        "1. ОПРЕДЕЛИ ЯЗЫК: Определи язык текста (иврит, русский, английский, китайский и т.д.).\n"
        "2. ВОССТАНОВЛЕНИЕ: Исправь OCR ошибки, особенно в юридических терминах, датах, суммах.\n"
        "3. СТРУКТУРА: Разбей текст на логические разделы: заголовок, стороны, предмет, условия, подписи.\n"
        "4. ФОРМАТИРОВАНИЕ: Используй заголовки '#' для разделов договора.\n"
        "5. ЧИСТКА: Удали артефакты OCR, но сохрани все юридически значимые элементы.\n"
        "6. ЯЗЫК: Сохраняй оригинальный язык текста БЕЗ ИЗМЕНЕНИЙ.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В ЧИСТОМ MARKDOWN. НЕ ПЕРЕВОДИ НИЧЕГО!"
    ),
    "TRANSLATE_TO_RU": (
        "ТЫ — ПРОФЕССИОНАЛЬНЫЙ ПЕРЕВОДЧИК. ПЕРЕД ТОБОЙ ТЕКСТ НА ЛЮБОМ ЯЗЫКЕ.\n\n"
        "ЗАДАЧА: Переведи текст на РУССКИЙ язык, сохранив структуру и смысл.\n\n"
        "ПРАВИЛА ПЕРЕВОДА:\n"
        "1. ТОЧНОСТЬ: Сохрани оригинальный смысл и стиль.\n"
        "2. СТРУКТУРА: Сохраняй абзацы и заголовки '#' из оригинала.\n"
        "3. ЦИТАТЫ: Сохраняй выделение цитат '**текст**'.\n"
        "4. ТЕРМИНОЛОГИЯ: Используй подходящую терминологию для религиозных/философских текстов.\n"
        "5. ЕСТЕСТВЕННОСТЬ: Перевод должен звучать естественно на русском.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN НА РУССКОМ ЯЗЫКЕ."
    ),
    "TRANSLATE_TO_EN": (
        "ТЫ — ПРОФЕССИОНАЛЬНЫЙ ПЕРЕВОДЧИК. ПЕРЕД ТОБОЙ ТЕКСТ НА ЛЮБОМ ЯЗЫКЕ.\n\n"
        "ЗАДАЧА: Переведи текст на АНГЛИЙСКИЙ язык, сохранив структуру и смысл.\n\n"
        "ПРАВИЛА ПЕРЕВОДА:\n"
        "1. ТОЧНОСТЬ: Сохрани оригинальный смысл и стиль.\n"
        "2. СТРУКТУРА: Сохраняй абзацы и заголовки '#' из оригинала.\n"
        "3. ЦИТАТЫ: Сохраняй выделение цитат '**текст**'.\n"
        "4. ТЕРМИНОЛОГИЯ: Используй подходящую терминологию для религиозных/философских текстов.\n"
        "5. ЕСТЕСТВЕННОСТЬ: Перевод должен звучать естественно на английском.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN НА АНГЛИЙСКОМ ЯЗЫКЕ."
    ),
    "TRANSLATE_TO_HE": (
        "ТЫ — ПРОФЕССИОНАЛЬНЫЙ ПЕРЕВОДЧИК. ПЕРЕД ТОБОЙ ТЕКСТ НА ЛЮБОМ ЯЗЫКЕ.\n\n"
        "ЗАДАЧА: Переведи текст на ИВРИТ, сохранив структуру и смысл.\n\n"
        "ПРАВИЛА ПЕРЕВОДА:\n"
        "1. ТОЧНОСТЬ: Сохрани оригинальный смысл и стиль.\n"
        "2. СТРУКТУРА: Сохраняй абзацы и заголовки '#' из оригинала.\n"
        "3. ЦИТАТЫ: Сохраняй выделение цитат '**текст**'.\n"
        "4. ТЕРМИНОЛОГИЯ: Используй подходящую терминологию для религиозных/философских текстов.\n"
        "5. ЕСТЕСТВЕННОСТЬ: Перевод должен звучать естественно на иврите.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN НА ИВРИТЕ."
    ),
    "CUSTOM": (
        "ТЫ — УНИВЕРСАЛЬНЫЙ РЕДАКТОР. ПЕРЕД ТОБОЙ ТЕКСТ.\n\n"
        "ИНСТРУКЦИЯ: {custom_instruction}\n\n"
        "ПРАВИЛА:\n"
        "1. Сохрани структуру текста (абзацы, заголовки).\n"
        "2. Примени указанные правила форматирования.\n"
        "3. ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN."
    ),
    "GENERAL": "Оформи текст в Markdown, расставь абзацы и логические заголовки."
}

def detect_language_auto(text):
    """Автоматическое определение языка текста"""
    if not text or not text.strip():
        return 'unknown'
    
    text_sample = text[:500]  # Анализируем первые 500 символов
    
    # Иврит
    hebrew_pattern = r'[\u0590-\u05FF\uFB1D-\uFB4F]'
    hebrew_chars = len(re.findall(hebrew_pattern, text_sample))
    if hebrew_chars > 5:
        return 'hebrew'
    
    # Русский
    russian_chars = len(re.findall(r'[а-яёА-ЯЁ]', text_sample))
    if russian_chars > 10:
        return 'russian'
    
    # Арабский
    arabic_pattern = r'[\u0600-\u06FF]'
    arabic_chars = len(re.findall(arabic_pattern, text_sample))
    if arabic_chars > 5:
        return 'arabic'
    
    # Китайский
    chinese_pattern = r'[\u4e00-\u9fff]'
    chinese_chars = len(re.findall(chinese_pattern, text_sample))
    if chinese_chars > 5:
        return 'chinese'
    
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
    
    # Испанский (проверка по характерным буквам)
    spanish_chars = len(re.findall(r'[ñÑáÁéÉíÍóÓúÚüÜ¿¡]', text_sample))
    if spanish_chars > 2:
        return 'spanish'
    
    # Французский (проверка по акцентам)
    french_chars = len(re.findall(r'[àâäéèêëïîôöùûüÿç]', text_sample))
    if french_chars > 2:
        return 'french'
    
    # Немецкий
    german_chars = len(re.findall(r'[äöüßÄÖÜ]', text_sample))
    if german_chars > 2:
        return 'german'
    
    # По умолчанию - английский (если есть латиница)
    latin_chars = len(re.findall(r'[a-zA-Z]', text_sample))
    if latin_chars > 20:
        return 'english'
    
    return 'unknown'

def find_best_model(api_key, is_large_text=True):
    """Ищет доступную модель Gemini"""
    for ver in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            models = r.json().get('models', [])
            candidates = [m['name'].replace('models/', '') for m in models 
                          if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if is_large_text:
                candidates = [c for c in candidates if "gemma" not in c.lower()]
            for m_name in sorted(candidates, reverse=True):
                test_url = f"https://generativelanguage.googleapis.com/{ver}/models/{m_name}:generateContent?key={api_key}"
                try:
                    res = requests.post(test_url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=3)
                    if res.status_code == 200: return m_name, ver
                except: continue
        except: continue
    return None, None

def run_refining(raw_path=None, mode="YT", use_gpt=False):
    """
    Универсальная обработка ИИ.
    mode: "PDF", "YT" или "GENERAL"
    use_gpt: Use GPT model instead of Gemini
    """
    CONF = utils.load_local_config()
    if not CONF: 
        utils.tbox_log("Конфиг не найден!", META, "ERROR")
        return

    # 1. Выбор файла (аргумент или последний из TXT_RAW)
    if not raw_path:
        raw_dir = CONF.get('TXT_RAW', '').replace('${BASE_DIR}', project_root)
        if not os.path.exists(raw_dir):
            utils.tbox_log(f"Папка {raw_dir} не найдена.", META, "ERROR")
            return
        files = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.lower().endswith('.txt')]
        if not files:
            utils.tbox_log("Нет файлов в TXT_RAW.", META, "ERROR")
            return
        raw_path = max(files, key=os.path.getmtime)

    if not os.path.exists(raw_path):
        utils.tbox_log(f"Файл не найден: {raw_path}", META, "ERROR")
        return

    with open(raw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. Определение режима и логирование промпта
    mode_key = mode.upper()
    
    # Автоопределение языка для MULTILANG
    if mode_key == "MULTILANG":
        detected_language = detect_language_auto(content)
        language_names = {
            'hebrew': 'иврит',
            'russian': 'русский', 
            'english': 'английский',
            'spanish': 'испанский',
            'french': 'французский',
            'german': 'немецкий',
            'unknown': 'неизвестный'
        }
        lang_name = language_names.get(detected_language, 'неизвестный')
        utils.tbox_log(f"DETECTED LANGUAGE: {lang_name}", META, "INFO")
    
    # Обработка кастомного промпта
    if mode_key.startswith("CUSTOM:"):
        custom_instruction = mode_key[7:]  # Убираем "CUSTOM:"
        instruction = PROMPT_TEMPLATES["CUSTOM"].format(custom_instruction=custom_instruction)
        mode_display = f"CUSTOM: {custom_instruction[:30]}..."
    else:
        instruction = PROMPT_TEMPLATES.get(mode_key, PROMPT_TEMPLATES["GENERAL"])
        mode_display = mode_key
    
    utils.tbox_log(f"MODE: {mode_display} | Prompt: {instruction[:60]}...", META, "INFO")

    # 3. API preparation
    if use_gpt:
        # Use GPT model
        openai_key = CONF.get('OPENAI_API_KEY', '').split('#')[0].strip()
        if not openai_key:
            utils.tbox_log("OpenAI API key not found for GPT mode", META, "ERROR")
            return
        m_name = CONF.get('MODEL_GPT', 'gpt-4').strip()
        m_ver = "openai"
        utils.tbox_log(f"Using GPT model: {m_name}", META, "INFO")
    else:
        # Use Gemini model
        api_key = CONF.get('API_KEY', '').split('#')[0].strip()
        m_name, m_ver = find_best_model(api_key, len(content) > 5000)
        if not m_name:
            utils.tbox_log("Gemini API unavailable.", META, "ERROR")
            return
        utils.tbox_log(f"Selected model: {m_name} ({m_ver})", META, "INFO")

    # 4. Нарезка и цикл обработки
    chunks = utils.tbox_chunk_text(content, max_chars=8000)
    refined_full = ""
    
    for i, chunk in enumerate(chunks, 1):
        if i > 1: 
            utils.tbox_log("Пауза 15 сек (лимиты API)...", META, "INFO")
            time.sleep(15)
            
        utils.tbox_log(f"Обработка части {i}/{len(chunks)} ({m_name})...", META, "START")
        
        # Склеиваем инструкцию и текст здесь
        prompt = (
            f"{instruction}\n\n"
            f"--- ТЕКСТ ДЛЯ ОБРАБОТКИ ---\n"
            f"{chunk}"
        )
        
        # API call based on model type
        if m_ver == "openai":
            # GPT API call
            url = f"https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}"}
            json_data = {
                "model": m_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        else:
            # Gemini API call
            url = f"https://generativelanguage.googleapis.com/{m_ver}/models/{m_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            json_data = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            r = requests.post(url, headers=headers, json=json_data, timeout=400)
            res = r.json()
            
            if m_ver == "openai":
                # GPT response parsing
                if 'choices' in res and res['choices'][0].get('message'):
                    chunk_result = res['choices'][0]['message']['content']
                    refined_full += chunk_result.strip() + "\n\n"
                else:
                    utils.tbox_log(f"Chunk {i} rejected, using original.", META, "WARNING")
                    refined_full += chunk + "\n\n"
            else:
                # Gemini response parsing
                if 'candidates' in res and res['candidates'][0].get('content'):
                    chunk_result = res['candidates'][0]['content']['parts'][0]['text']
                    refined_full += chunk_result.strip() + "\n\n"
                else:
                    utils.tbox_log(f"Chunk {i} rejected, using original.", META, "WARNING")
                    refined_full += chunk + "\n\n"
        except Exception as e:
            utils.tbox_log(f"Ошибка чанка {i}: {e}", META, "ERROR")
            refined_full += chunk + "\n\n"

    # 5. Сохранение результатов
    title_match = re.search(r"TITLE:\s*(.*)", content)
    display_title = title_match.group(1).strip() if title_match else os.path.basename(raw_path)
    base_name = os.path.basename(raw_path).replace("_raw.txt", "").replace(".txt", "")
    
    # Детекция иврита
    is_rtl = bool(re.search(r'[\u0590-\u05FF]', refined_full[:3000]))
    
    # Markdown
    md_path = os.path.join(CONF.get('MD_DIR', '02_TXT/MD'), f"{base_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        if is_rtl:
            f.write(f'<div dir="rtl">\n\n# {display_title}\n\n{refined_full}\n\n</div>')
        else:
            f.write(f'# {display_title}\n\n{refined_full}')
    
    # Word
    docx_path = os.path.join(CONF.get('DOC_ORIGINALS'), f"{base_name}.docx")
    try:
        utils.tbox_save_to_docx(refined_full, docx_path, title=display_title)
        utils.tbox_log(f"ГОТОВО: {base_name} (RTL: {is_rtl})", META, "DONE")
    except Exception as e:
        utils.tbox_log(f"Ошибка Word: {e}", META, "ERROR")

if __name__ == "__main__":
    # Если запуск вручную через 'python tbox_refine_standalone.py'

    # 1. Получаем путь к файлу из терминала (аргумент 1)
    # Пример: ref au.txt AUDIO -> здесь au.txt это sys.argv[1]
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 2. Получаем режим из терминала (аргумент 2)
    # Пример: ref au.txt AUDIO -> здесь AUDIO это sys.argv[2]
    if len(sys.argv) > 2:
        target_mode = sys.argv[2].upper()
    else:
        # АВТООПРЕДЕЛЕНИЕ: если ты не написал режим, скрипт посмотрит на имя файла
        if arg_path and "audio" in arg_path.lower():
            target_mode = "AUDIO"
        elif arg_path and "pdf" in arg_path.lower():
            target_mode = "PDF_HE"
        else:
            # Если совсем ничего не понятно — используем YT как базовый
            target_mode = "YT"
            
    # Логируем, что мы выбрали в итоге
    utils.tbox_log(f"Запуск: {os.path.basename(arg_path) if arg_path else 'ПОСЛЕДНИЙ RAW'} | Режим: {target_mode}", META, "INFO")
    
    # 3. Передаем всё в основную функцию
    run_refining(arg_path, mode=target_mode)