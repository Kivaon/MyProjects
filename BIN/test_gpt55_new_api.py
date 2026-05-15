#!/usr/bin/env python3
"""
Тестирование gpt-5.5-pro-2026-04-23 с НОВЫМ API v1/responses
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

def test_model_with_new_api(api_key, model_id):
    """Тестируем модель с НОВЫМ API v1/responses"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        print(f"📡 Тестируем {model_id} с НОВЫМ API v1/responses...")
        
        response = client.responses.create(
            model=model_id,
            input="Say 'Hello'"
        )
        
        return {
            'works': True,
            'response': response.output_text,
            'usage': response.usage.model_dump() if response.usage else None
        }
    except Exception as e:
        return {
            'works': False,
            'error': str(e)
        }

def test_model_with_old_api(api_key, model_id):
    """Тестируем модель со СТАРЫМ API v1/chat/completions"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        print(f"💬 Тестируем {model_id} со СТАРЫМ API v1/chat/completions...")
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=10,
            temperature=0.7
        )
        
        return {
            'works': True,
            'response': response.choices[0].message.content,
            'usage': response.usage.model_dump() if response.usage else None
        }
    except Exception as e:
        return {
            'works': False,
            'error': str(e)
        }

def main():
    """Главная функция тестирования"""
    print("🔍 Тестируем gpt-5.5-pro-2026-04-23 с разными API...")
    
    # Загружаем конфигурацию
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    model_id = "gpt-5.5-pro-2026-04-23"
    
    print(f"\n🎯 Модель: {model_id}")
    print("=" * 60)
    
    # Тестируем со СТАРЫМ API
    old_result = test_model_with_old_api(api_key, model_id)
    
    if old_result['works']:
        print(f"✅ СТАРЫЙ API работает")
        print(f"💬 Ответ: {old_result['response']}")
    else:
        print(f"❌ СТАРЫЙ API не работает")
        print(f"🚫 Ошибка: {old_result['error']}")
    
    print("\n" + "-" * 60)
    
    # Тестируем с НОВЫМ API
    new_result = test_model_with_new_api(api_key, model_id)
    
    if new_result['works']:
        print(f"✅ НОВЫЙ API работает")
        print(f"💬 Ответ: {new_result['response']}")
        if new_result['usage']:
            print(f"📊 Использование: {new_result['usage']}")
    else:
        print(f"❌ НОВЫЙ API не работает")
        print(f"🚫 Ошибка: {new_result['error']}")
    
    print("\n" + "=" * 60)
    print("📈 Вывод:")
    
    if old_result['works'] and new_result['works']:
        print("🎉 Оба API работают!")
    elif old_result['works']:
        print("📱 Работает только СТАРЫЙ API")
    elif new_result['works']:
        print("🚀 Работает только НОВЫЙ API")
    else:
        print("❌ Ни один API не работает")

if __name__ == "__main__":
    main()
