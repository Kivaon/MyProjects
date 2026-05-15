#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции get_available_gpt_models
"""

import openai
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(__file__))

def load_config():
    """Загружает конфигурацию из файла"""
    config = {}
    with open('_config/tconfig.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value.strip()
    return config

def simple_log(message, meta, level, conf):
    """Простая функция логирования"""
    print(f"[{level}] {message}")

# Импортируем функцию
try:
    from tbox_translator import get_available_gpt_models
    print("✅ Функция get_available_gpt_models импортирована")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def main():
    """Главная функция теста"""
    print("🔍 Тестируем получение списка GPT моделей от OpenAI API...")
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Получаем API ключ
    api_key = config.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в конфигурации")
        return
    
    print(f"🔑 API ключ: {api_key[:20]}...")
    
    # Создаем mock conf для логирования
    class MockConf:
        def __contains__(self, key):
            return False  # Возвращаем False для проверки 'LOG_FILE' in conf
    
    conf = MockConf()
    META = "test"
    
    try:
        # Вызываем функцию
        models = get_available_gpt_models(api_key, conf)
        
        print(f"\n✅ Получено {len(models)} GPT моделей:")
        print("=" * 50)
        
        for i, model in enumerate(models, 1):
            print(f"   {i:2d}. {model}")
        
        print("=" * 50)
        print(f"🎯 Первая модель (самая приоритетная): {models[0] if models else 'None'}")
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
