#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import pdfplumber
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Конфигурация директорий вывода
OUTPUT_CONFIG = {
    'debug_dir': "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug",
    'txt_raw': "/Users/kivaonmac/Documents/AI_Lab/02_TXT/txt_raw",
    'md_dir': "/Users/kivaonmac/Documents/AI_Lab/02_TXT/md"
}

# Создаем директории если они не существуют
for dir_path in OUTPUT_CONFIG.values():
    os.makedirs(dir_path, exist_ok=True)

from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.29.final-corrected"
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

def _detect_word_language(self, word_text: str) -> str:
    """Определяет направление отдельного слова с поддержкой множества языков"""
    # Иврит
    if re.search(r'[\u0590-\u05FF]', word_text):
        return 'rtl'
    # Арабский
    elif re.search(r'[\u0600-\u06FF]', word_text):
        return 'rtl'
    # Латиница, цифры, email, телефон, URL
    elif re.match(r'^[\d\w\.\-\+\/@\:]+$', word_text):
        return 'ltr'
    else:
        return 'unknown'  # Неопределенный язык

def _reverse_single_word(self, text: str) -> str:
    """Переворачивает буквы в одном слове с сохранением никуда"""
    groups = []
    i = 0
    while i < len(text):
        char = text[i]
        if '\u05D0' <= char <= '\u05EA':
            group = char
            i += 1
            while i < len(text) and '\u0590' <= text[i] <= '\u05CF':
                group += str(text[i])
                i += 1
            groups.append(group)
        else:
            groups.append(char)
            i += 1
    return ''.join(groups[::-1])

def has_nikud_in_text(words: List[Dict]) -> bool:
    """Проверяет, есть ли никуд в тексте"""
    for word in words:
        if is_nikud(word['text']):
            return True
    return False

# СТАРАЯ ФУНКЦИЯ (закомментирована для тестирования нового подхода)
# def reverse_rtl_words(words: List[Dict], only_with_nikud: bool = False) -> List[Dict]:
#     """Изменяет порядок букв в словах для RTL текста
#     
#     Args:
#         words: Список слов для переворота
#         only_with_nikud: Если True, переворачивает только слова с огласовками
#     """
#     reversed_words = []
#     for word in words:
#         reversed_word = word.copy()
#         
#         # Проверяем наличие огласовок если нужно
#         if only_with_nikud:
#             has_nikud = any('\u0590' <= char <= '\u05CF' for char in word['text'])
#             if has_nikud:
#                 reversed_word['text'] = word['text'][::-1]  # Реверс только слов с огласовками
#         else:
#             reversed_word['text'] = word['text'][::-1]  # Реверс всех слов
#         
#         reversed_words.append(reversed_word)
#     return reversed_words

def reverse_rtl_words(words: List[Dict]) -> List[Dict]:
    """Изменяет порядок букв в словах для RTL текста с сохранением связи буква+огласовки
    
    Новый подход: буква переносится вместе с близлежащим никудом (1 или 2 кода)
    Пример:
        было:  никуд32 никуд31 буква3 никуд2 буква2 буква1
        стало: буква1 никуд2 буква2 никуд32 никуд31 буква3
    """
    reversed_words = []
    for word in words:
        reversed_word = word.copy()
        text = word['text']
        
        # Группируем букву с огласовками, которые идут после неё
        groups = []
        i = 0
        while i < len(text):
            char = text[i]
            
            # Если это буква иврита
            if '\u05D0' <= char <= '\u05EA':
                # Собираем букву и все огласовки после неё
                group = char
                i += 1
                while i < len(text) and '\u0590' <= text[i] <= '\u05CF':
                    group += str(text[i])
                    i += 1
                groups.append(group)
            else:
                # Если это не буква (например, огласовка в начале слова или пунктуация)
                groups.append(char)
                i += 1
        
        # Реверсируем группы
        reversed_groups = groups[::-1]
        reversed_word['text'] = ''.join(reversed_groups)
        
        reversed_words.append(reversed_word)
    return reversed_words

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
                print(f"        📏 Расстояние до левого: {distance_left:.1f} pt")
                
                if distance_left <= merge_threshold:
                    print(f"        ✅ Объединяем с левым: '{left_word.text}'")
                    # В RTL левое слово идет после текущего
                    word.text = str(word.text) + str(left_word.text)
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

@dataclass
class ProcessedWord:
    """Обработанное слово с исправленными параметрами"""
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
    """Обработанная строка с исправленными параметрами"""
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

class FinalCorrectedAnalyzer:
    """Финальный исправленный анализатор"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
        self.global_block_counter = 0  # Глобальный счетчик блоков для сквозной нумерации

    def _detect_word_language(self, word_text: str) -> str:
        """Определяет направление отдельного слова с поддержкой множества языков"""
        # Иврит
        if re.search(r'[\u0590-\u05FF]', word_text):
            return 'rtl'
        # Арабский
        elif re.search(r'[\u0600-\u06FF]', word_text):
            return 'rtl'
        # Латиница, цифры, email, телефон, URL
        elif re.match(r'^[\d\w\.\-\+\/@\:]+$', word_text):
            return 'ltr'
        else:
            return 'unknown'  # Неопределенный язык

    def _reverse_single_word(self, text: str) -> str:
        """Переворачивает буквы в одном слове с сохранением никуда"""
        groups = []
        i = 0
        while i < len(text):
            char = text[i]
            if '\u05D0' <= char <= '\u05EA':
                group = char
                i += 1
                while i < len(text) and '\u0590' <= text[i] <= '\u05CF':
                    group += str(text[i])
                    i += 1
                groups.append(group)
            else:
                groups.append(char)
                i += 1
        return ''.join(groups[::-1])
    
    def analyze_page_with_final_corrected(self, pdf_path: str) -> bool:
        """Основной метод анализа с финальными исправлениями"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")

                # Анализируем все страницы
                all_page_text = []
                timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
                debug_dir = OUTPUT_CONFIG['debug_dir']
                
                # Формируем имя файла из оригинального PDF
                original_name = os.path.basename(pdf_path)
                clean_base_name = original_name.replace('.pdf', '').replace('.PDF', '')

                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"\n{'='*60}")
                    print(f"СТРАНИЦА {page_num}/{len(pdf.pages)}")
                    print('='*60)
                    page_text = self._analyze_page_with_final_corrected(page, page_num, timestamp, debug_dir, clean_base_name)
                    all_page_text.append(page_text)

                # Сохраняем общий текст всех страниц (TXT и MD)
                full_text_file = os.path.join(OUTPUT_CONFIG['txt_raw'], f"{timestamp}_{clean_base_name}_raw.txt")
                full_md_file = os.path.join(OUTPUT_CONFIG['md_dir'], f"{timestamp}_{clean_base_name}.md")
                
                # TXT формат
                with open(full_text_file, 'w', encoding='utf-8') as f:
                    f.write("ПОЛНЫЙ ТЕКСТ ВСЕХ СТРАНИЦ\n")
                    f.write("="*80 + "\n\n")
                    for page_text in all_page_text:
                        f.write(page_text + "\n\n")
                
                # MD формат
                with open(full_md_file, 'w', encoding='utf-8') as f:
                    f.write("# ПОЛНЫЙ ТЕКСТ ВСЕХ СТРАНИЦ\n\n")
                    for page_num, page_text in enumerate(all_page_text, 1):
                        f.write(f"## СТРАНИЦА {page_num}\n\n")
                        f.write("```\n")
                        f.write(page_text)
                        f.write("\n```\n\n")

                print(f"\n  💾 Полный текст сохранен:")
                print(f"     📄 TXT: {full_text_file}")
                print(f"     📄 MD: {full_md_file}")
                return True

        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_final_corrected(self, page, page_num: int, timestamp: str, debug_dir: str, clean_base_name: str) -> str:
        """Анализ страницы с финальными исправлениями, возвращает текст страницы"""
        print("\n" + "="*60)
        print("ШАГ 1: ИЗВЛЕЧЕНИЕ СЛОВ ИЗ PDF")
        print("="*60)
        
        # ШАГ 1: Извлекаем слова из PDF
        raw_words = page.extract_words()
        print(f"  📊 Извлечено слов: {len(raw_words)}")
        
        print("\n" + "="*60)
        print("ШАГ 2: ОПРЕДЕЛЕНИЕ ЯЗЫКА")
        print("="*60)
        
        # ШАГ 2: Определяем язык текста
        word_texts = [w['text'] for w in raw_words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Основной язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        
        print("\n" + "="*60)
        print("ШАГ 3: ИСПРАВЛЕНИЕ ПОРЯДКА БУКВ ДЛЯ RTL")
        print("="*60)
        
        # ШАГ 3: Если RTL, изменяем порядок букв в словах
        if self.language_info['direction'] == 'rtl':
            print(f"  🔄 RTL текст detected - изменяем порядок букв в словах")
            
            # ДЕБАГ: Собираем слова с огласовками для сравнения
            nikud_words_before = []
            for i, word in enumerate(raw_words):
                text = word['text']
                has_nikud = any('\u0590' <= char <= '\u05CF' for char in text)
                if has_nikud:
                    nikud_words_before.append((i, word, text))
            
            print(f"  📊 Всего найдено слов с огласовками: {len(nikud_words_before)}")
            
            #raw_words = reverse_rtl_words(raw_words)
            
            # ДЕБАГ: Таблица сравнения ДО и ПОСЛЕ переворота с кодами
            print(f"  🔍 ДЕБАГ: Таблица сравнения ДО и ПОСЛЕ переворота:")
            print(f"  {'ID':<5} {'ДО (слово)':<12} {'ПОСЛЕ (слово)':<12} {'ИЗМЕНЕНО':<8}")
            print(f"  {'-'*5} {'-'*12} {'-'*12} {'-'*8}")
            
            # Сохраняем таблицу в файл
            import os
            from datetime import datetime
            debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
            table_file = os.path.join(debug_dir, f"{timestamp}_nikud_reversal_table.txt")
            
            with open(table_file, 'w', encoding='utf-8') as f:
                f.write("ТАБЛИЦА СРАВНЕНИЯ СЛОВ С ОГЛАСОВКАМИ ДО И ПОСЛЕ ПЕРЕВОРОТА\n")
                f.write("="*80 + "\n")
                f.write("Формат: ДО = слово из PDF (исходное), ПОСЛЕ = после применения reverse_rtl_words\n")
                f.write("Направление: RTL (справа налево) для иврита\n")
                f.write("="*80 + "\n")
                f.write(f"{'ID':<5} {'ДО (слово)':<15} {'ПОСЛЕ (слово)':<15} {'ИЗМЕНЕНО':<8}\n")
                f.write(f"{'-'*5} {'-'*15} {'-'*15} {'-'*8}\n")
                
                for original_idx, original_word, before_text in nikud_words_before:
                    if original_idx < len(raw_words):
                        after_text = raw_words[original_idx]['text']
                        changed = "ДА" if before_text != after_text else "НЕТ"
                        
                        # Вывод в консоль
                        print(f"  {original_idx:<5} {before_text:<15} {after_text:<15} {changed:<8}")
                        
                        # Вывод кодов ДО с символами
                        before_codes = ' '.join([f"U+{ord(c):04X}({c})" for c in before_text])
                        print(f"    ДО коды (RTL):   {before_codes}")
                        
                        # Вывод кодов ПОСЛЕ с символами
                        after_codes = ' '.join([f"U+{ord(c):04X}({c})" for c in after_text])
                        print(f"    ПОСЛЕ коды (RTL): {after_codes}")
                        print()
                        
                        # Запись в файл
                        f.write(f"{original_idx:<5} {before_text:<15} {after_text:<15} {changed:<8}\n")
                        f.write(f"    ДО коды (RTL):   {before_codes}\n")
                        f.write(f"    ПОСЛЕ коды (RTL): {after_codes}\n")
                        f.write("\n")
            
            print(f"  📁 Таблица сохранена в файл: {table_file}")
        else:
            print(f"  ✅ LTR текст - порядок букв не изменяем")
        
        print("\n" + "="*60)
        print("ШАГ 4: СОЗДАНИЕ ГРУПП ПО Y КООРДИНАТАМ")
        print("="*60)
        
        # ШАГ 4: Создаем группы по Y координатам
        y_groups = self._create_y_groups(raw_words, use_bottom=True)
        print(f"  📋 Создано групп по Y (bottom): {len(y_groups)}")
        
        print("\n" + "="*60)
        print("ШАГ 5: ФОРМИРОВАНИЕ СТРОК")
        print("="*60)
        
        # ШАГ 5: Формируем строки
        processed_groups = []
        for group in y_groups:
            processed_group = self._create_y_group_without_nikud_merge(group)
            processed_groups.append(processed_group)
        
        print("\n" + "="*60)
        print("ШАГ 6: ОБЪЕДИНЕНИЕ СЛОВ С ОДИНАКОВЫМИ X")
        print("="*60)
        
        # ШАГ 6: Объединение слов с одинаковыми X
        merge_stats = self._merge_words_with_same_x(processed_groups)
        
        print("\n" + "="*60)
        print("ШАГ 7: ОБРАБОТКА ЗНАКОВ ПРЕПИНАНИЯ")
        print("="*60)
        
        # ШАГ 7: Обрабатываем знаки препинания
        for group in processed_groups:
            for line in group.lines:
                line.text = self._process_punctuation_in_line(line.text, self.language_info['direction'] == 'rtl')
        
        print("  ✅ Знаки препинания обработаны")
        
        print("\n" + "="*60)
        print("ШАГ 8: СБОРКА ТЕКСТА")
        print("="*60)
        
        # ШАГ 8: Собираем финальный текст
        for group in processed_groups:
            for line in group.lines:
                line.text = self._assemble_text_from_words(line.words, self.language_info['direction'] == 'rtl')
        
        print("  ✅ Текст собран")
        
        print("\n" + "="*60)
        print("ШАГ 9: СТАТИСТИКА И СОХРАНЕНИЕ")
        print("="*60)
        
        # ШАГ 9: Статистика и сохранение
        page_text = self._analyze_and_save_results(processed_groups, timestamp, debug_dir, page_num, clean_base_name)
        
        return page_text
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык текста с учетом смешанных языков"""
        language_counts = {}
        for text in word_texts:
            word_lang = self._detect_word_language(text)
            language_counts[word_lang] = language_counts.get(word_lang, 0) + 1
        
        # Определяем основной язык
        if language_counts.get('rtl', 0) > language_counts.get('ltr', 0):
            best_language = 'hebrew'  # Преимущество RTL при равенстве
        elif language_counts.get('ltr', 0) > language_counts.get('rtl', 0):
            best_language = 'english'
        else:
            # Равное количество - выбираем по другим критериям
            best_language = self.language_info.get('language', 'english')
        
        lang_config = LANGUAGE_CONFIGS.get(best_language, LANGUAGE_CONFIGS['english'])
        
        return {
            'language': best_language,
            'direction': lang_config['direction'],
            'confidence': max(language_counts.values()),
            'typical_font_size': lang_config.get('typical_font_size', 12.0)
        }
    
    def _create_y_groups(self, words: List[Dict], use_bottom: bool = False) -> List[Dict]:
        """Создает группы слов по Y координатам с поддержкой смешанных языков"""
        if not words:
            return []
        
        print(f"  🔍 _create_y_groups вызван с {len(words)} слов, use_bottom={use_bottom}")
        
        # Обрабатываем каждое слово - проверяем язык и переворачиваем если нужно
        processed_words = []
        reversed_count = 0
        kept_count = 0
        rtl_count = 0
        ltr_count = 0
        unknown_count = 0
        
        for word in words:
            processed_word = word.copy()
            word_language = self._detect_word_language(word['text'])
            
            # Определяем направление для слова
            if word_language == 'rtl':
                rtl_count += 1
                # RTL слова всегда переворачиваем
                original_text = word['text']
                processed_word['text'] = self._reverse_single_word(word['text'])
                if original_text != processed_word['text']:
                    reversed_count += 1
                    print(f"  🔄 RTL переворот: '{original_text}' → '{processed_word['text']}'")
            elif word_language == 'ltr':
                ltr_count += 1
                # LTR слова оставляем как есть
                processed_word['text'] = word['text']
                kept_count += 1
            else:
                unknown_count += 1
                # Неопределенные слова - по направлению документа
                if self.language_info['direction'] == 'rtl':
                    original_text = word['text']
                    processed_word['text'] = self._reverse_single_word(word['text'])
                    if original_text != processed_word['text']:
                        reversed_count += 1
                        print(f"  🔄 UNKNOWN переворот (RTL doc): '{original_text}' → '{processed_word['text']}'")
                else:
                    processed_word['text'] = word['text']
                    kept_count += 1
            
            processed_words.append(processed_word)
        
        print(f"  📊 Статистика языков: RTL={rtl_count}, LTR={ltr_count}, UNKNOWN={unknown_count}")
        print(f"  📊 Статистика переворота: {reversed_count} слов переворачено, {kept_count} слов оставлено")
        
        # Сортируем слова по Y (top или bottom), затем по X
        y_key = 'bottom' if use_bottom else 'top'
        sorted_words = sorted(processed_words, key=lambda w: (w[y_key], w['x0']))
        
        groups = []
        current_group_words = []
        current_y = None
        y_tolerance = 5
        
        for word in sorted_words:
            word_y = word.get('bottom', word['top']) if use_bottom else word['top']
            
            if current_y is None:
                current_y = word_y
                current_group_words = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                current_group_words.append(word)
            else:
                if current_group_words:
                    y_center = sum(w.get('bottom', w['top']) if use_bottom else w['top'] for w in current_group_words) / len(current_group_words)
                    groups.append({
                        'words': current_group_words,
                        'y_center': y_center
                    })
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            y_center = sum(w.get('bottom', w['top']) if use_bottom else w['top'] for w in current_group_words) / len(current_group_words)
            groups.append({
                'words': current_group_words,
                'y_center': y_center
            })
        
        print(f"  📋 Создано групп по Y ({y_key}): {len(groups)}")
        return groups
    
    def _create_y_group_with_nikud_merge(self, group: Dict) -> YGroup:
        """Создает Y-группу с объединением никуда"""
        words = group['words']
        y_center = group['y_center']
        
        # Преобразуем слова в ProcessedWord объекты
        processed_words = []
        for word in words:
            processed_word = ProcessedWord(
                text=word['text'],
                original_text=word['text'],
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word.get('bottom', word['top'] + 12),
                language=self.language_info['language'],
                font_size_estimate=12.0,
                is_punctuation=is_punctuation(word['text'])
            )
            processed_words.append(processed_word)
        
        # Объединяем слова с никудом, если язык = иврит
        if self.language_info['language'] == 'hebrew':
            merged_words = merge_nikud_with_neighbors(processed_words, is_rtl=True)
        else:
            merged_words = processed_words
        
        # Разделяем слова на строки с адаптивным порогом
        adaptive_gap_threshold = 14.0  # Уменьшенный порог
        
        # Сортируем слова по X с учетом направления
        direction = self.language_info['direction']
        if direction == 'rtl':
            sorted_words = sorted(merged_words, key=lambda w: -w.x0)  # RTL: справа налево
        else:
            sorted_words = sorted(merged_words, key=lambda w: w.x0)   # LTR: слева направо
        
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
            effective_threshold = adaptive_gap_threshold
            if is_punctuation(next_word.original_text) or is_punctuation(current_word.original_text):
                effective_threshold = adaptive_gap_threshold * 0.5
            
            if gap > effective_threshold:
                lines.append(current_line)
                current_line = [next_word]
            else:
                current_line.append(next_word)
        
        lines.append(current_line)
        
        # Создаем объекты ProcessedLine
        line_infos = []
        for i, line in enumerate(lines):
            if line:
                x0 = min(w.x0 for w in line)
                x1 = max(w.x1 for w in line)
                y0 = min(w.y0 for w in line)
                y1 = max(w.y1 for w in line)
                
                line_info = ProcessedLine(
                    words=line,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text='',  # Заполнится позже
                    line_number=i,
                    width=x1 - x0,
                    dominant_language=self.language_info['language'],
                    avg_font_size=sum(w.font_size_estimate for w in line) / len(line)
                )
                line_infos.append(line_info)
        
        # Собираем X позиции центров строк
        x_positions = []
        for line in line_infos:
            x_center = (line.x0 + line.x1) / 2
            x_positions.append(x_center)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=len(lines),
            x_positions=x_positions
        )

    def _create_y_group_without_nikud_merge(self, group: Dict) -> YGroup:
        """Создает Y-группу без объединения никуда (объединение уже сделано в ШАГЕ 3)"""
        words = group['words']
        y_center = group['y_center']
        
        # Преобразуем слова в ProcessedWord объекты
        processed_words = []
        for word in words:
            processed_word = ProcessedWord(
                text=word['text'],
                original_text=word['text'],
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word.get('bottom', word['top'] + 12),
                language=self.language_info['language'],
                font_size_estimate=12.0,
                is_punctuation=is_punctuation(word['text'])
            )
            processed_words.append(processed_word)
        
        # Без объединения никуда - уже сделано в ШАГЕ 3
        merged_words = processed_words
        
        # Разделяем слова на строки с адаптивным порогом
        adaptive_gap_threshold = 14.0  # Уменьшенный порог
        
        # Сортируем слова по X с учетом направления
        direction = self.language_info['direction']
        if direction == 'rtl':
            sorted_words = sorted(merged_words, key=lambda w: -w.x0)  # RTL: справа налево
        else:
            sorted_words = sorted(merged_words, key=lambda w: w.x0)   # LTR: слева направо
        
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
            effective_threshold = adaptive_gap_threshold
            if is_punctuation(next_word.original_text) or is_punctuation(current_word.original_text):
                effective_threshold = adaptive_gap_threshold * 0.5
            
            if gap > effective_threshold:
                lines.append(current_line)
                current_line = [next_word]
            else:
                current_line.append(next_word)
        
        lines.append(current_line)
        
        # Создаем объекты ProcessedLine
        line_infos = []
        for i, line in enumerate(lines):
            if line:
                x0 = min(w.x0 for w in line)
                x1 = max(w.x1 for w in line)
                y0 = min(w.y0 for w in line)
                y1 = max(w.y1 for w in line)
                
                line_info = ProcessedLine(
                    words=line,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text='',  # Заполнится позже
                    line_number=i,
                    width=x1 - x0,
                    dominant_language=self.language_info['language'],
                    avg_font_size=sum(w.font_size_estimate for w in line) / len(line)
                )
                line_infos.append(line_info)
        
        # Собираем X позиции центров строк
        x_positions = []
        for line in line_infos:
            x_center = (line.x0 + line.x1) / 2
            x_positions.append(x_center)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=len(lines),
            x_positions=x_positions
        )

    def _merge_words_with_same_x(self, processed_groups: List[YGroup]) -> Dict:
        """Объединение слов с одинаковыми X координатами"""
        total_merged = 0
        total_lines_processed = 0
        
        print(f"  🔍 Проверка слов с одинаковыми X координатами:")
        
        # Выводим координаты слов из групп 5 и 6 с проверкой совпадений
        print(f"\n  📋 ГРУППА 5 - детальный анализ слов:")
        if len(processed_groups) > 5:
            group_5 = processed_groups[5]  # Группа 5 (индекс 5)
            for line_idx, line in enumerate(group_5.lines):
                print(f"    Строка {line_idx}:")
                for word_idx, word in enumerate(line.words):
                    # Детальный анализ символов
                    for char_idx, char in enumerate(word.text):
                            unicode_code = ord(char)
                            char_type = "буква" if '\u05D0' <= char <= '\u05EA' else "огласовка" if '\u0590' <= char <= '\u05CF' else "пунктуация" if char in '.,;:?!-"' else "пробел/другое"
                            print(f"        [{char_idx}] '{char}' (U+{unicode_code:04X}) - {char_type}")
                    # Проверяем совпадения с соседними словами
                    if word_idx < len(line.words) - 1:
                        next_word = line.words[word_idx + 1]
                        if abs(word.x0 - next_word.x1) < 0.1:
                            print(f"        🔥 СОВПАДЕНИЕ: word[{word_idx}].x0={float(word.x0):.1f} == word[{word_idx+1}].x1={float(next_word.x1):.1f}")
        
        print(f"\n  📋 ГРУППА 6 - детальный анализ слов:")
        if len(processed_groups) > 6:
            group_6 = processed_groups[6]  # Группа 6 (индекс 6)
            for line_idx, line in enumerate(group_6.lines):
                print(f"    Строка {line_idx}:")
                for word_idx, word in enumerate(line.words):
                    print(f"      Слово {word_idx}: '{word.text}' x0={float(word.x0):.1f}, x1={word.x1:.1f}")
                    # Детальный анализ символов
                    for char_idx, char in enumerate(word.text):
                        unicode_code = ord(char)
                        char_type = "буква" if '\u05D0' <= char <= '\u05EA' else "огласовка" if '\u0590' <= char <= '\u05CF' else "пунктуация" if char in '.,;:?!-"' else "пробел/другое"
                        print(f"        [{char_idx}] '{char}' (U+{unicode_code:04X}) - {char_type}")
                    # Проверяем совпадения с соседними словами
                    if word_idx < len(line.words) - 1:
                        next_word = line.words[word_idx + 1]
                        if abs(word.x0 - next_word.x1) < 0.1:
                            word_x0 = getattr(word, 'x0', 0.0)
                            next_word_x1 = getattr(next_word, 'x1', 0.0)
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
                        print(f"      DEBUG: word[{i}] '{last_word.text}' x0={float(last_word.x0):.1f} vs next_word[{j}] '{next_word.text}' x1={float(next_word.x1):.1f} gap={gap:.1f}")
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
                            is_punctuation=bool(word.is_punctuation)
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

    def _process_punctuation_in_line(self, text: str, is_rtl: bool) -> str:
        """Обрабатывает знаки препинания в строке"""
        if not is_rtl:
            return text
        
        # Добавляем RTL Mark для финальных знаков препинания
        result = []
        chars = list(text)
        
        for i, char in enumerate(chars):
            if is_punctuation(char):
                # Если это последний знак препинания в строке
                if i == len(chars) - 1:
                    result.append('\u200F' + char)  # Вариант 1
                else:
                    result.append(char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _assemble_text_from_words(self, words: List[ProcessedWord], is_rtl: bool) -> str:
        """Собирает текст из списка слов"""
        if not words:
            return ""
        
        if is_rtl:
            # Для RTL: правильный порядок слов справа налево
            sorted_words = sorted(words, key=lambda w: -w.x0)
            
            # Собираем текст с правильными пробелами
            text_parts = []
            for i, word in enumerate(sorted_words):
                if word.is_punctuation and i > 0 and text_parts and isinstance(text_parts[-1], str):
                    if i == len(sorted_words) - 1:
                        text_parts[-1] += '\u200F' + str(word.text)
                    else:
                        text_parts[-1] += str(word.text)
                else:
                    text_parts.append(str(word.text))
            
            return ' '.join(str(part) for part in text_parts)
        else:
            # Для LTR: стандартный порядок слева направо
            sorted_words = sorted(words, key=lambda w: w.x0)
            return ' '.join(w.text for w in sorted_words)
    
    def _analyze_and_save_results(self, y_groups: List[YGroup], timestamp: str, debug_dir: str, page_num: int, clean_base_name: str):
        """Анализирует и сохраняет результаты"""
        print(f"  📊 Анализ {len(y_groups)} групп:")
        
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
        print(f"    Адаптивный порог разрыва: 14.0 pt")
        print(f"    Объединение никуда: встроено в формирование строк")
        
        print(f"\n    ТОП-10 X позиций по частоте:")
        for i, (x_pos, frequency) in enumerate(sorted_x_positions[:10]):
            confidence = min(1.0, frequency / 5.0)
            print(f"      {i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}")

        # Сохраняем результаты
        groups_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_final_corrected_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С ФИНАЛЬНЫМИ ИСПРАВЛЕНИЯМИ\n")
            f.write("="*60 + "\n\n")
            f.write(f"Основной язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Адаптивный порог разрыва: 14.0 pt\n")
            f.write(f"Объединение никуда: встроено в формирование строк\n")
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
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, ширина={line.width:.1f}, шрифт={line.avg_font_size:.1f}pt\n")
                    f.write(f"    Текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Файл анализа сохранен:")
        print(f"     📄 Группы: {groups_file}")
        
        # Сохраняем таблицу всех строк с сортировкой по y1
        self._save_sorted_lines_table(y_groups, timestamp, debug_dir, page_num)

        # Сохраняем статистику по x0 и x1
        self._save_x_coordinates_statistics(y_groups, timestamp, debug_dir, page_num)
        
        # Сканируем y-координаты
        self._scan_y_coordinates(y_groups, timestamp, debug_dir, page_num)
        
        # Создаем вертикальные блоки из строк
        return self._create_vertical_blocks(y_groups, timestamp, debug_dir, page_num, clean_base_name)
    
    def _save_sorted_lines_table(self, y_groups: List[YGroup], timestamp: str, debug_dir: str, page_num: int):
        """Сохраняет таблицу всех строк с сортировкой по y1"""
        # Собираем все строки из всех групп
        all_lines = []
        for group in y_groups:
            for line in group.lines:
                all_lines.append(line)
        
        # Сортировка: сначала по y1 (сверху вниз), затем по x0 в зависимости от RTL|LTR
        is_rtl = self.language_info['direction'] == 'rtl'
        
        if is_rtl:
            # RTL: сортировка по y1 (возрастание), затем по x0 (убывание)
            sorted_lines = sorted(all_lines, key=lambda l: (l.y1, -l.x0))
        else:
            # LTR: сортировка по y1 (возрастание), затем по x0 (возрастание)
            sorted_lines = sorted(all_lines, key=lambda l: (l.y1, l.x0))
        
        # Сохраняем в файл
        table_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_sorted_lines_table.txt")
        
        with open(table_file, 'w', encoding='utf-8') as f:
            f.write("ТАБЛИЦА СТРОК (СОРТИРОВКА ПО Y1)\n")
            f.write("="*80 + "\n")
            f.write(f"Направление текста: {self.language_info['direction'].upper()}\n")
            f.write(f"Всего строк: {len(sorted_lines)}\n")
            f.write(f"Сортировка: по y1 (сверху вниз), затем по x0 ({'справа налево' if is_rtl else 'слева направо'})\n")
            f.write("="*80 + "\n\n")
            
            # Заголовок таблицы
            f.write(f"{'№':<5} {'y1':<10} {'x0':<10} {'x1':<10} {'центр x':<12} {'текст':<30}\n")
            f.write("-"*80 + "\n")
            
            # Строки таблицы
            for i, line in enumerate(sorted_lines):
                center_x = (line.x0 + line.x1) / 2
                # Обрезаем текст если слишком длинный
                text_display = str(str(line.text))[:27] + "..." if len(str(line.text)) > 30 else str(line.text)
                f.write(f"{i+1:<5} {line.y1:<10.1f} {line.x0:<10.1f} {line.x1:<10.1f} {center_x:<12.1f} {text_display:<30}\n")
        
        print(f"     📊 Таблица строк: {table_file}")
    
    def _save_x_coordinates_statistics(self, y_groups: List[YGroup], timestamp: str, debug_dir: str, page_num: int):
        """Сохраняет статистику по x0 и x1 координатам"""
        # Собираем все строки из всех групп
        all_lines = []
        for group in y_groups:
            for line in group.lines:
                all_lines.append(line)
        
        # Собираем x0 и x1 значения
        x0_values = [line.x0 for line in all_lines]
        x1_values = [line.x1 for line in all_lines]
        
        # Округляем значения до целых для группировки
        x0_rounded = [round(x) for x in x0_values]
        x1_rounded = [round(x) for x in x1_values]
        
        # Статистика по частоте
        from collections import Counter
        x0_counter = Counter(x0_rounded)
        x1_counter = Counter(x1_rounded)
        
        # Находим повторяющиеся значения (более 1 раза)
        x0_repeated = {k: v for k, v in x0_counter.items() if v > 1}
        x1_repeated = {k: v for k, v in x1_counter.items() if v > 1}
        
        # Находим значения рядом (разница менее 5 pt)
        x0_sorted = sorted(x0_rounded)
        x1_sorted = sorted(x1_rounded)
        
        x0_nearby = []
        for i in range(len(x0_sorted) - 1):
            if x0_sorted[i+1] - x0_sorted[i] < 5 and x0_sorted[i+1] != x0_sorted[i]:
                x0_nearby.append((x0_sorted[i], x0_sorted[i+1], x0_sorted[i+1] - x0_sorted[i]))
        
        x1_nearby = []
        for i in range(len(x1_sorted) - 1):
            if x1_sorted[i+1] - x1_sorted[i] < 5 and x1_sorted[i+1] != x1_sorted[i]:
                x1_nearby.append((x1_sorted[i], x1_sorted[i+1], x1_sorted[i+1] - x1_sorted[i]))
        
        # Сохраняем статистику
        stats_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_x_coordinates_statistics.txt")
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА ПО X КООРДИНАТАМ\n")
            f.write("="*80 + "\n")
            f.write(f"Всего строк: {len(all_lines)}\n")
            f.write(f"Направление текста: {self.language_info['direction'].upper()}\n")
            f.write("="*80 + "\n\n")
            
            # Статистика по x0
            f.write("СТАТИСТИКА ПО X0 (левая граница)\n")
            f.write("-"*80 + "\n")
            f.write(f"Всего уникальных значений: {len(x0_counter)}\n")
            f.write(f"Минимум: {min(x0_values):.1f}\n")
            f.write(f"Максимум: {max(x0_values):.1f}\n")
            f.write(f"Среднее: {sum(x0_values)/len(x0_values):.1f}\n\n")
            
            f.write("ТОП-20 наиболее частых значений x0:\n")
            for x0, count in x0_counter.most_common(20):
                f.write(f"  X0={x0:7.1f} - частота: {count:2d}\n")
            
            f.write(f"\nПовторяющиеся значения x0 (более 1 раза): {len(x0_repeated)}\n")
            for x0, count in sorted(x0_repeated.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  X0={x0:7.1f} - частота: {count:2d}\n")
            
            f.write(f"\nЗначения x0 рядом (разница < 5pt): {len(x0_nearby)}\n")
            for x0_a, x0_b, diff in x0_nearby[:20]:
                f.write(f"  X0={x0_a:7.1f} и X0={x0_b:7.1f} - разница: {diff:.1f}pt\n")
            
            f.write("\n" + "="*80 + "\n\n")
            
            # Статистика по x1
            f.write("СТАТИСТИКА ПО X1 (правая граница)\n")
            f.write("-"*80 + "\n")
            f.write(f"Всего уникальных значений: {len(x1_counter)}\n")
            f.write(f"Минимум: {min(x1_values):.1f}\n")
            f.write(f"Максимум: {max(x1_values):.1f}\n")
            f.write(f"Среднее: {sum(x1_values)/len(x1_values):.1f}\n\n")
            
            f.write("ТОП-20 наиболее частых значений x1:\n")
            for x1, count in x1_counter.most_common(20):
                f.write(f"  X1={x1:7.1f} - частота: {count:2d}\n")
            
            f.write(f"\nПовторяющиеся значения x1 (более 1 раза): {len(x1_repeated)}\n")
            for x1, count in sorted(x1_repeated.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  X1={x1:7.1f} - частота: {count:2d}\n")
            
            f.write(f"\nЗначения x1 рядом (разница < 5pt): {len(x1_nearby)}\n")
            for x1_a, x1_b, diff in x1_nearby[:20]:
                f.write(f"  X1={x1_a:7.1f} и X1={x1_b:7.1f} - разница: {diff:.1f}pt\n")
            
            f.write("\n" + "="*80 + "\n\n")
            
            # Кластеризация значений
            f.write("КЛАСТЕРИЗАЦИЯ ЗНАЧЕНИЙ (группировка по 5 pt)\n")
            f.write("-"*80 + "\n")
            
            # Кластеризация x0
            x0_clusters = defaultdict(int)
            for x0 in x0_rounded:
                cluster = round(x0 / 5) * 5
                x0_clusters[cluster] += 1
            
            f.write("Кластеры x0 (шаг 5pt):\n")
            for cluster in sorted(x0_clusters.keys()):
                f.write(f"  Кластер {cluster:7.1f}-{cluster+5:7.1f}: {x0_clusters[cluster]:2d} значений\n")
            
            f.write("\n")
            
            # Кластеризация x1
            x1_clusters = defaultdict(int)
            for x1 in x1_rounded:
                cluster = round(x1 / 5) * 5
                x1_clusters[cluster] += 1
            
            f.write("Кластеры x1 (шаг 5pt):\n")
            for cluster in sorted(x1_clusters.keys()):
                f.write(f"  Кластер {cluster:7.1f}-{cluster+5:7.1f}: {x1_clusters[cluster]:2d} значений\n")
        
        print(f"     📊 Статистика X: {stats_file}")
    
    def _scan_y_coordinates(self, y_groups: List[YGroup], timestamp: str, debug_dir: str, page_num: int):
        """Сканирует y-координаты и определяет количество строк для каждого y"""
        # Собираем все строки из всех групп
        all_lines = []
        for group in y_groups:
            for line in group.lines:
                all_lines.append(line)
        
        if not all_lines:
            print("     ⚠️ Нет строк для сканирования по y")
            return
        
        print(f"  📊 Сканирование по y:")
        print(f"    Всего строк: {len(all_lines)}")
        
        # Создаем массив для подсчета строк по y (0-1000)
        y_line_counts = [0] * 1001
        
        # Алгоритм: перебор по строкам и заполнение диапазона y
        for line_idx, line in enumerate(all_lines):
            y_start = int(line.y0)
            y_end = int(line.y1)
            # Для каждого y в диапазоне строки увеличиваем счетчик
            for y in range(y_start+1, y_end):
                if 0 <= y <= 1000:  # Проверка границ массива
                    y_line_counts[y] += 1
        
        # Сохраняем результаты
        y_scan_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_y_scan.txt")
        
        with open(y_scan_file, 'w', encoding='utf-8') as f:
            # Добавляем отладочную информацию о координатах строк
            f.write("ОТЛАДОЧНАЯ ИНФОРМАЦИЯ - КООРДИНАТЫ СТРОК\n")
            f.write("-"*80 + "\n")
            f.write("Индекс | y0 | y1 | Текст\n")
            f.write("-"*80 + "\n")
            for line_idx, line in enumerate(all_lines):
                text_preview = str(line.text)[:40] + "..." if len(str(line.text)) > 40 else str(line.text)
                f.write(f"{line_idx:5d} | {line.y0:5.1f} | {line.y1:5.1f} | {text_preview}\n")
            f.write("\n" + "="*80 + "\n\n")
            f.write("СКАНИРОВАНИЕ ПО Y КОРДИНАТАМ (шаг 1 pt)\n")
            f.write("="*80 + "\n")
            f.write(f"Всего строк: {len(all_lines)}\n")
            f.write("="*80 + "\n\n")
            
            f.write("Формат: y | количество строк\n")
            f.write("-"*80 + "\n")
            
            for y in range(0, 1001):  # Сканирование с шагом 1 от 0 до 1000
                count = y_line_counts[y]
                if count > 0:  # Показываем только y со строками
                    f.write(f"{y:4d} | {count:3d}\n")
            
            # Статистика
            f.write("\n" + "="*80 + "\n")
            f.write("СТАТИСТИКА\n")
            f.write("="*80 + "\n")
            
            non_zero_counts = [count for count in y_line_counts if count > 0]
            if non_zero_counts:
                f.write(f"Максимальное количество строк на одном y: {max(non_zero_counts)}\n")
                #f.write(f"Минимальное количество строк на одном y: {min(non_zero_counts)}\n")
                #f.write(f"Среднее количество строк: {sum(non_zero_counts)/len(non_zero_counts):.2f}\n")
                
                # Y с максимальным количеством строк
                max_count = max(non_zero_counts)
                max_ys = [i for i, count in enumerate(y_line_counts) if count == max_count]
                f.write(f"\nY с максимальным количеством строк ({max_count}): {len(max_ys)} значений\n")
                f.write(f"Y: {max_ys[:20]}\n")  # Показываем первые 20
        
        print(f"     📊 Сканирование по y: {y_scan_file}")
    
    def _create_vertical_blocks(self, y_groups: List[YGroup], timestamp: str, debug_dir: str, page_num: int, clean_base_name: str) -> str:
        """Создает вертикальные блоки из строк"""
        # Собираем все строки из всех групп
        all_lines = []
        for group in y_groups:
            for line in group.lines:
                all_lines.append(line)
        
        # Сортируем строки по y1 (сверху вниз), затем по x0 в зависимости от RTL|LTR
        is_rtl = self.language_info['direction'] == 'rtl'
        
        if is_rtl:
            sorted_lines = sorted(all_lines, key=lambda l: (l.y1, -l.x0))
        else:
            sorted_lines = sorted(all_lines, key=lambda l: (l.y1, l.x0))
        
        # Вычисляем среднюю высоту строки
        line_heights = [l.y1 - l.y0 for l in sorted_lines]
        avg_height = sum(line_heights) / len(line_heights) if line_heights else 12.0
        max_y_distance = avg_height * 1.5  # Расстояние не больше высоты 1.5 строки
        
        print(f"\n  📊 Создание вертикальных блоков:")
        print(f"    Средняя высота строки: {avg_height:.1f}pt")
        print(f"    Максимальное расстояние по y: {max_y_distance:.1f}pt")
        print(f"    Порог перекрытия: 70%")
        
        # Создаем блоки
        blocks = []
        used_lines = set()
        debug_log = []
        
        for i, current_line in enumerate(sorted_lines):
            if i in used_lines:
                continue
            
            # Создаем новый блок
            block = [current_line]
            used_lines.add(i)
            
            # Инициализируем координаты блока
            block_x0 = current_line.x0
            block_x1 = current_line.x1
            block_y0 = current_line.y0
            block_y1 = current_line.y1
            
            debug_log.append(f"\nБЛОК {len(blocks)+1}: начинаем со строки {i+1}: y0={current_line.y0:.1f}, y1={current_line.y1:.1f}, x0={current_line.x0:.1f}, x1={current_line.x1:.1f}")
            debug_log.append(f"  Текст: {str(current_line.text)[:50]}...")
            
            # Ищем ближайшие строки для добавления в блок
            while True:
                best_match = None
                best_match_index = -1
                best_overlap = 0
                best_y_distance = float('inf')
                candidates_checked = 0
                
                # Ищем следующую строку, которая еще не использована
                for j, candidate_line in enumerate(sorted_lines):
                    if j in used_lines:
                        continue
                    
                    candidates_checked += 1
                    
                    # Вычисляем расстояние по y от нижней границы блока
                    y_distance = abs(candidate_line.y0 - block_y1)
                    
                    # Проверяем ограничение по расстоянию
                    if y_distance > max_y_distance:
                        continue
                    
                    # Вычисляем перекрытие по x с блоком
                    x_overlap_start = max(block_x0, candidate_line.x0)
                    x_overlap_end = min(block_x1, candidate_line.x1)
                    
                    if x_overlap_start >= x_overlap_end:
                        # Нет перекрытия
                        continue
                    
                    # Ширина перекрытия
                    overlap_width = x_overlap_end - x_overlap_start
                    
                    # Ширина меньшей строки
                    block_width = block_x1 - block_x0
                    candidate_width = candidate_line.x1 - candidate_line.x0
                    min_width = min(block_width, candidate_width)
                    
                    # Перекрытие в процентах
                    overlap_percent = (overlap_width / min_width) * 100
                    
                    # Проверяем порог перекрытия
                    if overlap_percent > 70:
                        # Это кандидат для добавления
                        # Выбираем ближайшую по y
                        if y_distance < best_y_distance:
                            best_overlap = overlap_percent
                            best_y_distance = y_distance
                            best_match = candidate_line
                            best_match_index = j
                            debug_log.append(f"  ✓ Кандидат {j+1}: y_distance={y_distance:.1f}pt, overlap={overlap_percent:.1f}% - ЛУЧШИЙ")
                    else:
                        debug_log.append(f"  ✗ Кандидат {j+1}: y_distance={y_distance:.1f}pt, overlap={overlap_percent:.1f}% - ОТКЛОНЕН (низкое перекрытие)")
                
                debug_log.append(f"  Проверено кандидатов: {candidates_checked}")
                
                if best_match is not None:
                    # Добавляем лучшую строку в блок
                    block.append(best_match)
                    used_lines.add(best_match_index)
                    current_line = best_match  # Продолжаем с этой строкой
                    
                    # Расширяем координаты блока
                    block_x0 = min(block_x0, best_match.x0)
                    block_x1 = max(block_x1, best_match.x1)
                    block_y0 = min(block_y0, best_match.y0)
                    block_y1 = max(block_y1, best_match.y1)
                    
                    debug_log.append(f"  → Добавлена строка {best_match_index+1} с перекрытием {best_overlap:.1f}%, y_distance={best_y_distance:.1f}pt")
                    debug_log.append(f"     Блок: x0={block_x0:.1f}, x1={block_x1:.1f}, y0={block_y0:.1f}, y1={block_y1:.1f}")
                else:
                    # Нет подходящих строк - блок завершен
                    debug_log.append(f"  → Нет подходящих кандидатов, блок завершен")
                    break

            blocks.append(block)

        print(f"  📊 Создано блоков: {len(blocks)}")

        # Оценка структуры листа
        self._analyze_page_structure(blocks, timestamp, debug_dir, page_num)

        # Сбор параграфов и заголовков внутри блоков
        self._analyze_block_structure(blocks, avg_height, timestamp, debug_dir, page_num)

        # Сбор итогового текста страницы
        page_text = self._assemble_page_text(blocks, timestamp, debug_dir, page_num, clean_base_name)

        # Сохраняем результаты блоков
        blocks_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_vertical_blocks.txt")
        
        with open(blocks_file, 'w', encoding='utf-8') as f:
            f.write("ВЕРТИКАЛЬНЫЕ БЛОКИ ИЗ СТРОК\n")
            f.write("="*80 + "\n")
            f.write(f"Всего строк: {len(sorted_lines)}\n")
            f.write(f"Всего блоков: {len(blocks)}\n")
            f.write(f"Средняя высота строки: {avg_height:.1f}pt\n")
            f.write(f"Максимальное расстояние по y: {max_y_distance:.1f}pt\n")
            f.write(f"Порог перекрытия: 70%\n")
            f.write("="*80 + "\n\n")
            
            for i, block in enumerate(blocks):
                f.write(f"БЛОК {i+1} ({len(block)} строк):\n")
                f.write("-"*80 + "\n")
                
                for j, line in enumerate(block):
                    f.write(f"  Строка {j+1}: y0={line.y0:.1f}, y1={line.y1:.1f}, x0={line.x0:.1f}, x1={line.x1:.1f}\n")
                    f.write(f"    Текст: {str(line.text)}\n")
                
                f.write("\n")
        
        print(f"     📊 Блоки: {blocks_file}")
        
        # Сохраняем отладочный лог
        debug_log_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_vertical_blocks_debug.txt")
        
        with open(debug_log_file, 'w', encoding='utf-8') as f:
            f.write("ОТЛАДОЧНЫЙ ЛОГ СОЗДАНИЯ ВЕРТИКАЛЬНЫХ БЛОКОВ\n")
            f.write("="*80 + "\n")
            f.write(f"Всего строк: {len(sorted_lines)}\n")
            f.write(f"Средняя высота строки: {avg_height:.1f}pt\n")
            f.write(f"Максимальное расстояние по y: {max_y_distance:.1f}pt\n")
            f.write(f"Порог перекрытия: 70%\n")
            f.write("="*80 + "\n")
            
            for line in debug_log:
                f.write(line + "\n")
        
        print(f"     📊 Отладочный лог: {debug_log_file}")

        return page_text

    def _analyze_page_structure(self, blocks: List[List], timestamp: str, debug_dir: str, page_num: int):
        """Оценивает структуру листа на основе расположения блоков"""
        # Вычисляем координаты каждого блока
        block_coords = []
        for i, block in enumerate(blocks):
            if not block:
                continue
            
            block_x0 = min(line.x0 for line in block)
            block_x1 = max(line.x1 for line in block)
            block_y0 = min(line.y0 for line in block)
            block_y1 = max(line.y1 for line in block)
            
            block_coords.append({
                'index': i,
                'x0': block_x0,
                'x1': block_x1,
                'y0': block_y0,
                'y1': block_y1,
                'lines_count': len(block)
            })
        
        # Сортируем блоки по y0 (сверху вниз)
        block_coords.sort(key=lambda b: b['y0'])
        
        # Определяем направление текста
        is_rtl = self.language_info['direction'] == 'rtl'
        
        print(f"\n  📊 Анализ структуры листа:")
        print(f"    Направление текста: {'RTL' if is_rtl else 'LTR'}")
        
        # Группируем блоки по уровням y (перекрытие по y)
        y_levels = []
        for block in block_coords:
            added = False
            for level in y_levels:
                # Проверяем перекрытие по y с блоками на этом уровне
                for level_block in level:
                    if self._y_overlap(block, level_block):
                        level.append(block)
                        added = True
                        break
                if added:
                    break
            if not added:
                y_levels.append([block])
        
        # Для каждого уровня определяем порядок по x
        structure_log = []
        structure_log.append("СТРУКТУРА ЛИСТА")
        structure_log.append("="*80)
        structure_log.append(f"Всего блоков: {len(block_coords)}")
        structure_log.append(f"Уровней по y: {len(y_levels)}")
        structure_log.append(f"Направление текста: {'RTL' if is_rtl else 'LTR'}")
        structure_log.append("="*80 + "\n")
        
        for level_idx, level in enumerate(y_levels):
            structure_log.append(f"УРОВЕНЬ {level_idx+1} ({len(level)} блоков):")
            
            # Сортируем блоки на уровне по x с учетом rtl|ltr
            if is_rtl:
                level_sorted = sorted(level, key=lambda b: -b['x0'])  # справа налево
            else:
                level_sorted = sorted(level, key=lambda b: b['x0'])  # слева направо
            
            for block in level_sorted:
                structure_log.append(f"  Блок {block['index']+1}: x0={block['x0']:.1f}, x1={block['x1']:.1f}, y0={block['y0']:.1f}, y1={block['y1']:.1f}, строк={block['lines_count']}")
            
            structure_log.append("")
        
        # Сохраняем результаты
        structure_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_page_structure.txt")
        with open(structure_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(structure_log))
        
        print(f"     📊 Структура: {structure_file}")

    def _y_overlap(self, block1: dict, block2: dict) -> bool:
        """Проверяет перекрытие двух блоков по y"""
        return not (block1['y1'] < block2['y0'] or block2['y1'] < block1['y0'])

    def _analyze_block_structure(self, blocks: List[List], avg_height: float, timestamp: str, debug_dir: str, page_num: int):
        """Анализирует структуру блоков: выделяет параграфы и заголовки"""
        # Порог для разделения на параграфы/заголовки
        paragraph_threshold = avg_height * 1.5  # 1.5 высоты строки
        
        print(f"\n  📊 Анализ структуры блоков:")
        print(f"    Порог разделения: {paragraph_threshold:.1f}pt")
        
        structure_log = []
        structure_log.append("СТРУКТУРА БЛОКОВ (ПАРАГРАФЫ И ЗАГОЛОВКИ)")
        structure_log.append("="*80)
        structure_log.append(f"Порог разделения: {paragraph_threshold:.1f}pt (1.5 * avg_height)")
        structure_log.append("="*80 + "\n")
        
        for block_idx, block in enumerate(blocks):
            if not block:
                continue
            
            structure_log.append(f"БЛОК {block_idx+1} ({len(block)} строк):")
            structure_log.append("-"*80)
            
            # Сортируем строки по y
            sorted_block = sorted(block, key=lambda l: l.y0)
            
            paragraphs = []
            current_paragraph = [sorted_block[0]]
            
            for i in range(1, len(sorted_block)):
                prev_line = sorted_block[i-1]
                curr_line = sorted_block[i]
                
                # Вычисляем расстояние между строками
                gap = curr_line.y0 - prev_line.y1
                
                if gap > paragraph_threshold:
                    # Большой разрыв - это заголовок, начинаем новый параграф
                    paragraphs.append(('paragraph', current_paragraph))
                    current_paragraph = [curr_line]
                    structure_log.append(f"  ЗАГОЛОВК/НОВЫЙ ПАРАГРАФ после строки {i}: gap={gap:.1f}pt")
                else:
                    # Маленький разрыв - продолжение параграфа
                    current_paragraph.append(curr_line)
            
            # Добавляем последний параграф
            if current_paragraph:
                paragraphs.append(('paragraph', current_paragraph))
            
            structure_log.append(f"  Всего параграфов: {len(paragraphs)}")
            
            for p_idx, (p_type, p_lines) in enumerate(paragraphs):
                structure_log.append(f"    Параграф {p_idx+1} ({len(p_lines)} строк):")
                for line in p_lines:
                    structure_log.append(f"      {str(line.text)[:60]}...")
            
            structure_log.append("")
        
        # Сохраняем результаты
        structure_file = os.path.join(debug_dir, f"{timestamp}_page{page_num:02d}_block_structure.txt")
        with open(structure_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(structure_log))
        
        print(f"     📊 Структура блоков: {structure_file}")

    def _assemble_page_text(self, blocks: List[List], timestamp: str, debug_dir: str, page_num: int, clean_base_name: str) -> str:
        """Собирает итоговый текст страницы с учетом структуры блоков, возвращает текст"""
        # Вычисляем координаты каждого блока
        block_coords = []
        for i, block in enumerate(blocks):
            if not block:
                continue
            
            block_x0 = min(line.x0 for line in block)
            block_x1 = max(line.x1 for line in block)
            block_y0 = min(line.y0 for line in block)
            block_y1 = max(line.y1 for line in block)
            
            # Сортируем строки внутри блока по y
            sorted_block = sorted(block, key=lambda l: l.y0)
            
            block_coords.append({
                'index': i,
                'x0': block_x0,
                'x1': block_x1,
                'y0': block_y0,
                'y1': block_y1,
                'lines': sorted_block
            })
        
        # Сортируем блоки по y0 (сверху вниз)
        block_coords.sort(key=lambda b: b['y0'])
        
        # Определяем направление текста
        is_rtl = self.language_info['direction'] == 'rtl'
        
        # Группируем блоки по уровням y (перекрытие по y)
        y_levels = []
        for block in block_coords:
            added = False
            for level in y_levels:
                # Проверяем перекрытие по y с блоками на этом уровне
                for level_block in level:
                    if self._y_overlap(block, level_block):
                        level.append(block)
                        added = True
                        break
                if added:
                    break
            if not added:
                y_levels.append([block])
        
        # Собираем текст по уровням со сквозной нумерацией блоков
        page_text = []
        page_text.append("ТЕКСТ СТРАНИЦЫ")
        page_text.append("="*80)
        page_text.append("")
        
        for level_idx, level in enumerate(y_levels):
            # Сортируем блоки на уровне по x с учетом rtl|ltr
            if is_rtl:
                level_sorted = sorted(level, key=lambda b: -b['x0'])  # справа налево
            else:
                level_sorted = sorted(level, key=lambda b: b['x0'])  # слева направо
            
            for block in level_sorted:
                self.global_block_counter += 1  # Увеличиваем глобальный счетчик
                page_text.append(f"БЛОК {self.global_block_counter}:")
                for line in block['lines']:
                    page_text.append(str(line.text))
                page_text.append("")
        
        # Сохраняем результаты (только TXT в DEBUG_DIR)
        text_file = os.path.join(debug_dir, f"{timestamp}_{clean_base_name}_page{page_num:02d}_raw.txt")
        
        # TXT формат
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(page_text))

        print(f"     📊 Текст страницы: {text_file}")

        # Возвращаем текст страницы для сборки полного текста
        return "\n".join(page_text)

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_final_corrected.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = FinalCorrectedAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_final_corrected(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с финальными исправлениями завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
