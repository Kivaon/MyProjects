#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.28.final-corrected"
DATE    = "2026-05-08"
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

def merge_nikud_with_neighbors(words: List, is_rtl: bool = True) -> List:
    """Объединение слов с никудом с соседними словами при формировании строк"""
    if not words or not is_rtl:
        return words
    
    print(f"    🔍 Объединение слов с никудом с соседями:")
    
    # Сортируем слова по X координате
    sorted_words = sorted(words, key=lambda w: w.x0)
    
    # Находим слова с никудом
    nikud_words = []
    for i, word in enumerate(sorted_words):
        if re.search(NIKUD_PATTERN, word.text):
            nikud_words.append((i, word))
    
    print(f"      📊 Слов с никудом: {len(nikud_words)}")
    
    # Объединяем слова с никудом с соседями
    merged_words = []
    skip_indices = set()
    
    for i, word in enumerate(sorted_words):
        if i in skip_indices:
            continue
        
        # Проверяем, есть ли никуд в слове
        if re.search(NIKUD_PATTERN, word.text):
            print(f"      🔤 Слово с никудом: '{word.text}' (индекс {i})")
            
            # Для RTL проверяем только левого соседа
            left_word = sorted_words[i-1] if i > 0 else None
            
            print(f"        ⬅️  Левый сосед: {left_word.text if left_word else 'None'}")
            
            # Порог для объединения
            merge_threshold = 5.0
            
            # Проверяем левого соседа
            if left_word and i-1 not in skip_indices:
                # Для RTL: конец левого слова должен быть близок к началу текущего
                distance_left = abs(left_word.x0 - word.x1)
                print(f"        📏 Расстояние до левого: {distance_left:.1f} пикселей")
                
                if distance_left <= merge_threshold:
                    print(f"        ✅ Объединяем с левым: '{left_word.text}'")
                    # В RTL левое слово идет после текущего
                    word.text = word.text + left_word.text
                    word.x1 = max(word.x1, left_word.x1)
                    skip_indices.add(i-1)
                    print(f"        🔗 Результат: '{word.text}'")
                    merged_words.append(word)
                else:
                    print(f"        ❌ Расстояние слишком большое для объединения")
                    merged_words.append(word)
            else:
                print(f"        ❌ Нет левого соседа или он уже объединен")
                merged_words.append(word)
        else:
            # Обычное слово - просто добавляем
            merged_words.append(word)
    
    print(f"      📊 Убрано слов: {len(skip_indices)}")
    print(f"      📊 Осталось слов: {len(merged_words)}")
    
    return merged_words

def merge_nikud_with_cells_improved(words: List[Dict]) -> List[Dict]:
    """Улучшенное объединение никуда с буквами по ячейковой логике"""
    if not words:
        return words
    
    # Проверяем, есть ли никуд в тексте
    if not has_nikud_in_text(words):
        return words
    
    print(f"    🔍 Анализ никуда в тексте:")
    
    # Сортируем слова по Y, затем по X для обработки
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    
    # Создаем ячейки для каждого слова
    cells = []
    nikud_count = 0
    for word in sorted_words:
        is_nikud_word = is_nikud(word['text'])
        if is_nikud_word:
            nikud_count += 1
        
        cells.append({
            'text': word['text'],
            'x0': word['x0'],
            'top': word['top'],
            'x1': word['x1'],
            'is_nikud': is_nikud_word,
            'original_word': word
        })
    
    print(f"      📊 Всего слов: {len(cells)}")
    print(f"      🔤 Слов с никудом: {nikud_count}")
    print(f"      🔤 Слов без никуда: {len(cells) - nikud_count}")
    
    # Увеличенные допуски для лучшего объединения
    y_tolerance = 10.0  # Увеличено с 8.0
    x_tolerance = 30.0  # Увеличено с 25.0
    
    print(f"      📏 Допуски: Y={y_tolerance}px, X={x_tolerance}px")
    
    # Объединяем отдельно стоящие никуды со следующим символом
    merged_cells = []
    removed_count = 0
    i = 0
    
    while i < len(cells):
        current_cell = cells[i]
        
        if current_cell['is_nikud']:
            # Ищем следующую ячейку (не никуд)
            next_cell = None
            for j in range(i + 1, len(cells)):
                if not cells[j]['is_nikud']:
                    # Проверяем близость по Y координатам
                    y_diff = abs(current_cell['top'] - cells[j]['top'])
                    if y_diff <= y_tolerance:
                        # Проверяем близость по X координатам
                        x_diff = abs(current_cell['x0'] - cells[j]['x0'])
                        if x_diff <= x_tolerance:
                            next_cell = cells[j]
                            print(f"      🔗 Объединение: '{current_cell['text']}' + '{cells[j]['text']}' (Y={y_diff:.1f}, X={x_diff:.1f})")
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
                removed_count += 1
                i += 1
                continue
            else:
                # Не нашли следующую ячейку - пропускаем никуд
                print(f"      ❌ Пропущен никуд: '{current_cell['text']}' (не найдено ближайшее слово)")
                i += 1
                continue
        else:
            # Обычная ячейка (буква)
            merged_cells.append(current_cell)
            i += 1
    
    print(f"      📊 Убрано ячеек: {removed_count}")
    
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
    """Обработанное слово с улучшенными параметрами"""
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
    """Обработанная строка с улучшенными параметрами"""
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

class FinalImprovedAnalyzer:
    """Финальный улучшенный анализатор"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_final_improved(self, pdf_path: str) -> bool:
        """Основной метод анализа с финальными улучшениями"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_final_improved(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_final_improved(self, page):
        """Анализ страницы с финальными улучшениями"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И ФИНАЛЬНЫЕ УЛУЧШЕНИЯ")
        print("="*60)
        
        # Извлекаем слова
        raw_words = page.extract_words()
        
        # Проверяем наличие никуда
        has_nikud = has_nikud_in_text(raw_words)
        print(f"  🔍 Обнаружен никуд: {'Да' if has_nikud else 'Нет'}")
        
        if has_nikud:
            # Улучшенное ячейковое объединение никуда с буквами
            merged_words = merge_nikud_with_cells_improved(raw_words)
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
        print("ШАГ 2: ОБРАБОТКА С ФИНАЛЬНЫМИ УЛУЧШЕНИЯМИ")
        print("="*60)
        
        # ЭТАП 1: Обрабатываем слова с финальными улучшениями
        processed_words = self._process_words_with_final_improved(merged_words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК С ФИНАЛЬНЫМИ УЛУЧШЕНИЯМИ")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с финальными улучшениями
        y_groups = self._form_lines_with_final_improved(processed_words, font_size_estimate)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА С ФИНАЛЬНЫМИ УЛУЧШЕНИЯМИ")
        print("="*60)
        
        # ЭТАП 3: Статистика с финальными улучшениями
        self._analyze_with_final_improved_stats(y_groups, font_size_estimate)
        
        # Сохраняем результаты
        self._save_final_improved_analysis(y_groups, font_size_estimate)
    
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
    
    def _process_words_with_final_improved(self, raw_words: List[Dict], font_size: float) -> List[ProcessedWord]:
        """ЭТАП 1: Обрабатываем слова с финальными улучшениями"""
        print(f"  🔤 Обработка {len(raw_words)} слов с финальными улучшениями:")
        
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
    
    def _form_lines_with_final_improved(self, words: List[ProcessedWord], font_size: float) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с финальными улучшениями"""
        print(f"  📋 Формирование строк с финальными улучшениями ({self.language_info['direction'].upper()}):")
        
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
                    group = self._create_y_group_with_final_improved(current_group_words, len(groups), font_size)
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_final_improved(current_group_words, len(groups), font_size)
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        return groups
    
    def _create_y_group_with_final_improved(self, words: List[ProcessedWord], group_number: int, font_size: float) -> YGroup:
        """Создает группу Y с финальными улучшениями"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        
        # УМЕНЬШЕННЫЙ АДАПТИВНЫЙ ПОРОГ РАЗРЫВА - 14.0 пикселей вместо 14.4
        adaptive_gap_threshold = 14.0  # Уменьшено с font_size * 1.2
        
        # Разделяем слова на строки с адаптивным порогом
        lines = self._split_words_into_lines_final_improved(words, adaptive_gap_threshold)
        
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
                text = self._assemble_text_with_final_improved(line)
                
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
    
    def _split_words_into_lines_final_improved(self, words: List[ProcessedWord], gap_threshold: float) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с финальными улучшениями"""
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
                # Объединяем слова с никудом с соседями в строке
                if direction == 'rtl':
                    current_line = merge_nikud_with_neighbors(current_line, is_rtl=True)
                lines.append(current_line)
                current_line = [next_word]
            else:
                current_line.append(next_word)
        
        # Объединяем слова с никудом в последней строке
        if direction == 'rtl':
            current_line = merge_nikud_with_neighbors(current_line, is_rtl=True)
        lines.append(current_line)
        return lines
    
    def _assemble_text_with_final_improved(self, words: List[ProcessedWord]) -> str:
        """Собирает текст с финальными улучшениями - ВАРИАНТ 1: word.text + '\u200F'"""
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
                        # Финальный знак препинания - добавляем RTL Mark после
                        text_parts[-1] += word.text + '\u200F'
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
    
    def _merge_words_with_same_x(self, processed_groups: List[YGroup]) -> Dict:
        """Объединение слов с одинаковыми X координатами"""
        total_merged = 0
        total_lines_processed = 0
        
        print(f"  🔍 Проверка слов с одинаковыми X координатами:")
        
        # Реализуем объединение перекрывающихся слов
        for group in processed_groups:
            for line in group.lines:
                total_lines_processed += 1
                words = line.words
                
                if len(words) < 2:
                    continue
                
                # НЕ сортируем слова - используем естественный порядок
                sorted_words = words
                
                # Находим перекрывающиеся слова
                merged_words = []
                skip_indices = set()
                
                for i, word in enumerate(sorted_words):
                    if i in skip_indices:
                        continue
                    
                    # Ищем перекрывающиеся слова - каскадное объединение
                    current_merged = [word]
                    
                    # Проверяем все последующие слова для каскадного объединения
                    for j in range(i + 1, len(sorted_words)):
                        if j in skip_indices:
                            continue
                        
                        next_word = sorted_words[j]
                        # Проверяем совпадение границ: x0 ПОСЛЕДНЕГО в current_merged == x1 следующего
                        last_word = current_merged[-1]
                        gap = abs(last_word.x0 - next_word.x1)
                        if gap <= 0.1:  # Совпадающие или очень близкие границы
                            current_merged.append(next_word)
                            skip_indices.add(j)
                            print(f"      🔗 КАСКАД: добавлено слово[{j}] '{next_word.text}', всего {len(current_merged)} слов")
                        else:
                            # НЕ ДЕЛАЕМ BREAK - продолжаем проверять другие слова
                            continue
                    
                    if len(current_merged) > 1:
                        # Объединяем слова
                        merged_text = ''.join(w.text for w in current_merged)
                        merged_x0 = min(w.x0 for w in current_merged)
                        merged_x1 = max(w.x1 for w in current_merged)
                        
                        merged_word = ProcessedWord(
                            text=merged_text,
                            original_text=merged_text,
                            x0=merged_x0,
                            y0=word.y0,
                            x1=merged_x1,
                            y1=word.y1,
                            language=word.language,
                            font_size_estimate=word.font_size_estimate,
                            is_punctuation=word.is_punctuation
                        )
                        
                        merged_words.append(merged_word)
                        total_merged += len(current_merged) - 1
                        
                        if len(current_merged) > 2:
                            print(f"    ✅ Объединено {len(current_merged)} слов: '{merged_text}'")
                    else:
                        merged_words.append(word)
                
                # Обновляем слова в строке
                line.words = merged_words
        
        print(f"  📊 Статистика объединения:")
        print(f"    Обработано строк: {total_lines_processed}")
        print(f"    Объединено слов: {total_merged}")
        
        return {
            'total_lines': total_lines_processed,
            'total_merged': total_merged
        }
    
    def _analyze_with_final_improved_stats(self, y_groups: List[YGroup], font_size: float):
        """ЭТАП 3: Статистика с финальными улучшениями"""
        print(f"  📊 Анализ {len(y_groups)} групп с финальными улучшениями:")
        
        # ШАГ 5: Объединение слов с одинаковыми X координатами
        print("\n" + "="*60)
        print("ШАГ 5: ОБЪЕДИНЕНИЕ СЛОВ С ОДИНАКОВЫМИ X")
        print("="*60)
        
        merge_stats = self._merge_words_with_same_x(y_groups)
        
        print(f"  📊 Статистика объединения:")
        print(f"    Обработано строк: {merge_stats['total_lines']}")
        print(f"    Объединено слов: {merge_stats['total_merged']}")
        
        print("\n" + "="*60)
        print("ШАГ 6: СТАТИСТИКА С ФИНАЛЬНЫМИ УЛУЧШЕНИЯМИ")
        print("="*60)
        
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
        print(f"    Адаптивный порог разрыва: 14.0 пикселей (уменьшен)")
        
        print(f"\n    ТОП-10 X позиций по частоте:")
        for i, (x_pos, frequency) in enumerate(sorted_x_positions[:10]):
            confidence = min(1.0, frequency / 5.0)
            print(f"      {i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}")
        
        # Сохраняем статистику
        self.font_size = font_size
        self.x_position_stats = x_position_stats
        self.x_position_details = x_position_details
        self.sorted_x_positions = sorted_x_positions
    
    def _save_final_improved_analysis(self, y_groups: List[YGroup], font_size: float):
        """Сохраняет результаты анализа с финальными улучшениями"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с финальными улучшениями (отладочный файл)
        groups_file = os.path.join(debug_dir, f"{timestamp}_final_corrected_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С ФИНАЛЬНЫМИ УЛУЧШЕНИЯМИ\n")
            f.write("="*60 + "\n\n")
            f.write(f"Основной язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Оценка размера шрифта: {font_size:.1f} пикселей\n")
            f.write(f"Адаптивный порог разрыва: 14.0 пикселей (уменьшен с 14.4)\n")
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
        
        print(f"\n  💾 Файл анализа с финальными улучшениями сохранен:")
        print(f"     📄 Группы с финальными улучшениями: {groups_file}")
        
        # Сохраняем таблицу в TXT формате
        table_file = os.path.join(debug_dir, f"{timestamp}_final_corrected_table.txt")
        with open(table_file, 'w', encoding='utf-8') as f:
            # Заголовок таблицы
            f.write("ТАБЛИЦА АНАЛИЗА ГРУПП\n")
            f.write("="*120 + "\n")
            f.write(f"{'Группа':<8} {'Y_центр':<10} {'Колонки':<8} {'X_позиции':<20} {'Строка':<8} {'X0':<8} {'X1':<8} {'Ширина':<8} {'Шрифт':<8} {'Текст'}\n")
            f.write("-"*120 + "\n")
            
            for i, group in enumerate(y_groups):
                x_positions_str = "|".join([f"{x:.1f}" for x in group.x_positions])
                for line in group.lines:
                    f.write(f"{i+1:<8} {group.y_center:<10.1f} {group.column_count:<8} {x_positions_str:<20} {line.line_number:<8} {line.x0:<8.1f} {line.x1:<8.1f} {line.width:<8.1f} {line.avg_font_size:<8.1f} {line.text}\n")
        
        print(f"     📊 Таблица TXT: {table_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_final_improved.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = FinalImprovedAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_final_improved(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с финальными улучшениями завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
