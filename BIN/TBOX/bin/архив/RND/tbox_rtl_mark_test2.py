#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.24.rtl-mark-test2"
DATE    = "2026-05-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# Конфигурация языков с направлениями текста
LANGUAGE_CONFIGS = {
    'hebrew': {
        'pattern': r'[\u0590-\u05FF]',
        'direction': 'rtl',
        'priority': 1,
        'typical_font_size': 12.0
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

# Никуд (гласные знаки в иврите)
NIKUD_PATTERN = r'[\u05B0-\u05BD\u05BF-\u05C7]'

def is_punctuation(text: str) -> bool:
    """Проверяет, является ли текст знаком препинания"""
    return bool(re.fullmatch(PUNCTUATION_PATTERNS['universal'], text))

def is_nikud(text: str) -> bool:
    """Проверяет, является ли текст никудом"""
    return bool(re.fullmatch(NIKUD_PATTERN, text))

def is_hebrew_text(text: str) -> bool:
    """Проверяет, содержит ли текст ивритские буквы"""
    return bool(re.search(r'[\u0590-\u05FF]', text))

def add_rtl_mark_for_punctuation(text: str, is_rtl: bool = True) -> str:
    """Добавляет RTL Mark (\u200F) для правильного позиционирования знаков препинания"""
    if not is_rtl:
        return text
    
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        
        # Если это знак препинания
        if is_punctuation(char):
            # Вставляем RTL Mark перед знаком препинания
            result.append('\u200F')
            result.append(char)
        else:
            result.append(char)
        
        i += 1
    
    return ''.join(result)

def has_nikud_in_text(words: List[Dict]) -> bool:
    """Проверяет, есть ли никуд в тексте"""
    for word in words:
        if is_nikud(word['text']):
            return True
    return False

def merge_nikud_with_cells(words: List[Dict]) -> List[Dict]:
    """Объединение никуда с буквами по ячейковой логике"""
    if not words:
        return words
    
    # Проверяем, есть ли никуд в тексте
    if not has_nikud_in_text(words):
        return words
    
    # Сортируем слова по Y, затем по X для обработки
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    
    # Создаем ячейки для каждого слова
    cells = []
    for word in sorted_words:
        cells.append({
            'text': word['text'],
            'x0': word['x0'],
            'top': word['top'],
            'x1': word['x1'],
            'is_nikud': is_nikud(word['text']),
            'original_word': word
        })
    
    # Объединяем отдельно стоящие никуды со следующим символом
    merged_cells = []
    i = 0
    
    while i < len(cells):
        current_cell = cells[i]
        
        if current_cell['is_nikud']:
            # Ищем следующую ячейку (не никуд)
            next_cell = None
            for j in range(i + 1, len(cells)):
                if not cells[j]['is_nikud']:
                    # Проверяем близость по Y координатам
                    if abs(current_cell['top'] - cells[j]['top']) <= 8.0:
                        # Проверяем близость по X координатам
                        if abs(current_cell['x0'] - cells[j]['x0']) <= 25.0:
                            next_cell = cells[j]
                            break
                    else:
                        # Y координаты слишком далеко - прекращаем поиск
                        break
            
            if next_cell:
                # Объединяем никуд со следующим символом
                next_cell['text'] = current_cell['text'] + next_cell['text']
                # Обновляем X координаты
                next_cell['x0'] = min(current_cell['x0'], next_cell['x0'])
                next_cell['x1'] = max(current_cell['x1'], next_cell['x1'])
                # Пропускаем текущую ячейку (никуд)
                i += 1
                continue
            else:
                # Не нашли следующую ячейку - пропускаем никуд
                i += 1
                continue
        else:
            # Обычная ячейка (буква)
            merged_cells.append(current_cell)
            i += 1
    
    # Преобразуем ячейки обратно в слова
    result_words = []
    for cell in merged_cells:
        if cell['text'].strip():  # Убираем пустые ячейки
            result_words.append({
                'text': cell['text'],
                'x0': cell['x0'],
                'top': cell['top'],
                'x1': cell['x1'],
                'bottom': cell['original_word'].get('bottom', cell['top'] + 12)
            })
    
    return result_words

@dataclass
class ProcessedWord:
    """Обработанное слово с тестом RTL Mark 2"""
    text: str
    original_text: str
    x0: float
    y0: float
    x1: float
    y1: float
    language: str
    font_size_estimate: float
    is_punctuation: bool

@dataclass
class ProcessedLine:
    """Обработанная строка с тестом RTL Mark 2"""
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

class RTLMarkTest2Analyzer:
    """Анализатор с тестом RTL Mark 2"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_rtl_mark_test2(self, pdf_path: str) -> bool:
        """Основной метод анализа с тестом RTL Mark 2"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_rtl_mark_test2(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_rtl_mark_test2(self, page):
        """Анализ страницы с тестом RTL Mark 2"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И ТЕСТ RTL MARK 2")
        print("="*60)
        
        # Извлекаем слова
        raw_words = page.extract_words()
        
        # Проверяем наличие никуда
        has_nikud = has_nikud_in_text(raw_words)
        print(f"  🔍 Обнаружен никуд: {'Да' if has_nikud else 'Нет'}")
        
        if has_nikud:
            # Ячейковое объединение никуда с буквами
            merged_words = merge_nikud_with_cells(raw_words)
            print(f"  📊 До объединения: {len(raw_words)} слов")
            print(f"  🔗 После объединения: {len(merged_words)} слов")
            print(f"  📝 Убрано ячеек: {len(raw_words) - len(merged_words)}")
        else:
            # Обрабатываем без объединения
            merged_words = raw_words
            print(f"  📊 Никуд не обнаружен, обрабатываем без объединения: {len(merged_words)} слов")
        
        # Определяем язык
        word_texts = [w['text'] for w in merged_words]
        self.language_info = self._detect_language(word_texts)
        
        # Оцениваем размер шрифта
        font_size_estimate = self._estimate_font_size(merged_words)
        
        print(f"  🎯 Основной язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        print(f"  🔤 Оценка размера шрифта: {font_size_estimate:.1f} пикселей")
        
        print("\n" + "="*60)
        print("ШАГ 2: ОБРАБОТКА С ТЕСТОМ RTL MARK 2")
        print("="*60)
        
        # ЭТАП 1: Обрабатываем слова с тестом RTL Mark 2
        processed_words = self._process_words_with_rtl_mark_test2(merged_words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК С ТЕСТОМ RTL MARK 2")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с тестом RTL Mark 2
        y_groups = self._form_lines_with_rtl_mark_test2(processed_words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА С ТЕСТОМ RTL MARK 2")
        print("="*60)
        
        # ЭТАП 3: Статистика с тестом RTL Mark 2
        self._analyze_with_rtl_mark_test2_stats(y_groups, font_size_estimate)
        
        # Сохраняем результаты
        self._save_rtl_mark_test2_analysis(y_groups, font_size_estimate)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык документа"""
        if not word_texts:
            return {'language': 'unknown', 'direction': 'ltr', 'confidence': 0.0}
        
        # Считаем слова для каждого языка (без учета знаков препинания и никуда)
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            clean_words = [re.sub(PUNCTUATION_PATTERNS['universal'] + '|' + NIKUD_PATTERN, '', w) for w in word_texts]
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
            if height > 0:
                heights.append(height)
        
        if heights:
            avg_height = sum(heights) / len(heights)
            if self.language_info and self.language_info['direction'] == 'rtl':
                return max(avg_height, self.language_info.get('typical_font_size', 12.0))
            else:
                return avg_height
        
        return 12.0
    
    def _process_words_with_rtl_mark_test2(self, raw_words: List[Dict], font_size: float) -> List[ProcessedWord]:
        """ЭТАП 1: Обрабатываем слова с тестом RTL Mark 2"""
        print(f"  🔤 Обработка {len(raw_words)} слов с тестом RTL Mark 2:")
        
        direction = self.language_info['direction']
        processed_words = []
        
        for i, word in enumerate(raw_words):
            original_text = word['text']
            
            # Определяем, является ли слово знаком препинания
            word_is_punctuation = is_punctuation(original_text)
            
            # Добавляем RTL Mark для знаков препинания в RTL тексте
            if self.language_info['language'] == 'hebrew' and direction == 'rtl':
                processed_text = add_rtl_mark_for_punctuation(original_text, is_rtl=True)
            else:
                processed_text = original_text
            
            # Инвертируем порядок букв только для RTL (но не для знаков препинания!)
            if direction == 'rtl' and not word_is_punctuation:
                processed_text = processed_text[::-1]
            
            processed_word = ProcessedWord(
                text=processed_text,
                original_text=original_text,
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word.get('bottom', word['top'] + font_size),
                language=self.language_info['language'],
                font_size_estimate=font_size,
                is_punctuation=word_is_punctuation
            )
            processed_words.append(processed_word)
            
            # Показываем первые 15 слов
            if i < 15:
                mark = "📝" if word_is_punctuation else "🔤"
                if original_text != processed_text:
                    change_mark = f" → {processed_text}"
                else:
                    change_mark = ""
                print(f"    {i+1:2d}. {original_text:15s}{change_mark:20s} {mark} ({word['x0']:6.1f},{word['top']:6.1f})")
            elif i == 15:
                print(f"    ... и еще {len(raw_words) - 15} слов")
        
        print(f"  ✅ Обработано слов: {len(processed_words)}")
        print(f"  📝 Знаков препинания: {sum(1 for w in processed_words if w.is_punctuation)}")
        
        return processed_words
    
    def _form_lines_with_rtl_mark_test2(self, words: List[ProcessedWord], font_size: float) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с тестом RTL Mark 2"""
        print(f"  📋 Формирование строк с тестом RTL Mark 2 ({self.language_info['direction'].upper()}):")
        
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
                    group = self._create_y_group_with_rtl_mark_test2(current_group_words, len(groups), font_size)
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_rtl_mark_test2(current_group_words, len(groups), font_size)
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        return groups
    
    def _create_y_group_with_rtl_mark_test2(self, words: List[ProcessedWord], group_number: int, font_size: float) -> YGroup:
        """Создает группу Y с тестом RTL Mark 2"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        
        # Вычисляем адаптивный порог разрыва
        adaptive_gap_threshold = font_size * 1.2
        
        # Разделяем слова на строки с адаптивным порогом
        lines = self._split_words_into_lines_rtl_mark_test2(words, adaptive_gap_threshold)
        
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
                # Формируем текст с правильным порядком слов
                text = self._assemble_text_with_rtl_mark_test2(line)
                
                x0 = min(w.x0 for w in line)
                x1 = max(w.x1 for w in line)
                y0 = min(w.y0 for w in line)
                y1 = max(w.y1 for w in line)
                
                # Вычисляем средний размер шрифта в строке
                avg_font_size = sum(w.font_size_estimate for w in line) / len(line)
                
                line_info = ProcessedLine(
                    words=line,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text=text.strip(),  # Убираем лишние пробелы по краям
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
    
    def _split_words_into_lines_rtl_mark_test2(self, words: List[ProcessedWord], gap_threshold: float) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с тестом RTL Mark 2"""
        if len(words) <= 1:
            return [words]
        
        direction = self.language_info['direction']
        
        # Сортируем слова по X с учетом направления
        if direction == 'rtl':
            sorted_words = sorted(words, key=lambda w: -w.x0)  # RTL: справа налево
        else:
            sorted_words = sorted(words, key=lambda w: w.x0)   # LTR: слева направо
        
        # Находим разрывы между словами
        lines = []
        current_line = [sorted_words[0]]
        
        for i in range(len(sorted_words) - 1):
            current_word = sorted_words[i]
            next_word = sorted_words[i + 1]
            
            # Вычисляем разрыв
            if direction == 'rtl':
                gap = abs(current_word.x0 - next_word.x1)
            else:
                gap = next_word.x0 - current_word.x1
            
            # Уменьшаем порог для знаков препинания
            effective_threshold = gap_threshold
            if next_word.is_punctuation or current_word.is_punctuation:
                effective_threshold = gap_threshold * 0.5
            
            if gap > effective_threshold:
                lines.append(current_line)
                current_line = [next_word]
            else:
                current_line.append(next_word)
        
        lines.append(current_line)
        return lines
    
    def _assemble_text_with_rtl_mark_test2(self, words: List[ProcessedWord]) -> str:
        """Собирает текст с тестом RTL Mark - ВАРИАНТ 2: '\u200F' + word.text"""
        if not words:
            return ""
        
        direction = self.language_info['direction']
        
        if direction == 'rtl':
            # Для RTL: правильный порядок слов справа налево
            sorted_words = sorted(words, key=lambda w: -w.x0)
            
            # Собираем текст с правильными пробелами
            text_parts = []
            for i, word in enumerate(sorted_words):
                if word.is_punctuation and i > 0:
                    # Если это знак препинания и оно последнее в строке
                    if i == len(sorted_words) - 1:
                        # Финальный знак препинания - добавляем RTL Mark перед
                        text_parts[-1] += '\u200F' + word.text
                    else:
                        # Другие знаки препинания - присоединяем к предыдущему слову
                        text_parts[-1] += word.text
                else:
                    text_parts.append(word.text)
            
            # Соединяем слова через пробелы
            return ' '.join(text_parts)
        else:
            # Для LTR: стандартный порядок слева направо
            sorted_words = sorted(words, key=lambda w: w.x0)
            return ' '.join(w.text for w in sorted_words)
    
    def _analyze_with_rtl_mark_test2_stats(self, y_groups: List[YGroup], font_size: float):
        """ЭТАП 3: Статистика с тестом RTL Mark 2"""
        print(f"  📊 Анализ {len(y_groups)} групп с тестом RTL Mark 2:")
        
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
    
    def _save_rtl_mark_test2_analysis(self, y_groups: List[YGroup], font_size: float):
        """Сохраняет результаты анализа с тестом RTL Mark 2"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с тестом RTL Mark 2
        groups_file = os.path.join(debug_dir, f"{timestamp}_rtl_mark_test2_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С ТЕСТОМ RTL MARK (ВАРИАНТ 2: '\\u200F' + word.text)\n")
            f.write("="*60 + "\n\n")
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
        
        print(f"\n  💾 Файл анализа с тестом RTL Mark 2 сохранен:")
        print(f"     📄 Группы с тестом RTL Mark 2: {groups_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_rtl_mark_test2.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = RTLMarkTest2Analyzer(debug_mode=True)
    success = analyzer.analyze_page_with_rtl_mark_test2(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с тестом RTL Mark 2 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
