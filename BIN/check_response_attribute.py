#!/usr/bin/env python3
"""
Проверка атрибута response в новых моделях
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

def check_response_attribute(api_key, model_id):
    """Проверяет атрибут response в модели"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        print(f"\n🔍 Проверяем {model_id}...")
        
        # Тестируем СТАРЫЙ API
        print("💬 Тест СТАРОГО API (chat/completions):")
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
            
            print(f"✅ СТАРЫЙ API работает")
            print(f"📋 Тип ответа: {type(response)}")
            
            # Проверяем атрибуты ответа
            print(f"🔍 Атрибуты ответа:")
            for attr in dir(response):
                if not attr.startswith('_'):
                    try:
                        value = getattr(response, attr)
                        if not callable(value):
                            print(f"   {attr}: {value}")
                    except:
                        pass
            
            # Проверяем есть ли атрибут response
            if hasattr(response, 'response'):
                print(f"🎯 Найден атрибут response: {response.response}")
            else:
                print(f"❌ Атрибут response не найден")
                
        except Exception as e:
            print(f"❌ СТАРЫЙ API не работает: {str(e)}")
        
        # Тестируем НОВЫЙ API
        print("\n📡 Тест НОВОГО API (responses):")
        try:
            response = client.responses.create(
                model=model_id,
                input="Say 'Hello'"
            )
            
            print(f"✅ НОВЫЙ API работает")
            print(f"📋 Тип ответа: {type(response)}")
            
            # Проверяем атрибуты ответа
            print(f"🔍 Атрибуты ответа:")
            for attr in dir(response):
                if not attr.startswith('_'):
                    try:
                        value = getattr(response, attr)
                        if not callable(value):
                            print(f"   {attr}: {value}")
                    except:
                        pass
            
            # Проверяем есть ли атрибут response
            if hasattr(response, 'response'):
                print(f"🎯 Найден атрибут response: {response.response}")
            else:
                print(f"❌ Атрибут response не найден")
                
        except Exception as e:
            print(f"❌ НОВЫЙ API не работает: {str(e)}")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

def main():
    """Главная функция"""
    print("🔍 Проверка атрибута response в новых моделях...")
    
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Проверяем разные модели
    models_to_check = [
        'gpt-5.5',
        'gpt-5-chat-latest',
        'gpt-4o',
        'gpt-4'
    ]
    
    for model in models_to_check:
        check_response_attribute(api_key, model)
        print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
