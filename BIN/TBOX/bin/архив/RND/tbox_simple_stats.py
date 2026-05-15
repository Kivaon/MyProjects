#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# --- ПАСПОРТ ---
VERSION = "v3.2.simple-stats"
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
class LineInfo:
    """Информация о строке"""
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    line_number: int

@dataclass
class YGroup:
    """Группа строк по Y координате"""
    y_center: float
    lines: List[LineInfo]
    column_count: int
    x_positions: List[float]

class SimplePageAnalyzer:
    """Простой анализатор страницы со статистикой"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.language_info = None
    
    def analyze_page_simple(self, pdf_path: str) -> bool:
        """Основной метод простого анализа страницы"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📖 Открыт PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} страниц)")
                
                # Анализируем первую страницу
                if pdf.pages:
                    page = pdf.pages[0]
                    self._analyze_page_simple(page)
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return False
    
    def _analyze_page_simple(self, page):
        """Простой анализ страницы со статистикой"""
        print("\n" + "="*60)
        print("ШАГ 1: ОПРЕДЕЛЕНИЕ ЯЗЫКА")
        print("="*60)
        
        # Определяем язык
        words = page.extract_words()
        word_texts = [w['text'] for w in words]
        self.language_info = self._detect_language(word_texts)
        
        print(f"  🎯 Язык: {self.language_info['language']} ({self.language_info['direction']})")
        print(f"  💪 Уверенность: {self.language_info['confidence']:.0f} слов")
        
        print("\n" + "="*60)
        print("ШАГ 2: ГРУППИРОВКА СТРОК ПО Y")
        print("="*60)
        
        # Группируем строки по Y координатам
        y_groups = self._group_lines_by_y(words)
        
        print("\n" + "="*60)
        print("ШАГ 3: АНАЛИЗ ГРУПП И СТАТИСТИКА")
        print("="*60)
        
        # Анализируем группы и делаем статистику
        self._analyze_groups_and_stats(y_groups)
        
        # Сохраняем результаты
        self._save_simple_stats(y_groups)
    
    def _detect_language(self, word_texts: List[str]) -> Dict:
        """Определяет язык документа"""
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
    
    def _group_lines_by_y(self, words: List[Dict]) -> List[YGroup]:
        """Группирует строки по Y координатам"""
        print(f"  📝 Группировка {len(words)} слов по Y:")
        
        # Сортируем слова по Y, затем по X
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        groups = []
        current_group_words = []
        current_y = None
        y_tolerance = 3.0
        
        for word in sorted_words:
            word_y = word['top']
            
            if current_y is None:
                current_y = word_y
                current_group_words = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                current_group_words.append(word)
            else:
                if current_group_words:
                    group = self._create_y_group(current_group_words, len(groups))
                    groups.append(group)
                current_group_words = [word]
                current_y = word_y
        
        if current_group_words:
            group = self._create_y_group(current_group_words, len(groups))
            groups.append(group)
        
        print(f"  ✅ Создано групп по Y: {len(groups)}")
        
        # Выводим информацию о группах
        for i, group in enumerate(groups[:10]):  # Первые 10 групп
            print(f"    Группа {i+1}: Y={group.y_center:.1f}, строк={len(group.lines)}, колонок={group.column_count}")
        
        if len(groups) > 10:
            print(f"    ... и еще {len(groups) - 10} групп")
        
        return groups
    
    def _create_y_group(self, words: List[Dict], group_number: int) -> YGroup:
        """Создает группу строк по Y"""
        # Группируем слова в строки по X разрывам
        lines = self._split_words_into_lines(words)
        
        # Вычисляем центр Y группы
        y_positions = [w['top'] for w in words]
        y_center = sum(y_positions) / len(y_positions)
        
        # Собираем X позиции центров строк
        x_positions = []
        for line in lines:
            if line:
                x_center = (line[0]['x0'] + line[-1]['x1']) / 2
                x_positions.append(x_center)
        
        # Определяем количество колонок
        column_count = len(lines)
        
        # Создаем объекты LineInfo
        line_infos = []
        for i, line in enumerate(lines):
            if line:
                text = ' '.join(w['text'] for w in line)
                x0 = min(w['x0'] for w in line)
                x1 = max(w['x1'] for w in line)
                y0 = min(w['top'] for w in line)
                y1 = max(w.get('bottom', w['top'] + 10) for w in line)
                
                line_info = LineInfo(
                    x0=x0, y0=y0, x1=x1, y1=y1,
                    text=text,
                    line_number=i
                )
                line_infos.append(line_info)
        
        return YGroup(
            y_center=y_center,
            lines=line_infos,
            column_count=column_count,
            x_positions=x_positions
        )
    
    def _split_words_into_lines(self, words: List[Dict]) -> List[List[Dict]]:
        """Разделяет слова на строки по X разрывам"""
        if len(words) <= 1:
            return [words]
        
        # Сортируем слова по X
        sorted_words = sorted(words, key=lambda w: w['x0'])
        
        # Находим разрывы между словами
        gaps = []
        for i in range(len(sorted_words) - 1):
            gap = sorted_words[i + 1]['x0'] - sorted_words[i]['x1']
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
    
    def _analyze_groups_and_stats(self, y_groups: List[YGroup]):
        """Анализирует группы и делает статистику"""
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
        
        print(f"\n  📈 СТАТИСТИКА X ПОЗИЦИЙ (многоколонные группы):")
        print(f"    Всего уникальных X позиций: {len(sorted_x_positions)}")
        
        print(f"\n    ТОП-10 X позиций по частоте:")
        for i, (x_pos, frequency) in enumerate(sorted_x_positions[:10]):
            confidence = min(1.0, frequency / 5.0)  # Уверенность max при 5 повторениях
            print(f"      {i+1:2d}. X={x_pos:6.1f} - частота: {frequency:2d}, уверенность: {confidence:.2f}")
            
            # Показываем детали для топ-5
            if i < 5:
                details = x_position_details[x_pos][:3]  # Первые 3 примера
                for detail in details:
                    print(f"         → Y={detail['y_center']:.1f}, колонок={detail['column_count']}, точный X={detail['exact_x']:.1f}")
        
        # Анализируем пары близких X позиций
        print(f"\n  🔍 АНАЛИЗ ПАР БЛИЗКИХ X ПОЗИЦИЙ:")
        x_positions = [x_pos for x_pos, freq in sorted_x_positions if freq >= 2]  # Только позиции с частотой >= 2
        
        if len(x_positions) >= 2:
            pairs = []
            for i in range(len(x_positions)):
                for j in range(i + 1, len(x_positions)):
                    distance = abs(x_positions[i] - x_positions[j])
                    if distance < 200:  # Близкие позиции (менее 200 пикселей)
                        pairs.append({
                            'x1': x_positions[i],
                            'x2': x_positions[j],
                            'distance': distance,
                            'freq1': x_position_stats[x_positions[i]],
                            'freq2': x_position_stats[x_positions[j]]
                        })
            
            # Сортируем по суммарной частоте
            pairs.sort(key=lambda p: p['freq1'] + p['freq2'], reverse=True)
            
            print(f"    Найдено пар близких X позиций: {len(pairs)}")
            
            for i, pair in enumerate(pairs[:5]):  # Топ-5 пар
                total_freq = pair['freq1'] + pair['freq2']
                print(f"      Пара {i+1}: X={pair['x1']:.1f} & X={pair['x2']:.1f}, "
                      f"расстояние={pair['distance']:.1f}, общая частота={total_freq}")
        
        # Сохраняем статистику для дальнейшего использования
        self.x_position_stats = x_position_stats
        self.x_position_details = x_position_details
        self.sorted_x_positions = sorted_x_positions
    
    def _save_simple_stats(self, y_groups: List[YGroup]):
        """Сохраняет простую статистику"""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        debug_dir = "/Users/kivaonmac/Documents/AI_Lab/02_TXT/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Сохраняем группы по Y
        groups_file = os.path.join(debug_dir, f"{timestamp}_y_groups.txt")
        with open(groups_file, 'w', encoding='utf-8') as f:
            f.write("ГРУППЫ СТРОК ПО Y КООРДИНАТЕ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info['language']} ({self.language_info['direction']})\n")
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
                    f.write(f"    Строка {line.line_number}: X={line.x0:.1f}-{line.x1:.1f}, текст: {line.text}\n")
                f.write("\n" + "-"*50 + "\n\n")
        
        # Сохраняем статистику X позиций
        stats_file = os.path.join(debug_dir, f"{timestamp}_x_stats.txt")
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА X ПОЗИЦИЙ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Язык: {self.language_info['language']} ({self.language_info['direction']})\n")
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
                    for detail in details[:5]:  # Первые 5 деталей
                        f.write(f"     → Y={detail['y_center']:.1f}, колонок={detail['column_count']}, точный X={detail['exact_x']:.1f}\n")
                    f.write("\n")
        
        print(f"\n  💾 Файлы статистики сохранены:")
        print(f"     📄 Группы по Y: {groups_file}")
        print(f"     📄 Статистика X: {stats_file}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_simple_stats.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    analyzer = SimplePageAnalyzer(debug_mode=True)
    success = analyzer.analyze_page_simple(pdf_path)
    
    if success:
        print(f"\n✅ Анализ завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
