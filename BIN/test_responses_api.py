#!/usr/bin/env python3
"""
Тестирование нового API v1/responses для GPT-5 моделей
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

def test_model_with_responses(api_key, model_id):
    """Тестирует модель с новым API v1/responses"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Используем новый API v1/responses без max_tokens
        response = client.responses.create(
            model=model_id,
            input="Say 'Hello'",
            temperature=0.7
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

def test_model_with_chat(api_key, model_id):
    """Тестирует модель с традиционным API v1/chat/completions"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
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
    print("🔍 Тестируем новый API v1/responses для GPT-5...")
    
    # Загружаем конфигурацию
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Импортируем функцию получения моделей
    try:
        from tbox_translator import get_available_gpt_models
        
        class MockConf:
            def __contains__(self, key):
                return False
        
        conf = MockConf()
        models = get_available_gpt_models(api_key, conf)
        
        # Находим GPT-5 модели
        gpt5_models = [m for m in models if 'gpt-5' in m.lower()]
        
        print(f"📊 Тестируем {len(gpt5_models)} GPT-5 моделей...")
        print("=" * 80)
        
        working_responses = []
        working_chat = []
        
        for i, model_id in enumerate(gpt5_models[:10], 1):  # Тестируем первые 10
            print(f"\n🔍 {i}. {model_id}")
            print("-" * 50)
            
            # Тестируем с v1/responses
            print("📡 Тестируем v1/responses...")
            responses_result = test_model_with_responses(api_key, model_id)
            
            if responses_result['works']:
                print(f"✅ v1/responses работает")
                print(f"💬 Ответ: {responses_result['response']}")
                working_responses.append(model_id)
            else:
                print(f"❌ v1/responses не работает: {responses_result['error']}")
            
            # Тестируем с v1/chat/completions
            print("💬 Тестируем v1/chat/completions...")
            chat_result = test_model_with_chat(api_key, model_id)
            
            if chat_result['works']:
                print(f"✅ v1/chat/completions работает")
                print(f"💬 Ответ: {chat_result['response']}")
                working_chat.append(model_id)
            else:
                print(f"❌ v1/chat/completions не работает: {chat_result['error']}")
        
        print("\n" + "=" * 80)
        print(f"📈 Результаты:")
        print(f"   Работают с v1/responses: {len(working_responses)}")
        print(f"   Работают с v1/chat/completions: {len(working_chat)}")
        
        if working_responses:
            print(f"\n✅ Модели, работающие с v1/responses:")
            for model in working_responses:
                print(f"   🚀 {model}")
        
        if working_chat:
            print(f"\n✅ Модели, работающие с v1/chat/completions:")
            for model in working_chat:
                print(f"   💬 {model}")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
