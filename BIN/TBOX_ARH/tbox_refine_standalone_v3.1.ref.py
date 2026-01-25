import sys, os, requests, time

# Добавляем путь, чтобы скрипт видел tbox_utils.py в корне
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импортируем именно то имя, которое у тебя на диске
try:
    import tbox_utils as utils
    from tbox_utils import tbox_log, load_local_config, tbox_chunk_text, tbox_save_to_docx
except ImportError as e:
    print(f"Критическая ошибка: Не найден файл tbox_utils.py в {project_root}")
    sys.exit(1)
    
# --- ПАСПОРТ (Тот самый стиль) ---
VERSION = "v3.1.ref"
DATE    = "2026-01-25"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

def find_best_model(api_key, is_large_text=True):
    """Ищет самую мощную доступную модель Gemini"""
    for ver in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            models = r.json().get('models', [])
            
            candidates = [m['name'].replace('models/', '') for m in models 
                          if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # Если текст большой, игнорируем слабые модели типа gemma
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

def run_refining(raw_path):
    """Основная логика: Читаем RAW -> Чистим через ИИ -> Сохраняем DOCX"""
    
    # 1. Загрузка окружения
    CONF = utils.load_local_config()
    if not CONF: 
        utils.tbox_log("Конфиг не найден!", META, "ERROR")
        return

    if not os.path.exists(raw_path):
        utils.tbox_log(f"Файл не найден: {raw_path}", META, "ERROR")
        return

    with open(raw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. Поиск модели
    api_key = CONF.get('API_KEY', '').split('#')[0].strip()
    m_name, m_ver = find_best_model(api_key, len(content) > 5000)

    if not m_name:
        utils.tbox_log("Нет подходящих моделей Gemini.", META, "ERROR")
        return

    # 3. Нарезка на чанки (используем утилиту из utils)
    chunks = utils.tbox_chunk_text(content, max_chars=11000)
    utils.tbox_log(f"Текст: {len(content)} симв. ({len(chunks)} ч.). Модель: {m_name}", META, "INFO")
    
    refined_full = ""
    for i, chunk in enumerate(chunks, 1):
        if i > 1: 
            utils.tbox_log("Пауза 15 сек (обход лимитов API)...", META, "INFO")
            time.sleep(15)
            
        utils.tbox_log(f"Обработка {i}/{len(chunks)}...", META, "START")
        
        prompt = (
            "ТЫ — МАСТЕР ВЕРСТКИ И ПУНКТУАЦИИ. СЛОВА НЕ МЕНЯТЬ.\n"
            "ЗАДАЧА: Оформить текст лекции, расставить абзацы и заголовки '#'.\n"
            "Важные мысли и цитаты выделяй жирным '**...**'.\n"
            f"\nТЕКСТ ДЛЯ ВЕРСТКИ:\n{chunk}"
        )
        url = f"https://generativelanguage.googleapis.com/{m_ver}/models/{m_name}:generateContent?key={api_key}"

        try:
            # Таймаут побольше, чтобы ИИ успел дописать
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=200)
            res = r.json()
            if 'candidates' in res and res['candidates'][0].get('content'):
                chunk_result = res['candidates'][0]['content']['parts'][0]['text']
                refined_full += chunk_result.strip() + "\n\n"
            else:
                utils.tbox_log(f"Часть {i} отклонена API, берем RAW", META, "ERROR")
                refined_full += chunk + "\n\n"
        except Exception as e:
            utils.tbox_log(f"Ошибка на части {i}: {e}", META, "ERROR")
            refined_full += chunk + "\n\n"

    # 4. Финализация (Сохранение)
    base_name = os.path.basename(raw_path).replace("_raw.txt", "").replace(".txt", "")
    
    # Сохраняем Markdown
    md_path = os.path.join(CONF.get('TXT_DIR'), f"{base_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(refined_full)
    
    # Сохраняем DOCX (через универсальную процедуру)
    docx_path = os.path.join(CONF.get('DOC_ORIGINALS'), f"{base_name}.docx")
    try:
        utils.tbox_save_to_docx(refined_full, docx_path, title=base_name)
        utils.tbox_log(f"Документация готова: {base_name}", META, "DONE")
    except Exception as e:
        utils.tbox_log(f"Ошибка сохранения DOCX: {e}", META, "ERROR")

# Позволяет запускать из терминала: python tbox_refine_standalone.py file.txt
if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_refining(sys.argv[1])
    else:
        print(f"--- {NAME} {VERSION} ({DATE}) ---")
        print("Использование: ref <raw_file_path>")