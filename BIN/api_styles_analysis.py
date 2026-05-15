#!/usr/bin/env python3
"""
Анализ двух стилей API и выбор моделей в нашем скрипте
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

def test_old_api_style(api_key, model_id):
    """Тест старого API стиля - v1/chat/completions"""
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
            'api_style': 'OLD (v1/chat/completions)',
            'usage': response.usage.model_dump() if response.usage else None
        }
    except Exception as e:
        return {
            'works': False,
            'error': str(e),
            'api_style': 'OLD (v1/chat/completions)'
        }

def test_new_api_style(api_key, model_id):
    """Тест нового API стиля - v1/responses"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.responses.create(
            model=model_id,
            input="Say 'Hello'"
        )
        
        return {
            'works': True,
            'response': response.output_text,
            'api_style': 'NEW (v1/responses)',
            'usage': response.usage.model_dump() if response.usage else None
        }
    except Exception as e:
        return {
            'works': False,
            'error': str(e),
            'api_style': 'NEW (v1/responses)'
        }

def analyze_script_logic():
    """Анализируем логику нашего скрипта"""
    print("🔍 АНАЛИЗ API СТИЛЕЙ И ВЫБОРА МОДЕЛЕЙ")
    print("=" * 60)
    
    print("\n📋 Два стиля API:")
    print("1. СТАРЫЙ стиль: v1/chat/completions")
    print("   - Параметры: messages, max_tokens, temperature")
    print("   - Работает с: GPT-3.5, GPT-4, GPT-4o")
    print("   - НЕ работает с: большинством GPT-5")
    
    print("\n2. НОВЫЙ стиль: v1/responses")
    print("   - Параметры: input (простой текст)")
    print("   - Работает с: GPT-5-chat-latest")
    print("   - НЕ работает с: GPT-3.5, GPT-4, GPT-4o")
    
    print("\n🤖 Логика нашего скрипта:")
    print("1. Приоритеты моделей: GPT-5 → GPT-4o → GPT-4 → GPT-3.5")
    print("2. Для GPT-5-chat-latest: используем НОВЫЙ API (v1/responses)")
    print("3. Для остальных: используем СТАРЫЙ API (v1/chat/completions)")
    print("4. Автоматический fallback при ошибках")

def main():
    """Главная функция анализа"""
    # Загружаем конфигурацию
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Анализируем логику скрипта
    analyze_script_logic()
    
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ РАБОТЫ СКРИПТА")
    
    # Импортируем функцию поиска моделей
    try:
        from tbox_translator import find_working_gpt_model
        
        class MockConf:
            def __contains__(self, key):
                return False
        
        conf = MockConf()
        
        print("\n🔍 Запускаем find_working_gpt_model()...")
        print("📋 Скрипт будет пробовать модели в таком порядке:")
        
        # Получаем список моделей для демонстрации
        from tbox_translator import get_available_gpt_models
        models = get_available_gpt_models(api_key, conf)
        
        print("\n🎯 ТОП-10 моделей по приоритету:")
        for i, model in enumerate(models[:10], 1):
            api_style = "NEW (v1/responses)" if "5" in model else "OLD (v1/chat/completions)"
            print(f"   {i:2d}. {model} - {api_style}")
        
        print(f"\n🚀 Запускаем поиск рабочей модели...")
        working_model = find_working_gpt_model(api_key, conf)
        
        if working_model:
            print(f"✅ Найдена рабочая модель: {working_model}")
            
            # Показываем какой API используется
            if "5-chat-latest" in working_model:
                print(f"📡 Используется НОВЫЙ API: v1/responses")
            else:
                print(f"💬 Используется СТАРЫЙ API: v1/chat/completions")
                
        else:
            print("❌ Рабочая модель не найдена")
            
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
