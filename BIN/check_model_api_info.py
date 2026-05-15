#!/usr/bin/env python3
"""
Проверка информации о моделях для определения типа API
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

def get_model_detailed_info(api_key, model_id):
    """Получает детальную информацию о модели"""
    try:
        client = openai.OpenAI(api_key=api_key)
        model = client.models.retrieve(model_id)
        
        # Собираем всю доступную информацию
        info = {
            'id': model.id,
            'created': model.created,
            'owned_by': model.owned_by,
            'object': model.object,
            'raw_model': model  # Для отладки
        }
        
        # Конвертируем timestamp в дату
        import datetime
        if model.created:
            created_date = datetime.datetime.fromtimestamp(model.created)
            info['created_date'] = created_date.strftime('%Y-%m-%d')
        
        # Проверяем все атрибуты модели
        print(f"\n🔍 Атрибуты модели {model_id}:")
        for attr in dir(model):
            if not attr.startswith('_'):
                try:
                    value = getattr(model, attr)
                    if not callable(value):
                        print(f"   {attr}: {value}")
                        info[attr] = value
                except:
                    pass
        
        return info
        
    except Exception as e:
        return {'error': str(e)}

def analyze_model_capabilities(api_key, model_id):
    """Анализирует возможности модели через тестирование"""
    capabilities = {
        'old_api': False,
        'new_api': False,
        'old_api_error': None,
        'new_api_error': None
    }
    
    client = openai.OpenAI(api_key=api_key)
    
    # Тестируем СТАРЫЙ API
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
        capabilities['old_api'] = True
    except Exception as e:
        capabilities['old_api_error'] = str(e)
    
    # Тестируем НОВЫЙ API
    try:
        response = client.responses.create(
            model=model_id,
            input="Say 'Hello'"
        )
        capabilities['new_api'] = True
    except Exception as e:
        capabilities['new_api_error'] = str(e)
    
    return capabilities

def main():
    """Главная функция анализа"""
    print("🔍 Анализ информации о моделях для определения типа API...")
    
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Получаем список моделей
    try:
        from tbox_translator import get_available_gpt_models
        
        class MockConf:
            def __contains__(self, key):
                return False
        
        conf = MockConf()
        models = get_available_gpt_models(api_key, conf)
        
        # Анализируем несколько моделей разных типов
        test_models = [
            'gpt-5.5',           # GPT-5
            'gpt-5-chat-latest',  # GPT-5 chat
            'gpt-4o',            # GPT-4o
            'gpt-4',             # GPT-4
            'gpt-3.5-turbo'      # GPT-3.5
        ]
        
        print(f"\n📊 Анализ {len(test_models)} моделей...")
        print("=" * 80)
        
        for model_id in test_models:
            if model_id not in models:
                print(f"\n❌ Модель {model_id} не найдена в списке доступных")
                continue
            
            print(f"\n🎯 Модель: {model_id}")
            print("-" * 60)
            
            # Получаем детальную информацию
            info = get_model_detailed_info(api_key, model_id)
            
            if 'error' in info:
                print(f"❌ Ошибка получения информации: {info['error']}")
                continue
            
            # Анализируем возможности
            capabilities = analyze_model_capabilities(api_key, model_id)
            
            print(f"\n📋 Возможности API:")
            print(f"   СТАРЫЙ API (chat/completions): {'✅' if capabilities['old_api'] else '❌'}")
            if capabilities['old_api_error']:
                print(f"      Ошибка: {capabilities['old_api_error'][:100]}...")
            
            print(f"   НОВЫЙ API (responses): {'✅' if capabilities['new_api'] else '❌'}")
            if capabilities['new_api_error']:
                print(f"      Ошибка: {capabilities['new_api_error'][:100]}...")
            
            # Определяем рекомендуемый API
            if capabilities['old_api'] and capabilities['new_api']:
                recommended = "Оба API"
            elif capabilities['old_api']:
                recommended = "СТАРЫЙ API"
            elif capabilities['new_api']:
                recommended = "НОВЫЙ API"
            else:
                recommended = "Нет рабочего API"
            
            print(f"   🎯 Рекомендуемый API: {recommended}")
        
        print("\n" + "=" * 80)
        print("📈 Вывод: можно ли определить тип API из информации о модели?")
        print("❌ Информация о модели НЕ содержит тип API")
        print("✅ Тип API можно определить только через тестирование")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
