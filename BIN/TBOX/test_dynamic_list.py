#!/usr/bin/env python3
"""
Тестовый скрипт для отладки логики динамического списка моделей
"""

import requests
import re
import os
import csv
from datetime import datetime

# Загрузка конфигурации из tconfig.txt
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "..", "_config", "tconfig.txt")
conf = {}
with open(config_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, val = line.split('=', 1)
                conf[key.strip()] = val.strip()

api_key = conf.get('API_KEY', '').split('#')[0].strip()

def get_api_ver(model_name):
    """Определение версии API по названию модели"""
    if 'preview' in model_name:
        return 'v1beta'
    return 'v1'

def get_gemini_model_priority(model_name):
    """Новый приоритет: версия + тип (lite менее приоритетен)"""
    if 'preview' in model_name:
        if '3-flash' in model_name:
            version = 3.0
        else:
            version = 1.0
    else:
        v_match = re.search(r'gemini-(\d+)(?:\.(\d+))?', model_name)
        if v_match:
            major = float(v_match.group(1))
            minor = float(v_match.group(2)) if v_match.group(2) else 0
            version = major + minor / 10
        else:
            version = 0.0
    
    type_penalty = 0
    if 'flash-lite' in model_name:
        type_penalty = 0.5
    elif 'flash' in model_name:
        type_penalty = 0
    elif 'pro' in model_name:
        type_penalty = 0.2
    
    return version - type_penalty

def is_text_model(model_name):
    """Фильтрация текстовых моделей"""
    exclude_patterns = [
        'robotics', 'computer-use', 'imagen', 'veo', 
        'music', 'speech', 'tts', 'embedding'
    ]
    return not any(pattern in model_name.lower() for pattern in exclude_patterns)

def extract_model_params(model_info):
    """Извлечение параметров модели из ответа API"""
    model_name = model_info.get('name', '').split('/')[-1]
    display_name = model_info.get('displayName', '')
    description = model_info.get('description', '')
    version = model_info.get('version', '')
    methods = model_info.get('supportedGenerationMethods', [])
    has_generate_content = 'generateContent' in methods
    max_output_tokens = model_info.get('maxOutputTokens', 0)
    
    return {
        'name': model_name,
        'display_name': display_name,
        'description': description,
        'version': version,
        'has_generate_content': has_generate_content,
        'max_output_tokens': max_output_tokens,
        'methods': ', '.join(methods)
    }

def save_models_table(models_data, stage_name, csv_file=None, is_first=False):
    """Сохранение таблицы моделей в CSV (добавление к существующему файлу)"""
    if csv_file is None:
        csv_file = f"models_all_stages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    mode = 'w' if is_first else 'a'
    
    with open(csv_file, mode, newline='', encoding='utf-8-sig') as f:
        if not models_data:
            f.write(f"\n# {stage_name}: Нет данных\n")
            print(f"  ⚠️ Нет данных для {stage_name}")
            return csv_file
        
        # Добавляем разделитель перед этапом (кроме первого)
        if not is_first:
            f.write(f"\n{'='*80}\n")
            f.write(f"# {stage_name}\n")
            f.write(f"{'='*80}\n\n")
        
        fieldnames = list(models_data[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(models_data)
    
    print(f"  💾 {stage_name}: {len(models_data)} моделей")
    return csv_file

def test_model_availability(model):
    """Детальная проверка доступности модели"""
    print(f"\n🔍 Тест модели: {model}")
    
    try:
        api_v = get_api_ver(model)
        test_url = f"https://generativelanguage.googleapis.com/{api_v}/models/{model}:generateContent?key={api_key}"
        
        print(f"  URL: {test_url}")
        tr = requests.post(test_url, json={"contents": [{"parts": [{"text": "test"}]}]}, timeout=5)
        
        # Детальная проверка status_code
        print(f"  status_code: {tr.status_code}")
        print(f"  type(status_code): {type(tr.status_code).__name__}")
        print(f"  repr(status_code): {repr(tr.status_code)}")
        print(f"  status_code == 200: {tr.status_code == 200}")
        print(f"  str(status_code) == '200': {str(tr.status_code) == '200'}")
        print(f"  int(status_code) == 200: {int(tr.status_code) == 200}")
        
        if tr.status_code == 200:
            response_data = tr.json()
            print(f"  response keys: {list(response_data.keys())}")
            
            if 'candidates' in response_data:
                print(f"  candidates: {len(response_data['candidates'])}")
                if len(response_data['candidates']) > 0:
                    candidate = response_data['candidates'][0]
                    print(f"  candidate keys: {list(candidate.keys())}")
                    
                    if 'content' in candidate:
                        print(f"  content keys: {list(candidate['content'].keys())}")
                        if 'parts' in candidate['content']:
                            print(f"  parts: {len(candidate['content']['parts'])}")
                            if len(candidate['content']['parts']) > 0:
                                part = candidate['content']['parts'][0]
                                print(f"  part keys: {list(part.keys())}")
                                if 'text' in part:
                                    print(f"  ✅ Текст найден: {part['text'][:50]}...")
                                    return True
                                else:
                                    print(f"  ❌ Нет поля text в part")
                            else:
                                print(f"  ❌ parts пуст")
                        else:
                            print(f"  ❌ Нет parts в content")
                    else:
                        print(f"  ❌ Нет content в candidate")
                else:
                    print(f"  ❌ candidates пуст")
            else:
                print(f"  ❌ Нет candidates в ответе")
        else:
            print(f"  ❌ Статус не 200")
        
        return False
        
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def main():
    print("=" * 80)
    print("ТЕСТ ДИНАМИЧЕСКОГО СПИСКА МОДЕЛЕЙ")
    print("=" * 80)
    
    # Один CSV файл для всех этапов
    csv_file = f"models_all_stages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    print(f"📁 Результат будет сохранен в: {csv_file}")
    
    # 1. Получение списка моделей с полными параметрами
    all_models_info = []
    for api_v in ["v1beta", "v1"]:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_v}/models?key={api_key}"
            r = requests.get(url, timeout=10)
            print(f"\n📡 GET {api_v}: status={r.status_code} (type: {type(r.status_code).__name__})")
            
            if r.status_code == 200:
                models_data = r.json().get('models', [])
                for model_info in models_data:
                    params = extract_model_params(model_info)
                    params['api_version'] = api_v
                    all_models_info.append(params)
                print(f"  ✅ Найдено {len(models_data)} моделей")
            else:
                print(f"  ❌ Статус: {r.status_code}")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    print(f"\n📋 ВСЕ МОДЕЛИ: {len(all_models_info)}")
    
    # Сохранение таблицы ДО фильтрации
    print("\n" + "=" * 80)
    print("ЭТАП 0: ДО ФИЛЬТРАЦИИ")
    print("=" * 80)
    save_models_table(all_models_info, "ЭТАП 0: ДО ФИЛЬТРАЦИИ", csv_file, is_first=True)
    
    # 2. Фильтрация первого этапа (GET параметры)
    print("\n" + "=" * 80)
    print("ЭТАП 1: ФИЛЬТРАЦИЯ ПО ПАРАМЕТРАМ GET")
    print("=" * 80)
    
    stage1_models = []
    for model_params in all_models_info:
        # Фильтр 1: должен быть generateContent
        if not model_params['has_generate_content']:
            continue
        
        # Фильтр 2: текстовая модель (по названию)
        if not is_text_model(model_params['name']):
            continue
        
        stage1_models.append(model_params)
    
    print(f"  ✅ После фильтрации: {len(stage1_models)} моделей")
    print(f"  ❌ Отсеяно: {len(all_models_info) - len(stage1_models)} моделей")
    
    # Сохранение таблицы ПОСЛЕ фильтрации первого этапа
    save_models_table(stage1_models, "ЭТАП 1: ПОСЛЕ ФИЛЬТРАЦИИ GET", csv_file)
    
    # 3. Тестирование POST запросами (второй этап)
    print("\n" + "=" * 80)
    print("ЭТАП 2: ТЕСТ POST ЗАПРОСАМИ")
    print("=" * 80)
    
    stage2_models = []
    for model_params in stage1_models:  # Тестируем все модели
        model_name = model_params['name']
        if test_model_availability(model_name):
            stage2_models.append(model_params)
    
    print(f"\n✅ РАБОЧИЕ МОДЕЛИ (POST): {len(stage2_models)}")
    
    # Сохранение таблицы после второго этапа
    save_models_table(stage2_models, "ЭТАП 2: ПОСЛЕ ТЕСТА POST", csv_file)
    
    # 4. Удаление дубликатов
    print("\n" + "=" * 80)
    print("ЭТАП 3: УДАЛЕНИЕ ДУБЛИКАТОВ")
    print("=" * 80)
    
    seen_names = set()
    unique_models = []
    for model in stage2_models:
        if model['name'] not in seen_names:
            seen_names.add(model['name'])
            unique_models.append(model)
    
    print(f"  ✅ Уникальных моделей: {len(unique_models)} (было {len(stage2_models)})")
    
    # 5. Сортировка по приоритету
    print("\n" + "=" * 80)
    print("ЭТАП 4: СОРТИРОВКА ПО ПРИОРИТЕТУ")
    print("=" * 80)
    
    sorted_models = sorted(unique_models, key=lambda x: get_gemini_model_priority(x['name']), reverse=True)
    print(f"🔄 ОТСОРТИРОВАННЫЕ: {[m['name'] for m in sorted_models]}")
    
    # Сохранение финальной таблицы
    save_models_table(sorted_models, "ЭТАП 3: ФИНАЛЬНЫЙ СПИСОК", csv_file)
    
    print(f"\n🎉 ГОТОВО! Все этапы сохранены в: {csv_file}")

if __name__ == "__main__":
    main()
