#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_character_width(pdf_path: str):
    """Анализирует ширину обычных символов"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                page = pdf.pages[0]
                words = page.extract_words()
                
                print("АНАЛИЗ ШИРИНЫ СИМВОЛОВ")
                print("="*50)
                
                # Собираем статистику по ширине символов
                char_widths = []
                word_details = []
                
                for word in words:
                    width = word['x1'] - word['x0']
                    length = len(word['text'])
                    
                    if length > 0 and width > 0:
                        avg_char_width = width / length
                        char_widths.append(avg_char_width)
                        word_details.append({
                            'text': word['text'],
                            'width': width,
                            'length': length,
                            'avg_char_width': avg_char_width,
                            'x0': word['x0'],
                            'top': word['top']
                        })
                
                if char_widths:
                    # Сортируем по средней ширине символа
                    word_details.sort(key=lambda w: w['avg_char_width'])
                    
                    print(f"Всего слов проанализировано: {len(char_widths)}")
                    print(f"Средняя ширина символа: {sum(char_widths)/len(char_widths):.2f} пикселей")
                    print(f"Минимальная ширина символа: {min(char_widths):.2f} пикселей")
                    print(f"Максимальная ширина символа: {max(char_widths):.2f} пикселей")
                    print()
                    
                    # Показываем примеры слов с разной шириной символов
                    print("ПРИМЕРЫ СЛОВ С РАЗНОЙ ШИРИНОЙ СИМВОЛОВ:")
                    print("-" * 50)
                    
                    categories = {
                        'Очень узкие': [],
                        'Узкие': [],
                        'Средние': [],
                        'Широкие': [],
                        'Очень широкие': []
                    }
                    
                    for detail in word_details:
                        avg_width = detail['avg_char_width']
                        if avg_width < 3:
                            categories['Очень узкие'].append(detail)
                        elif avg_width < 5:
                            categories['Узкие'].append(detail)
                        elif avg_width < 7:
                            categories['Средние'].append(detail)
                        elif avg_width < 10:
                            categories['Широкие'].append(detail)
                        else:
                            categories['Очень широкие'].append(detail)
                    
                    for category, items in categories.items():
                        if items:
                            print(f"\n{category} (первые 5 примеров):")
                            for item in items[:5]:
                                print(f"  '{item['text']}' - {item['avg_char_width']:.2f} px/символ (всего {item['width']:.1f}px, {item['length']} симв.)")
                    
                    print(f"\nАНАЛИЗ ПРОБЕЛОВ:")
                    print("-" * 30)
                    
                    # Анализируем типичные пробелы
                    gaps = []
                    for i in range(len(words) - 1):
                        current = words[i]
                        next_word = words[i + 1]
                        
                        # Только если слова на одной строке
                        if abs(current['top'] - next_word['top']) < 3:
                            gap = next_word['x0'] - current['x1']
                            if gap > 0:
                                gaps.append(gap)
                    
                    if gaps:
                        print(f"Средний пробел: {sum(gaps)/len(gaps):.2f} пикселей")
                        print(f"Минимальный пробел: {min(gaps):.2f} пикселей")
                        print(f"Максимальный пробел: {max(gaps):.2f} пикселей")
                        print(f"Типичный пробел: {sorted(gaps)[len(gaps)//2]:.2f} пикселей (медиана)")
                    
                    print(f"\nСРАВНЕНИЕ С ПОРОГОМ РАЗРЫВА:")
                    print("-" * 35)
                    print(f"Текущий порог разрыва: 14.4 пикселей")
                    print(f"Средняя ширина символа: {sum(char_widths)/len(char_widths):.2f} пикселей")
                    print(f"Отношение порога к символу: {14.4 / (sum(char_widths)/len(char_widths)):.1f}x")
                    print(f"Это примерно {int(14.4 / (sum(char_widths)/len(char_widths)))} символов пробела")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_analyze_char_width.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_character_width(pdf_path)
    
    if success:
        print(f"\n✅ Анализ ширины символов завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
