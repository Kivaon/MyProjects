#!/usr/bin/env python3
"""
Детальная отладка GPT-5 моделей - почему они не работают
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

def test_gpt5_model_detailed(api_key, model_id):
    """Детально тестируем GPT-5 модель"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        print(f"\n🔍 Тестируем {model_id}:")
        print("-" * 50)
        
        # Тестируем с НОВЫМ API
        print("📡 Пробуем НОВЫЙ API (v1/responses)...")
        try:
            response = client.responses.create(
                model=model_id,
                input="Say 'Hello'"
            )
            print(f"✅ НОВЫЙ API работает!")
            print(f"💬 Ответ: {response.output_text}")
            print(f"📊 Токены: {response.usage.total_tokens if response.usage else 'N/A'}")
            return True
        except Exception as e:
            print(f"❌ НОВЫЙ API ошибка: {str(e)}")
            
            # Пробуем разные подходы
            print(f"\n🔧 Пробуем исправить...")
            
            # Пробуем с температурой
            try:
                response = client.responses.create(
                    model=model_id,
                    input="Say 'Hello'",
                    temperature=0.7
                )
                print(f"✅ С температурой работает!")
                print(f"💬 Ответ: {response.output_text}")
                return True
            except Exception as e2:
                print(f"❌ С температурой ошибка: {str(e2)}")
            
            # Пробуем с max_tokens
            try:
                response = client.responses.create(
                    model=model_id,
                    input="Say 'Hello'",
                    max_tokens=10
                )
                print(f"✅ С max_tokens работает!")
                print(f"💬 Ответ: {response.output_text}")
                return True
            except Exception as e3:
                print(f"❌ С max_tokens ошибка: {str(e3)}")
            
            # Пробуем с разными промптами
            test_prompts = [
                "Hello",
                "Say hello",
                "Respond with hello",
                "Hi"
            ]
            
            for prompt in test_prompts:
                try:
                    response = client.responses.create(
                        model=model_id,
                        input=prompt
                    )
                    print(f"✅ С промптом '{prompt}' работает!")
                    print(f"💬 Ответ: {response.output_text}")
                    return True
                except:
                    continue
        
        return False
        
    except Exception as e:
        print(f"❌ Общая ошибка: {str(e)}")
        return False

def main():
    """Главная функция отладки"""
    print("🔍 Детальная отладка GPT-5 моделей...")
    
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Тестируем несколько GPT-5 моделей
    test_models = [
        'gpt-5.5',
        'gpt-5-chat-latest',
        'gpt-5',
        'gpt-5.5-pro-2026-04-23'
    ]
    
    working_models = []
    
    for model in test_models:
        if test_gpt5_model_detailed(api_key, model):
            working_models.append(model)
    
    print("\n" + "=" * 60)
    print("📈 РЕЗУЛЬТАТЫ:")
    print(f"✅ Рабочие модели: {len(working_models)}")
    for model in working_models:
        print(f"   🚀 {model}")
    
    if not working_models:
        print("❌ Нет рабочих моделей")
        print("\n🔧 Возможные проблемы:")
        print("1. Неправильный API ключ")
        print("2. Модели требуют другого формата запроса")
        print("3. Модели требуют специальных параметров")
        print("4. Модели еще не доступны для этого API ключа")

if __name__ == "__main__":
    main()
