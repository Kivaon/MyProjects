#!/usr/bin/env python3
"""
Тестовый скрипт для получения характеристик GPT моделей
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

def get_model_details(api_key, model_id):
    """Получает детальную информацию о модели"""
    try:
        client = openai.OpenAI(api_key=api_key)
        model = client.models.retrieve(model_id)
        
        details = {
            'id': model.id,
            'created': model.created,
            'owned_by': model.owned_by,
            'object': model.object,
            'type': getattr(model, 'type', 'unknown')
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
    """Главная функция теста"""
    print("🔍 Получаем характеристики GPT моделей...")
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Получаем API ключ
    api_key = config.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в конфигурации")
        return
    
    print(f"🔑 API ключ: {api_key[:20]}...")
    
    # Импортируем функцию получения моделей
    try:
        from tbox_translator import get_available_gpt_models
        
        # Создаем mock conf
        class MockConf:
            def __contains__(self, key):
                return False
        
        conf = MockConf()
        
        # Получаем список моделей
        models = get_available_gpt_models(api_key, conf)
        
        print(f"📊 Анализ {len(models)} моделей...")
        print("=" * 80)
        
        # Показываем детали для топ-20 моделей
        for i, model_id in enumerate(models[:20], 1):
            print(f"\n🔍 Модель {i}: {model_id}")
            print("-" * 40)
            
            details = get_model_details(api_key, model_id)
            
            if 'error' in details:
                print(f"❌ Ошибка: {details['error']}")
            else:
                print(f"📋 ID: {details.get('id', 'N/A')}")
                print(f"👤 Владелец: {details.get('owned_by', 'N/A')}")
                print(f"📅 Создана: {details.get('created_date', 'N/A')}")
                print(f"🏷️  Тип: {details.get('type', 'N/A')}")
                print(f"📦 Объект: {details.get('object', 'N/A')}")
        
        print("\n" + "=" * 80)
        print(f"📈 Статистика:")
        print(f"   Всего моделей: {len(models)}")
        print(f"   Показано: 20 из {len(models)}")
        
        # Анализ по владельцам
        print(f"\n👤 Анализ по владельцам:")
        owners = {}
        for model_id in models[:30]:  # Анализируем первые 30
            details = get_model_details(api_key, model_id)
            owner = details.get('owned_by', 'unknown')
            owners[owner] = owners.get(owner, 0) + 1
        
        for owner, count in owners.items():
            print(f"   {owner}: {count} моделей")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
