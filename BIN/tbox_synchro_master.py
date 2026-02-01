import os, sys, re, json
from datetime import datetime
from difflib import SequenceMatcher
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.shared import OxmlElement, qn
import tbox_utils as utils

# --- ПАСПОРТ ---
VERSION = "v2.0.universal"
DATE    = "2026-02-01"
NAME    = os.path.basename(__file__)
META = {"name": NAME, "version": VERSION, "date": DATE}

# --- КОНСТАНТЫ ---
SEGMENT_SIZE = 600  # Размер сегмента для "стены текста"
MIN_MATCH_RATIO = 0.3  # Минимальное сходство для якорей

class TextSegment:
    """Класс для представления текстового сегмента"""
    def __init__(self, text, original_index, is_header=False):
        self.text = text.strip()
        self.original_index = original_index
        self.is_header = is_header
        self.aligned_with = None
        
    def __repr__(self):
        preview = self.text[:50].replace('\n', ' ') + "..." if len(self.text) > 50 else self.text
        return f"Segment[{self.original_index}]: {preview}"

class SynchroMaster:
    """Основной класс синхронизации"""
    
    def __init__(self, conf):
        self.conf = conf
        self.left_segments = []
        self.right_segments = []
        self.alignment_map = []
        
    def log(self, message, level="INFO"):
        """Логирование через tbox_utils"""
        utils.tbox_log(message, META, level, self.conf)
        
    def preprocess_text(self, text):
        """Предварительная обработка текста"""
        # Виртуальное сегментирование для "стены текста"
        if text.count('\n') < len(text) / 1000:  # Если мало переносов строк
            return self.segment_wall_text(text)
        else:
            return self.segment_structured_text(text)
    
    def segment_wall_text(self, text):
        """Разбиваю стену текста на сегменты"""
        segments = []
        sentences = re.split(r'([.!?]+)', text)
        
        current_segment = ""
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]
            
            if len(current_segment + sentence) < SEGMENT_SIZE:
                current_segment += sentence
            else:
                if current_segment.strip():
                    segments.append(current_segment.strip())
                current_segment = sentence
        
        if current_segment.strip():
            segments.append(current_segment.strip())
            
        return segments
    
    def segment_structured_text(self, text):
        """Разбиваю структурированный текст"""
        segments = []
        lines = text.split('\n')
        current_segment = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_segment.strip():
                    segments.append(current_segment.strip())
                    current_segment = ""
                continue
                
            # Заголовки всегда отдельные сегменты
            if line.startswith('#'):
                if current_segment.strip():
                    segments.append(current_segment.strip())
                segments.append(line)
                current_segment = ""
            else:
                if current_segment:
                    current_segment += " " + line
                else:
                    current_segment = line
        
        if current_segment.strip():
            segments.append(current_segment.strip())
            
        return segments
    
    def create_segments(self, segments_list):
        """Создаю объекты TextSegment"""
        result = []
        for i, text in enumerate(segments_list):
            is_header = text.strip().startswith('#')
            result.append(TextSegment(text, i, is_header))
        return result
    
    def find_anchors(self):
        """Нахожу якоря для выравнивания"""
        self.log("Поиск якорей для выравнивания...")
        
        # Сначала выравниваем заголовки
        left_headers = [s for s in self.left_segments if s.is_header]
        right_headers = [s for s in self.right_segments if s.is_header]
        
        for left_header in left_headers:
            best_match = None
            best_ratio = 0
            
            for right_header in right_headers:
                if right_header.aligned_with:
                    continue
                    
                # Сравниваем без учета регистра и лишних пробелов
                left_clean = re.sub(r'\s+', ' ', left_header.text.lower())
                right_clean = re.sub(r'\s+', ' ', right_header.text.lower())
                
                ratio = SequenceMatcher(None, left_clean, right_clean).ratio()
                if ratio > best_ratio and ratio > MIN_MATCH_RATIO:
                    best_ratio = ratio
                    best_match = right_header
            
            if best_match:
                left_header.aligned_with = best_match
                best_match.aligned_with = left_header
                self.log(f"Якорь найден: {left_header.text[:30]}... ↔ {best_match.text[:30]}...")
    
    def align_remaining_segments(self):
        """Выравниваю оставшиеся сегменты"""
        self.log("Выравнивание оставшихся сегментов...")
        
        # Создаем карту выравнивания
        used_left = set()
        used_right = set()
        
        # Добавляем уже выравненные заголовки
        for left_seg in self.left_segments:
            if left_seg.aligned_with:
                self.alignment_map.append((left_seg, left_seg.aligned_with))
                used_left.add(left_seg)
                used_right.add(left_seg.aligned_with)
        
        # Выравниваем остальные сегменты
        left_unaligned = [s for s in self.left_segments if s not in used_left]
        right_unaligned = [s for s in self.right_segments if s not in used_right]
        
        i = j = 0
        while i < len(left_unaligned) or j < len(right_unaligned):
            if i < len(left_unaligned) and j < len(right_unaligned):
                left_seg = left_unaligned[i]
                right_seg = right_unaligned[j]
                
                # Проверяем сходство
                left_clean = re.sub(r'\s+', ' ', left_seg.text.lower())
                right_clean = re.sub(r'\s+', ' ', right_seg.text.lower())
                ratio = SequenceMatcher(None, left_clean, right_clean).ratio()
                
                if ratio > MIN_MATCH_RATIO:
                    # Нашли совпадение
                    self.alignment_map.append((left_seg, right_seg))
                    i += 1
                    j += 1
                else:
                    # Добавляем пустые ячейки
                    if i < len(left_unaligned):
                        self.alignment_map.append((left_unaligned[i], None))
                        i += 1
                    if j < len(right_unaligned):
                        self.alignment_map.append((None, right_unaligned[j]))
                        j += 1
            elif i < len(left_unaligned):
                self.alignment_map.append((left_unaligned[i], None))
                i += 1
            elif j < len(right_unaligned):
                self.alignment_map.append((None, right_unaligned[j]))
                j += 1
    
    def detect_language(self, text):
        """Определяю язык текста"""
        if re.search(r'[\u0590-\u05FF]', text):
            return 'hebrew'
        elif re.search(r'[а-яё]', text.lower()):
            return 'russian'
        else:
            return 'english'
    
    def create_docx(self, left_path, right_path, output_path):
        """Создаю DOCX документ"""
        self.log(f"Создание DOCX: {os.path.basename(output_path)}")
        
        doc = Document()
        
        # Альбомная ориентация
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        new_width, new_height = section.page_height, section.page_width
        section.page_width = new_width
        section.page_height = new_height
        
        # Минимальные поля
        section.left_margin = Cm(1)
        section.right_margin = Cm(1)
        section.top_margin = Cm(1)
        section.bottom_margin = Cm(1)
        
        # Заголовок
        title = doc.add_heading(f"Сверка: {os.path.basename(left_path)} ↔ {os.path.basename(right_path)}", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Информация
        info_para = doc.add_paragraph()
        info_para.add_run(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        info_para.add_run(f"Версия: TBox Synchro Master {VERSION}")
        info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()  # Пробел
        
        # Создаем таблицу
        table = doc.add_table(rows=len(self.alignment_map) + 1, cols=2)
        table.style = 'Table Grid'
        
        # Заголовки таблицы
        header_cells = table.rows[0].cells
        header_cells[0].text = os.path.basename(left_path)
        header_cells[1].text = os.path.basename(right_path)
        
        # Заполняем таблицу
        for row_idx, (left_seg, right_seg) in enumerate(self.alignment_map, 1):
            cells = table.rows[row_idx].cells
            
            # Левая ячейка
            if left_seg:
                self.format_cell(cells[0], left_seg.text)
            else:
                cells[0].text = ""
                self.format_cell(cells[0], "")
            
            # Правая ячейка
            if right_seg:
                self.format_cell(cells[1], right_seg.text)
            else:
                cells[1].text = ""
                self.format_cell(cells[1], "")
        
        doc.save(output_path)
        self.log(f"DOCX сохранен: {os.path.basename(output_path)}", "DONE")
    
    def format_cell(self, cell, text):
        """Форматирую ячейку с учетом языка"""
        if not text.strip():
            return
            
        language = self.detect_language(text)
        
        # Очищаем ячейку
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run._element.getparent().remove(run._element)
        
        paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
        run = paragraph.add_run(text)
        
        if language == 'hebrew':
            # RTL для иврита
            paragraph.paragraph_format.right_to_left = True
            run.font.name = 'Arial'
            run.font.rtl = True
        else:
            # LTR для русского/английского
            paragraph.paragraph_format.right_to_left = False
            run.font.name = 'Times New Roman'
        
        run.font.size = Pt(10)
    
    def process_files(self, left_path, right_path, output_path):
        """Основной процесс синхронизации"""
        self.log(f"Старт синхронизации: {os.path.basename(left_path)} ↔ {os.path.basename(right_path)}")
        
        # Читаем файлы
        with open(left_path, 'r', encoding='utf-8') as f:
            left_text = f.read()
        with open(right_path, 'r', encoding='utf-8') as f:
            right_text = f.read()
        
        # Предварительная обработка
        self.log("Предварительная обработка текстов...")
        left_segments_raw = self.preprocess_text(left_text)
        right_segments_raw = self.preprocess_text(right_text)
        
        # Создаем сегменты
        self.left_segments = self.create_segments(left_segments_raw)
        self.right_segments = self.create_segments(right_segments_raw)
        
        self.log(f"Сегментов создано: левый={len(self.left_segments)}, правый={len(self.right_segments)}")
        
        # Выравнивание
        self.find_anchors()
        self.align_remaining_segments()
        
        self.log(f"Выравнивание завершено: {len(self.alignment_map)} пар")
        
        # Создаем DOCX
        self.create_docx(left_path, right_path, output_path)
    
    def export_corrections(self, docx_path, output_md_path):
        """Экспорт правок из правой колонки"""
        self.log(f"Экспорт правок из: {os.path.basename(docx_path)}")
        
        doc = Document(docx_path)
        extracted_text = []
        
        # Пропускаем заголовок таблицы
        for row in doc.tables[0].rows[1:]:
            right_cell = row.cells[1]
            if right_cell.text.strip():
                extracted_text.append(right_cell.text.strip())
        
        # Сохраняем как MD
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(extracted_text))
        
        self.log(f"Правки экспортированы: {os.path.basename(output_md_path)}", "DONE")

def find_file_pairs(conf, mode):
    """Поиск пар файлов для разных режимов"""
    base_dir = conf.get('BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if mode == "refinery":
        raw_dir = conf.get('TXT_RAW', '02_TXT/raw')
        md_dir = conf.get('MD_DIR', '02_TXT/MD')
        
        # Ищем последнюю пару raw ↔ md по соответствию имен
        raw_files = {f: os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.endswith('.txt')}
        md_files = {f: os.path.join(md_dir, f) for f in os.listdir(md_dir) if f.endswith('.md')}
        
        # Ищем пары с похожими именами
        best_pair = None
        best_time = 0
        
        for raw_name, raw_path in raw_files.items():
            # Убираем расширения и префиксы для сравнения
            raw_base = re.sub(r'_raw\.txt$', '', raw_name)
            raw_base = re.sub(r'^\d{6}_\d{6}_', '', raw_base)  # убираем таймстемп
            
            for md_name, md_path in md_files.items():
                md_base = re.sub(r'\.md$', '', md_name)
                md_base = re.sub(r'^\d{6}_\d{6}_', '', md_base)  # убираем таймстемп
                
                # Проверяем сходство имен
                if raw_base.lower() in md_name.lower() or md_name.lower() in raw_name.lower():
                    # Нашли пару - проверяем время
                    pair_time = max(os.path.getmtime(raw_path), os.path.getmtime(md_path))
                    if pair_time > best_time:
                        best_time = pair_time
                        best_pair = (raw_path, md_path)
        
        return best_pair if best_pair else (None, None)
    
    elif mode == "translate":
        md_dir = conf.get('MD_DIR', '02_TXT/MD')
        doc_dir = conf.get('DOC_TRANSLATED', '03_DOC/TRANSLATED')
        
        # Ищем последнюю пару md ↔ docx по соответствию имен
        md_files = {f: os.path.join(md_dir, f) for f in os.listdir(md_dir) if f.endswith('.md')}
        doc_files = {f: os.path.join(doc_dir, f) for f in os.listdir(doc_dir) if f.endswith('.docx')}
        
        # Ищем пары с похожими именами
        best_pair = None
        best_time = 0
        
        for md_name, md_path in md_files.items():
            # Убираем расширения и префиксы
            md_base = re.sub(r'\.md$', '', md_name)
            md_base = re.sub(r'^\d{6}_\d{6}_', '', md_base)
            
            for doc_name, doc_path in doc_files.items():
                doc_base = re.sub(r'\.docx$', '', doc_name)
                doc_base = re.sub(r'^Ready_', '', doc_base)  # убираем префикс Ready_
                doc_base = re.sub(r'^\d{6}_\d{6}_', '', doc_base)
                
                # Проверяем сходство имен
                if md_base.lower() in doc_name.lower() or doc_name.lower() in md_name.lower():
                    # Нашли пару - проверяем время
                    pair_time = max(os.path.getmtime(md_path), os.path.getmtime(doc_path))
                    if pair_time > best_time:
                        best_time = pair_time
                        best_pair = (md_path, doc_path)
        
        return best_pair if best_pair else (None, None)
    
    return None, None

def main():
    """Главная функция"""
    # Загрузка конфигурации
    conf = utils.load_local_config()
    if not conf:
        print("Ошибка: config.txt не найден")
        return
    
    synchro = SynchroMaster(conf)
    
    # Парсинг аргументов
    if len(sys.argv) < 2:
        print("TBox Synchro Master v2.0")
        print("\nИспользование:")
        print("  python tbox_synchro_master.py manual <left_file> <right_file>")
        print("  python tbox_synchro_master.py autoref")
        print("  python tbox_synchro_master.py autotr")
        print("  python tbox_synchro_master.py export <docx_file> <output_md>")
        return
    
    command = sys.argv[1].lower()
    
    if command == "manual":
        if len(sys.argv) < 4:
            print("Ошибка: нужны два файла для сравнения")
            return
        
        left_path = sys.argv[2]
        right_path = sys.argv[3]
        
        if not os.path.exists(left_path) or not os.path.exists(right_path):
            print("Ошибка: один из файлов не найден")
            return
        
        # Создаем выходное имя
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        left_name = os.path.splitext(os.path.basename(left_path))[0]
        right_name = os.path.splitext(os.path.basename(right_path))[0]
        output_path = f"synchro_{timestamp}_{left_name}_vs_{right_name}.docx"
        
        synchro.process_files(left_path, right_path, output_path)
    
    elif command == "autoref":
        left_path, right_path = find_file_pairs(conf, "refinery")
        if not left_path or not right_path:
            synchro.log("Пара файлов для refinery не найдена", "ERROR")
            return
        
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        output_path = f"synchro_refinery_{timestamp}.docx"
        
        synchro.process_files(left_path, right_path, output_path)
    
    elif command == "autotr":
        left_path, right_path = find_file_pairs(conf, "translate")
        if not left_path or not right_path:
            synchro.log("Пара файлов для translate не найдена", "ERROR")
            return
        
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        output_path = f"synchro_translate_{timestamp}.docx"
        
        synchro.process_files(left_path, right_path, output_path)
    
    elif command == "export":
        if len(sys.argv) < 4:
            print("Ошибка: нужны docx файл и выходной md файл")
            return
        
        docx_path = sys.argv[2]
        output_md = sys.argv[3]
        
        if not os.path.exists(docx_path):
            print("Ошибка: DOCX файл не найден")
            return
        
        synchro.export_corrections(docx_path, output_md)
    
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == "__main__":
    main()
