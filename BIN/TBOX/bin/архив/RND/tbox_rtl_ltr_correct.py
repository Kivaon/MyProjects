#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.3.rtl-ltr-correct"
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
class ProcessedWord:
    """Обработанное слово с учетом направления"""
    text: str
    original_text: str
    x0: float
    y0: float
    x1: float
    y1: float

@dataclass
class ProcessedLine:
    """Обработанная строка с учетом направления"""
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
    """Группа строк по Y координате с учетом направления"""
    y_center: float
    lines: List[ProcessedLine]
    column_count: int
    x_positions: List[float]

class RTLLTRAnalyzer:
    """Анализатор с учетом RTL/LTR на каждом этапе"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_direction(self, pdf_path: str) -> bool:
        """Основной метод анализа с учетом направления текста"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_direction(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_direction(self, page):
        """Анализ страницы с учетом RTL/LTR"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И НАПРАВЛЕНИЯ")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        
        print("\n" + "="*60)
        print("ШАГ 2: ФОРМИРОВАНИЕ СЛОВ (УЧЕТ НАПРАВЛЕНИЯ БУКВ)")
        print("="*60)
        
        # ЭТАП 1: Формируем слова с учетом направления букв
        processed_words = self._process_words_with_letter_direction(words)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК (УЧЕТ НАПРАВЛЕНИЯ СЛОВ)")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с учетом направления слов
        y_groups = self._form_lines_with_word_direction(processed_words)
        
        print("\n" + "="*60)
        print("ШАГ 4: ФОРМИРОВАНИЕ ПОРЯДКА СТРОК (УЧЕТ НАПРАВЛЕНИЯ СТРОК)")
        print("="*60)
        
        # ЭТАП 3: Формируем порядок строк с учетом направления
        ordered_groups = self._order_lines_with_line_direction(y_groups)
        
        print("\n" + "="*60)
        print("ШАГ 5: СТАТИСТИКА ПОЗИЦИЙ КОЛОНОК (УЧЕТ НАПРАВЛЕНИЯ КОЛОНОК)")
        print("="*60)
        
        # ЭТАП 4: Статистика с учетом направления колонок
        self._analyze_column_positions_with_direction(ordered_groups)
        
        # Сохраняем результаты
        self._save_direction_analysis(ordered_groups)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык и направление"""
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
            'confidence': confidence
        }
    
    def _process_words_with_letter_direction(self, raw_words: List[Dict]) -> List[ProcessedWord]:
        """ЭТАП 1: Формируем слова с учетом направления букв"""
        print(f"  🔤 Обработка {len(raw_words)} слов с учетом направления букв:")
        
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
                y1=word.get('bottom', word['top'] + 10)
            )
            processed_words.append(processed_word)
            
            # Показываем первые 10 слов
            if i < 10:
                print(f"    {i+1:2d}. {original_text:12s} → {processed_text:12s}  ({word['x0']:6.1f},{word['top']:6.1f})")
            elif i == 10:
                print(f"    ... и еще {len(raw_words) - 10} слов")
        
        print(f"  ✅ Обработано слов: {len(processed_words)} (направление букв: {direction.upper()})")
        return processed_words
    
    def _form_lines_with_word_direction(self, words: List[ProcessedWord]) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с учетом направления слов"""
        print(f"  📋 Формирование строк с учетом направления слов:")
        
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
                    group = self._create_y_group_with_direction(current_group_words, len(groups))
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_direction(current_group_words, len(groups))
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)} (направление слов: {direction.upper()})")
        return groups
    
    def _create_y_group_with_direction(self, words: List[ProcessedWord], group_number: int) -> YGroup:
        """Создает группу Y с учетом направления слов"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        
        # Разделяем слова на строки по X разрывам
        lines = self._split_words_into_lines_with_direction(words)
        
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
    
    def _split_words_into_lines_with_direction(self, words: List[ProcessedWord]) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с учетом направления"""
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
        
        # Вычисляем порог для разделения
        avg_gap = sum(gaps) / len(gaps)
        threshold = avg_gap * 2.0
        
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
    
    def _order_lines_with_line_direction(self, y_groups: List[YGroup]) -> List[YGroup]:
        """ЭТАП 3: Формируем порядок строк с учетом направления"""
        print(f"  📊 Упорядочивание групп с учетом направления строк:")
        
        direction = self.language_info['direction']
        
        # Сортируем группы по Y с учетом направления строк
        if direction == 'rtl':
            # Для RTL: сверху вниз (Y возрастание)
            sorted_groups = sorted(y_groups, key=lambda g: g.y_center)
        else:
            # Для LTR: сверху вниз (Y возрастание)  
            sorted_groups = sorted(y_groups, key=lambda g: g.y_center)
        
        print(f"  ✅ Упорядочено групп: {len(sorted_groups)} (направление строк: {direction.upper()})")
        
        # Показываем первые 5 групп
        for i, group in enumerate(sorted_groups[:5]):
            print(f"    Группа {i+1}: Y={group.y_center:.1f}, колонок={group.column_count}, строк={len(group.lines)}")
        
        if len(sorted_groups) > 5:
            print(f"    ... и еще {len(sorted_groups) - 5} групп")
        
        return sorted_groups
    
    def _analyze_column_positions_with_direction(self, y_groups: List[YGroup]):
        """ЭТАП 4: Анализ позиций колонок с учетом направления"""
        print(f"  📈 Анализ позиций колонок с учетом направления:")
        
        direction = self.language_info['direction']
        
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
        
        # Собираем статистику X позиций для многоколонных групп
        x_position_stats = defaultdict(int)
        x_position_details = defaultdict(list)
        
        for group in multi_column_groups:
            for x_pos in group.x_positions:
                # Округляем до ближайших 5 пикселей для группировки
                rounded_x = round(x_pos / 5) * 5
                x_position_stats[rounded_x] += 1
                x_position_details[rounded_x].append({
                    'y_center': group.y_center,
                    'column_count': group.column_count,
                    'exact_x': x_pos
                })
        
        # Сортируем по частоте
        sorted_x_positions = sorted(x_position_stats.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n  📈 СТАТИСТИКА X ПОЗИЦИЙ (направление колонок: {direction.upper()}):")
        print(f"    Всего уникальных X позиций: {len(sorted_x_positions)}")
        
        print(f"\n    ТОП-10 X позиций по частоте:")
        for i, (x_pos, frequency) in enumerate(sorted_x_positions[:10]):
            confidence = min(1.0, frequency / 5.0)
            print(f"      {i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}")
        
        # Сохраняем статистику
        self.x_position_stats = x_position_stats
        self.x_position_details = x_position_details
        self.sorted_x_positions = sorted_x_positions
    
    def _save_direction_analysis(self, y_groups: List[YGroup]):
        """Сохраняет результаты анализа с учетом направления"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с учетом направления
        groups_file = os.path.join(debug_dir, f"{timestamp}_rtl_ltr_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С УЧЕТОМ RTL/LTR\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
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
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, ширина={line.width:.1f}\n")
                    f.write(f"    Текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        # Сохраняем статистику X позиций
        stats_file = os.path.join(debug_dir, f"{timestamp}_rtl_ltr_stats.txt")
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА X ПОЗИЦИЙ С УЧЕТОМ RTL/LTR\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Всего уникальных X позиций: {len(self.sorted_x_positions)}\n\n")
            
            f.write("ТОП X ПОЗИЦИЙ ПО ЧАСТОТЕ:\n")
            f.write("-"*50 + "\n")
            for i, (x_pos, frequency) in enumerate(self.sorted_x_positions):
                confidence = min(1.0, frequency / 5.0)
                f.write(f"{i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}\n")
                
                # Добавляем детали для топ-10
                if i < 10:
                    details = self.x_position_details[x_pos]
                    f.write(f"   Детали ({len(details)} упоминаний):\n")
                    for detail in details[:5]:
                        f.write(f"     → Y={detail['y_center']:.1f}, колонок={detail['column_count']}, точный X={detail['exact_x']:.1f}\n")
                    f.write("\n")
        
        print(f"\n  💾 Файлы анализа сохранены:")
        print(f"     📄 Группы с учетом RTL/LTR: {groups_file}")
        print(f"     📄 Статистика X с учетом RTL/LTR: {stats_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_rtl_ltr_correct.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = RTLLTRAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_direction(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с учетом RTL/LTR завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
