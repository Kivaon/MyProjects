#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# --- ПАСПОРТ ---
VERSION = "v3.0.step-by-step"
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

class PDFExtractorStepByStep:
    """Извлекатель текста из PDF с пошаговой обработкой"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def extract_from_pdf(self, pdf_path: str) -> bool:
        """Основной метод извлечения текста из PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # ШАГ 1: Определяем язык документа
                self._detect_language_from_pdf(pdf)
                
                # Обрабатываем первую страницу для отладки
                if pdf.pages:
                    page = pdf.pages[0]
                    self._process_first_page_debug(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка извлечения PDF: {e}")
            return False
    
    def _detect_language_from_pdf(self, pdf) -> LanguageInfo:
        """ШАГ 1: Определяем язык документа"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА ДОКУМЕНТА")
        print("="*60)
        
        all_words = []
        for page in pdf.pages:
            words = page.extract_words()
            all_words.extend([w['text'] for w in words])
        
        # Считаем слова для каждого языка
        language_scores = {}
        
        for lang_name, lang_config in LANGUAGE_CONFIGS.items():
            pattern = lang_config['pattern']
            count = sum(1 for word in all_words if re.search(pattern, word))
            language_scores[lang_name] = count
        
        if not language_scores:
            self.language_info = LanguageInfo('unknown', 'ltr', 0.0)
            print("  ❌ Не удалось определить язык")
            return self.language_info
        
        # Находим язык с максимальным счетом
        best_language = max(language_scores.items(), key=lambda x: x[1])
        lang_name, confidence = best_language
        
        lang_config = LANGUAGE_CONFIGS[lang_name]
        self.language_info = LanguageInfo(
            language=lang_name,
            direction=lang_config['direction'],
            confidence=confidence
        )
        
        print(f"  📊 Проанализировано слов: {len(all_words)}")
        print(f"  📈 Счета языков: {language_scores}")
        print(f"  🎯 Определен язык: {lang_name.upper()}")
        print(f"  📝 Направление текста: {self.language_info.direction.upper()}")
        print(f"  💪 Уверенность: {confidence:.0f} слов")
        print(f"  ✅ Результат: {lang_name} ({self.language_info.direction})")
        
        return self.language_info
    
    def _process_first_page_debug(self, page):
        """Обрабатываем первую страницу с полной отладкой"""
        print("\n" + "="*60)
        print("ШАГ 2: ОБРАБОТКА СЛОВ ПЕРВОЙ СТРАНИЦЫ")
        print("="*60)
        
        # Извлекаем слова
        raw_words = page.extract_words()
        print(f"  📝 Извлечено слов: {len(raw_words)}")
        
        # Обрабатываем слова с правильным порядком букв
        processed_words = self._process_words_with_direction(raw_words)
        
        print("\n" + "="*60)
        print("ШАГ 3: ФОРМИРОВАНИЕ СТРОК ПО Y КООРДИНАТЕ")
        print("="*60)
        
        # Формируем строки по Y
        lines = self._form_lines_by_y(processed_words)
        
        print("\n" + "="*60)
        print("ШАГ 4: РАЗБИЕНИЕ СТРОК И НУМЕРАЦИЯ")
        print("="*60)
        
        # Разбиваем строки и нумеруем
        final_lines = self._split_and_number_lines(lines)
        
        print("\n" + "="*60)
        print("ШАГ 5: ВЕРТИКАЛЬНАЯ СЕГМЕНТАЦИЯ СТРАНИЦЫ")
        print("="*60)
        
        # Разделяем страницу на вертикальные сегменты
        segments = self._segment_page_vertically(final_lines)
        
        print("\n" + "="*60)
        print("ШАГ 6: ОПРЕДЕЛЕНИЕ КОЛОНОК В КАЖДОМ СЕГМЕНТЕ")
        print("="*60)
        
        # Определяем колонки для каждого сегмента
        segments_with_columns = []
        for segment in segments:
            segment_columns = self._detect_columns(segment['lines'])
            segment['columns'] = segment_columns
            segments_with_columns.append(segment)
        
        # Сохраняем результаты
        self._save_debug_results(processed_words, lines, final_lines, segments_with_columns)
    
    def _process_words_with_direction(self, raw_words: List[Dict]) -> List[ProcessedWord]:
        """ШАГ 2: Обрабатываем слова с правильным порядком букв"""
        processed_words = []
        
        print(f"  🔤 Обработка слов для языка {self.language_info.direction.upper()}:")
        
        for i, word in enumerate(raw_words):
            original_text = word['text']
            
            if self.language_info.direction == 'rtl':
                # Для RTL инвертируем порядок букв
                processed_text = original_text[::-1]
            else:
                # Для LTR оставляем как есть
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
            
            # Выводим первые 10 слов в отладку
            if i < 10:
                print(f"    {i+1:2d}. {original_text:15s} → {processed_text:15s}  ({word['x0']:6.1f},{word['top']:6.1f})")
            elif i == 10:
                print(f"    ... и еще {len(raw_words) - 10} слов")
        
        print(f"  ✅ Обработано слов: {len(processed_words)}")
        return processed_words
    
    def _form_lines_by_y(self, words: List[ProcessedWord]) -> List[ProcessedLine]:
        """ШАГ 3: Формируем строки по Y координате"""
        if not words:
            return []
        
        print(f"  📋 Формирование строк по Y координате:")
        
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
                # Создаем новую строку
                if current_line_words:
                    line = self._create_processed_line(current_line_words, len(lines))
                    lines.append(line)
                current_line_words = [word]
                current_y = word_y
        
        # Добавляем последнюю строку
        if current_line_words:
            line = self._create_processed_line(current_line_words, len(lines))
            lines.append(line)
        
        print(f"    📄 Создано строк: {len(lines)}")
        
        # Выводим первые 5 строк в отладку
        for i, line in enumerate(lines[:5]):
            print(f"    Строка {i+1}: {line.text[:50]}{'...' if len(line.text) > 50 else ''}")
        
        if len(lines) > 5:
            print(f"    ... и еще {len(lines) - 5} строк")
        
        return lines
    
    def _create_processed_line(self, words: List[ProcessedWord], line_number: int) -> ProcessedLine:
        """Создает обработанную строку из слов"""
        if not words:
            return None
        
        # Сортируем слова по X с учетом направления языка
        if self.language_info.direction == 'rtl':
            # Для RTL: справа налево (X убывание)
            sorted_words = sorted(words, key=lambda w: -w.x0)
        else:
            # Для LTR: слева направо (X возрастание)
            sorted_words = sorted(words, key=lambda w: w.x0)
        
        # Собираем текст
        text = ' '.join(w.text for w in sorted_words)
        
        # Вычисляем границы строки
        y0 = min(w.y0 for w in words)
        y1 = max(w.y1 for w in words)
        x0 = min(w.x0 for w in words)
        x1 = max(w.x1 for w in words)
        
        return ProcessedLine(
            words=sorted_words,
            y0=y0, y1=y1, x0=x0, x1=x1,
            text=text,
            line_number=line_number
        )
    
    def _split_and_number_lines(self, lines: List[ProcessedLine]) -> List[ProcessedLine]:
        """ШАГ 4: Разбиваем строки и нумеруем"""
        print(f"  ✂️  Разбиение строк и нумерация:")
        
        final_lines = []
        line_counter = 1
        
        for line in lines:
            # Проверяем, нужно ли разбивать строку
            if self._should_split_line(line):
                # Разбиваем строку на подстроки
                split_lines = self._split_line(line)
                
                for split_line in split_lines:
                    split_line.line_number = line_counter
                    final_lines.append(split_line)
                    line_counter += 1
            else:
                # Не разбиваем, просто нумеруем
                line.line_number = line_counter
                final_lines.append(line)
                line_counter += 1
        
        print(f"    📝 Итоговых строк: {len(final_lines)}")
        
        # Выводим первые 5 строк в отладку
        for i, line in enumerate(final_lines[:5]):
            print(f"    Строка {line.line_number:2d}: {line.text[:50]}{'...' if len(line.text) > 50 else ''}")
        
        if len(final_lines) > 5:
            print(f"    ... и еще {len(final_lines) - 5} строк")
        
        return final_lines
    
    def _should_split_line(self, line: ProcessedLine) -> bool:
        """Определяет, нужно ли разбивать строку"""
        if len(line.words) < 5:
            return False
        
        # Находим большие пробелы между словами
        gaps = []
        for i in range(len(line.words) - 1):
            gap = abs(line.words[i + 1].x0 - line.words[i].x1)
            gaps.append(gap)
        
        if not gaps:
            return False
        
        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        
        # Разбиваем если максимальный пробел в 2 раза больше среднего
        return max_gap > avg_gap * 2.0
    
    def _split_line(self, line: ProcessedLine) -> List[ProcessedLine]:
        """Разбивает строку на подстроки"""
        if len(line.words) < 2:
            return [line]
        
        # Находим точки разрыва
        split_points = []
        for i in range(len(line.words) - 1):
            gap = abs(line.words[i + 1].x0 - line.words[i].x1)
            
            # Вычисляем средний пробел
            all_gaps = [abs(line.words[j + 1].x0 - line.words[j].x1) for j in range(len(line.words) - 1)]
            avg_gap = sum(all_gaps) / len(all_gaps)
            
            if gap > avg_gap * 2.0:
                split_points.append(i + 1)
        
        if not split_points:
            return [line]
        
        # Разбиваем по точкам
        split_lines = []
        start_idx = 0
        
        for split_point in split_points:
            split_words = line.words[start_idx:split_point]
            if split_words:
                split_line = ProcessedLine(
                    words=split_words,
                    y0=line.y0, y1=line.y1,
                    x0=split_words[0].x0,
                    x1=split_words[-1].x1,
                    text=' '.join(w.text for w in split_words),
                    line_number=0  # Установим позже
                )
                split_lines.append(split_line)
            start_idx = split_point
        
        # Добавляем последнюю часть
        if start_idx < len(line.words):
            split_words = line.words[start_idx:]
            split_line = ProcessedLine(
                words=split_words,
                y0=line.y0, y1=line.y1,
                x0=split_words[0].x0,
                x1=split_words[-1].x1,
                text=' '.join(w.text for w in split_words),
                line_number=0  # Установим позже
            )
            split_lines.append(split_line)
        
        return split_lines
    
    def _detect_columns(self, lines: List[ProcessedLine]) -> Dict:
        """ШАГ 5: Определяет колонки в документе (2, 3 или более)"""
        print(f"  📊 Анализ колонок из {len(lines)} строк:")
        
        if not lines:
            return {'columns': [], 'type': 'none'}
        
        # Собираем центры всех строк
        line_centers = []
        for line in lines:
            center = (line.x0 + line.x1) / 2
            line_centers.append(center)
        
        if len(line_centers) < 2:
            return {'columns': [], 'type': 'single_column'}
        
        # Сортируем центры
        sorted_centers = sorted(line_centers)
        
        # Находим разрывы между соседними центрами
        gaps = []
        for i in range(len(sorted_centers) - 1):
            gap = sorted_centers[i + 1] - sorted_centers[i]
            gaps.append(gap)
        
        # Вычисляем статистику разрывов
        avg_gap = sum(gaps) / len(gaps)
        std_gap = (sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)) ** 0.5
        
        # Порог для разделения колонок - адаптивный
        # Больший порог для документов с большим количеством колонок
        if len(lines) > 50:
            separation_threshold = avg_gap + std_gap * 0.8  # Более строгий для больших документов
        else:
            separation_threshold = avg_gap + std_gap * 1.2  # Более мягкий для маленьких документов
        
        print(f"    📏 Средний разрыв: {avg_gap:.1f} пикселей")
        print(f"    📊 Стандартное отклонение: {std_gap:.1f} пикселей")
        print(f"    🎯 Порог разделения: {separation_threshold:.1f} пикселей")
        
        # Находим точки разделения колонок
        column_boundaries = [sorted_centers[0]]
        current_column_centers = [sorted_centers[0]]
        
        for i in range(len(sorted_centers) - 1):
            gap = sorted_centers[i + 1] - sorted_centers[i]
            if gap > separation_threshold:
                # Начинаем новую колонку
                column_boundaries.append(sorted_centers[i + 1])
                current_column_centers = [sorted_centers[i + 1]]
            else:
                current_column_centers.append(sorted_centers[i + 1])
        
        # Создаем колонки
        columns = {}
        column_info = []
        
        for i, boundary in enumerate(column_boundaries):
            col_name = f'column_{i+1}'
            col_lines = []
            
            # Находим строки, принадлежащие этой колонке
            for line in lines:
                line_center = (line.x0 + line.x1) / 2
                
                # Проверяем, принадлежит ли строка к этой колонке
                if i == len(column_boundaries) - 1:
                    # Последняя колонка - все строки справа от границы
                    if line_center >= boundary - 30:  # Допуск 30 пикселей
                        col_lines.append(line)
                else:
                    # Не последняя колонка - строки между границами
                    next_boundary = column_boundaries[i + 1] if i + 1 < len(column_boundaries) else float('inf')
                    if boundary - 30 <= line_center < next_boundary - 30:
                        col_lines.append(line)
            
            if col_lines:
                # Сортируем строки в колонке по Y
                col_lines.sort(key=lambda l: l.y0)
                columns[col_name] = col_lines
                
                # Вычисляем статистику колонки
                col_centers = [(l.x0 + l.x1) / 2 for l in col_lines]
                col_center = sum(col_centers) / len(col_centers) if col_centers else 0
                col_variance = sum((c - col_center) ** 2 for c in col_centers) / len(col_centers) if col_centers else 0
                col_std = col_variance ** 0.5
                
                column_info.append({
                    'name': col_name,
                    'center': col_center,
                    'std': col_std,
                    'count': len(col_lines),
                    'lines': col_lines
                })
        
        # Определяем тип колонок
        num_columns = len(columns)
        if num_columns == 0:
            column_type = 'none'
        elif num_columns == 1:
            column_type = 'single_column'
        elif num_columns == 2:
            column_type = 'double_column'
        elif num_columns == 3:
            column_type = 'triple_column'
        else:
            column_type = f'multi_column_{num_columns}'
        
        print(f"    📊 Найдено колонок: {num_columns}")
        print(f"    📝 Тип колонок: {column_type}")
        
        for col in column_info:
            print(f"      {col['name']}: центр X={col['center']:.1f}±{col['std']:.1f}, строк={col['count']}")
        
        return {
            'type': column_type,
            'columns': columns,
            'column_info': column_info,
            'separation_threshold': separation_threshold,
            'total_lines': len(lines)
        }
    
    def _segment_page_vertically(self, lines: List[ProcessedLine]) -> List[Dict]:
        """Разделяет страницу на вертикальные сегменты с разной структурой колонок"""
        print(f"  📊 Вертикальная сегментация {len(lines)} строк:")
        
        if not lines:
            return []
        
        # Сортируем строки по Y
        sorted_lines = sorted(lines, key=lambda l: l.y0)
        
        # Определяем высоту сегмента
        segment_height = 100.0  # Высота сегмента для анализа
        
        segments = []
        current_segment_lines = []
        segment_start_y = sorted_lines[0].y0 if sorted_lines else 0
        
        for line in sorted_lines:
            # Проверяем, нужно ли начать новый сегмент
            if line.y0 - segment_start_y > segment_height:
                # Создаем текущий сегмент
                if current_segment_lines:
                    segment = {
                        'y_start': segment_start_y,
                        'y_end': current_segment_lines[-1].y1,
                        'lines': current_segment_lines,
                        'line_count': len(current_segment_lines)
                    }
                    segments.append(segment)
                
                # Начинаем новый сегмент
                current_segment_lines = [line]
                segment_start_y = line.y0
            else:
                current_segment_lines.append(line)
        
        # Добавляем последний сегмент
        if current_segment_lines:
            segment = {
                'y_start': segment_start_y,
                'y_end': current_segment_lines[-1].y1,
                'lines': current_segment_lines,
                'line_count': len(current_segment_lines)
            }
            segments.append(segment)
        
        print(f"    📄 Создано сегментов: {len(segments)}")
        
        for i, segment in enumerate(segments):
            print(f"      Сегмент {i+1}: Y={segment['y_start']:.1f}-{segment['y_end']:.1f}, строк={segment['line_count']}")
        
        return segments
    
    def _cluster_x_positions(self, x_positions: List[float]) -> List[Dict]:
        """Кластеризует X позиции для определения колонок"""
        if len(x_positions) < 2:
            return []
        
        # Сортируем позиции
        sorted_positions = sorted(x_positions)
        
        # Находим большие разрывы между позициями
        gaps = []
        for i in range(len(sorted_positions) - 1):
            gap = sorted_positions[i + 1] - sorted_positions[i]
            gaps.append(gap)
        
        if not gaps:
            return []
        
        # Вычисляем статистику разрывов
        avg_gap = sum(gaps) / len(gaps)
        std_gap = (sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)) ** 0.5
        
        # Порог для разделения колонок - адаптивный
        # Больший порог для документов с большим количеством колонок
        if len(sorted_positions) > 50:
            separation_threshold = avg_gap + std_gap * 0.8  # Более строгий для больших документов
        else:
            separation_threshold = avg_gap + std_gap * 1.2  # Более мягкий для маленьких документов
        
        # Разделяем на кластеры
        clusters = []
        current_cluster = [sorted_positions[0]]
        
        for i in range(len(sorted_positions) - 1):
            gap = sorted_positions[i + 1] - sorted_positions[i]
            if gap > threshold:
                # Завершаем текущий кластер
                if current_cluster:
                    clusters.append(self._create_cluster_info(current_cluster))
                current_cluster = [sorted_positions[i + 1]]
            else:
                current_cluster.append(sorted_positions[i + 1])
        
        # Добавляем последний кластер
        if current_cluster:
            clusters.append(self._create_cluster_info(current_cluster))
        
        return clusters
    
    def _create_cluster_info(self, positions: List[float]) -> Dict:
        """Создает информацию о кластере"""
        if not positions:
            return None
        
        center = sum(positions) / len(positions)
        variance = sum((p - center) ** 2 for p in positions) / len(positions)
        std = variance ** 0.5
        
        return {
            'positions': positions,
            'center': center,
            'std': std,
            'count': len(positions),
            'min': min(positions),
            'max': max(positions)
        }
    
    def _determine_column_type(self, clusters: List[Dict], lines: List[ProcessedLine]) -> str:
        """Определяет тип колонок"""
        if len(clusters) == 0:
            return 'none'
        elif len(clusters) == 1:
            return 'single_column'
        elif len(clusters) == 2:
            # Проверяем симметрию для двух колонок
            if len(clusters) >= 2:
                center_page = (clusters[0]['center'] + clusters[1]['center']) / 2
                distance = abs(clusters[1]['center'] - clusters[0]['center'])
                
                # Если колонки симметричны относительно центра
                if abs(center_page - 300) < 100:  # Предполагаем центр страницы ~300
                    return 'double_column'
                else:
                    return 'asymmetric_columns'
            else:
                return 'double_column'
        else:
            return 'multi_column'
    
    def _group_lines_by_columns(self, lines: List[ProcessedLine], clusters: List[Dict]) -> Dict:
        """Группирует строки по колонкам"""
        if not clusters:
            return {'single': lines}
        
        columns = {}
        
        for i, cluster in enumerate(clusters):
            col_name = f'column_{i+1}'
            col_lines = []
            
            # Находим строки, принадлежащие этому кластеру
            for line in lines:
                # Проверяем, попадает ли X0 линии в кластер
                if cluster['min'] - 20 <= line.x0 <= cluster['max'] + 20:  # +20 для допуска
                    col_lines.append(line)
            
            # Сортируем строки в колонке по Y
            col_lines.sort(key=lambda l: l.y0)
            columns[col_name] = col_lines
        
        return columns
    
    def _save_debug_results(self, words: List[ProcessedWord], lines: List[ProcessedLine], final_lines: List[ProcessedLine], segments_with_columns: List[Dict] = None):
        """Сохраняем результаты отладки"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем слова
        words_file = os.path.join(debug_dir, f"{timestamp}_words_debug.txt")
        with open(words_file, 'w', encoding='utf-8') as f:
            f.write("ОТЛАДКА СЛОВ ПЕРВОЙ СТРАНИЦЫ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info.language} ({self.language_info.direction})\n")
            f.write(f"Всего слов: {len(words)}\n\n")
            
            for i, word in enumerate(words):
                f.write(f"{i+1:3d}. {word.original_text:15s} → {word.text:15s}  ({word.x0:6.1f},{word.y0:6.1f})\n")
        
        # Сохраняем строки
        lines_file = os.path.join(debug_dir, f"{timestamp}_lines_debug.txt")
        with open(lines_file, 'w', encoding='utf-8') as f:
            f.write("ОТЛАДКА СТРОК ПЕРВОЙ СТРАНИЦЫ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info.language} ({self.language_info.direction})\n")
            f.write(f"Всего строк: {len(final_lines)}\n\n")
            
            for line in final_lines:
                f.write(f"Строка {line.line_number:3d}: Y={line.y0:6.1f}-{line.y1:6.1f}, X={line.x0:6.1f}-{line.x1:6.1f}\n")
                f.write(f"Текст: {line.text}\n")
                f.write("-"*50 + "\n")
        
        # Сохраняем информацию о сегментах и колонках
        if segments_with_columns:
            segments_file = os.path.join(debug_dir, f"{timestamp}_segments_debug.txt")
            with open(segments_file, 'w', encoding='utf-8') as f:
                f.write("ОТЛАДКА СЕГМЕНТОВ И КОЛОНОК ПЕРВОЙ СТРАНИЦЫ\n")
                f.write("="*50 + "\n\n")
                f.write(f"Язык: {self.language_info.language} ({self.language_info.direction})\n")
                f.write(f"Всего сегментов: {len(segments_with_columns)}\n")
                f.write(f"Всего строк: {sum(s['line_count'] for s in segments_with_columns)}\n\n")
                
                for i, segment in enumerate(segments_with_columns):
                    f.write(f"СЕГМЕНТ {i+1}:\n")
                    f.write(f"  Диапазон Y: {segment['y_start']:.1f} - {segment['y_end']:.1f}\n")
                    f.write(f"  Количество строк: {segment['line_count']}\n")
                    f.write(f"  Тип колонок: {segment['columns']['type']}\n")
                    
                    columns_info = segment['columns'].get('column_info', [])
                    for col_info in columns_info:
                        f.write(f"    {col_info['name'].upper()}: центр X={col_info['center']:.1f}±{col_info['std']:.1f}, строк={col_info['count']}\n")
                    
                    f.write(f"  СТРОКИ В КОЛОНКАХ:\n")
                    columns_dict = segment['columns'].get('columns', {})
                    if columns_dict:
                        for col_name, col_lines in columns_dict.items():
                            f.write(f"    {col_name.upper()} ({len(col_lines)} строк):\n")
                            for line in col_lines:
                                f.write(f"      Строка {line.line_number:3d}: Y={line.y0:6.1f}, X={line.x0:6.1f}-{line.x1:6.1f}\n")
                                f.write(f"        Текст: {line.text}\n")
                    else:
                        f.write("    Нет колонок\n")
                    f.write("\n" + "-"*50 + "\n\n")
        
        print(f"\n  💾 Отладочные файлы сохранены:")
        print(f"     📄 Слова: {words_file}")
        print(f"     📄 Строки: {lines_file}")
        if segments_with_columns:
            print(f"     📄 Сегменты и колонки: {segments_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_extract_v3.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    extractor = PDFExtractorStepByStep(debug_mode=True)
    success = extractor.extract_from_pdf(pdf_path)
    
    if success:
        print(f"\n✅ Обработка завершена успешно")
    else:
        print(f"\n❌ Обработка завершена с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
