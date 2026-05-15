#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def analyze_group7_words(pdf_path: str):
    """Разбивает на слова текст из ГРУППА 7 для анализа"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                page = pdf.pages[0]
                words = page.extract_words()
                
                # Находим группу 7 (Y центр около 262.6)
                group7_words = []
                target_y = 262.6
                y_tolerance = 5.0
                
                for word in words:
                    if abs(word['top'] - target_y) <= y_tolerance:
                        group7_words.append(word)
                
                # Сортируем по X координате
                group7_words.sort(key=lambda w: w['x0'])
                
                print("ГРУППА 7 - РАЗБИВКА НА СЛОВА")
                print("="*60)
                print(f"Найдено слов: {len(group7_words)}")
                print(f"Y центр: {target_y}")
                print()
                
                # Выводим каждое слово и его координаты
                for i, word in enumerate(group7_words):
                    print(f"СЛОВО {i+1:2d}: '{word['text']}'")
                    print(f"  Координаты: X={word['x0']:.1f}-{word['x1']:.1f}, Y={word['top']:.1f}")
                    print(f"  Ширина: {word['x1'] - word['x0']:.1f} пикселей")
                    print(f"  Длина текста: {len(word['text'])} символов")
                    
                    # Проверяем на никуд
                    if re.search(r'[\u05B0-\u05BD\u05BF-\u05C7]', word['text']):
                        print("  🔤 СОДЕРЖИТ НИКУД")
                    
                    # Проверяем на знаки препинания
                    if re.search(r'[.,:;!?""''(){}\[\]–—]', word['text']):
                        print("  📝 СОДЕРЖИТ ЗНАК ПРЕПИНАНИЯ")
                    
                    print()
                
                # Собираем полный текст группы
                full_text = ' '.join(w['text'] for w in group7_words)
                print("ПОЛНЫЙ ТЕКСТ ГРУППЫ 7:")
                print(f"'{full_text}'")
                print()
                
                # Анализируем разрывы между словами
                print("АНАЛИЗ РАЗРЫВОВ МЕЖДУ СЛОВАМИ:")
                print("-" * 40)
                
                font_size = 12.0
                adaptive_gap_threshold = font_size * 1.2  # 14.4 пикселей
                
                for i in range(len(group7_words) - 1):
                    current_word = group7_words[i]
                    next_word = group7_words[i + 1]
                    
                    gap = next_word['x0'] - current_word['x1']
                    
                    print(f"Разрыв {i+1:2d}: '{current_word['text']}' → '{next_word['text']}'")
                    print(f"  Расстояние: {gap:.1f} пикселей")
                    print(f"  Порог: {adaptive_gap_threshold:.1f} пикселей")
                    
                    if gap > adaptive_gap_threshold:
                        print(f"  🔄 РАЗДЕЛЕНИЕ НА СТРОКИ!")
                    else:
                        print(f"  ➡️  Продолжение строки")
                    
                    print()
                
                # Ищем конкретно слова שמות и כאשר
                print("ПОИСК СЛОВ 'שמות' И 'כאשר':")
                print("-" * 30)
                
                shemot_word = None
                kaasher_word = None
                
                for word in group7_words:
                    if 'שמות' in word['text']:
                        shemot_word = word
                        print(f"Найдено 'שמות': '{word['text']}' на X={word['x0']:.1f}-{word['x1']:.1f}")
                    elif 'כאשר' in word['text']:
                        kaasher_word = word
                        print(f"Найдено 'כאשר': '{word['text']}' на X={word['x0']:.1f}-{word['x1']:.1f}")
                
                if shemot_word and kaasher_word:
                    gap = kaasher_word['x0'] - shemot_word['x1']
                    print(f"Разрыв между ними: {gap:.1f} пикселей")
                    print(f"Порог разрыва: {adaptive_gap_threshold:.1f} пикселей")
                    
                    if gap > adaptive_gap_threshold:
                        print("🔄 ДОЛЖНО БЫТЬ РАЗДЕЛЕНИЕ НА СТРОКИ!")
                    else:
                        print("➡️  РАЗРЫВ НЕДОСТАТОЧЕН ДЛЯ РАЗДЕЛЕНИЯ")
                else:
                    print("❌ Слова 'שמות' и 'כאשר' не найдены как отдельные слова")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_debug_group7_words.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group7_words(pdf_path)
    
    if success:
        print(f"\n✅ Анализ группы 7 завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
