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
VERSION = "v4.2.final"
DATE    = "2026-01-25"
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
       "ТЫ — МАСТЕР ВЕРСТКИ И ПУНКТУАЦИИ. СЛОВА НЕ МЕНЯТЬ.\n"
            "ТВОЯ ЗАДАЧА: Оформить авторский текст, сохранив каждое слово в оригинальном виде.\n\n"
            "ПРАВИЛА ОФОРМЛЕНИЯ:\n"
            "1. ПУНКТУАЦИЯ: Если в RAW-тексте не хватает знаков препинания или заглавных букв — расставь их, не меняя порядок слов.\n"
            "2. АБЗАЦЫ: Разделяй текст на абзацы СТРОГО по смыслу. Не делай их слишком мелкими или огромными.\n"
            "3. ЗАГОЛОВКИ: Если в тексте нет заголовков, то можно дать название темы для логических блоков, оформи его строкой с символом '#' в начале.\n"
            "4. ЦИТАТЫ: Все приводимые автором цитаты, выдержки или ссылки на источники выделяй жирным шрифтом '**...**'.\n"
            "5. ПОЛНЫЙ ЗАПРЕТ: Никаких комментариев, вступлений, резюме от ИИ или перефразирования. \n"
            "НАЧНИ ВЫВОД СРАЗУ С ПЕРВОГО СЛОВА АВТОРСКОГО ТЕКСТА И ЗАКОНЧИ ПОСЛЕДНИМ\n"
    ),
    "AUDIO": (
        "ТЫ — ЭКСПЕРТ-РЕДАКТОР ЕВРЕЙСКИХ ТЕКСТОВ И ЛЕКЦИЙ.\n"
        "ПЕРЕД ТОБОЙ ТРАНСКРИБАТ АУДИОУРОКА.\n\n"
        "ТВОЯ ЗАДАЧА:\n"
        "1. ОФОРМЛЕНИЕ: Сделай текст читабельным. Разбей монолог на логические абзацы. "
        "Добавь подзаголовки '#' для каждой новой подтемы урока.\n"
        "2. ЧИСТКА: Удали слова-паразиты, повторы и типичные ошибки распознавания речи (особенно в именах и терминах).\n"
        "3. СОХРАННОСТЬ:  Нужно постараться сохранить каждое слово в оригинальном виде (кроме исправлений распознавания)."
        "Если в тексте упоминаются стихи из Торы или Гмары, оформи их как цитаты (через '*').\n"
        "4. СТИЛЬ: Текст должен выглядеть как качественная стенограмма.\n\n"
        "ВЕРНИ РЕЗУЛЬТАТ В MARKDOWN. ЕСЛИ ТЕКСТ НА ИВРИТЕ — СОХРАНЯЙ ИВРИТ."
    ),
    "GENERAL": "Оформи текст в Markdown, расставь абзацы и логические заголовки."
}

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

def run_refining(raw_path=None, mode="YT"):
    """
    Универсальная обработка ИИ.
    mode: "PDF", "YT" или "GENERAL"
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
    instruction = PROMPT_TEMPLATES.get(mode_key, PROMPT_TEMPLATES["GENERAL"])
    
    utils.tbox_log(f"MODE: {mode_key} | Prompt: {instruction[:60]}...", META, "INFO")

    # 3. Подготовка API
    api_key = CONF.get('API_KEY', '').split('#')[0].strip()
    m_name, m_ver = find_best_model(api_key, len(content) > 5000)
    if not m_name:
        utils.tbox_log("Gemini API недоступен.", META, "ERROR")
        return

    # 4. Нарезка и цикл обработки
    chunks = utils.tbox_chunk_text(content, max_chars=8000)
    refined_full = ""
    
    for i, chunk in enumerate(chunks, 1):
        if i > 1: 
            utils.tbox_log("Пауза 15 сек (лимиты API)...", META, "INFO")
            time.sleep(15)
            
        utils.tbox_log(f"Обработка части {i}/{len(chunks)}...", META, "START")
        
        # Склеиваем инструкцию и текст здесь
        prompt = (
            f"{instruction}\n\n"
            f"--- ТЕКСТ ДЛЯ ОБРАБОТКИ ---\n"
            f"{chunk}"
        )
        
        url = f"https://generativelanguage.googleapis.com/{m_ver}/models/{m_name}:generateContent?key={api_key}"

        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=400)
            res = r.json()
            if 'candidates' in res and res['candidates'][0].get('content'):
                chunk_result = res['candidates'][0]['content']['parts'][0]['text']
                refined_full += chunk_result.strip() + "\n\n"
            else:
                utils.tbox_log(f"Чанк {i} отклонен, берем оригинал.", META, "WARNING")
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
            f.write(f"# {display_title}\n\n{refined_full}")
    
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