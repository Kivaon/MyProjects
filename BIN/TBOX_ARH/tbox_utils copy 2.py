import os, sys, re, requests
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MANIFEST ---
VERSION = "v1.3.refinery"
DATE    = "2026-01-23"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def tbox_log(message, script_meta, level="INFO", conf=None):
    """Унифицированный вывод TranslateBox (как у тебя было)"""
    now = datetime.now()
    tag = f"[{script_meta['name']} {script_meta['version']}]"
    time_s = now.strftime('%H:%M:%S')
    time_f = now.strftime('%Y-%m-%d %H:%M:%S')
    t_msg = f"[{time_s}] {tag} [{level}] {message}"
    f_msg = f"[{time_f}] {tag} [{level}] {message}"
    print(t_msg)
    if conf and 'LOG_FILE' in conf:
        try:
            with open(conf['LOG_FILE'], "a", encoding="utf-8") as f:
                f.write(f_msg + "\n")
        except: pass

def tbox_chunk_text(text, max_chars=12000):
    """Утилита: нарезка текста для обхода лимитов API"""
    chunks = []
    current_chunk = []
    current_length = 0
    for line in text.split('\n'):
        if current_length + len(line) > max_chars:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line)
    if current_chunk: chunks.append("\n".join(current_chunk))
    return chunks

def tbox_refine_and_save(raw_text, base_name, conf, title="Original"):
    """
    Улучшенная Refinery: поддерживает нарезку длинных текстов
    """
    # 1. Поиск модели (вызываем нашу новую процедуру поиска)
    api_key = conf.get('API_KEY', '').split('#')[0].strip()
    m_name, m_ver = find_first_ready_model(api_key) # Та самая процедура перебора

    if not m_name:
        return None, "No models available"

    # 2. Нарезка
    chunks = tbox_chunk_text(raw_text)
    refined_full = ""
    
    for i, chunk in enumerate(chunks, 1):
        tbox_log(f"Refinery: Обработка части {i}/{len(chunks)} через {m_name}", META, "INFO", conf)
        
        prompt = (
            f"Ты — редактор. Оформи часть {i} этой лекции: пунктуация, абзацы, "
            "заголовки '#', важные мысли '**'.\n"
            f"ТЕКСТ:\n{chunk}"
        )
        
        url = f"https://generativelanguage.googleapis.com/{m_ver}/models/{m_name}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=120)
            res = r.json()
            # Добавляем кусок к итоговому тексту
            refined_full += res['candidates'][0]['content']['parts'][0]['text'] + "\n\n"
        except Exception as e:
            refined_full += f"\n[ERROR CHUNK {i}]\n{chunk}"

    # 3. Сохранение (MD и DOCX) — код остается прежним, берет refined_full
    # ... здесь твой код записи файлов ...