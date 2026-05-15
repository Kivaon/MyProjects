#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        'pattern': r'[а-яёА-ЯЁ]',
        'direction': 'ltr',
        'bidi': False,
        'priority': 4
    }
}

@dataclass
class LanguageInfo:
    """Информация о языке документа"""
    language: str
    direction: str  # 'ltr' или 'rtl'
    bidi: bool
    confidence: float

@dataclass
class PageSegment:
    """Сегмент страницы с определенной структурой"""
    y_start: float
    y_end: float
    structure: str  # 'single_column', 'double_column', 'single_centered'
    words: List[Dict]

@dataclass
class TextBlock:
    """Текстовый блок"""
    text: str
    block_type: BlockType
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    confidence: float
    source_lines: Optional[List[List[Dict]]] = None

class PDFBlockExtractor:
    """Извлекатель текстовых блоков из PDF с улучшенным алгоритмом"""
    
    def __init__(self, config: Dict):
        self.config = config
        self._debug_mode = config.get('debug_mode', False)
        self._language_info = None
        self._current_pdf_path = None
    
    def extract_from_pdf(self, pdf_path: str, conf: Dict) -> bool:
        """Основной метод извлечения текста из PDF"""
        try:
            # Сохраняем путь к PDF для отладки
            self._current_pdf_path = pdf_path
            
            # Определяем путь вывода
            output_path = self._get_output_path(pdf_path, conf)
            
            # Открываем PDF
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                all_blocks = []
                full_text = []
                
                # Обрабатываем каждую страницу
                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"\n📄 Страница {page_num}:")
                    blocks = self._extract_blocks_from_page(page, page_num, conf)
                    all_blocks.extend(blocks)
                    
                    # Преобразуем блоки в текст
                    page_text = self._blocks_to_text(blocks, conf)
                    
                    if page_text:
                        full_text.append(page_text)
                    
                    if page_num % 10 == 0:
                        utils.tbox_log(f"Прогресс: {page_num}/{len(pdf.pages)} страниц", META, "INFO", conf)
            
            # Сохраняем результат
            self._save_text(all_blocks, output_path, pdf_path, conf)
            
            # Передаем в Refinery если доступен
            self._auto_refinery(output_path, all_blocks, conf)
            
            return True
            
        except Exception as e:
            utils.tbox_log(f"Ошибка извлечения PDF: {e}", META, "ERROR", conf)
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
            utils.tbox_log(f"Ошибка извлечения блоков со страницы {page_num}: {e}", META, "WARNING", conf)
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
        
        # Группируем слова в строки по Y координате
        lines = self._group_words_to_lines(segment.words, language_info)
        
        # Разбиваем строки на подстроки по большим X пробелам
        substrings = []
        for line in lines:
            line_substrings = self._split_line_by_gaps(line, language_info)
            substrings.extend(line_substrings)
        
        # Группируем подстроки в параграфы по вертикальным промежуткам
        all_paragraphs = self._group_substrings_to_paragraphs(substrings, language_info)
        
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
                
                text = '\n'.join(text_parts)
                
                # Вычисляем координаты параграфа
                if paragraph:
                    min_top = min(w['top'] for line in paragraph for w in line)
                    max_bottom = max(w.get('bottom', w['top'] + 12) for line in paragraph for w in line)
                    min_left = min(w['x0'] for line in paragraph for w in line)
                    max_right = max(w['x1'] for line in paragraph for w in line)
                else:
                    min_top = max_bottom = min_left = max_right = 0
                
                block = TextBlock(
                    text=text,
                    block_type=BlockType.PARAGRAPH,
                    x0=min_left, y0=min_top, x1=max_right, y1=max_bottom,
                    page_num=page_num,
                    confidence=0.8,
                    source_lines=paragraph
                )
                blocks.append(block)
                
            except Exception as e:
                print(f"Ошибка при создании блока: {e}")
                continue
        
        if self._debug_mode:
            print(f"  Создано {len(blocks)} блоков из параграфов")
        
        return blocks
    
    def _group_words_to_lines(self, words: List[Dict], language_info: LanguageInfo) -> List[List[Dict]]:
        """Группирует слова в строки по Y координате"""
        if not words:
            return []
        
        # Сортируем слова по Y, затем по X
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        lines = []
        current_line = []
        current_y = None
        y_tolerance = 3.0
        
        for word in sorted_words:
            word_y = word['top']
            
            if current_y is None:
                current_y = word_y
                current_line = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [word]
                current_y = word_y
        
        if current_line:
            lines.append(current_line)
        
        if self._debug_mode:
            print(f"  Сгруппировано {len(words)} слов в {len(lines)} строк")
        
        return lines
    
    def _split_line_by_gaps(self, line: List[Dict], language_info: LanguageInfo) -> List[List[Dict]]:
        """Разбивает строку на подстроки по большим X пробелам"""
        if len(line) <= 1:
            return [line]
        
        # Сортируем слова в строке по X
        sorted_words = sorted(line, key=lambda w: w['x0'])
        
        # Находим большие пробелы между словами
        gaps = []
        for i in range(len(sorted_words) - 1):
            gap = sorted_words[i + 1]['x0'] - sorted_words[i]['x1']
            if gap > 0:
                gaps.append(gap)
        
        if not gaps:
            return [line]
        
        # Вычисляем порог для разделения
        avg_gap = sum(gaps) / len(gaps)
        gap_threshold = avg_gap * 2.0
        
        if self._debug_mode:
            print(f"    Найдено {len(gaps)} пробелов, средний: {avg_gap:.1f}, порог: {gap_threshold:.1f}")
        
        # Разбиваем строку на подстроки
        substrings = []
        current_substring = [sorted_words[0]]
        
        for i in range(len(sorted_words) - 1):
            gap = sorted_words[i + 1]['x0'] - sorted_words[i]['x1']
            if gap > gap_threshold:
                substrings.append(current_substring)
                current_substring = [sorted_words[i + 1]]
            else:
                current_substring.append(sorted_words[i + 1])
        
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
        paragraph_gap_threshold = avg_height * 1.5
        
        if self._debug_mode:
            print(f"\n🔍 [PARA] Группировка подстрок в параграфы:")
            print(f"  Всего подстрок: {len(sorted_substrings)}")
            print(f"  Средняя высота: {avg_height:.1f}")
            print(f"  Порог разрыва: {paragraph_gap_threshold:.1f}")
        
        for i, substring in enumerate(sorted_substrings):
            if not current_paragraph:
                current_paragraph = substring
            else:
                # Проверяем вертикальный разрыв
                last_bottom = max(w.get('bottom', w['top'] + 12) for w in current_paragraph[-1])
                current_top = min(w['top'] for w in substring)
                
                if current_top - last_bottom > paragraph_gap_threshold:
                    # Начинаем новый параграф
                    paragraphs.append(current_paragraph)
                    current_paragraph = substring
                else:
                    # Продолжаем текущий параграф
                    current_paragraph.extend(substring)
        
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        if self._debug_mode:
            print(f"  Создано {len(paragraphs)} параграфов")
        
        return paragraphs
    
    def _segment_page(self, page, conf: Dict) -> List[PageSegment]:
        """Сегментирует страницу на горизонтальные полосы"""
        try:
            words = page.extract_words()
            if not words:
                return []
            
            # Разделяем страницу на горизонтальные полосы
            page_height = page.height
            strip_height = 50.0  # Высота полосы для анализа
            
            num_strips = int(page_height / strip_height) + 1
            segments = []
            
            for i in range(num_strips):
                y_start = i * strip_height
                y_end = min((i + 1) * strip_height, page_height)
                
                # Находим слова в этой полосе
                strip_words = [w for w in words if y_start <= w['top'] <= y_end]
                
                if not strip_words:
                    continue
                
                # Анализируем структуру полосы
                structure = self._analyze_strip_structure(strip_words, conf)
                
                segment = PageSegment(
                    y_start=y_start,
                    y_end=y_end,
                    structure=structure,
                    words=strip_words
                )
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            print(f"Ошибка сегментации страницы: {e}")
            return []
    
    def _analyze_strip_structure(self, words: List[Dict], conf: Dict) -> str:
        """Анализирует структуру полосы (одна/две колонки)"""
        if len(words) < 3:
            return 'single_column'
        
        # Сортируем слова по X
        sorted_words = sorted(words, key=lambda w: w['x0'])
        
        # Находим центральный разрыв
        x_positions = [w['x0'] for w in sorted_words]
        min_x = min(x_positions)
        max_x = max(x_positions)
        center_x = (min_x + max_x) / 2
        
        # Считаем слова слева и справа от центра
        left_words = [w for w in sorted_words if w['x0'] < center_x]
        right_words = [w for w in sorted_words if w['x0'] >= center_x]
        
        # Проверяем условие двух колонок
        if len(left_words) >= 2 and len(right_words) >= 2:
            return 'double_column'
        elif len(right_words) >= 3 and len(left_words) < 2:
            return 'single_centered'
        else:
            return 'single_column'
    
    def _detect_language(self, word_texts: List[str]) -> LanguageInfo:
        """Определяет основной язык документа"""
        if not word_texts:
            return LanguageInfo('unknown', 'ltr', False, 0.0)
        
        # Считаем слова для каждого языка
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            count = sum(1 for word in word_texts if re.search(pattern, word))
            language_scores[lang_name] = count
        
        if not language_scores:
            return LanguageInfo('unknown', 'ltr', False, 0.0)
        
        # Находим язык с максимальным счетом
        best_language = max(language_scores.items(), key=lambda x: x[1])
        lang_name, confidence = best_language
        
        if self._debug_mode:
            print(f"\n🔍 [LANG] Определение языка:")
            print(f"  Анализируем {len(word_texts)} слов")
            print(f"  Счета языков: {language_scores}")
            print(f"  Лучший язык: {lang_name} (confidence: {confidence:.2f})")
        
        # Проверяем порог для доминирующего языка
        if confidence < self.config.get('language_threshold', 0.3):
            if self._debug_mode:
                print(f"  Результат: mixed (confidence {confidence:.2f} < threshold {self.config.get('language_threshold', 0.3)})")
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
    
    def _blocks_to_text(self, blocks: List[TextBlock], conf: Dict) -> str:
        """Преобразует блоки в текст с учетом языка"""
        if not blocks:
            return ""
        
        # Определяем язык если еще не определен
        if self._language_info is None:
            word_texts = []
            for block in blocks:
                if hasattr(block, 'source_lines') and block.source_lines:
                    for line in block.source_lines:
                        word_texts.extend(w['text'] for w in line)
            self._language_info = self._detect_language(word_texts)
        
        language_info = self._language_info
        
        # Сортируем блоки по колонкам и Y
        if language_info.direction == 'rtl':
            # Для RTL: сначала правая колонка, потом левая
            # Сортируем по X убыванию, затем по Y возрастанию
            sorted_blocks = sorted(blocks, key=lambda b: (-b.x0, b.y0))
        else:
            # Для LTR: сначала левая колонка, потом правая
            # Сортируем по X возрастанию, затем по Y возрастанию
            sorted_blocks = sorted(blocks, key=lambda b: (b.x0, b.y0))
        
        # Обрабатываем текст в каждом блоке с учетом языка
        text_parts = []
        for block in sorted_blocks:
            processed_text = self._process_text_for_language(block.text, language_info)
            if processed_text.strip():
                text_parts.append(processed_text.strip())
        
        return '\n\n'.join(text_parts)
    
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
    
    def _save_text(self, blocks: List[TextBlock], output_path: str, pdf_path: str, conf: Dict):
        """Сохраняет извлеченный текст в файл"""
        try:
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Преобразуем блоки в текст
            text = self._blocks_to_text(blocks, conf)
            
            # Сохраняем в файл
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            utils.tbox_log(f"Текст извлечен: {output_path}", META, "DONE", conf)
            
        except Exception as e:
            utils.tbox_log(f"Ошибка сохранения текста: {e}", META, "ERROR", conf)
    
    def _get_output_path(self, pdf_path: str, conf: Dict) -> str:
        """Генерирует путь для выходного файла"""
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        output_dir = conf.get('output_dir', '/Users/kivaonmac/Documents/AI_Lab/02_TXT/raw')
        return os.path.join(output_dir, f"{timestamp}_{base_name}_blocks.txt")
    
    def _auto_refinery(self, output_path: str, blocks: List[TextBlock], conf: Dict):
        """Автоматически передает текст в Refinery если доступен"""
        if refinery and self.config.get('auto_refinery', False):
            try:
                refinery.process_file(output_path, conf)
            except Exception as e:
                utils.tbox_log(f"Ошибка Refinery: {e}", META, "WARNING", conf)
    
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
            utils.tbox_log(f"Ошибка fallback извлечения: {e}", META, "ERROR", conf)
        
        return []

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_extract_pdf_v2.py <pdf_file> [options]")
        print("Опции:")
        print("  --debug     Включить отладочный режим")
        print("  --output-dir <dir>  Директория для выходных файлов")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Конфигурация по умолчанию
    config = {
        'debug_mode': '--debug' in sys.argv,
        'output_dir': '/Users/kivaonmac/Documents/AI_Lab/02_TXT/raw',
        'language_threshold': 0.3,
        'auto_refinery': False
    }
    
    # Парсим опции командной строки
    for i, arg in enumerate(sys.argv[2:]):
        if arg == '--output-dir' and i + 1 < len(sys.argv) - 1:
            config['output_dir'] = sys.argv[i + 2]
        elif arg == '--language-threshold' and i + 1 < len(sys.argv) - 1:
            config['language_threshold'] = float(sys.argv[i + 2])
        elif arg == '--auto-refinery':
            config['auto_refinery'] = True
    
    # Создаем извлекатель и запускаем
    extractor = PDFBlockExtractor(config)
    success = extractor.extract_from_pdf(pdf_path, config)
    
    if success:
        print(f"\n✅ Извлечение завершено успешно")
    else:
        print(f"\n❌ Извлечение завершено с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
