#!/usr/bin/env python3
"""
Тестирование gpt-5.5 с обоими API для определения правильного
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

def main():
    """Главная функция тестирования"""
    print("🔍 Тестируем gpt-5.5 с обоими API...")
    
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    client = openai.OpenAI(api_key=api_key)
    model_id = "gpt-5.5"
    
    print(f"\n🎯 Модель: {model_id}")
    print("=" * 60)
    
    # Тестируем СТАРЫЙ API
    print("\n💬 Тест СТАРОГО API (v1/chat/completions):")
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=10,
            temperature=0.7
        )
        print(f"✅ СТАРЫЙ API работает!")
        print(f"💬 Ответ: {response.choices[0].message.content}")
        if response.usage:
            print(f"📊 Токены: {response.usage.total_tokens}")
    except Exception as e:
        print(f"❌ СТАРЫЙ API не работает: {str(e)}")
    
    # Тестируем НОВЫЙ API
    print("\n📡 Тест НОВОГО API (v1/responses):")
    try:
        response = client.responses.create(
            model=model_id,
            input="Say 'Hello'"
        )
        print(f"✅ НОВЫЙ API работает!")
        print(f"💬 Ответ: {response.output_text}")
        if response.usage:
            print(f"📊 Токены: {response.usage.total_tokens}")
    except Exception as e:
        print(f"❌ НОВЫЙ API не работает: {str(e)}")
    
    print("\n" + "=" * 60)
    print("📈 Вывод: какой API использовать для gpt-5.5?")

if __name__ == "__main__":
    main()
