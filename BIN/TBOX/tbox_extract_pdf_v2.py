import os, sys, re, pdfplumber
from datetime import datetime
from bidi.algorithm import get_display
import tbox_utils as utils
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Импортируем наш универсальный Refinery
try:
    import tbox_refine_standalone as refinery
except ImportError:
    refinery = None

# --- ПАСПОРТ ---
VERSION = "v4.0.block-extractor"
DATE    = "2026-05-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

class BlockType(Enum):
    """Типы текстовых блоков"""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    COLUMN_LEFT = "column_left"
    COLUMN_RIGHT = "column_right"
    TABLE = "table"
    FOOTER = "footer"
    UNKNOWN = "unknown"

# Конфигурация языков с направлениями текста
LANGUAGE_CONFIGS = {
    'hebrew': {
        'pattern': r'[\u0590-\u05FF]',
        'direction': 'rtl',
        'bidi': True,
        'priority': 1
    },
    'arabic': {
        'pattern': r'[\u0600-\u06FF]',
        'direction': 'rtl',
        'bidi': True,
        'priority': 2
    },
    'english': {
        'pattern': r'[a-zA-Z]',
        'direction': 'ltr',
        'bidi': False,
        'priority': 3
    },
    'russian': {
        'pattern': r'[\u0400-\u04FF]',
        'direction': 'ltr',
        'bidi': False,
        'priority': 4
    }
}

@dataclass
class LanguageInfo:
    """Информация о языке документа"""
    language: str
    direction: str  # 'rtl' or 'ltr'
    bidi: bool
    confidence: float

@dataclass
class ExtractionConfig:
    """Конфигурация параметров извлечения"""
    band_height: int = 50
    line_tolerance: int = 3
    column_tolerance: int = 5
    min_column_width: float = 300
    max_column_width: float = 450
    center_threshold: float = 0.7
    column_balance_threshold: float = 0.3
    column_min_content: float = 0.25
    density_ratio_threshold: float = 0.4
    # Пороги для группировки параграфов
    paragraph_large_gap: float = 1.5  # > 1.5 * line_height
    paragraph_medium_gap: float = 1.0  # > 1.0 * line_height
    # Пороги для определения доминирующего языка
    language_threshold: float = 0.6  # > 60% для доминирующего языка

@dataclass
class TextBlock:
    """Текстовый блок с метаданными"""
    text: str
    block_type: BlockType
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    confidence: float = 1.0

@dataclass
class PageSegment:
    """Сегмент страницы"""
    structure: str
    y_start: float
    y_end: float
    words: List[Dict]
    blocks: List[TextBlock]

class PDFBlockExtractor:
    """Улучшенный извлекатель текстовых блоков из PDF"""
    
    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()
        self._debug_mode = True  # Включен для отладки блоков
        self._language_info = None  # Кэш для информации о языке
        
    def extract_from_pdf(self, pdf_path: str, output_path: str, conf: Dict, max_pages: int = None) -> bool:
        """Основной метод извлечения текста из PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                if max_pages:
                    total_pages = min(total_pages, max_pages)
                utils.tbox_log(f"Всего страниц: {len(pdf.pages)} (обрабатываем: {total_pages})", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "INFO", conf)
                
                full_text = []
                all_blocks = []
                for page_num, page in enumerate(pdf.pages, 1):
                    if max_pages and page_num > max_pages:
                        break
                        
                    utils.tbox_log(f"Обработка страницы {page_num}/{total_pages}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "INFO", conf)
                    
                    # Извлекаем блоки со страницы
                    page_blocks = self._extract_blocks_from_page(page, page_num, conf)
                    all_blocks.extend(page_blocks)
                    
                    # Преобразуем блоки в текст
                    page_text = self._blocks_to_text(page_blocks, conf)
                    
                    if page_text:
                        full_text.append(page_text)
                    
                # Сохраняем результат
                self._save_text(all_blocks, output_path, pdf_path, conf)
                
                # Передаем в Refinery если доступен
                self._auto_refinery(output_path, all_blocks, conf)
            
            return True
            
        except Exception as e:
            utils.tbox_log(f"Ошибка извлечения PDF: {e}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", conf)
            return False
    
    def _extract_blocks_from_page(self, page, page_num: int, conf: Dict) -> List[TextBlock]:
        """Извлекает текстовые блоки со страницы с использованием улучшенного алгоритма"""
        try:
            # Извлекаем слова со страницы
            words = page.extract_words()
            if not words:
                return []
            
            # Определяем язык документа
            word_texts = [w['text'] for w in words]
            language_info = self._detect_language(word_texts)
            
            # Используем умную сегментацию
            segments = self._segment_page(page, conf)
            
            # Преобразуем сегменты в блоки с учетом языка
            blocks = []
            for segment in segments:
                segment_blocks = self._segment_to_blocks_enhanced(segment, language_info, page_num, conf)
                blocks.extend(segment_blocks)
            
            return blocks
            
        except Exception as e:
            utils.tbox_log(f"Ошибка извлечения блоков со страницы {page_num}: {e}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "WARNING", conf)
            # Fallback к простому извлечению
            return self._fallback_extraction(page, page_num, conf)
    
    def _segment_to_blocks_enhanced(self, segment: PageSegment, language_info: LanguageInfo, page_num: int, conf: Dict) -> List[TextBlock]:
        """Преобразует сегмент в блоки с использованием НОВОГО алгоритма"""
        if not segment.words:
            return []
        
        if self._debug_mode:
            print(f"\n🔍 [SEGMENT] Обработка сегмента страницы {page_num}:")
            print(f"  Y диапазон: {segment.y_start:.1f}-{segment.y_end:.1f}")
            print(f"  Структура: {segment.structure}")
            print(f"  Слов: {len(segment.words)}")
        
        # Этап 1: Группируем слова в строки по Y и разбиваем по X
        lines = self._words_to_lines_with_x_split(segment.words, language_info)
        
        # Этап 2: Анализ гистограмм для определения колонок с учетом X и Y
        column_blocks = self._group_lines_by_columns(lines, language_info, segment.structure)
        
        # Этап 3: В каждом блоке колонки сортируем строки и группируем в параграфы
        all_paragraphs = []
        
        for col_name, blocks in column_blocks.items():
            for block in blocks:
                # Сортируем строки внутри блока по Y координате
                block['lines'].sort(key=lambda line: line[0]['top'])
                
                # Группируем строки в параграфы
                paragraphs = self._group_lines_to_paragraphs(block['lines'], language_info)
                
                # Добавляем параграфы с информацией о колонке
                for paragraph in paragraphs:
                    all_paragraphs.append({
                        'column_name': col_name,
                        'column_x': block['x0'],
                        'paragraph': paragraph
                    })
        
        # Сортируем параграфы с учетом направления текста
        if language_info.direction == 'rtl':
            # RTL: сначала по X (справа налево), потом по Y (сверху вниз)
            all_paragraphs.sort(key=lambda p: (-p['column_x'], p['paragraph'][0][0]['top'] if p['paragraph'] and p['paragraph'][0] else float('inf')))
        else:
            # LTR: сначала по X (слева направо), потом по Y (сверху вниз)
            all_paragraphs.sort(key=lambda p: (p['column_x'], p['paragraph'][0][0]['top'] if p['paragraph'] and p['paragraph'][0] else float('inf')))
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Блоки колонок:")
            for col_name, blocks in column_blocks.items():
                print(f"  Колонка {col_name}: {len(blocks)} блок(ов)")
                for i, block in enumerate(blocks):
                    print(f"    Блок #{i}: X={block['x0']:.1f}-{block['x1']:.1f}, Y={block['y0']:.1f}-{block['y1']:.1f}")
            print(f"  Всего параграфов: {len(all_paragraphs)}")
        
        # Создаем текстовые блоки из параграфов
        blocks = []
        for para_data in all_paragraphs:
            try:
                paragraph = para_data['paragraph']
                
                # Собираем текст из всех строк параграфа
                text_parts = []
                for line in paragraph:
                    # Сортируем слова в строке по X
                    sorted_words = sorted(line, key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in sorted_words)
                    text_parts.append(line_text)
                
                paragraph_text = ' '.join(text_parts)
                
                # Определяем координаты блока
                x0 = min(w['x0'] for line in paragraph for w in line)
                x1 = max(w['x1'] for line in paragraph for w in line)
                y0 = min(w['top'] for line in paragraph for w in line)
                y1 = max(w['bottom'] for line in paragraph for w in line)
                
                # Классифицируем блок
                block_type = self._classify_paragraph_block_by_text(paragraph_text, language_info)
                
                block = TextBlock(
                    text=paragraph_text,
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    page_num=page_num,
                    block_type=block_type
                )
                # Сохраняем исходные строки для отладки
                block.source_lines = paragraph
                blocks.append(block)
                
                if self._debug_mode:
                    print(f"  Создан блок #{len(blocks)} с {len(paragraph)} строками")
            except Exception as e:
                import traceback
                if self._debug_mode:
                    print(f"  Ошибка создания блока: {e}")
                    print(f"  Тип ошибки: {type(e)}")
                    print(f"  Параграф: {para_data}")
                    print(f"  Traceback: {traceback.format_exc()}")
                continue
        
        if self._debug_mode:
            self._debug_blocks_info(blocks, column_blocks)
            
            # Сохраняем отладочную информацию в отдельный файл
            debug_file_path = output_path.replace('.txt', '_debug.txt')
            self._save_debug_info(blocks, debug_file_path)
        
        # Сортируем блоки
        if language_info.direction == 'rtl':
            # RTL: сверху вниз, справа налево
            columns = {}
            for block in blocks:
                col_x = round(block.x0, 1)
                if col_x not in columns:
                    columns[col_x] = []
                columns[col_x].append(block)
            
            for col_x in columns:
                columns[col_x].sort(key=lambda b: b.y0)
            
            sorted_columns = sorted(columns.items(), key=lambda item: item[0], reverse=True)
            
            blocks = []
            for col_x, col_blocks in sorted_columns:
                blocks.extend(col_blocks)
        else:
            blocks.sort(key=lambda b: (b.page_num, b.y0, b.x0))
        
        return blocks
    
    def _process_text_for_language(self, text: str, language_info: LanguageInfo) -> str:
        """Обрабатывает текст в соответствии с языком документа"""
        if not text:
            return text
            
        # Определяем направление языка
        is_rtl = language_info.direction == 'rtl'
        
        if is_rtl:
            # Для RTL инвертируем порядок букв в каждом слове
            words = text.split(' ')
            processed_words = []
            
            for word in words:
                # Проверяем, содержит ли слово ивритские буквы
                if any(ord(char) >= 1424 and ord(char) <= 1514 for char in word):
                    # Инвертируем порядок букв для RTL
                    processed_word = word[::-1]
                else:
                    processed_word = word
                processed_words.append(processed_word)
            
            # Для RTL НЕ инвертируем порядок слов - они уже в правильном порядке
            return ' '.join(processed_words)
        else:
            # Для LTR оставляем как есть
            return text
    
    def _words_to_lines_enhanced(self, words: List[Dict], language_info: LanguageInfo) -> List[Dict]:
        """Группирует слова в строки с учетом языка"""
        if not words:
            return []
        
        lines = []
        current_line = []
        current_y = None
        line_tolerance = self.config.line_tolerance
        
        for word in words:
            word_y = word['top']
            
            if current_y is None:
                current_y = word_y
                current_line = [word]
            elif abs(word_y - current_y) <= line_tolerance:
                # Слово в той же строке
                current_line.append(word)
            else:
                # Новая строка - обрабатываем предыдущую
                if current_line:
                    # Сортируем слова в строке с учетом направления
                    if language_info.direction == 'rtl':
                        current_line.sort(key=lambda w: -w['x0'])
                    else:
                        current_line.sort(key=lambda w: w['x0'])
                    
                    line_text = ' '.join(w['text'] for w in current_line)
                    
                    # Применяем BIDI обработку если нужно
                    if language_info.bidi and language_info.language in LANGUAGE_CONFIGS:
                        if re.search(LANGUAGE_CONFIGS[language_info.language]['pattern'], line_text):
                            line_text = get_display(line_text)
                    
                    lines.append({
                        'text': line_text,
                        'y': current_y,
                        'words': current_line.copy()
                    })
                
                # Начинаем новую строку
                current_y = word_y
                current_line = [word]
        
        # Обрабатываем последнюю строку
        if current_line:
            if language_info.direction == 'rtl':
                current_line.sort(key=lambda w: -w['x0'])
            else:
                current_line.sort(key=lambda w: w['x0'])
            
            line_text = ' '.join(w['text'] for w in current_line)
            
            if language_info.bidi and language_info.language in LANGUAGE_CONFIGS:
                if re.search(LANGUAGE_CONFIGS[language_info.language]['pattern'], line_text):
                    line_text = get_display(line_text)
            
            lines.append({
                'text': line_text,
                'y': current_y if current_y is not None else 0,
                'words': current_line.copy()
            })
        
        return lines
    
    def _classify_paragraph_block(self, paragraph: List[Dict], language_info: LanguageInfo) -> BlockType:
        """Классифицирует параграф как HEADER или PARAGRAPH"""
        if not paragraph:
            return BlockType.PARAGRAPH
        
        # Анализируем текст параграфа
        text = ' '.join(line.get('text', '') for line in paragraph)
        return self._classify_paragraph_block_by_text(text, language_info)
    
    def _classify_paragraph_block_by_text(self, text: str, language_info: LanguageInfo) -> BlockType:
        """Классифицирует текст как HEADER или PARAGRAPH"""
        if not text or not text.strip():
            return BlockType.PARAGRAPH
        
        text = text.strip()
        
        # Признаки заголовка:
        # 1. Короткий текст (менее 50 символов)
        if len(text) < 50:
            return BlockType.HEADER
        
        # 2. Текст в верхнем регистре
        if text.isupper() and len(text) < 100:
            return BlockType.HEADER
        
        # 3. Заканчивается двоеточием
        if text.endswith(':'):
            return BlockType.HEADER
        
        # 4. Содержит только цифры и символы
        if text.replace(' ', '').replace('-', '').replace('.', '').isdigit():
            return BlockType.HEADER
        
        return BlockType.PARAGRAPH
    
    def _segment_page(self, page, conf: Dict) -> List[PageSegment]:
        """Сегментирует страницу на горизонтальные полосы"""
        words = page.extract_words()
        if not words:
            return []
        
        # Отладочный вывод координат слов (только для первой страницы)
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"\n🔍 DEBUG: Страница {page.page_number + 1} - Координаты слов:")
            print(f"{'Слово':<20} {'X0':<8} {'X1':<8} {'Y':<8} {'Ширина':<8}")
            print("-" * 60)
            for i, word in enumerate(words[:50]):  # Первые 50 слов
                print(f"{word['text'][:18]:<20} {word['x0']:<8.1f} {word['x1']:<8.1f} {word['top']:<8.1f} {word['x1']-word['x0']:<8.1f}")
                if i >= 49:
                    print(f"... и еще {len(words)-50} слов")
                    break
            print()
        
        page_height = page.height
        bands = []
        
        # Создаем горизонтальные полосы
        for y_start in range(0, int(page_height), self.config.band_height):
            y_end = min(y_start + self.config.band_height, page_height)
            band_words = [w for w in words 
                         if w['top'] >= y_start and w['top'] < y_end]
            bands.append({
                'y_start': y_start,
                'y_end': y_end, 
                'words': band_words
            })
        
        # Группируем похожие полосы
        segments = self._group_similar_bands(bands)
        
        return segments
    
    def _group_similar_bands(self, bands: List[Dict]) -> List[PageSegment]:
        """Группирует последовательные полосы с одинаковой структурой"""
        if not bands:
            return []
        
        segments = []
        
        # Анализируем структуру для каждой полосы
        for band in bands:
            band['structure'] = self._analyze_band_structure(band['words'])
        
        # Группируем похожие полосы с отладкой
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"\n🔍 Группировка {len(bands)} полос в сегменты:")
        
        segments = []
        current_segment = None
        
        for i, band in enumerate(bands):
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"  Полоса {i+1}: {band['structure']} (Y:{band['y_start']}-{band['y_end']}, {len(band['words'])} слов)")
            
            if current_segment is None:
                # Первая полоса - начинаем новый сегмент
                current_segment = PageSegment(
                    structure=band['structure'],
                    y_start=band['y_start'],
                    y_end=band['y_end'],
                    words=band['words'],
                    blocks=[]
                )
                if hasattr(self, '_debug_mode') and self._debug_mode:
                    print(f"    → Начинаем новый сегмент: {band['structure']}")
            elif band['structure'] == current_segment.structure:
                # Та же структура - расширяем текущий сегмент
                current_segment.y_end = band['y_end']
                current_segment.words.extend(band['words'])
                if hasattr(self, '_debug_mode') and self._debug_mode:
                    print(f"    → Расширяем текущий сегмент")
            else:
                # Другая структура - завершаем текущий и начинаем новый
                if current_segment.words:  # Добавляем только непустые сегменты
                    segments.append(current_segment)
                    if hasattr(self, '_debug_mode') and self._debug_mode:
                        print(f"    → Сохраняем сегмент: {current_segment.structure} (Y:{current_segment.y_start}-{current_segment.y_end})")
                
                current_segment = PageSegment(
                    structure=band['structure'],
                    y_start=band['y_start'],
                    y_end=band['y_end'],
                    words=band['words'],
                    blocks=[]
                )
                if hasattr(self, '_debug_mode') and self._debug_mode:
                    print(f"    → Начинаем новый сегмент: {band['structure']}")
        
        # Добавляем финальный сегмент
        if current_segment and current_segment.words:
            segments.append(current_segment)
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"    → Сохраняем финальный сегмент: {current_segment.structure} (Y:{current_segment.y_start}-{current_segment.y_end})")
        
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"\n🔍 Итого {len(segments)} сегментов:")
            for i, seg in enumerate(segments):
                print(f"  Сегмент {i+1}: {seg.structure} (Y:{seg.y_start}-{seg.y_end}, {len(seg.words)} слов)")
        
        return segments
    
    def _analyze_band_structure(self, words: List[Dict]) -> str:
        """Анализирует структуру полосы (single/double column)"""
        if not words:
            return 'single_column'
        
        # Находим границы текста
        x_positions = [w['x0'] for w in words]
        min_x = min(x_positions)
        max_x = max(x_positions)
        width = max_x - min_x
        
        # Отладочный вывод для анализа структуры
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"\n🔍 Анализ структуры полосы:")
            print(f"  Слов: {len(words)}")
            print(f"  X диапазон: {min_x:.1f} - {max_x:.1f} (ширина: {width:.1f})")
            print(f"  Y диапазон: {min(w['top'] for w in words):.1f} - {max(w['top'] for w in words):.1f}")
            print(f"  Слова: {[w['text'] for w in words[:5]]}")
        
        # Проверяем наличие пустого пространства в центре
        center = width / 2
        center_tolerance = width * 0.1
        
        words_left = [w for w in words if w['x0'] < center - center_tolerance]
        words_right = [w for w in words if w['x0'] > center + center_tolerance]
        
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"  Центр: {center:.1f} ±{center_tolerance:.1f}")
            print(f"  Слова слева: {len(words_left)}, справа: {len(words_right)}")
        
        # Если есть слова в обеих колонках - двухколоночный
        if words_left and words_right:
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"  → Результат: double_column")
            return 'double_column'
        
        # Проверяем центрирование
        if len(words) == 1:
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"  → Результат: single_centered (одно слово)")
            return 'single_centered'
        
        # Анализируем распределение по X
        x_spread = max(x_positions) - min(x_positions)
        if x_spread < self.config.center_threshold * width:
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"  → Результат: single_centered (x_spread: {x_spread:.1f} < {self.config.center_threshold * width:.1f})")
            return 'single_centered'
        
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"  → Результат: single_column")
        return 'single_column'
    
    def _segment_to_blocks(self, segment: PageSegment, language_info: LanguageInfo, page_num: int, conf: Dict) -> List[TextBlock]:
        """Преобразует сегмент в текстовые блоки"""
        if segment.structure == 'empty' or not segment.words:
            return []
        
        if conf:
            utils.tbox_log(f"Сегмент: {segment.structure} ({len(segment.words)} слов, Y:{segment.y_start}-{segment.y_end})", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "INFO", conf)
        
        if segment.structure in ['single_column', 'single_centered']:
            return self._extract_single_column_blocks(segment.words, language_info, page_num)
        elif segment.structure == 'double_column':
            return self._extract_double_column_blocks(segment.words, language_info, page_num)
        
        return []
    
    def _extract_single_column_blocks(self, words: List[Dict], language_info: LanguageInfo, page_num: int) -> List[TextBlock]:
        """Извлекает блоки из одноколоночного текста"""
        if not words:
            return []
        
        # Сортируем слова по координатам с учетом RTL
        if language_info.direction == 'rtl':
            # Для RTL текста: слова сортируются справа налево (убывание X)
            words_sorted = sorted(words, key=lambda w: (w['top'], -w['x0']))
        else:
            # Для LTR текста: стандартная сортировка
            words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        # Собираем строки
        lines = []
        current_line = []
        current_y = None
        
        for word in words_sorted:
            if current_y is None or abs(word['top'] - current_y) > self.config.line_tolerance:
                if current_line:
                    line_text = ' '.join(current_line)
                    # Применяем bidi обработку на уровне строки
                    if language_info.bidi and language_info.language in LANGUAGE_CONFIGS:
                        if re.search(LANGUAGE_CONFIGS[language_info.language]['pattern'], line_text):
                            line_text = get_display(line_text)
                    if line_text.strip():
                        lines.append({
                            'text': line_text,
                            'y': current_y,
                            'words': current_line.copy()
                        })
                    current_line = []
                    current_y = word['top']
                
                current_line.append(word['text'])
            else:
                current_line.append(word['text'])
        
        if current_line:
            line_text = ' '.join(current_line)
            # Применяем bidi обработку на уровне строки
            if language_info.bidi and language_info.language in LANGUAGE_CONFIGS:
                if re.search(LANGUAGE_CONFIGS[language_info.language]['pattern'], line_text):
                    line_text = get_display(line_text)
            if line_text.strip():
                lines.append({
                    'text': line_text,
                    'y': current_y if current_y is not None else 0,
                    'words': current_line.copy()
                })
        
        # Группируем строки в блоки (параграфы)
        blocks = []
        current_paragraph = []
        
        for line in lines:
            # Определяем тип блока по характеристикам
            block_type = self._classify_line_block(line['text'])
            
            if block_type == BlockType.HEADER:
                # Заголовок - отдельный блок
                if current_paragraph:
                    blocks.append(self._create_paragraph_block(current_paragraph, page_num))
                    current_paragraph = []
                blocks.append(self._create_header_block(line, page_num))
            else:
                # Параграф
                current_paragraph.append(line)
        
        # Добавляем финальный параграф
        if current_paragraph:
            blocks.append(self._create_paragraph_block(current_paragraph, page_num))
        
        return blocks
    
    def _extract_double_column_blocks(self, words: List[Dict], language_info: LanguageInfo, page_num: int) -> List[TextBlock]:
        """Извлекает блоки из двухколоночного текста"""
        if not words:
            return []
        
        # Находим границу колонок
        x_coords = [w['x0'] for w in words]
        min_x, max_x = min(x_coords), max(x_coords)
        mid_x = min_x + (max_x - min_x) / 2
        
        # Разделяем на колонки
        left_column = [w for w in words if w['x0'] < mid_x]
        right_column = [w for w in words if w['x0'] >= mid_x]
        
        # Извлекаем блоки из каждой колонки
        left_blocks = self._extract_single_column_blocks(left_column, language_info, page_num)
        right_blocks = self._extract_single_column_blocks(right_column, language_info, page_num)
        
        # Помечаем типы колонок
        for block in left_blocks:
            block.block_type = BlockType.COLUMN_LEFT
        for block in right_blocks:
            block.block_type = BlockType.COLUMN_RIGHT
        
        # Объединяем в правильном порядке чтения
        if language_info.direction == 'rtl':
            # RTL: правая колонка первой
            return right_blocks + left_blocks
        else:
            # LTR: левая колонка первой
            return left_blocks + right_blocks
    
    def _classify_line_block(self, text: str) -> BlockType:
        """Классифицирует строку по типу блока"""
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        
        if not text:
            return BlockType.PARAGRAPH
        
        # Заголовки: короткие, могут быть написаны заглавными буквами
        if len(text) < 100 and (text.isupper() or text.endswith(':') or re.match(r'^\d+\.', text)):
            return BlockType.HEADER
        
        # Колонтитулы: обычно содержат номера страниц
        if re.search(r'\d+$', text) and len(text) < 50:
            return BlockType.FOOTER
        
        # По умолчанию - параграф
        return BlockType.PARAGRAPH
    
    def _create_header_block(self, line: Dict, page_num: int) -> TextBlock:
        """Создает блок заголовка"""
        # В текущей реализации words - это список строк, не словарей с координатами
        # Используем упрощенную версию без координат
        return TextBlock(
            text=line['text'],
            block_type=BlockType.HEADER,
            x0=0, y0=line.get('y', 0), x1=0, y1=line.get('y', 0) + 10,
            page_num=page_num,
            confidence=0.9
        )
    
    def _create_paragraph_block(self, lines: List[Dict], page_num: int) -> TextBlock:
        """Создает блок параграфа"""
        if not lines:
            return TextBlock("", BlockType.PARAGRAPH, 0, 0, 0, 0, page_num, 0.0)
        
        text = '\n'.join(line['text'] for line in lines)
        # Упрощенная версия без координат, так как words - это строки
        y0 = min(line['y'] for line in lines) if lines else 0
        
        return TextBlock(
            text=text,
            block_type=BlockType.PARAGRAPH,
            x0=0, y0=y0, x1=0, y1=y0 + 10,
            page_num=page_num,
            confidence=0.8
        )
    
    def _blocks_to_text(self, blocks: List[TextBlock], conf: Dict) -> str:
        """Преобразует блоки в текст с правильным порядком чтения"""
        if not blocks:
            return ""
        
        # Определяем язык документа
        word_texts = [w['text'] for block in blocks for line in getattr(block, 'source_lines', []) for w in line]
        language_info = self._detect_language(word_texts)
        
        # Сортируем блоки в правильном порядке
        if language_info.direction == 'rtl':
            # Для RTL: сначала правая колонка, потом левая
            # Сортируем по X убыванию, затем по Y возрастанию
            sorted_blocks = sorted(blocks, key=lambda b: (-b.x0, b.y0))
        else:
            # Для LTR: сначала левая колонка, потом правая
            # Сортируем по X возрастанию, затем по Y возрастанию
            sorted_blocks = sorted(blocks, key=lambda b: (b.x0, b.y0))
        
        # Сортируем параграфы внутри блоков
        sorted_blocks = self._sort_paragraphs_in_blocks(sorted_blocks, language_info)
        
        # Обрабатываем текст в каждом блоке с учетом языка
        text_parts = []
        for block in sorted_blocks:
            processed_text = self._process_text_for_language(block.text, language_info)
            if processed_text.strip():
                text_parts.append(processed_text.strip())
        
        return '\n\n'.join(text_parts)
    
    def _sort_paragraphs_in_blocks(self, blocks: List[TextBlock], language_info: LanguageInfo) -> List[TextBlock]:
        """Сортирует параграфы внутри блоков"""
        for block in blocks:
            if language_info.direction == 'rtl':
                # Для RTL: параграфы сортируются по Y убыванию (сверху вниз)
                # Но текст внутри параграфа уже обработан
                pass  # Параграфы уже в правильном порядке
            else:
                # Для LTR: параграфы сортируются по Y возрастанию (сверху вниз)
                pass  # Параграфы уже в правильном порядке
        
        return blocks
    
    def _save_words_debug_info(self, words_debug_path: str):
        """Сохраняет все слова с координатами"""
        try:
            with pdfplumber.open(self._current_pdf_path) as pdf:
                if not pdf.pages:
                    return
                
                page = pdf.pages[0]
                words = page.extract_words()
                
                with open(words_debug_path, 'w', encoding='utf-8') as f:
                    f.write("ВСЕ СЛОВА НА ПЕРВОЙ СТРАНИЦЕ\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"{'№':>4} | {'X':>8} | {'Y':>8} | {'Ширина':>8} | {'Высота':>8} | Слово\n")
                    f.write("-" * 70 + "\n")
                    
                    for i, word in enumerate(words):
                        x0 = word['x0']
                        y0 = word['top']
                        width = word['x1'] - word['x0']
                        height = word['bottom'] - word['top']
                        text = word['text']
                        
                        f.write(f"{i+1:>4} | {x0:>8.1f} | {y0:>8.1f} | {width:>8.1f} | {height:>8.1f} | {text}\n")
                    
                    f.write("-" * 70 + "\n")
                    f.write(f"Всего слов: {len(words)}\n")
                
            print(f"Информация о словах сохранена: {words_debug_path}")
            
        except Exception as e:
            print(f"Ошибка сохранения слов: {e}")
    
    def _save_sentences_debug_info(self, blocks: List[TextBlock], sentences_path: str, output_path: str = None, before_splitting: bool = True):
        """Сохраняет предложения до или после разделения"""
        try:
            with open(sentences_path, 'w', encoding='utf-8') as f:
                if before_splitting:
                    f.write("ПРЕДЛОЖЕНИЯ ДО РАЗДЕЛЕНИЯ НА БЛОКИ\n")
                else:
                    f.write("ПРЕДЛОЖЕНИЯ ПОСЛЕ РАЗДЕЛЕНИЯ НА БЛОКИ\n")
                f.write("=" * 50 + "\n\n")
                
                sentence_num = 1
                for block in blocks:
                    if hasattr(block, 'text') and block.text and block.text.strip():
                        # Разделяем текст на предложения
                        sentences = [s.strip() for s in block.text.split('.') if s.strip()]
                        
                        for sentence in sentences:
                            if sentence:
                                f.write(f"{sentence_num}. {sentence}\n")
                                sentence_num += 1
                
                f.write(f"\nВсего предложений: {sentence_num - 1}\n")
                
            print(f"Информация о предложениях сохранена: {sentences_path}")
            
        except Exception as e:
            print(f"Ошибка сохранения предложений: {e}")
    
    def _fallback_extraction(self, page, page_num: int, conf: Dict) -> List[TextBlock]:
        """Запасной метод извлечения текста"""
        try:
            text = page.extract_text() or ""
            if text.strip():
                return [TextBlock(
                    text=text,
                    block_type=BlockType.PARAGRAPH,
                    x0=0, y0=0, x1=0, y1=0,
                    page_num=page_num,
                    confidence=0.3
                )]
        except Exception as e:
            utils.tbox_log(f"Ошибка fallback извлечения: {e}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", conf)
        
        return []
    
    def _save_text(self, full_text: List[str], output_path: str, pdf_path: str, conf: Dict):
        """Сохраняет извлеченный текст в файл и открывает его"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        clean_base_name = os.path.basename(pdf_path).replace('.pdf', '').replace('.PDF', '')
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {clean_base_name}\n")
            f.write(f"SOURCE: PDF_BLOCK_EXTRACTOR\n")
            f.write(f"VERSION: {VERSION}\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write("\n\n".join(full_text))
        
        utils.tbox_log(f"Текст извлечен: {output_path}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "DONE", conf)
        
        # Автоматически открываем файл
        import subprocess
        import platform
        system = platform.system()
        try:
            if system == 'Darwin':  # macOS
                subprocess.run(['open', output_path])
            elif system == 'Windows':
                subprocess.run(['start', output_path], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', output_path])
        except Exception as e:
            utils.tbox_log(f"Не удалось открыть файл автоматически: {e}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "WARNING", conf)
    
    def _detect_language(self, words: List[str]) -> LanguageInfo:
        """Автоопределение основного языка документа"""
        if not words:
            return LanguageInfo('unknown', 'ltr', False, 0.0)
        
        # Анализируем первые 100 слов для определения языка
        sample_words = words[:100]
        total_chars = 0
        language_scores = {}
        
        for lang_name, config in LANGUAGE_CONFIGS.items():
            lang_chars = 0
            for word in sample_words:
                matches = len(re.findall(config['pattern'], word))
                lang_chars += matches
                total_chars += len(word)
            
            if total_chars > 0:
                score = lang_chars / total_chars
                language_scores[lang_name] = score
        
        # Находим язык с максимальным счетом
        if not language_scores:
            return LanguageInfo('unknown', 'ltr', False, 0.0)
        
        best_language = max(language_scores.items(), key=lambda x: x[1])
        lang_name, confidence = best_language
        
        if self._debug_mode:
            print(f"\n🔍 [LANG] Определение языка:")
            print(f"  Анализируем {len(sample_words)} слов")
            print(f"  Счета языков: {language_scores}")
            print(f"  Лучший язык: {lang_name} (confidence: {confidence:.2f})")
        
        # Проверяем порог для доминирующего языка
        if confidence < self.config.language_threshold:
            if self._debug_mode:
                print(f"  Результат: mixed (confidence {confidence:.2f} < threshold {self.config.language_threshold})")
            return LanguageInfo('mixed', 'ltr', False, confidence)
        
        lang_config = LANGUAGE_CONFIGS[lang_name]
        result = LanguageInfo(
            language=lang_name,
            direction=lang_config['direction'],
            bidi=lang_config['bidi'],
            confidence=confidence
        )
        
        if self._debug_mode:
            print(f"  Результат: {lang_name} (direction: {lang_config['direction']}, bidi: {lang_config['bidi']})")
        
        return result
    
    def _detect_columns(self, words: List[Dict], language_info: LanguageInfo = None) -> List[List[Dict]]:
        """Определяет колонки с помощью кластеризации X координат"""
        if not words:
            return [[]]
        
        if self._debug_mode:
            print(f"\n🔍 [COL] Определение колонок:")
            print(f"  Всего блоков: {len(blocks)}")
        
        return column_blocks
    
    def _debug_blocks_info(self, blocks: List[TextBlock], column_blocks: Dict[str, List[Dict]]):
        """Выводит детальную отладочную информацию по блокам"""
        print(f"\n🔍 [BLOCKS] Детальная информация по блокам:")
        for i, block in enumerate(blocks):
            preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
            print(f"\n  === БЛОК #{i} ===")
            print(f"  Координаты блока: X={block.x0:.1f}-{block.x1:.1f}, Y={block.y0:.1f}-{block.y1:.1f}")
            print(f"  Тип: {block.block_type}")
            print(f"  Полный текст: \"{block.text}\"")
            print(f"  Предложений: {len(block.text.split('.'))}")
            print(f"  Слов: {len(block.text.split())}")
            print(f"\n  Исходные строки, входящие в блок:")
            
            # Показываем исходные строки из блока
            if hasattr(block, 'source_lines') and block.source_lines:
                for j, line in enumerate(block.source_lines):
                    # Сортируем слова в строке по X
                    sorted_words = sorted(line, key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in sorted_words)
                    line_y = line[0]['top']
                    line_x0 = sorted_words[0]['x0']
                    line_x1 = sorted_words[-1]['x1']
                    print(f"      {j+1}. Y={line_y:.1f}, X={line_x0:.1f}-{line_x1:.1f}")
                    print(f"         Текст: \"{line_text}\"")
            else:
                print(f"    Нет исходных строк для этого блока")
            
            print()
        print(f"  Итого блоков: {len(blocks)}")
    
    def _save_debug_info(self, blocks: List[TextBlock], debug_file_path: str):
        """Сохраняет отладочную информацию по блокам в отдельный файл"""
        try:
            with open(debug_file_path, 'w', encoding='utf-8') as f:
                f.write("ОТЛАДОЧНАЯ ИНФОРМАЦИЯ ПО БЛОКАМ\n")
                f.write("=" * 50 + "\n\n")
                
                for i, block in enumerate(blocks):
                    f.write(f"=== БЛОК #{i} ===\n")
                    f.write(f"Координаты блока: X={block.x0:.1f}-{block.x1:.1f}, Y={block.y0:.1f}-{block.y1:.1f}\n")
                    f.write(f"Тип: {block.block_type}\n")
                    f.write(f"Предложений: {len(block.text.split('.'))}\n")
                    f.write(f"Слов: {len(block.text.split())}\n")
                    f.write(f"\nИсходные строки, входящие в блок:\n")
                    
                    # Показываем исходные строки из блока
                    if hasattr(block, 'source_lines') and block.source_lines:
                        for j, line in enumerate(block.source_lines):
                            # Сортируем слова в строке по X
                            sorted_words = sorted(line, key=lambda w: w['x0'])
                            line_text = ' '.join(w['text'] for w in sorted_words)
                            line_y = line[0]['top']
                            line_x0 = sorted_words[0]['x0']
                            line_x1 = sorted_words[-1]['x1']
                            f.write(f"  {j+1}. Y={line_y:.1f}, X={line_x0:.1f}-{line_x1:.1f}\n")
                            f.write(f"     Текст: \"{line_text}\"\n")
                    else:
                        f.write(f"  Нет исходных строк для этого блока\n")
                    
                    f.write("\n" + "-" * 40 + "\n\n")
                
                f.write(f"Итого блоков: {len(blocks)}\n")
                
            print(f"Отладочная информация сохранена: {debug_file_path}")
            
        except Exception as e:
            print(f"Ошибка сохранения отладочной информации: {e}")
    
    def _save_line_debug_info(self, lines: List[List[Dict]], debug_file_path: str):
        """Сохраняет таблицу всех строк с координатами после разбиения на подстроки"""
        try:
            with open(debug_file_path, 'w', encoding='utf-8') as f:
                f.write("ТАБЛИЦА СТРОК ПОСЛЕ РАЗБИЕНИЯ НА ПОДСТРОКИ\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"{'№':>3} | {'Y':>8} | {'X0':>8} | {'X1':>8} | {'Ширина':>8} | {'Слов':>5} | Текст\n")
                f.write("-" * 90 + "\n")
                
                for i, line in enumerate(lines):
                    # Сортируем слова в строке по X
                    sorted_words = sorted(line, key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in sorted_words)
                    line_y = line[0]['top']
                    line_x0 = sorted_words[0]['x0']
                    line_x1 = sorted_words[-1]['x1']
                    line_width = line_x1 - line_x0
                    word_count = len(sorted_words)
                    
                    # Обрезаем длинный текст для таблицы
                    display_text = line_text[:60] + "..." if len(line_text) > 60 else line_text
                    
                    f.write(f"{i+1:>3} | {line_y:>8.1f} | {line_x0:>8.1f} | {line_x1:>8.1f} | {line_width:>8.1f} | {word_count:>5} | {display_text}\n")
                
                f.write("-" * 90 + "\n")
                f.write(f"Всего строк: {len(lines)}\n")
                
            print(f"Таблица строк сохранена: {debug_file_path}")
            
        except Exception as e:
            print(f"Ошибка сохранения таблицы строк: {e}")
    
    def _create_lines_debug_file(self, words: List[Dict], debug_file_path: str):
        """Создает таблицу строк прямо из слов"""
        try:
            # Группируем слова в строки по Y координате
            lines = []
            if words:
                # Сортируем слова по Y
                sorted_words = sorted(words, key=lambda w: w['top'])
                
                # Группируем в строки
                current_line = []
                current_y = sorted_words[0]['top']
                
                for word in sorted_words:
                    if abs(word['top'] - current_y) < 2:  # Тот же Y
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = [word]
                        current_y = word['top']
                
                if current_line:
                    lines.append(current_line)
            
            # Сохраняем таблицу
            with open(debug_file_path, 'w', encoding='utf-8') as f:
                f.write("ТАБЛИЦА СТРОК ПОСЛЕ РАЗБИЕНИЯ НА ПОДСТРОКИ\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"{'№':>3} | {'Y':>8} | {'X0':>8} | {'X1':>8} | {'Ширина':>8} | {'Слов':>5} | Текст\n")
                f.write("-" * 90 + "\n")
                
                for i, line in enumerate(lines):
                    # Сортируем слова в строке по X
                    sorted_words = sorted(line, key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in sorted_words)
                    line_y = line[0]['top']
                    line_x0 = sorted_words[0]['x0']
                    line_x1 = sorted_words[-1]['x1']
                    line_width = line_x1 - line_x0
                    word_count = len(sorted_words)
                    
                    # Обрабатываем текст строки с учетом языка
                    # Для таблицы строк НЕ инвертируем слова - они уже в правильном порядке
                    # Только инвертируем буквы в словах для RTL
                    if self._language_info.direction == 'rtl':
                        words = line_text.split(' ')
                        processed_words = []
                        for word in words:
                            if any(ord(char) >= 1424 and ord(char) <= 1514 for char in word):
                                processed_words.append(word[::-1])
                            else:
                                processed_words.append(word)
                        processed_line_text = ' '.join(processed_words)
                    else:
                        processed_line_text = line_text
                    
                    # Обрезаем длинный текст для таблицы
                    display_text = processed_line_text[:60] + "..." if len(processed_line_text) > 60 else processed_line_text
                    
                    f.write(f"{i+1:>3} | {line_y:>8.1f} | {line_x0:>8.1f} | {line_x1:>8.1f} | {line_width:>8.1f} | {word_count:>5} | {display_text}\n")
                
                f.write("-" * 90 + "\n")
                f.write(f"Всего строк: {len(lines)}\n")
                
            print(f"Таблица строк создана: {debug_file_path}")
            
        except Exception as e:
            print(f"Ошибка создания таблицы строк: {e}")
        
        for n_clusters in range(1, 5):
            try:
                # Простая кластеризация по равным интервалам
                min_x = min(coord[0] for coord in x_coords)
                max_x = max(coord[0] for coord in x_coords)
                
                if n_clusters == 1:
                    clusters = [0] * len(words)
                else:
                    # Разделяем на n_clusters равных интервалов
                    interval_width = (max_x - min_x) / n_clusters
                    clusters = []
                    
                    for coord in x_coords:
                        cluster_id = min(int((coord[0] - min_x) / interval_width), n_clusters - 1)
                        clusters.append(cluster_id)
                
                # Проверяем качество кластеризации
                cluster_quality = self._evaluate_clustering(words, clusters, n_clusters)
                
                if self._debug_mode:
                    print(f"  Кластеров {n_clusters}: качество = {cluster_quality:.2f}")
                
                if cluster_quality > self._evaluate_clustering(words, best_clusters, best_n_clusters):
                    best_n_clusters = n_clusters
                    best_clusters = clusters
                    
            except Exception:
                continue
        
        # Группируем слова по кластерам
        if best_n_clusters == 1:
            if self._debug_mode:
                print(f"  Результат: 1 колонка (все слова вместе)")
            return [words]
        
        columns = [[] for _ in range(best_n_clusters)]
        for word, cluster_id in zip(words, best_clusters):
            columns[cluster_id].append(word)
        
        # Сортируем колонки по X координате с учетом направления текста
        # Для RTL: правая колонка (больший X) первой
        # Для LTR: левая колонка (меньший X) первой
        if language_info and language_info.direction == 'rtl':
            columns.sort(key=lambda col: min(w['x0'] for w in col), reverse=True)
        else:
            columns.sort(key=lambda col: min(w['x0'] for w in col))
        
        if self._debug_mode:
            print(f"  Результат: {best_n_clusters} колонки")
            direction = language_info.direction if language_info else 'ltr'
            print(f"  Сортировка колонок: {direction} ({'справа налево' if direction == 'rtl' else 'слева направо'})")
            for i, col in enumerate(columns):
                x_range = (min(w['x0'] for w in col), max(w['x1'] for w in col))
                print(f"    Колонка #{i}: {len(col)} слов, X диапазон: {x_range[0]:.1f}-{x_range[1]:.1f}")
        
        return columns
    
    def _evaluate_clustering(self, words: List[Dict], clusters: List[int], n_clusters: int) -> float:
        """Оценивает качество кластеризации"""
        if not clusters or n_clusters <= 1:
            return 0.0
        
        # Вычисляем среднее внутрикластерное расстояние
        total_intra_distance = 0
        cluster_count = 0
        
        for cluster_id in range(n_clusters):
            cluster_words = [words[i] for i, c in enumerate(clusters) if c == cluster_id]
            if len(cluster_words) < 2:
                continue
            
            # Среднее расстояние между словами в кластере
            distances = []
            for i in range(len(cluster_words)):
                for j in range(i + 1, len(cluster_words)):
                    dist = abs(cluster_words[i]['x0'] - cluster_words[j]['x0'])
                    distances.append(dist)
            
            if distances:
                total_intra_distance += sum(distances) / len(distances)
                cluster_count += 1
        
        if cluster_count == 0:
            return 0.0
        
        # Чем меньше внутрикластерное расстояние, тем лучше
        avg_intra_distance = total_intra_distance / cluster_count
        
        # Вычисляем межкластерное расстояние
        cluster_centers = []
        for cluster_id in range(n_clusters):
            cluster_words = [words[i] for i, c in enumerate(clusters) if c == cluster_id]
            if cluster_words:
                center = sum(w['x0'] for w in cluster_words) / len(cluster_words)
                cluster_centers.append(center)
        
        if len(cluster_centers) < 2:
            return 0.0
        
        inter_distances = []
        for i in range(len(cluster_centers)):
            for j in range(i + 1, len(cluster_centers)):
                inter_distances.append(abs(cluster_centers[i] - cluster_centers[j]))
        
        avg_inter_distance = sum(inter_distances) / len(inter_distances)
        
        # Качество = межкластерное / внутрикластерное
        return avg_inter_distance / (avg_intra_distance + 1)
    
    def _group_lines_to_paragraphs(self, lines: List[List[Dict]], language_info: LanguageInfo) -> List[List[List[Dict]]]:
        """Группирует строки (списки слов) в параграфы по вертикальным промежуткам"""
        if not lines:
            return []
        
        if self._debug_mode:
            print(f"\n🔍 [PARA] Группировка строк в параграфы:")
            print(f"  Всего строк: {len(lines)}")
        
        paragraphs = []
        current_paragraph = []
        
        # Вычисляем среднюю высоту строки
        line_heights = []
        for line in lines:
            if line:
                # Оцениваем высоту строки по координатам слов
                word_heights = []
                for word in line:
                    if 'bottom' in word and 'top' in word:
                        word_heights.append(word['bottom'] - word['top'])
                if word_heights:
                    line_heights.append(sum(word_heights) / len(word_heights))
        
        avg_line_height = sum(line_heights) / len(line_heights) if line_heights else 12
        large_gap_threshold = avg_line_height * self.config.paragraph_large_gap
        medium_gap_threshold = avg_line_height * self.config.paragraph_medium_gap
        
        if self._debug_mode:
            print(f"  Средняя высота строки: {avg_line_height:.1f}")
            print(f"  Пороги: large_gap={large_gap_threshold:.1f}, medium_gap={medium_gap_threshold:.1f}")
        
        for i, line in enumerate(lines):
            if not line:
                continue
            
            if not current_paragraph:
                current_paragraph.append(line)
                if self._debug_mode:
                    print(f"  Строка #{i}: начало параграфа (Y={line[0]['top']:.1f})")
                continue
            
            # Анализ промежутка до предыдущей строки
            prev_line = current_paragraph[-1]
            vertical_gap = line[0]['top'] - prev_line[0]['top']
            
            # Определяем тип разрыва параграфа
            if vertical_gap > large_gap_threshold:
                # Большой промежуток - новый параграф
                if self._debug_mode:
                    print(f"  Строка #{i}: gap={vertical_gap:.1f} > {large_gap_threshold:.1f} -> НОВЫЙ ПАРАГРАФ")
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                current_paragraph = [line]
            elif vertical_gap > medium_gap_threshold:
                # Средний промежуток - проверяем дополнительные признаки
                is_break = self._is_likely_paragraph_break_new(line, prev_line, language_info)
                if self._debug_mode:
                    print(f"  Строка #{i}: gap={vertical_gap:.1f} > {medium_gap_threshold:.1f}, break={is_break}")
                if is_break:
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                    current_paragraph = [line]
                else:
                    current_paragraph.append(line)
            else:
                # Маленький промежуток - продолжение параграфа
                if self._debug_mode and i % 5 == 0:
                    print(f"  Строка #{i}: gap={vertical_gap:.1f} -> продолжение параграфа")
                current_paragraph.append(line)
        
        # Добавляем финальный параграф
        if current_paragraph:
            paragraphs.append(current_paragraph)
            if self._debug_mode:
                print(f"  Итого: {len(paragraphs)} параграфов")
        
        return paragraphs
    
    def _is_likely_paragraph_break_new(self, current_line: List[Dict], prev_line: List[Dict], language_info: LanguageInfo) -> bool:
        """Определяет, является ли разрыв параграфным (для нового формата строк)"""
        # Собираем текст из строк
        current_text = ' '.join(w['text'] for w in current_line)
        prev_text = ' '.join(w['text'] for w in prev_line)
        
        # Признаки разрыва параграфа:
        
        # 1. Предыдущая строка заканчивается на знак препинания (., !, ?)
        if prev_text and len(prev_text) > 0 and prev_text[-1] in '.!?':
            return True
        
        # 2. Текущая строка начинается с заглавной буквы (для латиницы)
        if current_text and current_text[0].isupper() and current_text[0].isalpha():
            return True
        
        # 3. Предыдущая строка короткая (возможно, заголовок)
        if len(prev_text) < 30:
            return True
        
        # 4. Текущая строка начинается с цифры (нумерованный список)
        if current_text and current_text[0].isdigit():
            return True
        
        return False
    
    def _is_likely_paragraph_break(self, current_line: Dict, prev_line: Dict, language_info: LanguageInfo) -> bool:
        """Определяет, является ли разрыв параграфным"""
        current_text = current_line.get('text', '')
        prev_text = prev_line.get('text', '')
        
        # Признаки разрыва параграфа:
        
        # 1. Точка в конце предыдущей строки
        if prev_text.strip().endswith(('.', '!', '?', ':')):
            return True
        
        # 2. Заглавная буква в начале текущей строки (для LTR языков)
        if language_info.direction == 'ltr' and current_text and current_text[0].isupper():
            return True
        
        # 3. Короткая предыдущая строка (возможно заголовок)
        if len(prev_text.strip()) < 20 and len(current_text.strip()) > 30:
            return True
        
        # 4. Отступ первой строки (проверяем по X координате)
        if 'words' in current_line and 'words' in prev_line:
            current_x = min(w.get('x0', 0) for w in current_line['words'] if isinstance(w, dict))
            prev_x = min(w.get('x0', 0) for w in prev_line['words'] if isinstance(w, dict))
            
            # Для LTR: отступ вправо, для RTL: отступ влево
            if language_info.direction == 'ltr' and current_x > prev_x + 20:
                return True
            elif language_info.direction == 'rtl' and current_x < prev_x - 20:
                return True
        
        return False
    
    # ==================== НОВЫЙ АЛГОРИТМ ОБРАБОТКИ ====================
    
    def _words_to_lines_with_x_split(self, words: List[Dict], language_info: LanguageInfo) -> List[List[Dict]]:
        """Группирует слова в строки по Y и разбивает строки по большим зазорам X"""
        if not words:
            return []
        
        # Сортируем слова по Y (сверху вниз)
        sorted_words = sorted(words, key=lambda w: w['top'])
        
        lines = []
        current_line = []
        current_y = None
        y_tolerance = 5  # пикселей допуска по Y
        
        for word in sorted_words:
            word_y = word['top']
            
            if current_y is None or abs(word_y - current_y) <= y_tolerance:
                # Слово в той же строке
                current_line.append(word)
                current_y = word_y
            else:
                # Новая строка - разбиваем текущую по X и добавляем
                if current_line:
                    split_lines = self._split_line_by_gaps(current_line, language_info)
                    lines.extend(split_lines)
                current_line = [word]
                current_y = word_y
        
        # Добавляем последнюю строку
        if current_line:
            split_lines = self._split_line_by_gaps(current_line, language_info)
            lines.extend(split_lines)
        
        # Сортируем все строки по Y координате для правильного порядка
        lines.sort(key=lambda line: line[0]['top'] if line else float('inf'))
        
        if self._debug_mode:
            print(f"\n🔍 [LINES] Группировка слов в строки с разбиением по X:")
            print(f"  Всего слов: {len(words)}")
            print(f"  Получено строк: {len(lines)}")
            for i, line in enumerate(lines):
                # Сортируем слова в строке по X для вывода
                line_sorted = sorted(line, key=lambda w: w['x0'])
                line_text = ' '.join(w['text'] for w in line_sorted)
                print(f"    Строка #{i}: Y={line[0]['top']:.1f}, {len(line)} слов: \"{line_text}\"")
        
        return lines
    
    def _group_lines_by_columns(self, lines: List[List[Dict]], language_info: LanguageInfo, structure: str = None) -> Dict[str, List[List[Dict]]]:
        """Группирует строки по колонкам с учетом X и Y координат"""
        if not lines:
            return {}
        
        # Если структура предопределена, используем её
        if structure == 'single_column' or structure == 'single_centered':
            # Одна колонка - создаем блок колонки
            all_x = [w['x0'] for line in lines for w in line]
            all_y = [w['top'] for line in lines for w in line]
            
            column_block = {
                'x0': min(all_x),
                'x1': max(all_x),
                'y0': min(all_y),
                'y1': max(all_y),
                'lines': lines
            }
            
            if self._debug_mode:
                print(f"\n🔍 [COLS] Структура: {structure} - одна колонка")
                print(f"  Блок: X={column_block['x0']:.1f}-{column_block['x1']:.1f}, Y={column_block['y0']:.1f}-{column_block['y1']:.1f}")
                print(f"  Строк: {len(lines)}")
            
            return {'single': [column_block]}
        
        elif structure == 'double_column':
            # Две колонки - определяем блоки по X и Y
            return self._create_double_column_blocks(lines, language_info)
        
        else:
            # Структура не предопределена - используем статистический анализ
            return self._create_column_blocks_statistical(lines, language_info)
    
    def _create_double_column_blocks(self, lines: List[List[Dict]], language_info: LanguageInfo) -> Dict[str, List[List[Dict]]]:
        """Создает блоки для двухколоночной структуры с учетом X и Y"""
        if not lines:
            return {}
        
        # Собираем все X и Y координаты
        all_x = [line[0]['x0'] for line in lines]
        all_y = [line[0]['top'] for line in lines]
        
        # Находим медиану X для разделения колонок
        import statistics
        try:
            median_x = statistics.median(all_x)
        except:
            median_x = sum(all_x) / len(all_x)
        
        # Разделяем строки на левую и правую колонки
        left_lines = []
        right_lines = []
        
        for line in lines:
            x0 = line[0]['x0']
            if x0 < median_x:
                left_lines.append(line)
            else:
                right_lines.append(line)
        
        # Создаем блоки колонок
        column_blocks = {}
        
        if left_lines:
            left_x = [w['x0'] for line in left_lines for w in line]
            left_y = [w['top'] for line in left_lines for w in line]
            
            left_block = {
                'x0': min(left_x),
                'x1': max(left_x),
                'y0': min(left_y),
                'y1': max(left_y),
                'lines': left_lines
            }
            column_blocks['left'] = [left_block]
        
        if right_lines:
            right_x = [w['x0'] for line in right_lines for w in line]
            right_y = [w['top'] for line in right_lines for w in line]
            
            right_block = {
                'x0': min(right_x),
                'x1': max(right_x),
                'y0': min(right_y),
                'y1': max(right_y),
                'lines': right_lines
            }
            column_blocks['right'] = [right_block]
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Двухколоночная структура с блоками:")
            print(f"  Граница по медиане X: {median_x:.1f}")
            for col_name, blocks in column_blocks.items():
                print(f"  Колонка {col_name}: {len(blocks)} блок(ов)")
                for i, block in enumerate(blocks):
                    print(f"    Блок #{i}: X={block['x0']:.1f}-{block['x1']:.1f}, Y={block['y0']:.1f}-{block['y1']:.1f}, {len(block['lines'])} строк")
        
        return column_blocks
    
    def _create_column_blocks_statistical(self, lines: List[List[Dict]], language_info: LanguageInfo) -> Dict[str, List[List[Dict]]]:
        """Статистическое создание блоков колонок с учетом X и Y"""
        # Собираем X координаты для определения колонок
        all_x = [line[0]['x0'] for line in lines]
        
        # Строим гистограмму X координат
        min_x, max_x = min(all_x), max(all_x)
        num_bins = 30
        bin_width = (max_x - min_x) / num_bins if max_x != min_x else 1
        
        histogram = [0] * num_bins
        for x in all_x:
            bin_idx = int((x - min_x) / bin_width)
            if bin_idx >= num_bins:
                bin_idx = num_bins - 1
            histogram[bin_idx] += 1
        
        # Находим пики (колонки)
        peaks = []
        for i in range(1, num_bins - 1):
            if histogram[i] > histogram[i-1] and histogram[i] > histogram[i+1]:
                if histogram[i] > 0:
                    peak_x = min_x + (i + 0.5) * bin_width
                    peaks.append((peak_x, histogram[i]))
        
        peaks.sort(key=lambda p: p[1], reverse=True)
        top_peaks = peaks[:3]  # Максимум 3 колонки
        top_peaks.sort(key=lambda p: p[0])
        
        if not top_peaks:
            # Одна колонка
            all_coords = [w for line in lines for w in line]
            block = {
                'x0': min(w['x0'] for w in all_coords),
                'x1': max(w['x1'] for w in all_coords),
                'y0': min(w['top'] for w in all_coords),
                'y1': max(w['bottom'] for w in all_coords),
                'lines': lines
            }
            return {'single': [block]}
        
        # Определяем границы колонок
        column_boundaries = []
        for i in range(len(top_peaks) - 1):
            boundary = (top_peaks[i][0] + top_peaks[i+1][0]) / 2
            column_boundaries.append(boundary)
        
        # Распределяем строки по колонкам
        column_blocks = {}
        for i, (peak_x, _) in enumerate(top_peaks):
            col_name = f'col_{i}'
            col_lines = []
            
            for line in lines:
                x0 = line[0]['x0']
                
                if i == 0:
                    if not column_boundaries or x0 < column_boundaries[0]:
                        col_lines.append(line)
                elif i == len(top_peaks) - 1:
                    if x0 >= column_boundaries[-1]:
                        col_lines.append(line)
                else:
                    if column_boundaries[i-1] <= x0 < column_boundaries[i]:
                        col_lines.append(line)
            
            if col_lines:
                col_coords = [w for line in col_lines for w in line]
                block = {
                    'x0': min(w['x0'] for w in col_coords),
                    'x1': max(w['x1'] for w in col_coords),
                    'y0': min(w['top'] for w in col_coords),
                    'y1': max(w['bottom'] for w in col_coords),
                    'lines': col_lines
                }
                column_blocks[col_name] = [block]
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Статистические блоки колонок:")
            print(f"  Найдено колонок: {len(top_peaks)}")
            for col_name, blocks in column_blocks.items():
                print(f"  {col_name}: {len(blocks)} блок(ов)")
                for i, block in enumerate(blocks):
                    print(f"    Блок #{i}: X={block['x0']:.1f}-{block['x1']:.1f}, Y={block['y0']:.1f}-{block['y1']:.1f}, {len(block['lines'])} строк")
        
        return column_blocks
    
    def _group_lines_by_columns_statistical(self, lines: List[List[Dict]], language_info: LanguageInfo) -> Dict[float, List[List[Dict]]]:
        """Группирует строки по колонкам на основе статистического анализа X координат"""
        if not lines:
            return {}
        
        # Собираем X координаты всех строк
        all_x = [line[0]['x0'] for line in lines]
        
        if not all_x:
            return {}
        
        # Строим гистограмму X координат
        min_x, max_x = min(all_x), max(all_x)
        num_bins = 50
        if max_x == min_x:
            avg_x = sum(line[0]['x0'] for line in lines) / len(lines)
            return {avg_x: lines}
        bin_width = (max_x - min_x) / num_bins
        
        histogram = [0] * num_bins
        for x in all_x:
            bin_idx = int((x - min_x) / bin_width)
            if bin_idx >= num_bins:
                bin_idx = num_bins - 1
            histogram[bin_idx] += 1
        
        # Находим пики в гистограмме (колонки)
        peaks = []
        for i in range(1, num_bins - 1):
            if histogram[i] > histogram[i-1] and histogram[i] > histogram[i+1]:
                if histogram[i] > 0:
                    peak_x = min_x + (i + 0.5) * bin_width
                    peaks.append((peak_x, histogram[i]))
        
        peaks.sort(key=lambda p: p[1], reverse=True)
        top_peaks = peaks[:4]
        top_peaks.sort(key=lambda p: p[0])
        
        if not top_peaks:
            avg_x = sum(line[0]['x0'] for line in lines) / len(lines)
            return {avg_x: lines}
        
        # Определяем границы колонок
        column_boundaries = []
        for i in range(len(top_peaks) - 1):
            boundary = (top_peaks[i][0] + top_peaks[i+1][0]) / 2
            column_boundaries.append(boundary)
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Статистический анализ колонок:")
            print(f"  Всего строк: {len(lines)}")
            print(f"  X диапазон: {min_x:.1f} - {max_x:.1f}")
            print(f"  Найдено пиков: {len(top_peaks)}")
            for i, (peak_x, count) in enumerate(top_peaks):
                print(f"    Пик #{i}: X={peak_x:.1f}, строк={count}")
            if column_boundaries:
                print(f"  Границы колонок: {[f'{b:.1f}' for b in column_boundaries]}")
        
        # Группируем строки по колонкам
        columns = {}
        for peak_x, _ in top_peaks:
            columns[peak_x] = []
        
        for line in lines:
            x0 = line[0]['x0']
            
            assigned = False
            for i, peak_x in enumerate([p[0] for p in top_peaks]):
                if i == 0:
                    if not column_boundaries or x0 < column_boundaries[0]:
                        columns[peak_x].append(line)
                        assigned = True
                        break
                elif i == len(top_peaks) - 1:
                    if x0 >= column_boundaries[-1]:
                        columns[peak_x].append(line)
                        assigned = True
                        break
                else:
                    if column_boundaries[i-1] <= x0 < column_boundaries[i]:
                        columns[peak_x].append(line)
                        assigned = True
                        break
            
            if not assigned:
                closest_peak = min(top_peaks, key=lambda p: abs(p[0] - x0))
                columns[closest_peak[0]].append(line)
        
        columns = {k: v for k, v in columns.items() if v}
        
        if self._debug_mode:
            print(f"  Получено колонок: {len(columns)}")
            for col_x, col_lines in columns.items():
                print(f"    Колонка X={col_x:.1f}: {len(col_lines)} строк")
        
        return columns
    
    def _group_substrings_by_columns(self, substrings: List[List[Dict]], language_info: LanguageInfo, structure: str = None) -> Dict[float, List[List[Dict]]]:
        """Группирует подстроки по колонкам с учетом предопределенной структуры"""
        if not substrings:
            return {}
        
        # Если структура предопределена, используем её
        if structure == 'single_column' or structure == 'single_centered':
            # Одна колонка
            avg_x = sum(s[0]['x0'] for s in substrings) / len(substrings)
            if self._debug_mode:
                print(f"\n🔍 [COLS] Структура: {structure} - одна колонка")
                print(f"  Колонка X={avg_x:.1f}: {len(substrings)} подстрок")
            return {avg_x: substrings}
        
        elif structure == 'double_column':
            # Две колонки - определяем границу статистически
            # Собираем X координаты всех слов
            all_x = []
            for substring in substrings:
                for word in substring:
                    all_x.append(word['x0'])
            
            if not all_x:
                avg_x = sum(s[0]['x0'] for s in substrings) / len(substrings)
                return {avg_x: substrings}
            
            # Находим медиану X как границу между колонками
            import statistics
            try:
                median_x = statistics.median(all_x)
            except:
                median_x = sum(all_x) / len(all_x)
            
            # Группируем по медиане
            left_col = []
            right_col = []
            
            for substring in substrings:
                if not substring:
                    continue
                x0 = substring[0]['x0']
                if x0 < median_x:
                    left_col.append(substring)
                else:
                    right_col.append(substring)
            
            columns = {}
            if left_col:
                avg_left = sum(s[0]['x0'] for s in left_col) / len(left_col)
                columns[avg_left] = left_col
            if right_col:
                avg_right = sum(s[0]['x0'] for s in right_col) / len(right_col)
                columns[avg_right] = right_col
            
            if self._debug_mode:
                print(f"\n🔍 [COLS] Структура: double_column - две колонки")
                print(f"  Граница по медиане X: {median_x:.1f}")
                print(f"  Получено колонок: {len(columns)}")
                for col_x, col_substrings in columns.items():
                    print(f"    Колонка X={col_x:.1f}: {len(col_substrings)} подстрок")
            
            return columns
        
        else:
            # Структура не предопределена - используем статистический анализ
            return self._group_substrings_by_columns_statistical(substrings, language_info)
    
    def _group_substrings_by_columns_statistical(self, substrings: List[List[Dict]], language_info: LanguageInfo) -> Dict[float, List[List[Dict]]]:
        """Группирует подстроки по колонкам на основе статистического анализа X координат"""
        if not substrings:
            return {}
        
        # Собираем X координаты всех слов во всех подстроках
        all_x = []
        for substring in substrings:
            for word in substring:
                all_x.append(word['x0'])
        
        if not all_x:
            return {}
        
        # Строим гистограмму X координат
        min_x, max_x = min(all_x), max(all_x)
        num_bins = 50  # Количество бинов для гистограммы
        if max_x == min_x:
            # Все слова на одной X координате - одна колонка
            avg_x = sum(s[0]['x0'] for s in substrings) / len(substrings)
            return {avg_x: substrings}
        bin_width = (max_x - min_x) / num_bins
        
        # Подсчитываем слова в каждом бине
        histogram = [0] * num_bins
        for x in all_x:
            bin_idx = int((x - min_x) / bin_width)
            if bin_idx >= num_bins:
                bin_idx = num_bins - 1
            histogram[bin_idx] += 1
        
        # Находим пики в гистограмме (колонки)
        peaks = []
        for i in range(1, num_bins - 1):
            if histogram[i] > histogram[i-1] and histogram[i] > histogram[i+1]:
                # Локальный максимум
                if histogram[i] > 0:  # Игнорируем пустые бины
                    peak_x = min_x + (i + 0.5) * bin_width
                    peaks.append((peak_x, histogram[i]))
        
        # Сортируем пики по высоте и берем самые высокие
        peaks.sort(key=lambda p: p[1], reverse=True)
        top_peaks = peaks[:4]  # Максимум 4 колонки
        top_peaks.sort(key=lambda p: p[0])  # Сортируем по X
        
        if not top_peaks:
            # Если пиков не найдено, используем все подстроки как одну колонку
            avg_x = sum(s[0]['x0'] for s in substrings) / len(substrings)
            return {avg_x: substrings}
        
        # Определяем границы колонок
        column_boundaries = []
        for i in range(len(top_peaks) - 1):
            # Граница между пиками - середина между ними
            boundary = (top_peaks[i][0] + top_peaks[i+1][0]) / 2
            column_boundaries.append(boundary)
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Статистический анализ колонок:")
            print(f"  Всего подстрок: {len(substrings)}")
            print(f"  X диапазон: {min_x:.1f} - {max_x:.1f}")
            print(f"  Найдено пиков: {len(top_peaks)}")
            for i, (peak_x, count) in enumerate(top_peaks):
                print(f"    Пик #{i}: X={peak_x:.1f}, слов={count}")
            if column_boundaries:
                print(f"  Границы колонок: {[f'{b:.1f}' for b in column_boundaries]}")
        
        # Группируем подстроки по колонкам
        columns = {}
        for peak_x, _ in top_peaks:
            columns[peak_x] = []
        
        for substring in substrings:
            if not substring:
                continue
            x0 = substring[0]['x0']
            
            # Находим подходящую колонку
            assigned = False
            for i, peak_x in enumerate([p[0] for p in top_peaks]):
                if i == 0:
                    # Первая колонка: до первой границы
                    if not column_boundaries or x0 < column_boundaries[0]:
                        columns[peak_x].append(substring)
                        assigned = True
                        break
                elif i == len(top_peaks) - 1:
                    # Последняя колонка: после последней границы
                    if x0 >= column_boundaries[-1]:
                        columns[peak_x].append(substring)
                        assigned = True
                        break
                else:
                    # Промежуточные колонки: между границами
                    if column_boundaries[i-1] <= x0 < column_boundaries[i]:
                        columns[peak_x].append(substring)
                        assigned = True
                        break
            
            if not assigned:
                # Если не назначено, добавляем в ближайшую колонку
                closest_peak = min(top_peaks, key=lambda p: abs(p[0] - x0))
                columns[closest_peak[0]].append(substring)
        
        # Удаляем пустые колонки
        columns = {k: v for k, v in columns.items() if v}
        
        if self._debug_mode:
            print(f"  Получено колонок: {len(columns)}")
            for col_x, col_substrings in columns.items():
                print(f"    Колонка X={col_x:.1f}: {len(col_substrings)} подстрок")
        
        return columns
    
    def _split_line_by_gaps(self, line_words: List[Dict], language_info: LanguageInfo) -> List[List[Dict]]:
        """Разбивает строку на подстроки по большим зазорам между словами"""
        if not line_words:
            return []
        
        if len(line_words) == 1:
            return [line_words]
        
        # Сортируем слова по X
        sorted_words = sorted(line_words, key=lambda w: w['x0'])
        
        # Вычисляем зазоры между соседними словами
        gaps = []
        for i in range(len(sorted_words) - 1):
            gap = sorted_words[i+1]['x0'] - sorted_words[i]['x1']
            gaps.append(gap)
        
        if not gaps:
            return [sorted_words]
        
        # Определяем порог разбиения
        # Используем медиану + множитель для адаптивного порога
        import statistics
        try:
            median_gap = statistics.median(gaps)
        except:
            median_gap = sum(gaps) / len(gaps)
        
        # Порог: зазор в 2 раза больше медианы или минимум 20 пикселей
        threshold = max(median_gap * 2, 20)
        
        if self._debug_mode:
            line_text = ' '.join(w['text'] for w in sorted_words)
            print(f"    Строка: \"{line_text}\"")
            print(f"    Зазоры: {gaps} (медиана: {median_gap:.1f}, порог: {threshold:.1f})")
        
        # Разбиваем по большим зазорам
        substrings = []
        current_substring = [sorted_words[0]]
        
        for i, gap in enumerate(gaps):
            if gap > threshold:
                # Большой зазор - новая подстрока (новая колонка)
                substrings.append(current_substring)
                current_substring = [sorted_words[i+1]]
            else:
                # Маленький зазор - продолжение подстроки
                current_substring.append(sorted_words[i+1])
        
        substrings.append(current_substring)
        
        if self._debug_mode:
            if len(substrings) > 1:
                print(f"    → Разбито на {len(substrings)} подстрок:")
                for j, substring in enumerate(substrings):
                    substring_text = ' '.join(w['text'] for w in substring)
                    print(f"      Подстрока #{j}: \"{substring_text}\"")
            else:
                print(f"    → Не разбито (1 подстрока)")
        
        return substrings
    
    def _group_substrings_to_paragraphs(self, all_substrings: List[List[Dict]], language_info: LanguageInfo) -> List[List[List[Dict]]]:
        """Группирует подстроки в параграфы по вертикальным промежуткам"""
        if not all_substrings:
            return []
        
        # Сортируем подстроки по Y координате
        sorted_substrings = sorted(all_substrings, key=lambda s: s[0]['top'])
        
        paragraphs = []
        current_paragraph = []
        
        # Вычисляем среднюю высоту подстроки
        heights = []
        for substr in sorted_substrings:
            if substr:
                min_top = min(w['top'] for w in substr)
                max_bottom = max(w.get('bottom', w['top'] + 12) for w in substr)
                heights.append(max_bottom - min_top)
        
        avg_height = sum(heights) / len(heights) if heights else 12
        paragraph_gap_threshold = avg_height * 1.5  # Параграфный разрыв
        
        if self._debug_mode:
            print(f"\n🔍 [PARA] Группировка подстрок в параграфы:")
            print(f"  Всего подстрок: {len(sorted_substrings)}")
            print(f"  Средняя высота: {avg_height:.1f}")
            print(f"  Порог разрыва: {paragraph_gap_threshold:.1f}")
        
        for i, substring in enumerate(sorted_substrings):
            if not current_paragraph:
                current_paragraph.append(substring)
                if self._debug_mode:
                    print(f"  Подстрока #{i}: начало параграфа (Y={substring[0]['top']:.1f})")
                continue
            
            # Проверяем вертикальный зазор
            prev_substring = current_paragraph[-1]
            prev_bottom = max(w.get('bottom', w['top'] + 12) for w in prev_substring)
            current_top = substring[0]['top']
            vertical_gap = current_top - prev_bottom
            
            if vertical_gap > paragraph_gap_threshold:
                # Большой зазор - новый параграф
                paragraphs.append(current_paragraph)
                current_paragraph = [substring]
                if self._debug_mode:
                    print(f"  Подстрока #{i}: gap={vertical_gap:.1f} > {paragraph_gap_threshold:.1f} → НОВЫЙ ПАРАГРАФ")
            else:
                # Маленький зазор - продолжение параграфа
                current_paragraph.append(substring)
                if self._debug_mode and i % 10 == 0:
                    print(f"  Подстрока #{i}: gap={vertical_gap:.1f} → продолжение")
        
        # Добавляем последний параграф
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        if self._debug_mode:
            print(f"  Итого: {len(paragraphs)} параграфов")
        
        return paragraphs
    
    def _assign_columns_to_paragraphs(self, paragraphs: List[List[List[Dict]]], language_info: LanguageInfo) -> List[Dict]:
        """Определяет колонку для каждого параграфа и сортирует их"""
        if not paragraphs:
            return []
        
        # Добавляем информацию о колонке каждому параграфу
        paragraph_data = []
        for para in paragraphs:
            if para and para[0]:
                # X координата первой подстроки первого слова
                col_x = para[0][0]['x0']
                paragraph_data.append({
                    'paragraph': para,
                    'column_x': col_x
                })
        
        # Сортируем параграфы по колонкам с учетом направления текста
        if language_info.direction == 'rtl':
            # RTL: справа налево (убывание X)
            paragraph_data.sort(key=lambda p: p['column_x'], reverse=True)
        else:
            # LTR: слева направо (возрастание X)
            paragraph_data.sort(key=lambda p: p['column_x'])
        
        if self._debug_mode:
            print(f"\n🔍 [COLS] Сортировка параграфов по колонкам:")
            print(f"  Направление: {language_info.direction}")
            for i, p_data in enumerate(paragraph_data[:5]):
                print(f"    Параграф #{i}: X={p_data['column_x']:.1f}, {len(p_data['paragraph'])} подстрок")
        
        return paragraph_data
    
    def _auto_refinery(self, output_path: str, full_text: List[str], conf: Dict):
        """Отключено для чистого теста чтения"""
        utils.tbox_log("Refinery отключен для чистого теста чтения", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "INFO", conf)
        return

def extract_pdf():
    """Основная функция извлечения PDF"""
    # 1. Сбор вводных
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.dirname(script_dir)
    
    # Загружаем конфиг
    CONF = utils.load_local_config()
    if not CONF:
        utils.tbox_log("Критическая ошибка: Конфиг не найден.", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", CONF)
        return

    INBOX_DIR = CONF.get('INBOX_DIR')
    RAW_DIR = CONF.get('TXT_RAW')

    if not INBOX_DIR or not RAW_DIR:
        utils.tbox_log("В конфиге не заданы INBOX_DIR или TXT_RAW", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", CONF)
        return

    # 2. ЛОГИКА ПОИСКА ФАЙЛА (из старого скрипта)
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
        utils.tbox_log("Целевой файл не определен.", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", CONF)
        return

    # 3. Подготовка сохранения
    time_tag = datetime.now().strftime("%y%m%d_%H%M%S")
    original_name = os.path.basename(target_path)
    clean_base_name = original_name.replace('.pdf', '').replace('.PDF', '')
    output_txt = os.path.join(RAW_DIR, f"{time_tag}_{clean_base_name}_blocks.txt")

    # 4. Извлечение с новым классом
    utils.tbox_log(f"Старт извлечения: {original_name}", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "START", CONF)
    
    # Создаем экстрактор с конфигурацией по умолчанию
    extractor = PDFBlockExtractor()
    
    # Запускаем извлечение
    success = extractor.extract_from_pdf(target_path, output_txt, CONF)
    
    if success:
        utils.tbox_log(f"Извлечение завершено успешно", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "DONE", CONF)
    else:
        utils.tbox_log(f"Извлечение завершено с ошибками", {"name": "tbox_extract_pdf_v2.py", "version": "v4.0.block-extractor"}, "ERROR", CONF)

if __name__ == "__main__":
    extract_pdf()
