#!/usr/bin/env python3
"""
Тестирование новой модели gpt-4o-mini
"""

import subprocess
import sys
import os

def test_gpt4o_mini():
    """Тестируем gpt-4o-mini модель"""
    print("🧪 Тестируем новую модель gpt-4o-mini")
    
    # Создаем тестовый файл
    test_text = """
    This is a comprehensive test document to evaluate the performance of gpt-4o-mini model.
    The document contains multiple paragraphs with varying complexity and technical terminology.
    
    The first paragraph introduces the fundamental concepts and establishes the context.
    It includes detailed explanations of key terms and provides background information.
    
    The second section delves into more advanced topics and presents complex arguments.
    This section features longer sentences with multiple clauses and sophisticated vocabulary.
    
    The third section examines practical applications and real-world implications.
    It includes case studies, examples, and detailed analysis.
    
    The fourth section provides a comprehensive conclusion that synthesizes the main points.
    This section ties together the various threads of the discussion.
    """
    
    with open('test_gpt4o.txt', 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    try:
        # Запускаем с gpt-4o-mini
        cmd = ['python3', 'TBOX/tbox_translator.py', '--gpt', 'test_gpt4o.txt', '-s', '--no-archive']
        print(f"🚀 Команда: {' '.join(cmd)}")
        print(f"📊 Размер текста: {len(test_text):,} символов")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/kivaonmac/Documents/AI_Lab/BIN')
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Время выполнения: {duration:.2f} секунд")
        
        # Ищем ключевую информацию
        important_lines = []
        for line in result.stdout.split('\n'):
            if any(keyword in line for keyword in [
                "Будет использована GPT модель", "Лимит чанка", "Текст разбит на",
                "Обработано чанков", "Входные токены", "Выходные токены", 
                "Общая стоимость", "ГОТОВО"
            ]):
                important_lines.append(line.strip())
        
        print(f"\n📋 Ключевая информация:")
        for line in important_lines:
            print(f"   {line}")
        
        print(f"\n🔄 Код возврата: {result.returncode}")
        
        # Оценка производительности
        if duration < 30:
            print("🚀 ОТЛИЧНО: Очень быстрая модель!")
        elif duration < 60:
            print("✅ ХОРОШО: Быстрая модель")
        elif duration < 120:
            print("🟡 НОРМАЛЬНО: Средняя скорость")
        else:
            print("🔴 МЕДЛЕННО: Требует оптимизации")
            
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
    
    finally:
        # Удаляем тестовые файлы
        for file in ['test_gpt4o.txt', 'test_gpt4o.docx']:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    import time
    test_gpt4o_mini()
