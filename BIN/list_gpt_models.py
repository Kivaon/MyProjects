#!/usr/bin/env python3
"""
Получение списка доступных GPT моделей с приоритетом более быстрых
"""

import openai
import sys
import os

def load_config():
    """Загружаем конфигурацию"""
    config = {}
    with open('_config/tconfig.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value.strip()
    return config

def list_available_models():
    """Получаем список всех доступных моделей"""
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    client = openai.OpenAI(api_key=api_key)
    
    try:
        print("🔍 Запрос списка моделей у OpenAI API...")
        models = client.models.list()
        
        # Фильтруем только GPT модели
        gpt_models = []
        for model in models.data:
            model_id = model.id
            if 'gpt' in model_id.lower():
                gpt_models.append(model_id)
        
        # Сортируем по приоритету (более быстрые в начале)
        priority_order = [
            'gpt-3.5', 'gpt-4', 'gpt-4o', 'gpt-4o-mini', 
            'gpt-5', 'gpt-5.5', 'gpt-5-chat'
        ]
        
        def get_priority(model_id):
            for i, priority in enumerate(priority_order):
                if priority in model_id.lower():
                    return i
            return 999  # В конце списка
        
        gpt_models.sort(key=get_priority)
        
        print(f"\n📋 Найдено {len(gpt_models)} GPT моделей:")
        print("=" * 60)
        
        for i, model in enumerate(gpt_models, 1):
            # Определяем тип модели
            if '3.5' in model.lower():
                model_type = "🟢 Быстрый/Дешевый"
            elif '4o-mini' in model.lower():
                model_type = "🟡 Быстрый/Средний"
            elif '4o' in model.lower():
                model_type = "🟠 Средний/Быстрый"
            elif '4' in model.lower():
                model_type = "🔴 Тяжелый/Дорогой"
            elif '5' in model.lower():
                model_type = "🔴 Очень тяжелый/Медленный"
            else:
                model_type = "⚪ Неизвестный тип"
            
            print(f"{i:2d}. {model:<40} {model_type}")
        
        print("=" * 60)
        
        # Рекомендации
        print("\n💡 РЕКОМЕНДАЦИИ ДЛЯ БЫСТРОГО ПЕРЕВОДА:")
        print("1. 🟢 gpt-3.5-turbo - самый быстрый и дешевый")
        print("2. 🟡 gpt-4o-mini - хороший баланс скорости и качества")
        print("3. 🟠 gpt-4o - высокое качество, приемлемая скорость")
        print("4. 🔴 Избегать gpt-5 моделей для быстрых задач")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    list_available_models()
