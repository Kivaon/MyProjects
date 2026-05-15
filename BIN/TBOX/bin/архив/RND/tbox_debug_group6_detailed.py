#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_group6_detailed(pdf_path: str):
    """Детальная разбивка ГРУППЫ 6 по словам и буквам"""
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
                
                print("ГРУППА 6 - ДЕТАЛЬНАЯ РАЗБИВКА ПО СЛОВАМ И БУКВАМ")
                print("="*60)
                print(f"Найдено слов: {len(group6_words)}")
                print(f"Y центр: {target_y}")
                print()
                
                # Выводим каждое слово с детальной информацией
                for i, word in enumerate(group6_words):
                    print(f"СЛОВО {i+1:2d}: '{word['text']}'")
                    print(f"  Координаты: X={word['x0']:.1f}-{word['x1']:.1f}, Y={word['top']:.1f}")
                    print(f"  Ширина: {word['x1'] - word['x0']:.1f} пикселей")
                    print(f"  Длина текста: {len(word['text'])} символов")
                    
                    # Проверяем на никуд
                    nikud_chars = []
                    regular_chars = []
                    for char in word['text']:
                        if re.search(r'[\u05B0-\u05BD\u05BF-\u05C7]', char):
                            nikud_chars.append(char)
                        else:
                            regular_chars.append(char)
                    
                    if nikud_chars:
                        print(f"  🔤 НИКУД: {len(nikud_chars)} символов")
                    
                    # Проверяем на знаки препинания
                    if re.search(r'[.,:;!?""''(){}\[\]–—]', word['text']):
                        print("  📝 СОДЕРЖИТ ЗНАК ПРЕПИНАНИЯ")
                    
                    # Детальная разбивка по буквам
                    print("  📝 РАЗБИВКА ПО БУКВАМ:")
                    for j, char in enumerate(word['text']):
                        char_code = ord(char)
                        char_type = "НИКУД" if re.search(r'[\u05B0-\u05BD\u05BF-\u05C7]', char) else "БУКВА"
                        if re.search(r'[.,:;!?""''(){}\[\]–—]', char):
                            char_type = "ПРЕПИНАНИЕ"
                        print(f"    {j+1:2d}. '{char}' (U+{char_code:04X}) - {char_type}")
                    
                    print()
                
                # Собираем полный текст группы
                full_text = ' '.join(w['text'] for w in group6_words)
                print("ПОЛНЫЙ ТЕКСТ ГРУППЫ 6:")
                print(f"'{full_text}'")
                print()
                
                # Статистика по типам символов
                total_chars = 0
                total_nikud = 0
                total_punctuation = 0
                total_regular = 0
                
                for word in group6_words:
                    for char in word['text']:
                        total_chars += 1
                        if re.search(r'[\u05B0-\u05BD\u05BF-\u05C7]', char):
                            total_nikud += 1
                        elif re.search(r'[.,:;!?""''(){}\[\]–—]', char):
                            total_punctuation += 1
                        else:
                            total_regular += 1
                
                print("СТАТИСТИКА ПО СИМВОЛАМ:")
                print(f"  Всего символов: {total_chars}")
                print(f"  Обычных букв: {total_regular}")
                print(f"  Никуд: {total_nikud}")
                print(f"  Знаков препинания: {total_punctuation}")
                print(f"  Процент никуда: {(total_nikud/total_chars*100):.1f}%")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_debug_group6_detailed.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group6_detailed(pdf_path)
    
    if success:
        print(f"\n✅ Анализ группы 6 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
