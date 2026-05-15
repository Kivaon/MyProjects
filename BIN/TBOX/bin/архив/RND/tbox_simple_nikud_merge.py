#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def is_nikud(text: str) -> bool:
    """Проверяет, является ли текст никудом"""
    return bool(re.fullmatch(r'[\u05B0-\u05BD\u05BF-\u05C7]', text))

def has_nikud_in_text(text: str) -> bool:
    """Проверяет, есть ли никуд в тексте"""
    return bool(re.search(r'[\u05B0-\u05BD\u05BF-\u05C7]', text))

def simple_nikud_merge(words: List[Dict]) -> List[Dict]:
    """Простой алгоритм объединения слов с никудом и соседними словами"""
    if not words:
        return words
    
    print("🔍 ПРОСТОЙ АЛГОРИТМ ОБЪЕДИНЕНИЯ НИКУД")
    print("="*50)
    
    # Сортируем слова по X координате
    sorted_words = sorted(words, key=lambda w: w['x0'])
    
    print(f"📊 Всего слов: {len(sorted_words)}")
    
    # Находим слова с никудом
    nikud_indices = []
    for i, word in enumerate(sorted_words):
        if is_nikud(word['text']) or has_nikud_in_text(word['text']):
            nikud_indices.append(i)
    
    print(f"🔤 Слов с никудом: {len(nikud_indices)}")
    print(f"📍 Индексы слов с никудом: {nikud_indices}")
    print()
    
    # Объединяем слова с никудом с соседними словами
    merged_words = []
    skip_indices = set()
    
    for i in range(len(sorted_words)):
        if i in skip_indices:
            continue
        
        word = sorted_words[i]
        
        # Если в слове есть никуд - проверяем соседей
        if has_nikud_in_text(word['text']):
            print(f"🔤 Найдено слово с никудом: '{word['text']}' (индекс {i})")
            
            # Ищем соседние слова
            left_word = sorted_words[i-1] if i > 0 else None
            right_word = sorted_words[i+1] if i < len(sorted_words)-1 else None
            
            print(f"  ⬅️  Левое слово: {left_word['text'] if left_word else 'None'}")
            print(f"  ➡️  Правое слово: {right_word['text'] if right_word else 'None'}")
            
            # Проверяем соседние слова на близость X координат
            merged_with_left = False
            merged_with_right = False
            
            # Проверяем левого соседа (следующее слово в RTL)
            if left_word:
                # В RTL: конец левого слова должен быть близок к началу текущего
                distance_left = abs(left_word['x0'] - word['x1'])
                print(f"  📏 Расстояние до левого (RTL): {distance_left:.1f} пикселей")
                
                if distance_left <= 5.0:  # Порог для объединения
                    print(f"  ✅ Объединяем с левым словом: '{left_word['text']}' (расстояние: {distance_left:.1f})")
                    # В RTL левое слово идет после текущего
                    word['text'] = word['text'] + left_word['text']
                    word['x1'] = max(word['x1'], left_word['x1'])
                    skip_indices.add(i-1)  # Пропускаем левое слово
                    merged_with_left = True
                    print(f"  🔗 Результат: '{word['text']}'")
            
            # Проверяем правого соседа (предыдущее слово в RTL)
            if right_word and not merged_with_left:
                # В RTL: конец текущего слова должен быть близок к началу правого
                distance_right = abs(right_word['x0'] - word['x1'])
                print(f"  📏 Расстояние до правого (RTL): {distance_right:.1f} пикселей")
                
                if distance_right <= 5.0:  # Порог для объединения
                    print(f"  ✅ Объединяем с правым словом: '{right_word['text']}' (расстояние: {distance_right:.1f})")
                    # В RTL правое слово идет перед текущим
                    right_word['text'] = right_word['text'] + word['text']
                    right_word['x0'] = min(word['x0'], right_word['x0'])
                    right_word['x1'] = max(word['x1'], right_word['x1'])
                    skip_indices.add(i)  # Пропускаем текущее слово
                    merged_with_right = True
                    print(f"  🔗 Результат: '{right_word['text']}'")
            
            if not merged_with_left and not merged_with_right:
                print(f"  ❌ Не найдено подходящих соседей для объединения")
                merged_words.append(word)
        else:
            # Обычное слово - просто добавляем
            merged_words.append(word)
    
    print()
    print(f"📊 Убрано слов: {len(skip_indices)}")
    print(f"📊 Осталось слов: {len(merged_words)}")
    
    return merged_words

def analyze_group6_simple_merge(pdf_path: str):
    """Анализ ГРУППЫ 6 с простым объединением никуда"""
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
                
                print("ГРУППА 6 - ПРОСТОЕ ОБЪЕДИНЕНИЕ НИКУД")
                print("="*60)
                print(f"Найдено слов: {len(group6_words)}")
                print()
                
                # Показываем исходные слова
                print("📋 ИСХОДНЫЕ СЛОВА:")
                for i, word in enumerate(group6_words):
                    nikud_status = "🔤" if is_nikud(word['text']) or has_nikud_in_text(word['text']) else "📝"
                    print(f"  {i+1:2d}. '{word['text']}' (X:{word['x0']:.1f}-{word['x1']:.1f}) {nikud_status}")
                print()
                
                # Применяем простой алгоритм объединения
                merged_words = simple_nikud_merge(group6_words)
                
                print()
                print("📋 РЕЗУЛЬТАТ ОБЪЕДИНЕНИЯ:")
                for i, word in enumerate(merged_words):
                    nikud_status = "🔤" if is_nikud(word['text']) or has_nikud_in_text(word['text']) else "📝"
                    print(f"  {i+1:2d}. '{word['text']}' (X:{word['x0']:.1f}-{word['x1']:.1f}) {nikud_status}")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python tbox_simple_nikud_merge.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    success = analyze_group6_simple_merge(pdf_path)
    
    if success:
        print(f"\n✅ Анализ с простым объединением никуда завершен успешно")
    else:
        print(f"\n❌ Анализ завершен с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    main()
