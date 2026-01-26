import os, pdfplumber, sys
from datetime import datetime
from bidi.algorithm import get_display

# v1.4-stable - 2026-01-19
# NEW: Формат имени [YYMMDD_HHMMSS]_[OriginalName].txt
# NEW: Пути PDF2TXT -> TXT2DOC

# --- НАСТРОЙКИ ПУТЕЙ ---
PDF_DIR = os.path.expanduser("~/Documents/AI_Lab/PDF2TXT")
RAW_DIR = os.path.expanduser("~/Documents/AI_Lab/TXT2DOC")

def get_now():
    return datetime.now().strftime("%H:%M:%S")

def find_file(search_str=None):
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
        return None
        
    files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    if not files:
        return None

    if search_str:
        # Ищем файлы, содержащие строку в имени
        matches = [f for f in files if search_str.lower() in f.lower()]
        if not matches:
            print(f"[{get_now()}] Файл с меткой '{search_str}' не найден в {PDF_DIR}")
            return None
        # Берем самый свежий из совпавших
        return max([os.path.join(PDF_DIR, f) for f in matches], key=os.path.getmtime)
    
    # По умолчанию берем самый свежий PDF в папке
    return max([os.path.join(PDF_DIR, f) for f in files], key=os.path.getmtime)

def extract_pdf():
    os.makedirs(RAW_DIR, exist_ok=True)
    
    # Читаем аргументы: python extract_pdf.py [имя]
    search_str = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Хелп
    if search_str in ['-h', '--help']:
        print("\n[ PDF EXTRACTOR v1.4 HELP ]")
        print(f"Источник:  {PDF_DIR}")
        print(f"Результат: {RAW_DIR}")
        print("\nИспользование: python3 extract_pdf.py [часть_имени]")
        print("Пример: python3 extract_pdf.py 275")
        return

    target_path = find_file(search_str)
    if not target_path:
        print(f"[{get_now()}] В папке PDF2TXT нет файлов для обработки.")
        return

    # --- ЛОГИКА ИМЕНОВАНИЯ С СЕКУНДАМИ ---
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_file_name = os.path.basename(target_path)
    
    # Итоговое имя: ГГММДД_ЧЧММСС_ИмяФайла.pdf.txt
    new_file_name = f"{time_tag}_{original_file_name}.txt"
    output_txt = os.path.join(RAW_DIR, new_file_name)

    print(f"[{get_now()}] --- ЗАПУСК PDF-ЭКСТРАКТОРА ---")
    print(f"[{get_now()}] Входной файл: {original_file_name}")
    print(f"[{get_now()}] Создаю: {new_file_name}")
    
    full_text = []
    try:
        with pdfplumber.open(target_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                print(f"[{get_now()}] Обработка страницы {i}/{total_pages}...", end='\r')
                page_text = page.extract_text()
                if page_text:
                    # Исправляем направление иврита для каждой страницы
                    full_text.append(get_display(page_text))
    
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write("\n\n".join(full_text))
        
        print(f"\n[{get_now()}] --- УСПЕХ: Файл сохранен в TXT2DOC ---")
        
    except Exception as e:
        print(f"\n[{get_now()}] Ошибка при чтении PDF: {e}")

if __name__ == "__main__":
    extract_pdf()