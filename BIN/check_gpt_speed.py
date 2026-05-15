#!/usr/bin/env python3
"""
Проверка скорости работы GPT-5.5 Pro API
"""

import time
import openai
import sys
import os

# Загружаем конфигурацию
def load_config():
    config = {}
    with open('_config/tconfig.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value.strip()
    return config

def test_gpt_speed():
    """Тестируем скорость ответа GPT-5.5 Pro"""
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    client = openai.OpenAI(api_key=api_key)
    
    # Простой тестовый запрос
    test_prompt = "Translate this to Russian: 'Hello world, how are you today?'"
    
    print("🧪 Тестируем скорость GPT-5.5 Pro...")
    print(f"📝 Запрос: {test_prompt}")
    
    try:
        start_time = time.time()
        
        response = client.responses.create(
            model="gpt-5.5-pro-2026-04-23",
            input=test_prompt
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ Ответ получен за {response_time:.2f} секунд")
        print(f"📄 Результат: {response.output_text}")
        
        if response_time > 30:
            print("⚠️  ОЧЕНЬ МЕДЛЕННЫЙ ОТВЕТ (>30 сек)")
        elif response_time > 10:
            print("⚠️  МЕДЛЕННЫЙ ОТВЕТ (>10 сек)")
        elif response_time > 5:
            print("✅  Нормальный ответ (5-10 сек)")
        else:
            print("🚀  БЫСТРЫЙ ОТВЕТ (<5 сек)")
            
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    test_gpt_speed()
