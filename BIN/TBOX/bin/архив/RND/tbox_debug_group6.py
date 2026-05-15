#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_group6_characters(pdf_path: str):
    """Анализирует символы в группе 6 и выводит их коды"""
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
                
                print("ГРУППА 6 - АНАЛИЗ СИМВОЛОВ")
                print("="*50)
                print(f"Найдено слов: {len(group6_words)}")
                print(f"Y центр: {target_y}")
                print()
                
                # Выводим каждое слово и его символы
                for i, word in enumerate(group6_words):
                    print(f"СЛОВО {i+1}: '{word['text']}'")
                    print(f"  Координаты: X={word['x0']:.1f}, Y={word['top']:.1f}")
                    print(f"  Длина: {len(word['text'])} символов")
                    print("  Символы и их коды:")
                    
                    for j, char in enumerate(word['text']):
                        char_code = ord(char)
                        char_name = f"U+{char_code:04X}"
                        print(f"    {j+1:2d}. '{char}' -> {char_name} (десятичный: {char_code})")
                    
                    print()
                
                # Собираем полный текст группы
                full_text = ' '.join(w['text'] for w in group6_words)
                print("ПОЛНЫЙ ТЕКТ ГРУППЫ 6:")
                print(f"'{full_text}'")
                print()
                print("ПОЛНЫЙ ТЕКТ - КОДЫ СИМВОЛОВ:")
                for i, char in enumerate(full_text):
                    char_code = ord(char)
                    char_name = f"U+{char_code:04X}"
                    print(f"  {i+1:3d}. '{char}' -> {char_name} (десятичный: {char_code})")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_debug_group6.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group6_characters(pdf_path)
    
    if success:
        print(f"\n✅ Анализ группы 6 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
