#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.4.nikud-improved"
DATE    = "2026-05-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# Конфигурация языков с направлениями текста
LANGUAGE_CONFIGS = {
    'hebrew': {
        'pattern': r'[\u0590-\u05FF]',
        'direction': 'rtl',
        'priority': 1,
        'has_nikud': True  # Иврит может иметь огласовки
    },
    'arabic': {
        'pattern': r'[\u0600-\u06FF]',
        'direction': 'rtl',
        'priority': 2,
        'has_nikud': False
    },
    'english': {
        'pattern': r'[a-zA-Z]',
        'direction': 'ltr',
        'priority': 3,
        'has_nikud': False
    },
    'russian': {
        'pattern': r'[а-яёА-ЯЁ]',
        'direction': 'ltr',
        'priority': 4,
        'has_nikud': False
    }
}

# Диапазоны Unicode для огласовок иврита
NIKUD_RANGES = [
    (0x0591, 0x05C7),  # Hebrew punctuation, niqqud
    (0x05B0, 0x05BD),  # Hebrew vowels
    (0xFB1D, 0xFB4F),  # Alphabetic Presentation Forms
]

def has_nikud(text: str) -> bool:
    """Проверяет, содержит ли текст огласовки"""
    for char in text:
        for start, end in NIKUD_RANGES:
            if start <= ord(char) <= end:
                return True
    return False

@dataclass
class ProcessedWord:
    """Обработанное слово с учетом огласовок"""
    text: str
    original_text: str
    x0: float
    y0: float
    x1: float
    y1: float
    has_nikud: bool

@dataclass
class ProcessedLine:
    """Обработанная строка с учетом огласовок"""
    words: List[ProcessedWord]
    y0: float
    y1: float
    x0: float
    x1: float
    text: str
    line_number: int
    width: float

@dataclass
class YGroup:
    """Группа строк по Y координате"""
    y_center: float
    lines: List[ProcessedLine]
    column_count: int
    x_positions: List[float]

class NikudImprovedAnalyzer:
    """Анализатор с улучшенной обработкой огласовок"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_nikud(self, pdf_path: str) -> bool:
        """Основной метод анализа с учетом огласовок"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_nikud(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_nikud(self, page):
        """Анализ страницы с учетом огласовок"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И ПРОВЕРКА ОГЛАСОВОК")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        
        # Проверяем наличие огласовок
        nikud_words = sum(1 for w in word_texts if has_nikud(w))
        print(f"  🔤 Слов с огласовками: {nikud_words} из {len(word_texts)}")
        
        print("\n" + "="*60)
        print("ШАГ 2: ОБЪЕДИНЕНИЕ СЛОВ С ОГЛАСОВКАМИ")
        print("="*60)
        
        # ЭТАП 1: Объединяем слова с огласовками
        processed_words = self._process_words_with_nikud_merging(words)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК (УМЕНЬШЕННЫЕ ПОРОГИ)")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с уменьшенными порогами
        y_groups = self._form_lines_with_reduced_gaps(processed_words)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА С УЧЕТОМ ОГЛАСОВОК")
        print("="*60)
        
        # ЭТАП 3: Статистика с учетом огласовок
        self._analyze_with_nikud_stats(y_groups)
        
        # Сохраняем результаты
        self._save_nikud_analysis(y_groups)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык и проверяет наличие огласовок"""
        if not word_texts:
            return {'language': 'unknown', 'direction': 'ltr', 'confidence': 0.0}
        
        # Считаем слова для каждого языка
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            count = sum(1 for word in word_texts if re.search(pattern, word))
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
            'has_nikud': lang_config.get('has_nikud', False)
        }
    
    def _process_words_with_nikud_merging(self, raw_words: List[Dict]) -> List[ProcessedWord]:
        """ЭТАП 1: Объединяем слова с огласовками"""
        print(f"  🔤 Обработка {len(raw_words)} слов с объединением огласовок:")
        
        processed_words = []
        direction = self.language_info['direction']
        
        i = 0
        while i < len(raw_words):
            word = raw_words[i]
            original_text = word['text']
            
            # Проверяем, есть ли огласовки
            word_has_nikud = has_nikud(original_text)
            
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
                y1=word.get('bottom', word['top'] + 10),
                has_nikud=word_has_nikud
            )
            processed_words.append(processed_word)
            
            # Показываем первые 10 слов
            if len(processed_words) <= 10:
                nikud_mark = "🔤" if word_has_nikud else "📝"
                print(f"    {len(processed_words):2d}. {original_text:15s} → {processed_text:15s} {nikud_mark} ({word['x0']:6.1f},{word['top']:6.1f})")
            elif len(processed_words) == 11:
                print(f"    ... и еще {len(raw_words) - 10} слов")
            
            i += 1
        
        print(f"  ✅ Обработано слов: {len(processed_words)}")
        print(f"  🔤 С огласовками: {sum(1 for w in processed_words if w.has_nikud)}")
        return processed_words
    
    def _form_lines_with_reduced_gaps(self, words: List[ProcessedWord]) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с уменьшенными порогами"""
        print(f"  📋 Формирование строк с уменьшенными порогами:")
        
        if not words:
            return []
        
        direction = self.language_info['direction']
        has_nikud_support = self.language_info.get('has_nikud', False)
        
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
                    group = self._create_y_group_with_nikud(current_group_words, len(groups))
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_nikud(current_group_words, len(groups))
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        return groups
    
    def _create_y_group_with_nikud(self, words: List[ProcessedWord], group_number: int) -> YGroup:
        """Создает группу Y с учетом огласовок"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        has_nikud_support = self.language_info.get('has_nikud', False)
        
        # Разделяем слова на строки с адаптивными порогами
        lines = self._split_words_into_lines_with_nikud(words)
        
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
                
                line_info = ProcessedLine(
                    words=sorted_words,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text=text,
                    line_number=i,
                    width=x1 - x0
                )
                line_infos.append(line_info)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=len(lines),
            x_positions=x_positions
        )
    
    def _split_words_into_lines_with_nikud(self, words: List[ProcessedWord]) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с учетом огласовок"""
        if len(words) <= 1:
            return [words]
        
        direction = self.language_info['direction']
        has_nikud_support = self.language_info.get('has_nikud', False)
        
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
        
        # Вычисляем порог для разделения с учетом огласовок
        avg_gap = sum(gaps) / len(gaps)
        
        # Уменьшаем порог для языков с огласовками
        if has_nikud_support:
            threshold = avg_gap * 1.5  # Меньший порог для иврита с огласовками
            print(f"    📏 Порог разрыва: {threshold:.1f} (уменьшен для огласовок)")
        else:
            threshold = avg_gap * 2.0  # Стандартный порог
            print(f"    📏 Порог разрыва: {threshold:.1f} (стандартный)")
        
        # Разделяем на строки
        lines = []
        current_line = [sorted_words[0]]
        
        for i in range(len(sorted_words) - 1):
            gap = gaps[i]
            if gap > threshold:
                lines.append(current_line)
                current_line = [sorted_words[i + 1]]
            else:
                current_line.append(sorted_words[i + 1])
        
        lines.append(current_line)
        return lines
    
    def _analyze_with_nikud_stats(self, y_groups: List[YGroup]):
        """ЭТАП 3: Статистика с учетом огласовок"""
        print(f"  📊 Анализ {len(y_groups)} групп с учетом огласовок:")
        
        direction = self.language_info['direction']
        has_nikud_support = self.language_info.get('has_nikud', False)
        
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
        
        # Собираем статистику по огласовкам
        nikud_stats = {
            'total_words': 0,
            'nikud_words': 0,
            'groups_with_nikud': 0
        }
        
        for group in y_groups:
            group_has_nikud = False
            for line in group.lines:
                for word in line.words:
                    nikud_stats['total_words'] += 1
                    if word.has_nikud:
                        nikud_stats['nikud_words'] += 1
                        group_has_nikud = True
            
            if group_has_nikud:
                nikud_stats['groups_with_nikud'] += 1
        
        print(f"    🔤 Статистика огласовок:")
        print(f"      Всего слов: {nikud_stats['total_words']}")
        print(f"      С огласовками: {nikud_stats['nikud_words']}")
        print(f"      Групп с огласовками: {nikud_stats['groups_with_nikud']}")
        print(f"      Процент огласовок: {nikud_stats['nikud_words']/nikud_stats['total_words']*100:.1f}%")
        
        # Сохраняем статистику
        self.nikud_stats = nikud_stats
    
    def _save_nikud_analysis(self, y_groups: List[YGroup]):
        """Сохраняет результаты анализа с учетом огласовок"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с учетом огласовок
        groups_file = os.path.join(debug_dir, f"{timestamp}_nikud_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С УЧЕТОМ ОГЛАСОВОК\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Поддержка огласовок: {self.language_info.get('has_nikud', False)}\n")
            f.write(f"Всего групп: {len(y_groups)}\n\n")
            
            f.write(f"Статистика огласовок:\n")
            f.write(f"  Всего слов: {self.nikud_stats['total_words']}\n")
            f.write(f"  С огласовками: {self.nikud_stats['nikud_words']}\n")
            f.write(f"  Процент: {self.nikud_stats['nikud_words']/self.nikud_stats['total_words']*100:.1f}%\n\n")
            
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
                    nikud_words_in_line = sum(1 for w in line.words if w.has_nikud)
                    nikud_mark = f" 🔤{nikud_words_in_line}" if nikud_words_in_line > 0 else ""
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, ширина={line.width:.1f}{nikud_mark}\n")
                    f.write(f"    Текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Файл анализа с огласовками сохранен:")
        print(f"     📄 Группы с учетом огласовок: {groups_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_nikud_improved.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = NikudImprovedAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_nikud(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с учетом огласовок завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
