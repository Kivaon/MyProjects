#!/usr/bin/env python3

# Временный скрипт для отладки y-координат слов

def debug_y_coordinates(lines):
    """Выводит y-координаты слов для отладки"""
    print("ОТЛАДКА Y-КООРДИНАТ СЛОВ:")
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
    # Тестовые данные
    test_lines = [
        # Здесь нужно будет вставить реальные данные
    ]
    debug_y_coordinates(test_lines)
