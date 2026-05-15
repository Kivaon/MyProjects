#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.5.punctuation-context"
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

# Знаки препинания для разных языков
PUNCTUATION_PATTERNS = {
    'hebrew': r'[.,:;!?""''(){}\[\]–—]',
    'arabic': r'[.,:;!?""''(){}\[\]–—]',
    'english': r'[.,:;!?""''(){}\[\]–—]',
    'russian': r'[.,:;!?""''(){}\[\]–—]',
    'universal': r'[.,:;!?""''(){}\[\]–—]'
}

@dataclass
class ProcessedWord:
    """Обработанное слово с учетом контекста"""
    text: str
    original_text: str
    x0: float
    y0: float
    x1: float
    y1: float
    language: str  # 'hebrew', 'english', 'russian', 'unknown'

@dataclass
class ProcessedLine:
    """Обработанная строка с учетом контекста"""
    words: List[ProcessedWord]
    y0: float
    y1: float
    x0: float
    x1: float
    text: str
    line_number: int
    width: float
    dominant_language: str

@dataclass
class YGroup:
    """Группа строк по Y координате"""
    y_center: float
    lines: List[ProcessedLine]
    column_count: int
    x_positions: List[float]

class PunctuationContextAnalyzer:
    """Анализатор с контекстуальным определением знаков препинания"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_with_context(self, pdf_path: str) -> bool:
        """Основной метод анализа с контекстом знаков препинания"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_with_context(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_with_context(self, page):
        """Анализ страницы с контекстуальным определением знаков препинания"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА И КОНТЕКСТА")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Основной язык: {self.language_info['language']}")
        print(f"  📝 Направление: {self.language_info['direction'].upper()}")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        
        print("\n" + "="*60)
        print("ШАГ 2: КОНТЕКСТУАЛЬНОЕ ОПРЕДЕЛЕНИЕ ЯЗЫКА СЛОВ")
        print("="*60)
        
        # ЭТАП 1: Определяем язык каждого слова с учетом контекста
        processed_words = self._process_words_with_context(words)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК С КОНТЕКСТОМ")
        print("="*60)
        
        # ЭТАП 2: Формируем строки с учетом контекста
        y_groups = self._form_lines_with_context(processed_words)
        
        print("\n" + "="*60)
        print("ШАГ 4: СТАТИСТИКА С КОНТЕКСТОМ")
        print("="*60)
        
        # ЭТАП 3: Статистика с учетом контекста
        self._analyze_with_context_stats(y_groups)
        
        # Сохраняем результаты
        self._save_context_analysis(y_groups)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет основной язык документа"""
        if not word_texts:
            return {'language': 'unknown', 'direction': 'ltr', 'confidence': 0.0}
        
        # Считаем слова для каждого языка (без учета знаков препинания)
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            # Исключаем знаки препинания из подсчета
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
            'confidence': confidence
        }
    
    def _process_words_with_context(self, raw_words: List[Dict]) -> List[ProcessedWord]:
        """ЭТАП 1: Определяем язык каждого слова с учетом контекста"""
        print(f"  🔤 Контекстуальная обработка {len(raw_words)} слов:")
        
        processed_words = []
        
        for i, word in enumerate(raw_words):
            original_text = word['text']
            
            # Определяем язык слова на основе контекста
            word_language = self._detect_word_language_contextual(original_text, i, raw_words)
            
            # Инвертируем порядок букв только для RTL
            if self.language_info['direction'] == 'rtl':
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
                language=word_language
            )
            processed_words.append(processed_word)
            
            # Показываем первые 15 слов с контекстом
            if i < 15:
                lang_mark = self._get_language_mark(word_language)
                print(f"    {i+1:2d}. {original_text:15s} → {processed_text:15s} {lang_mark} ({word['x0']:6.1f},{word['top']:6.1f})")
            elif i == 15:
                print(f"    ... и еще {len(raw_words) - 15} слов")
        
        # Статистика по языкам слов
        language_counts = {}
        for word in processed_words:
            language_counts[word.language] = language_counts.get(word.language, 0) + 1
        
        print(f"\n  📊 Статистика языков слов:")
        for lang, count in language_counts.items():
            percentage = (count / len(processed_words)) * 100
            print(f"      {lang}: {count} слов ({percentage:.1f}%)")
        
        print(f"  ✅ Обработано слов: {len(processed_words)}")
        return processed_words
    
    def _detect_word_language_contextual(self, word_text: str, word_index: int, all_words: List[Dict]) -> str:
        """Определяет язык слова на основе контекста (соседних слов)"""
        # Проверяем, является ли слово знаком препинания
        if re.match(PUNCTUATION_PATTERNS['universal'], word_text):
            return 'punctuation'
        
        # Проверяем наличие ивритских/арабских букв
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', word_text))
        has_arabic = bool(re.search(r'[\u0600-\u06FF]', word_text))
        has_english = bool(re.search(r'[a-zA-Z]', word_text))
        has_russian = bool(re.search(r'[а-яёА-ЯЁ]', word_text))
        
        # Если слово содержит только один язык - возвращаем его
        languages = []
        if has_hebrew:
            languages.append('hebrew')
        if has_arabic:
            languages.append('arabic')
        if has_english:
            languages.append('english')
        if has_russian:
            languages.append('russian')
        
        if len(languages) == 1:
            return languages[0]
        
        # Если смешанный язык - анализируем контекст
        return self._analyze_context_for_mixed_word(word_text, word_index, all_words, languages)
    
    def _analyze_context_for_mixed_word(self, word_text: str, word_index: int, all_words: List[Dict], languages: List[str]) -> str:
        """Анализирует контекст для слова со смешанными языками"""
        # Получаем соседние слова
        prev_words = []
        next_words = []
        
        # Предыдущие слова (до 3)
        for i in range(max(0, word_index - 3), word_index):
            prev_words.append(all_words[i]['text'])
        
        # Следующие слова (до 3)
        for i in range(word_index + 1, min(len(all_words), word_index + 4)):
            next_words.append(all_words[i]['text'])
        
        # Анализируем контекст
        hebrew_count = 0
        arabic_count = 0
        english_count = 0
        russian_count = 0
        
        # Считаем языки в контексте
        context_words = prev_words + next_words
        for ctx_word in context_words:
            if re.search(r'[\u0590-\u05FF]', ctx_word):
                hebrew_count += 1
            if re.search(r'[\u0600-\u06FF]', ctx_word):
                arabic_count += 1
            if re.search(r'[a-zA-Z]', ctx_word):
                english_count += 1
            if re.search(r'[а-яёА-ЯЁ]', ctx_word):
                russian_count += 1
        
        # Определяем доминирующий язык в контексте
        context_scores = {
            'hebrew': hebrew_count,
            'arabic': arabic_count,
            'english': english_count,
            'russian': russian_count
        }
        
        dominant_context_lang = max(context_scores.items(), key=lambda x: x[1])[0]
        
        # Если в контексте доминирует один язык - присваиваем его
        if context_scores[dominant_context_lang] > 0:
            return dominant_context_lang
        
        # Если контекст смешанный - возвращаем 'mixed'
        return 'mixed'
    
    def _get_language_mark(self, language: str) -> str:
        """Возвращает маркировку языка"""
        marks = {
            'hebrew': '🔤',
            'arabic': '🕌',
            'english': '🇺🇸',
            'russian': '🇷🇺',
            'punctuation': '📝',
            'mixed': '🌐',
            'unknown': '❓'
        }
        return marks.get(language, '❓')
    
    def _form_lines_with_context(self, words: List[ProcessedWord]) -> List[YGroup]:
        """ЭТАП 2: Формируем строки с учетом контекста"""
        print(f"  📋 Формирование строк с контекстом:")
        
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
                    group = self._create_y_group_with_context(current_group_words, len(groups))
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group_with_context(current_group_words, len(groups))
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        return groups
    
    def _create_y_group_with_context(self, words: List[ProcessedWord], group_number: int) -> YGroup:
        """Создает группу Y с учетом контекста"""
        if not words:
            return None
        
        direction = self.language_info['direction']
        
        # Разделяем слова на строки по X разрывам
        lines = self._split_words_into_lines_with_context(words)
        
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
                
                # Определяем доминирующий язык в строке
                line_languages = [w.language for w in sorted_words]
                language_counts = {}
                for lang in line_languages:
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                
                dominant_language = max(language_counts.items(), key=lambda x: x[1])[0]
                
                line_info = ProcessedLine(
                    words=sorted_words,
                    y0=y0, y1=y1, x0=x0, x1=x1,
                    text=text,
                    line_number=i,
                    width=x1 - x0,
                    dominant_language=dominant_language
                )
                line_infos.append(line_info)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=len(lines),
            x_positions=x_positions
        )
    
    def _split_words_into_lines_with_context(self, words: List[ProcessedWord]) -> List[List[ProcessedWord]]:
        """Разделяет слова на строки с учетом контекста"""
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
    
    def _analyze_with_context_stats(self, y_groups: List[YGroup]):
        """ЭТАП 3: Статистика с учетом контекста"""
        print(f"  📊 Анализ {len(y_groups)} групп с контекстом:")
        
        # Собираем статистику по языкам в строках
        language_stats = {
            'hebrew': 0,
            'arabic': 0,
            'english': 0,
            'russian': 0,
            'punctuation': 0,
            'mixed': 0,
            'unknown': 0
        }
        
        total_lines = 0
        for group in y_groups:
            for line in group.lines:
                total_lines += 1
                language_stats[line.dominant_language] += 1
        
        print(f"    📄 Всего строк: {total_lines}")
        print(f"    📊 Статистика по доминирующим языкам:")
        
        for lang, count in language_stats.items():
            if count > 0:
                percentage = (count / total_lines) * 100
                mark = self._get_language_mark(lang)
                print(f"      {mark} {lang}: {count} строк ({percentage:.1f}%)")
        
        # Сохраняем статистику
        self.language_stats = language_stats
        self.total_lines = total_lines
    
    def _save_context_analysis(self, y_groups: List[YGroup]):
        """Сохраняет результаты анализа с контекстом"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы с контекстом
        groups_file = os.path.join(debug_dir, f"{timestamp}_context_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ С КОНТЕКСТОМ ЯЗЫКОВ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Основной язык: {self.language_info['language']}\n")
            f.write(f"Направление: {self.language_info['direction'].upper()}\n")
            f.write(f"Всего групп: {len(y_groups)}\n\n")
            
            f.write("СТАТИСТИКА ПО ЯЗЫКАМ В СТРОКАХ:\n")
            f.write("-"*50 + "\n")
            for lang, count in self.language_stats.items():
                if count > 0:
                    percentage = (count / self.total_lines) * 100
                    mark = self._get_language_mark(lang)
                    f.write(f"{mark} {lang}: {count} строк ({percentage:.1f}%)\n")
            f.write("\n")
            
            for i, group in enumerate(y_groups):
                f.write(f"ГРУППА {i+1}:\n")
                f.write(f"  Y центр: {group.y_center:.1f}\n")
                f.write(f"  Количество колонок: {group.column_count}\n")
                f.write(f"  X позиции: {[f'{x:.1f}' for x in group.x_positions]}\n")
                f.write(f"  Строки ({len(group.lines)}):\n")
                for line in group.lines:
                    lang_mark = self._get_language_mark(line.dominant_language)
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, ширина={line.width:.1f} {lang_mark}\n")
                    f.write(f"    Текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Файл анализа с контекстом сохранен:")
        print(f"     📄 Группы с контекстом: {groups_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_punctuation_context.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = PunctuationContextAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_with_context(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с контекстом завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
