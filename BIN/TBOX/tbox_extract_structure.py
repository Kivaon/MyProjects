#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# --- ПАСПОРТ ---
VERSION = "v3.1.structure-analyzer"
DATE    = "2026-05-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# Конфигурация языков с направлениями текста
LANGUAGE_CONFIGS = {
    'hebrew': {
        'pattern': r'[\u0590-\u05FF]',
        'direction': 'rtl',
        'priority': 1
    },
    'arabic': {
        'pattern': r'[\u0600-\u06FF]',
        'direction': 'rtl',
        'priority': 2
    },
    'english': {
        'pattern': r'[a-zA-Z]',
        'direction': 'ltr',
        'priority': 3
    },
    'russian': {
        'pattern': r'[а-яёА-ЯЁ]',
        'direction': 'ltr',
        'priority': 4
    }
}

@dataclass
class LanguageInfo:
    """Информация о языке документа"""
    language: str
    direction: str  # 'ltr' или 'rtl'
    confidence: float

@dataclass
class ProcessedWord:
    """Обработанное слово"""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    original_text: str

@dataclass
class ProcessedLine:
    """Обработанная строка"""
    words: List[ProcessedWord]
    y0: float
    y1: float
    x0: float
    x1: float
    text: str
    line_number: int
    width: float  # Ширина строки

@dataclass
class ColumnGap:
    """Разрыв между колонками"""
    x_position: float
    frequency: int
    confidence: float
    gap_width: float

@dataclass
class PageSegment:
    """Сегмент страницы с определенной структурой"""
    y_start: float
    y_end: float
    structure_type: str  # 'single_column', 'multi_column'
    column_count: int
    column_gaps: List[ColumnGap]
    lines: List[ProcessedLine]

class PDFStructureAnalyzer:
    """Анализатор структуры страниц PDF с пошаговой обработкой"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_structure(self, pdf_path: str) -> bool:
        """Основной метод анализа структуры страницы"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_first_page_structure(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_first_page_structure(self, page):
        """Анализирует структуру первой страницы"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА ДОКУМЕНТА")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Язык: {self.language_info.language} ({self.language_info.direction})")
        print(f"  💪 Уверенность: {self.language_info.confidence:.0f} слов")
        
        print("\n" + "="*60)
        print("ШАГ 2: ОБРАБОТКА СЛОВ И ФОРМИРОВАНИЕ СТРОК")
        print("="*60)
        
        # Обрабатываем слова и формируем строки
        lines = self._process_words_and_form_lines(words)
        
        print("\n" + "="*60)
        print("ШАГ 3: АНАЛИЗ СТРОК СВЕРХУ ВНИЗ")
        print("="*60)
        
        # Анализируем строки сверху вниз для определения структуры
        segments = self._analyze_lines_top_to_bottom(lines)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА СТРУКТУРЫ СТРАНИЦЫ")
        print("="*60)
        
        # Формируем статистику страницы
        self._generate_page_statistics(segments)
        
        # Сохраняем результаты
        self._save_structure_analysis(lines, segments)
    
    def _detect_language(self, word_texts: List[str]) -> LanguageInfo:
        """Определяет язык документа"""
        if not word_texts:
            return LanguageInfo('unknown', 'ltr', 0.0)
        
        # Считаем слова для каждого языка
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            count = sum(1 for word in word_texts if re.search(pattern, word))
            language_scores[lang_name] = count
        
        if not language_scores:
            return LanguageInfo('unknown', 'ltr', 0.0)
        
        # Находим язык с максимальным счетом
        best_language = max(language_scores.items(), key=lambda x: x[1])
        lang_name, confidence = best_language
        
        lang_config = LANGUAGE_CONFIGS[lang_name]
        return LanguageInfo(
            language=lang_name,
            direction=lang_config['direction'],
            confidence=confidence
        )
    
    def _process_words_and_form_lines(self, raw_words: List[Dict]) -> List[ProcessedLine]:
        """Обрабатывает слова и формирует строки"""
        print(f"  📝 Обработка {len(raw_words)} слов:")
        
        # Обрабатываем слова с правильным порядком букв
        processed_words = []
        for word in raw_words:
            original_text = word['text']
            
            if self.language_info.direction == 'rtl':
                processed_text = original_text[::-1]
            else:
                processed_text = original_text
            
            processed_word = ProcessedWord(
                text=processed_text,
                original_text=original_text,
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word.get('bottom', word['top'] + 10)
            )
            processed_words.append(processed_word)
        
        # Группируем слова в строки по Y координате
        lines = self._group_words_to_lines(processed_words)
        
        print(f"  ✅ Создано строк: {len(lines)}")
        return lines
    
    def _group_words_to_lines(self, words: List[ProcessedWord]) -> List[ProcessedLine]:
        """Группирует слова в строки по Y координате"""
        if not words:
            return []
        
        # Сортируем слова по Y, затем по X
        sorted_words = sorted(words, key=lambda w: (w.y0, w.x0))
        
        lines = []
        current_line_words = []
        current_y = None
        y_tolerance = 3.0
        
        for word in sorted_words:
            word_y = word.y0
            
            if current_y is None:
                current_y = word_y
                current_line_words = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                current_line_words.append(word)
            else:
                if current_line_words:
                    line = self._create_processed_line(current_line_words, len(lines))
                    lines.append(line)
                current_line_words = [word]
                current_y = word_y
        
        if current_line_words:
            line = self._create_processed_line(current_line_words, len(lines))
            lines.append(line)
        
        return lines
    
    def _create_processed_line(self, words: List[ProcessedWord], line_number: int) -> ProcessedLine:
        """Создает обработанную строку из слов"""
        if not words:
            return None
        
        # Сортируем слова по X с учетом направления языка
        if self.language_info.direction == 'rtl':
            sorted_words = sorted(words, key=lambda w: -w.x0)
        else:
            sorted_words = sorted(words, key=lambda w: w.x0)
        
        # Собираем текст
        text = ' '.join(w.text for w in sorted_words)
        
        # Вычисляем границы строки
        y0 = min(w.y0 for w in words)
        y1 = max(w.y1 for w in words)
        x0 = min(w.x0 for w in words)
        x1 = max(w.x1 for w in words)
        width = x1 - x0
        
        return ProcessedLine(
            words=sorted_words,
            y0=y0, y1=y1, x0=x0, x1=x1,
            text=text,
            line_number=line_number,
            width=width
        )
    
    def _analyze_lines_top_to_bottom(self, lines: List[ProcessedLine]) -> List[PageSegment]:
        """Анализирует строки сверху вниз для определения структуры"""
        print(f"  🔍 Анализ {len(lines)} строк сверху вниз:")
        
        if not lines:
            return []
        
        # Сортируем строки по Y
        sorted_lines = sorted(lines, key=lambda l: l.y0)
        
        # Определяем общую ширину страницы
        page_width = max(l.x1 for l in sorted_lines) - min(l.x0 for l in sorted_lines)
        print(f"    📏 Ширина страницы: {page_width:.1f} пикселей")
        
        # Порог для определения строки на всю ширину
        full_width_threshold = page_width * 0.85  # 85% от ширины страницы
        
        segments = []
        current_segment_lines = []
        segment_start_y = sorted_lines[0].y0
        segment_structure = 'unknown'
        column_gaps = []
        
        for line in sorted_lines:
            line_width = line.width
            
            # Определяем тип строки
            is_full_width = line_width >= full_width_threshold
            
            if is_full_width:
                # Строка на всю ширину - начинаем новую 1-колоночную секцию
                if current_segment_lines:
                    # Сохраняем текущий сегмент
                    segment = self._create_page_segment(
                        segment_start_y, current_segment_lines[-1].y1,
                        current_segment_lines, segment_structure, column_gaps
                    )
                    if segment:
                        segments.append(segment)
                
                # Начинаем новую 1-колоночную секцию
                current_segment_lines = [line]
                segment_start_y = line.y0
                segment_structure = 'single_column'
                column_gaps = []
                
                print(f"    📄 Строка {line.line_number}: ширина {line_width:.1f} (полная ширина) → 1 колонка")
                
            else:
                # Строка не на всю ширину - анализируем разрывы
                current_segment_lines.append(line)
                
                # Определяем текущую структуру
                if segment_structure == 'single_column':
                    segment_structure = 'multi_column'
                
                # Ищем разрывы между словами в строке
                gaps = self._find_gaps_in_line(line)
                for gap in gaps:
                    self._add_gap_to_statistics(gap, column_gaps)
                
                print(f"    📊 Строка {line.line_number}: ширина {line_width:.1f} (многоколонка) → разрывы: {len(gaps)}")
        
        # Сохраняем последний сегмент
        if current_segment_lines:
            segment = self._create_page_segment(
                segment_start_y, current_segment_lines[-1].y1,
                current_segment_lines, segment_structure, column_gaps
            )
            if segment:
                segments.append(segment)
        
        print(f"    ✅ Создано сегментов: {len(segments)}")
        
        for i, segment in enumerate(segments):
            print(f"      Сегмент {i+1}: Y={segment.y_start:.1f}-{segment.y_end:.1f}, "
                  f"тип={segment.structure_type}, колонок={segment.column_count}")
        
        return segments
    
    def _find_gaps_in_line(self, line: ProcessedLine) -> List[float]:
        """Находит разрывы между словами в строке"""
        if len(line.words) < 2:
            return []
        
        gaps = []
        for i in range(len(line.words) - 1):
            gap = abs(line.words[i + 1].x0 - line.words[i].x1)
            if gap > 5:  # Минимальный разрыв 5 пикселей
                gap_position = (line.words[i].x1 + line.words[i + 1].x0) / 2
                gaps.append(gap_position)
        
        return gaps
    
    def _add_gap_to_statistics(self, gap_position: float, column_gaps: List[ColumnGap]):
        """Добавляет разрыв в статистику"""
        # Ищем существующий разрыв в той же позиции
        tolerance = 10.0  # Допуск 10 пикселей
        
        for existing_gap in column_gaps:
            if abs(existing_gap.x_position - gap_position) <= tolerance:
                existing_gap.frequency += 1
                existing_gap.confidence = min(1.0, existing_gap.frequency / 5.0)  # Макс. уверенность при 5 повторениях
                return
        
        # Создаем новый разрыв
        new_gap = ColumnGap(
            x_position=gap_position,
            frequency=1,
            confidence=0.2,  # Начальная уверенность
            gap_width=0  # Будет вычислено позже
        )
        column_gaps.append(new_gap)
    
    def _create_page_segment(self, y_start: float, y_end: float, lines: List[ProcessedLine], 
                           structure_type: str, column_gaps: List[ColumnGap]) -> Optional[PageSegment]:
        """Создает сегмент страницы"""
        if not lines:
            return None
        
        # Определяем количество колонок
        if structure_type == 'single_column':
            column_count = 1
        else:
            # Считаем количество уверенных разрывов
            confident_gaps = [g for g in column_gaps if g.confidence >= 0.4]
            column_count = len(confident_gaps) + 1
        
        return PageSegment(
            y_start=y_start,
            y_end=y_end,
            structure_type=structure_type,
            column_count=column_count,
            column_gaps=column_gaps,
            lines=lines
        )
    
    def _generate_page_statistics(self, segments: List[PageSegment]):
        """Генерирует статистику структуры страницы"""
        print(f"  📊 Статистика структуры страницы:")
        
        total_segments = len(segments)
        single_column_segments = sum(1 for s in segments if s.structure_type == 'single_column')
        multi_column_segments = sum(1 for s in segments if s.structure_type == 'multi_column')
        
        # Собираем все разрывы между колонками
        all_gaps = {}
        for segment in segments:
            for gap in segment.column_gaps:
                if gap.x_position not in all_gaps:
                    all_gaps[gap.x_position] = {
                        'total_frequency': 0,
                        'max_confidence': 0,
                        'segments': []
                    }
                
                all_gaps[gap.x_position]['total_frequency'] += gap.frequency
                all_gaps[gap.x_position]['max_confidence'] = max(all_gaps[gap.x_position]['max_confidence'], gap.confidence)
                all_gaps[gap.x_position]['segments'].append(segment)
        
        # Сортируем разрывы по частоте
        sorted_gaps = sorted(all_gaps.items(), key=lambda x: x[1]['total_frequency'], reverse=True)
        
        print(f"    📄 Всего сегментов: {total_segments}")
        print(f"      1-колоночных: {single_column_segments}")
        print(f"      Многоколонных: {multi_column_segments}")
        
        print(f"    📊 Разрывы между колонками (топ-5):")
        for i, (gap_pos, gap_info) in enumerate(sorted_gaps[:5]):
            print(f"      Разрыв {i+1}: X={gap_pos:.1f}, частота={gap_info['total_frequency']}, "
                  f"уверенность={gap_info['max_confidence']:.2f}")
    
    def _save_structure_analysis(self, lines: List[ProcessedLine], segments: List[PageSegment]):
        """Сохраняет результаты анализа структуры"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем строки
        lines_file = os.path.join(debug_dir, f"{timestamp}_structure_lines.txt")
        with open(lines_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ СТРОК ПЕРВОЙ СТРАНИЦЫ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info.language} ({self.language_info.direction})\n")
            f.write(f"Всего строк: {len(lines)}\n\n")
            
            for line in lines:
                f.write(f"Строка {line.line_number:3d}: Y={line.y0:6.1f}, X={line.x0:6.1f}-{line.x1:6.1f}, ширина={line.width:6.1f}\n")
                f.write(f"Текст: {line.text}\n")
                f.write("-"*50 + "\n")
        
        # Сохраняем сегменты
        segments_file = os.path.join(debug_dir, f"{timestamp}_structure_segments.txt")
        with open(segments_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ СЕГМЕНТОВ СТРАНИЦЫ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info.language} ({self.language_info.direction})\n")
            f.write(f"Всего сегментов: {len(segments)}\n\n")
            
            for i, segment in enumerate(segments):
                f.write(f"СЕГМЕНТ {i+1}:\n")
                f.write(f"  Диапазон Y: {segment.y_start:.1f} - {segment.y_end:.1f}\n")
                f.write(f"  Тип структуры: {segment.structure_type}\n")
                f.write(f"  Количество колонок: {segment.column_count}\n")
                f.write(f"  Количество строк: {len(segment.lines)}\n")
                
                if segment.column_gaps:
                    f.write(f"  Разрывы между колонками:\n")
                    for gap in segment.column_gaps:
                        f.write(f"    X={gap.x_position:.1f}, частота={gap.frequency}, уверенность={gap.confidence:.2f}\n")
                
                f.write(f"  Строки в сегменте:\n")
                for line in segment.lines:
                    f.write(f"    Строка {line.line_number:3d}: ширина={line.width:6.1f}, текст: {line.text}\n")
                
                f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Файлы анализа сохранены:")
        print(f"     📄 Строки: {lines_file}")
        print(f"     📄 Сегменты: {segments_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_extract_structure.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = PDFStructureAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_structure(pdf_path)
    
    if success:
        print(f"\n✅ Анализ структуры завершен успешно")
    else:
        print(f"\n❌ Анализ структуры завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
