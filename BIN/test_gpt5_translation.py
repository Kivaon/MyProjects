#!/usr/bin/env python3
"""
Тестирование перевода с GPT-5 моделями
"""

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
    print("🔍 Тестирование перевода с GPT-5 моделями...")
    
    config = load_config()
    api_key = config.get('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден")
        return
    
    # Импортируем функции из tbox_translator
    try:
        from tbox_translator import find_working_gpt_model, translate_with_gpt, get_gpt_chunk_limits
        
        # Создаем mock конф с API ключом
        class MockConf:
            def __init__(self):
                self.data = {}
            
            def __contains__(self, key):
                return key in ['OPENAI_API_KEY', 'MODEL_GPT'] or key in self.data
            
            def get(self, key, default=None):
                if key == 'OPENAI_API_KEY':
                    return api_key
                elif key == 'MODEL_GPT':
                    return self.data.get('MODEL_GPT', working_model)
                return self.data.get(key, default)
            
            def __setitem__(self, key, value):
                self.data[key] = value
        
        conf = MockConf()
        
        print("\n🚀 Поиск рабочей GPT-5 модели...")
        working_model = find_working_gpt_model(api_key, conf)
        
        if not working_model:
            print("❌ Рабочая модель не найдена")
            return
        
        print(f"✅ Найдена модель: {working_model}")
        
        # Получаем лимиты модели
        limits = get_gpt_chunk_limits(working_model)
        print(f"📊 Лимиты модели: {limits}")
        
        # Тестовый текст для перевода
        test_text = """
        Hello world! This is a test of GPT-5 translation capabilities.
        We are testing the new API v1/responses with output_text extraction.
        This should work perfectly with GPT-5 models.
        """
        
        print(f"\n📝 Тестовый текст ({len(test_text)} символов):")
        print(f"   {test_text[:100]}...")
        
        # Промпты для перевода
        prompts = {
            'system': "You are a professional translator. Translate the given text accurately.",
            'user': "Translate this text to Russian: {text}"
        }
        
        print(f"\n🔄 Запускаем перевод...")
        
        # Выполняем перевод
        try:
            translation = translate_with_gpt(
                chunk=test_text,
                part_num=1,
                total_parts=1,
                author="Test",
                conf=conf,
                prompts=prompts,
                prompt_code="test",
                include_original=False
            )
            
            print(f"\n✅ Перевод выполнен успешно!")
            print(f"📄 Результат перевода:")
            print(f"   {translation}")
            
        except Exception as e:
            print(f"❌ Ошибка перевода: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
