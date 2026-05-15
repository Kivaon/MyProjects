#!/usr/bin/env python3
"""
Тестирование новой системы ограничений чанков
"""

import subprocess
import sys
import os

def test_chunk_limit(limit, description):
    """Тестируем лимит чанков"""
    print(f"\n🧪 Тестируем лимит: {limit} символов")
    print(f"📝 Описание: {description}")
    
    # Создаем тестовый файл (~25K символов)
    test_text = """
    This is a test document with multiple paragraphs to check chunking behavior.
    The first paragraph contains some introductory information about the topic.
    
    The second paragraph goes into more detail and provides specific examples.
    It includes technical terminology and complex sentence structures that need careful translation.
    
    The third paragraph discusses implications and consequences of the topic.
    It contains longer sentences and more sophisticated vocabulary.
    
    The fourth paragraph provides a conclusion and summary of the main points.
    This should test how well the chunking algorithm handles different text structures.
    
    Additional content to ensure we exceed the normal chunk limits and test the new functionality.
    More text here to make sure we have enough content to trigger multiple chunks.
    Even more text to test the boundary detection and smart splitting algorithms.
    Final paragraph to complete the test document with sufficient length.
    """
    
    with open('test_chunk_limits.txt', 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    try:
        # Запускаем с разнымы лимитами
        cmd = ['python3', 'TBOX/tbox_translator.py', '--gpt', 'test_chunk_limits.txt', '-s', '--no-archive']
        if limit != 'default':
            cmd.insert(-1, f'--max-chars={limit}')
        
        print(f"🚀 Команда: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/kivaonmac/Documents/AI_Lab/BIN')
        
        print(f"📤 STDOUT (последние 10 строк):")
        lines = result.stdout.split('\n')[-10:]
        for line in lines:
            if line.strip():
                print(f"   {line}")
        
        if result.stderr:
            print(f"❌ STDERR:")
            print(result.stderr)
        
        print(f"🔄 Код возврата: {result.returncode}")
        
        # Ищем информацию о чанках
        if "Текст разбит на" in result.stdout:
            for line in result.stdout.split('\n'):
                if "Текст разбит на" in line:
                    print(f"📦 {line.strip()}")
                    break
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
    
    finally:
        # Удаляем тестовые файлы
        for file in ['test_chunk_limits.txt', 'test_chunk_limits.docx']:
            if os.path.exists(file):
                os.remove(file)

def main():
    """Главная функция"""
    print("🔍 Тестирование системы ограничений чанков...")
    
    # Тестируем разные лимиты
    test_chunk_limit('default', 'Лимит из модели (17,202 символов)')
    test_chunk_limit(8000, 'Лимит из конфига (8,000 символов)')
    test_chunk_limit(5000, 'Маленький лимит (5,000 символов)')
    test_chunk_limit(3000, 'Очень маленький лимит (3,000 символов)')

if __name__ == "__main__":
    main()
