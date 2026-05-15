#!/usr/bin/env python3
"""
Тестирование исправленной логики --gpt параметра
"""

import subprocess
import sys
import os

def test_gpt_param():
    """Тестируем --gpt параметр"""
    print("🧪 Тестируем --gpt параметр (должен использовать модель из конфига без поиска)")
    
    # Создаем тестовый файл
    test_text = "Hello world! This is a test of the fixed --gpt parameter logic."
    with open('test_gpt_fix.txt', 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    try:
        # Запускаем tbox_translator с --gpt
        cmd = ['python3', 'TBOX/tbox_translator.py', '--gpt', 'test_gpt_fix.txt', '-s', '--no-archive']
        print(f"🚀 Команда: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/kivaonmac/Documents/AI_Lab/BIN')
        
        print(f"📤 STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"❌ STDERR:\n{result.stderr}")
        print(f"🔄 Код возврата: {result.returncode}")
        
        # Проверяем что НЕ было поиска модели
        if "Поиск рабочей GPT модели" not in result.stdout:
            print("✅ УСПЕХ: Поиск модели не запускался (как и ожидалось)")
        else:
            print("❌ ПРОБЛЕМА: Поиск модели запускался (не должен был)")
        
        # Проверяем что была использована модель из конфига
        if "Используем модель из конфига" in result.stdout:
            print("✅ УСПЕХ: Модель использована из конфига")
        else:
            print("❌ ПРОБЛЕМА: Модель не была использована из конфига")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
    
    finally:
        # Удаляем тестовые файлы
        for file in ['test_gpt_fix.txt', 'test_gpt_fix.docx']:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    test_gpt_param()
