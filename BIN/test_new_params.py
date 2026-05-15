#!/usr/bin/env python3
"""
Тестирование новых параметров --gpt и --gptlast
"""

import subprocess
import sys
import os

def test_param(param_name, description):
    """Тестируем параметр"""
    print(f"\n🧪 Тестируем параметр: {param_name}")
    print(f"📝 Описание: {description}")
    
    # Создаем тестовый файл
    test_text = "Hello world! This is a test of the new parameter system."
    with open('test_file.txt', 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    try:
        # Запускаем tbox_translator с параметром
        cmd = ['python3', 'TBOX/tbox_translator.py', param_name, 'test_file.txt', '-s']
        print(f"🚀 Команда: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/kivaonmac/Documents/AI_Lab/BIN')
        
        print(f"📤 STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"❌ STDERR:\n{result.stderr}")
        print(f"🔄 Код возврата: {result.returncode}")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
    
    finally:
        # Удаляем тестовый файл
        if os.path.exists('test_file.txt'):
            os.remove('test_file.txt')
        if os.path.exists('test_file.docx'):
            os.remove('test_file.docx')

def main():
    """Главная функция"""
    print("🔍 Тестирование новых параметров GPT...")
    
    # Тестируем --gpt (модель из конфига)
    test_param('--gpt', 'Использовать GPT модель из конфига (gpt-5.5-pro-2026-04-23)')
    
    # Тестируем --gptlast (поиск последней модели)
    test_param('--gptlast', 'Использовать последнюю доступную GPT модель')
    
    # Тестируем без параметра (Gemini по умолчанию)
    test_param('', 'Использовать Gemini по умолчанию')

if __name__ == "__main__":
    main()
