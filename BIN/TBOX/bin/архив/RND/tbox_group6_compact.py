#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_group6_compact(pdf_path: str):
    """Компактный вывод ГРУППЫ 6: номер, слово, буквы с кодами"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                page = pdf.pages[0]
                words = page.extract_words()
                
                # Находим группу 6 (Y центр около 253.7)
                group6_words = []
                target_y = 253.7
                y_tolerance = 5.0
                
                for word in words:
                    if abs(word['top'] - target_y) <= y_tolerance:
                        group6_words.append(word)
                
                # Сортируем по X координате
                group6_words.sort(key=lambda w: w['x0'])
                
                print("ГРУППА 6 - КОМПАКТНЫЙ ВЫВОД")
                print("="*40)
                
                # Выводим в компактном формате с координатами
                for i, word in enumerate(group6_words):
                    # Собираем буквы с кодами и координатами
                    chars_with_codes = []
                    word_width = word['x1'] - word['x0']
                    char_width = word_width / len(word['text']) if len(word['text']) > 0 else 0
                    
                    for j, char in enumerate(word['text']):
                        char_code = ord(char)
                        char_x_start = word['x0'] + (j * char_width)
                        char_x_end = char_x_start + char_width
                        chars_with_codes.append(f"'{char}'='U+{char_code:04X}'(X:{char_x_start:.1f}-{char_x_end:.1f})")
                    
                    # Форматируем вывод
                    chars_str = ", ".join(chars_with_codes)
                    print(f"{i+1:2d}, '{word['text']}'(X:{word['x0']:.1f}-{word['x1']:.1f}): [{chars_str}]")
                
                print()
                print(f"Всего слов: {len(group6_words)}")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_group6_compact.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group6_compact(pdf_path)
    
    if success:
        print(f"\n✅ Анализ группы 6 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
