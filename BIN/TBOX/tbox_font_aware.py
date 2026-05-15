#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.6.font-aware-rtl"
DATE    = "2026-05-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# Конфигурация языков с направлениями текста
LANGUAGE_CONFIGS = {
    'hebrew': {
        'pattern': r'[\u0590-\u05FF]',
        'direction': 'rtl',
        'priority': 1,
        'typical_font_size': 12.0  # Типичный размер шрифта для иврита
    },
    'arabic': {
        'pattern': r'[\u0600-\u06FF]',
        'direction': 'rtl',
        'priority': 2,
        'typical_font_size': 14.0
    },
    'english': {
        'pattern': r'[a-zA-Z]',
        'direction': 'ltr',
        'priority': 3,
        'typical_font_size': 10.0
    },
    'russian': {
        'pattern': r'[а-яёА-ЯЁ]',
        'direction': 'ltr',
        'priority': 4,
        'typical_font_size': 11.0
    }
}

# Знаки препинания для разных языков
PUNCTUATION_PATTERNS = {
    'hebrew': r'[.,:;!?""''(){}\[\]–—]',
    'arabic': r'[.,:;!?""''(){}\[\]–—]',
    'english': r'[.,:;!?""''(){}\[\]–—]',
    'russian': r'[.,:;!?""''(){}\[\]–—]',
    'universal': r'[.,:;!?""''(){}\[\]–—]'
}

def has_nikud(text: str) -> bool:
    """Проверяет, содержит ли текст огласовки"""
    for char in text:
        if 0x05B0 <= ord(char) <= 0x05BD:  # Hebrew vowels
            return True
        if 0xFB1D <= ord(char) <= 0xFB4F:  # Alphabetic Presentation Forms
            return True
    return False

@dataclass
class ProcessedWord:
    """Обработанное слово с учетом шрифта"""
    text: str
    original_text: str
    x0: float
    y0: float
    x1: float
    y1: float
    language: str
    font_size_estimate: float  # Оценка размера шрифта

@dataclass
class ProcessedLine:
    """Обработанная строка с учетом шрифта"""
    words: List[ProcessedWord]
    y0: float
    y1: float
    x0: float
    x1: float
    text: str
    line_number: int
    width: float
    dominant_language: str
    avg_font_size: float

@dataclass
class YGroup:
    """Группа строк по Y координате"""
    y_center: float
    lines: List[ProcessedLine]
    column_count: int
    x_positions: List[float]

class FontAwareRTLAnalyzer:
    """Анализатор с учетом размера шрифта для RTL текста"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_font_aware(self, pdf_path: str) -> bool:
        """Основной метод анализа с учетом размера шрифта"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_font_aware(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_font_aware(self, page):
        """Анализ страницы с учетом размера шрифта"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И ОЦЕНКА ШРИФТА")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        # Оцениваем размер шрифта
        font_size_estimate = self._estimate_font_size(words)
        
        print(f"  🎯 Основной язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        print(f"  🔤 Оценка размера шрифта: {font_size_estimate:.1f} пикселей")
        
        print("\n" + "="*60)
        print("ШАГ 2: ОБРАБОТКА СЛОВ С УЧЕТОМ ШРИФТА")
        print("="*60)
        
        # ЭТАП 1: Обрабатываем слова с учетом шрифта
        processed_words = self._process_words_with_font_aware(words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК С АДАПТИВНЫМИ ПОРОГАМИ")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с адаптивными порогами
        y_groups = self._form_lines_with_font_aware(processed_words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА С УЧЕТОМ ШРИФТА")
        print("="*60)
        
        # ЭТАП 3: Статистика с учетом размера шрифта
        self._analyze_with_font_stats(y_groups, font_size_estimate)
        
        # Сохраняем результаты
        self._save_font_aware_analysis(y_groups, font_size_estimate)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык документа"""
        if not word_texts:
            return {'language': 'unknown', 'direction': 'ltr', 'confidence': 0.0}
        
        # Считаем слова для каждого языка (без учета знаков препинания)
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            clean_words = [re.sub(PUNCTUATION_PATTERNS['universal'], '', w) for w in word_texts]
            count = sum(1 for word in clean_words if re.search(pattern, word))
            language_scores[lang_name] = count
        
        if not language_scores:
            return {'language': 'unknown', 'direction': 'ltr', 'confidence': 0.0}
        
        # Находим язык с максимальным счетом
        best_language = max(language_scores.items(), key=lambda x: x[1])
        lang_name, confidence = best_language
        
        lang_config = LANGUAGE_CONFIGS[lang_name]
        return {
            'language': lang_name,
            'direction': lang_config['direction'],
            'confidence': confidence,
            'typical_font_size': lang_config.get('typical_font_size', 12.0)
        }
    
    def _estimate_font_size(self, words: List[Dict]) -> float:
        """Оценивает средний размер шрифта на основе высоты слов"""
        if not words:
            return 12.0
        
        heights = []
        for word in words:
            height = word.get('bottom', word['top'] + 12) - word['top']
            if height > 0:  # Игнорируем некорректные высоты
                heights.append(height)
        
        if heights:
            avg_height = sum(heights) / len(heights)
            # Для RTL текста часто используются большие шрифты
            if self.language_info and self.language_info['direction'] == 'rtl':
                return max(avg_height, self.language_info.get('typical_font_size', 12.0))
            else:
                return avg_height
        
        return 12.0
    
    def _process_words_with_font_aware(self, raw_words: List[Dict], font_size: float) -> List[ProcessedWord]:
        """ЭТАП 1: Обрабатываем слова с учетом размера шрифта"""
        print(f"  🔤 Обработка {len(raw_words)} слов с учетом шрифта:")
        
        processed_words = []
        direction = self.language_info['direction']
        
        for i, word in enumerate(raw_words):
            original_text = word['text']
            
            # Инвертируем порядок букв только для RTL
            if direction == 'rtl':
                processed_text = original_text[::-1]
            else:
                processed_text = original_text
            
            processed_word = ProcessedWord(
                text=processed_text,
                original_text=original_text,
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word.get('bottom', word['top'] + font_size),
                language=self.language_info['language'],
                font_size_estimate=font_size
            )
            processed_words.append(processed_word)
            
            # Показываем первые 10 слов
            if i < 10:
                print(f"    {i+1:2d}. {original_text:12s} → {processed_text:12s}  ({word['x0']:6.1f},{word['top']:6.1f})")
            elif i == 10:
                print(f"    ... и еще {len(raw_words) - 10} слов")
        
        print(f"  ✅ Обработано слов: {len(processed_words)} (шрифт: {font_size:.1f}px)")
        return processed_words
    
    def _form_lines_with_font_aware(self, words: List[ProcessedWord], font_size: float) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с адаптивными порогами"""
        print(f"  📋 Формирование строк с адаптивными порогами (шрифт: {font_size:.1f}px):")
        
        if not words:
            return []
        
        direction = self.language_info['direction']
        
        # Сортируем слова по Y, затем по X
        sorted_words = sorted(words, key=lambda w: (w.y0, w.x0))
        
        groups = []
        current_group_words = []
        current_y = None
        y_tolerance = 3.0
        
        for word in sorted_words:
            word_y = word.y0
            
            if current_y is None:
                current_y = word_y
                current_group_words = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                current_group_words.append(word)
            else:
                if current_group_words:
                    group = self._create_y_group_with_font_aware(current_group_words, len(groups), font_size)
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_font_aware(current_group_words, len(groups), font_size)
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        return groups
    
    def _create_y_group_with_font_aware(self, words: List[ProcessedWord], group_number: int, font_size: float) -> YGroup:
        """Создает группу Y с учетом размера шрифта"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        
        # Вычисляем адаптивный порог разрыва на основе размера шрифта
        # Для больших шрифтов увеличиваем порог
        adaptive_gap_threshold = font_size * 1.2  # 120% от размера шрифта
        
        # Разделяем слова на строки с адаптивным порогом
        lines = self._split_words_into_lines_font_aware(words, adaptive_gap_threshold)
        
        # Вычисляем центр Y группы
        y_positions = [w.y0 for w in words]
        y_center = sum(y_positions) / len(y_positions)
        
        # Собираем X позиции центров строк
        x_positions = []
        for line in lines:
            if line:
                x_center = (line[0].x0 + line[-1].x1) / 2
                x_positions.append(x_center)
        
        # Создаем объекты ProcessedLine
        line_infos = []
        for i, line in enumerate(lines):
            if line:
                # Сортируем слова в строке с учетом направления
                if direction == 'rtl':
                    sorted_words = sorted(line, key=lambda w: -w.x0)  # RTL: справа налево
                else:
                    sorted_words = sorted(line, key=lambda w: w.x0)   # LTR: слева направо
                
                # Собираем текст с учетом направления слов
                if direction == 'rtl':
                    text = ' '.join(w.text for w in sorted_words)  # RTL: порядок слов инвертирован при сортировке
                else:
                    text = ' '.join(w.text for w in sorted_words)  # LTR: прямой порядок
                
                x0 = min(w.x0 for w in sorted_words)
                x1 = max(w.x1 for w in sorted_words)
                y0 = min(w.y0 for w in sorted_words)
                y1 = max(w.y1 for w in sorted_words)
                
                # Вычисляем средний размер шрифта в строке
                avg_font_size = sum(w.font_size_estimate for w in sorted_words) / len(sorted_words)
                
                line_info = ProcessedLine(
                    words=sorted_words,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text=text,
                    line_number=i,
                    width=x1 - x0,
                    dominant_language=self.language_info['language'],
                    avg_font_size=avg_font_size
                )
                line_infos.append(line_info)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=len(lines),
            x_positions=x_positions
        )
    
    def _split_words_into_lines_font_aware(self, words: List[ProcessedWord], gap_threshold: float) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с адаптивным порогом"""
        if len(words) <= 1:
            return [words]
        
        direction = self.language_info['direction']
        
        # Сортируем слова по X с учетом направления
        if direction == 'rtl':
            sorted_words = sorted(words, key=lambda w: -w.x0)  # RTL: справа налево
        else:
            sorted_words = sorted(words, key=lambda w: w.x0)   # LTR: слева направо
        
        # Находим разрывы между словами
        gaps = []
        for i in range(len(sorted_words) - 1):
            if direction == 'rtl':
                # Для RTL: разрыв между левым краем правого слова и правым краем левого слова
                gap = abs(sorted_words[i].x0 - sorted_words[i + 1].x1)
            else:
                # Для LTR: разрыв между правым краем левого слова и левым краем правого слова
                gap = sorted_words[i + 1].x0 - sorted_words[i].x1
            gaps.append(gap)
        
        if not gaps:
            return [sorted_words]
        
        # Разделяем на строки с адаптивным порогом
        lines = []
        current_line = [sorted_words[0]]
        
        for i in range(len(sorted_words) - 1):
            gap = gaps[i]
            if gap > gap_threshold:
                lines.append(current_line)
                current_line = [sorted_words[i + 1]]
            else:
                current_line.append(sorted_words[i + 1])
        
        lines.append(current_line)
        return lines
    
    def _analyze_with_font_stats(self, y_groups: List[YGroup], font_size: float):
        """ЭТАП 3: Статистика с учетом размера шрифта"""
        print(f"  📊 Анализ {len(y_groups)} групп с учетом шрифта ({font_size:.1f}px):")
        
        # Разделяем группы на 1-колоночные и многоколонные
        single_column_groups = []
        multi_column_groups = []
        
        for group in y_groups:
            if group.column_count == 1:
                single_column_groups.append(group)
            else:
                multi_column_groups.append(group)
        
        print(f"    📄 1-колоночных групп: {len(single_column_groups)}")
        print(f"    📊 Многоколонных групп: {len(multi_column_groups)}")
        
        # Собираем статистику X позиций
        x_position_stats = defaultdict(int)
        x_position_details = defaultdict(list)
        
        for group in multi_column_groups:
            for x_pos in group.x_positions:
                rounded_x = round(x_pos / 5) * 5
                x_position_stats[rounded_x] += 1
                x_position_details[rounded_x].append({
                    'y_center': group.y_center,
                    'column_count': group.column_count,
                    'exact_x': x_pos
                })
        
        # Сортируем по частоте
        sorted_x_positions = sorted(x_position_stats.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n  📈 СТАТИСТИКА X ПОЗИЦИЙ:")
        print(f"    Всего уникальных X позиций: {len(sorted_x_positions)}")
        print(f"    Адаптивный порог разрыва: {font_size * 1.2:.1f} пикселей")
        
        print(f"\n    ТОП-10 X позиций по частоте:")
        for i, (x_pos, frequency) in enumerate(sorted_x_positions[:10]):
            confidence = min(1.0, frequency / 5.0)
            print(f"      {i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}")
        
        # Сохраняем статистику
        self.font_size = font_size
        self.x_position_stats = x_position_stats
        self.x_position_details = x_position_details
        self.sorted_x_positions = sorted_x_positions
    
    def _save_font_aware_analysis(self, y_groups: List[YGroup], font_size: float):
        """Сохраняет результаты анализа с учетом шрифта"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с учетом шрифта
        groups_file = os.path.join(debug_dir, f"{timestamp}_font_aware_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С УЧЕТОМ РАЗМЕРА ШРИФТА\n")
            f.write("="*50 + "\n\n")
            f.write(f"Основной язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Оценка размера шрифта: {font_size:.1f} пикселей\n")
            f.write(f"Адаптивный порог разрыва: {font_size * 1.2:.1f} пикселей\n")
            f.write(f"Всего групп: {len(y_groups)}\n\n")
            
            single_count = sum(1 for g in y_groups if g.column_count == 1)
            multi_count = len(y_groups) - single_count
            
            f.write(f"1-колоночных групп: {single_count}\n")
            f.write(f"Многоколонных групп: {multi_count}\n\n")
            
            for i, group in enumerate(y_groups):
                f.write(f"ГРУППА {i+1}:\n")
                f.write(f"  Y центр: {group.y_center:.1f}\n")
                f.write(f"  Количество колонок: {group.column_count}\n")
                f.write(f"  X позиции: {[f'{x:.1f}' for x in group.x_positions]}\n")
                f.write(f"  Строки ({len(group.lines)}):\n")
                for line in group.lines:
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, ширина={line.width:.1f}, шрифт={line.avg_font_size:.1f}px\n")
                    f.write(f"    Текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Файл анализа с учетом шрифта сохранен:")
        print(f"     📄 Группы с учетом шрифта: {groups_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_font_aware.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = FontAwareRTLAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_font_aware(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с учетом шрифта завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
