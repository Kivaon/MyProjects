#!/usr/bin/env python3
"""
Анализ GPT-5 моделей и их характеристик
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

def test_model(api_key, model_id):
    """Тестирует модель на работоспособность"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Простой тестовый запрос
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

def get_model_details(api_key, model_id):
    """Получает детальную информацию о модели"""
    try:
        client = openai.OpenAI(api_key=api_key)
        model = client.models.retrieve(model_id)
        
        details = {
            'id': model.id,
            'created': model.created,
            'owned_by': model.owned_by,
            'object': model.object
        }
        
        # Конвертируем timestamp в дату
        import datetime
        if model.created:
            created_date = datetime.datetime.fromtimestamp(model.created)
            details['created_date'] = created_date.strftime('%Y-%m-%d')
        
        return details
    except Exception as e:
        return {'error': str(e)}

def main():
    """Главная функция анализа"""
    print("🔍 Анализ GPT-5 моделей...")
    
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
        
        # Находим все GPT-5 модели
        gpt5_models = [m for m in models if 'gpt-5' in m.lower()]
        
        print(f"📊 Найдено {len(gpt5_models)} GPT-5 моделей:")
        print("=" * 80)
        
        working_gpt5 = []
        
        for i, model_id in enumerate(gpt5_models, 1):
            print(f"\n🔍 {i}. {model_id}")
            print("-" * 50)
            
            # Получаем детали
            details = get_model_details(api_key, model_id)
            if 'error' not in details:
                print(f"📅 Создана: {details.get('created_date', 'N/A')}")
                print(f"👤 Владелец: {details.get('owned_by', 'N/A')}")
            
            # Тестируем работоспособность
            test_result = test_model(api_key, model_id)
            
            if test_result['works']:
                print(f"✅ РАБОТАЕТ")
                print(f"💬 Ответ: {test_result['response']}")
                if test_result['usage']:
                    print(f"📊 Использование: {test_result['usage']}")
                working_gpt5.append(model_id)
            else:
                print(f"❌ НЕ РАБОТАЕТ")
                print(f"🚫 Ошибка: {test_result['error']}")
        
        print("\n" + "=" * 80)
        print(f"📈 Результаты:")
        print(f"   Всего GPT-5 моделей: {len(gpt5_models)}")
        print(f"   Работающих: {len(working_gpt5)}")
        print(f"   Неработающих: {len(gpt5_models) - len(working_gpt5)}")
        
        if working_gpt5:
            print(f"\n✅ Рабочие GPT-5 модели:")
            for model in working_gpt5:
                print(f"   🚀 {model}")
        
        # Сравнение с GPT-4o
        print(f"\n🎯 Сравнение с GPT-4o:")
        gpt4o_test = test_model(api_key, 'gpt-4o')
        if gpt4o_test['works']:
            print(f"   ✅ gpt-4o работает: {gpt4o_test['response']}")
        else:
            print(f"   ❌ gpt-4o не работает: {gpt4o_test['error']}")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
