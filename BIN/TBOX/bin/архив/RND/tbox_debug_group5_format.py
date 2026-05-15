#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_group5_characters_format(pdf_path: str):
    """Анализирует символы в группе 5 и выводит в формате через запятую"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                page = pdf.pages[0]
                words = page.extract_words()
                
                # Находим группу 5 (Y центр около 262.6)
                group5_words = []
                target_y = 262.6
                y_tolerance = 5.0
                
                for word in words:
                    if abs(word['top'] - target_y) <= y_tolerance:
                        group5_words.append(word)
                
                # Сортируем по X координате
                group5_words.sort(key=lambda w: w['x0'])
                
                print("ГРУППА 5 - ФОРМАТИРОВАННЫЙ ВЫВОД")
                print("="*60)
                
                # Выводим каждое слово в формате через запятую
                for i, word in enumerate(group5_words):
                    parts = []
                    
                    # Номер слова
                    parts.append(f"Слово {i+1}")
                    
                    # Само слово
                    parts.append(f"'{word['text']}'")
                    
                    # Символы и их коды
                    for char in word['text']:
                        char_code = ord(char)
                        char_name = f"U+{char_code:04X}"
                        parts.append(f"'{char}' и '{char_name}'")
                    
                    # Соединяем через запятую
                    line = ", ".join(parts)
                    print(line)
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_debug_group5_format.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group5_characters_format(pdf_path)
    
    if success:
        print(f"\n✅ Анализ группы 5 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
