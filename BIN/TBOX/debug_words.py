#!/usr/bin/env python3

# Скрипт для отладки y-координат слов

def debug_words_y_coordinates(words):
    """Выводит y-координаты слов для отладки"""
    print("ОТЛАДКА Y-КООРДИНАТ СЛОВ:")
    print("="*60)
    
    for i, word in enumerate(words):
        print(f"Слово {i+1}: y0={word.y0:.1f}, y1={word.y1:.1f}, текст='{word.text[:20]}...'")
    
    print("\n" + "="*60)
    
    # Группируем слова по строкам (простой алгоритм)
    lines = []
    current_line = [words[0]]
    
    for i in range(len(words) - 1):
        current_word = words[i]
        next_word = words[i + 1]
        
        # Простой разрыв по X
        gap = abs(next_word.x0 - current_word.x1)
        if gap > 14.0:
            lines.append(current_line)
            current_line = [next_word]
        else:
            current_line.append(next_word)
    
    lines.append(current_line)
    
    print("\nГРУППИРОВКА В СТРОКИ:")
    print("="*60)
    
    for i, line in enumerate(lines):
        print(f"\nСТРОКА {i+1}:")
        for j, word in enumerate(line):
            print(f"  Слово {j+1}: y0={word.y0:.1f}, y1={word.y1:.1f}, текст='{word.text[:20]}...'")
        
        y0 = min(w.y0 for w in line)
        y1 = max(w.y1 for w in line)
        print(f"  РЕЗУЛЬТАТ: y0={y0:.1f}, y1={y1:.1f}, диапазон={y1-y0:.1f}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    # Пример использования
    print("Этот скрипт нужно интегрировать в основной код для отладки")
