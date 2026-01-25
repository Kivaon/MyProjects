import os, sys, time, glob, requests, shutil, re
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from tbox_utils import tbox_log

# --- MANIFEST ---
VERSION = "v5.80.clean_docx"
DATE    = "2026-01-23"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def load_tbox_config():
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(script_dir, "config.txt")
    conf = {}
    if not os.path.exists(config_path): return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    conf[key.strip()] = val.strip()
        actual_base = conf.get('BASE_DIR', script_dir)
        for key in conf:
            if '${BASE_DIR}' in conf[key]:
                conf[key] = conf[key].replace('${BASE_DIR}', actual_base)
        return conf
    except: return None

def translate_md_chunk(chunk, author, conf):
    """Перевод MD-текста с сохранением MD-разметки"""
    api_key = conf.get('API_KEY', '').split('#')[0].strip()
    model = conf.get('MODEL_GEMINI', 'gemini-2.0-flash')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = (
        f"Ты — редактор лекций Рава {author}. Переведи этот текст на русский.\n"
        f"СТРОГО СОХРАНЯЙ РАЗМЕТКУ: '#' для заголовков и '**' для выделений.\n"
        f"Стиль: возвышенный, точный. ТЕКСТ:\n{chunk}"
    )
    
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=120)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"\n[ОШИБКА ПЕРЕВОДА: {e}]\n{chunk}"

def render_md_to_docx(md_text, doc):
    """Отрисовка Markdown в параграфы Word"""
    for line in md_text.split('\n'):
        line = line.strip()
        if not line: continue
        p = doc.add_paragraph()
        if line.startswith('#'):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(line.lstrip('#').strip())
            run.bold = True; run.font.size = Pt(14)
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                run = p.add_run(part.replace('**', ''))
                run.font.name = 'Times New Roman'; run.font.size = Pt(12)
                if part.startswith('**'): run.bold = True

def main():
    CONF = load_tbox_config()
    if not CONF: return
    
    # Вход и выход
    in_dir = CONF.get('TXT_DIR')           # 02_TXT
    out_dir = CONF.get('DOC_TRANSLATED')   # 03_DOC/TRANSLATED
    arh_dir = CONF.get('ARH_TXT')          # 05_ARH/TXT
    
    files = glob.glob(os.path.join(in_dir, "*.txt"))
    if not files:
        tbox_log("Нет новых MD-файлов для перевода в 02_TXT.", META, "INFO", CONF)
        return

    # Берем самый свежий файл
    target = max(files, key=os.path.getmtime)
    file_name = os.path.basename(target)
    author = file_name.split('-')[1].replace('_', ' ') if '-' in file_name else "Раввин"
    
    tbox_log(f"ПЕРЕВОД: {file_name}", META, "START", CONF)

    with open(target, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Делим на куски по 10к символов
    chunks = [full_text[i:i+10000] for i in range(0, len(full_text), 10000)]
    
    doc = Document()
    # Красивые поля
    section = doc.sections[0]
    section.left_margin = Cm(2); section.right_margin = Cm(2)
    doc.add_heading(f"Перевод: {author}", 0).alignment = WD_ALIGN_PARAGRAPH.CENTER

    for i, chunk in enumerate(chunks, 1):
        tbox_log(f"Чанк {i}/{len(chunks)}...", META, "INFO", CONF)
        translated_md = translate_md_chunk(chunk, author, CONF)
        render_md_to_docx(translated_md, doc)
        time.sleep(5) # Пауза для лимитов API

    # Сохранение
    os.makedirs(out_dir, exist_ok=True)
    res_name = f"Ready_{file_name.replace('.txt', '.docx')}"
    res_path = os.path.join(out_dir, res_name)
    doc.save(res_path)
    
    # Архивируем MD-исходник
    os.makedirs(arh_dir, exist_ok=True)
    shutil.move(target, os.path.join(arh_dir, f"TR_DONE_{file_name}"))
    
    tbox_log(f"ГОТОВО: {res_name}", META, "DONE", CONF)

if __name__ == "__main__":
    main()