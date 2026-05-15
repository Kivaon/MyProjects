#!/usr/bin/env python3
"""
Тестовый скрипт для анализа всех моделей Gemini
Собирает полную таблицу признаков и открывает результат в Excel
"""

import requests
import re
import csv
import json
import subprocess
import os
from datetime import datetime

# Загрузка конфигурации из tconfig.txt как в tbox_translator.py
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

def get_model_priority(model_name):
    """Приоритет модели для сортировки"""
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
    """Проверка - текстовая ли модель"""
    exclude_patterns = [
        'robotics', 'computer-use', 'imagen', 'veo', 
        'music', 'speech', 'tts', 'embedding', 'gemma'
    ]
    return not any(pattern in model_name.lower() for pattern in exclude_patterns)

def get_model_type(model_name):
    """Определение типа модели"""
    if 'flash-lite' in model_name:
        return 'flash-lite'
    elif 'flash' in model_name:
        return 'flash'
    elif 'pro' in model_name:
        return 'pro'
    elif 'gemma' in model_name:
        return 'gemma'
    else:
        return 'unknown'

def get_model_version(model_name):
    """Получение версии модели"""
    if 'preview' in model_name:
        if '3-flash' in model_name:
            return '3.0-preview'
        else:
            return '1.0-preview'
    
    v_match = re.search(r'gemini-(\d+)(?:\.(\d+))?', model_name)
    if v_match:
        major = v_match.group(1)
        minor = v_match.group(2) if v_match.group(2) else '0'
        return f"{major}.{minor}"
    return 'unknown'

def analyze_models():
    """Анализ всех моделей Gemini"""
    print("🔍 Начинаем анализ моделей Gemini...")
    
    # 1. Получение всех моделей
    all_models = []
    for api_v in ["v1beta", "v1"]:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_v}/models?key={api_key}"
            r = requests.get(url, timeout=10)
            print(f"  Запрос {api_v}: status={r.status_code}")
            if r.status_code == 200:
                models = [m['name'].split('/')[-1] for m in r.json().get('models', []) 
                          if 'generateContent' in m.get('supportedGenerationMethods', [])]
                all_models.extend(models)
                print(f"    ✅ {api_v} - найдено {len(models)} моделей")
        except Exception as e:
            print(f"    ❌ {api_v} - ошибка: {e}")
    
    print(f"\n📋 ВСЕ МОДЕЛИ С generateContent: {len(all_models)}")
    
    # 2. Анализ каждой модели
    models_data = []
    for model in all_models:
        print(f"\n🔍 Анализ модели: {model}")
        
        # Проверка доступности
        working = False
        status_code = None
        has_candidates = False
        error_msg = ""
        
        try:
            api_v = get_api_ver(model)
            test_url = f"https://generativelanguage.googleapis.com/{api_v}/models/{model}:generateContent?key={api_key}"
            tr = requests.post(test_url, json={"contents": [{"parts": [{"text": "test"}]}]}, timeout=5)
            status_code = tr.status_code
            
            if status_code == 200:
                response_data = tr.json()
                if 'candidates' in response_data and len(response_data['candidates']) > 0:
                    working = True
                    has_candidates = True
                    print(f"    ✅ Работает (status=200, has_candidates)")
                else:
                    has_candidates = False
                    error_msg = "Нет candidates в ответе"
                    print(f"    ❌ status=200, но нет candidates")
            else:
                error_msg = f"status={status_code}"
                print(f"    ❌ {error_msg}")
        except Exception as e:
            error_msg = str(e)
            print(f"    ❌ Ошибка: {error_msg}")
        
        # Сбор признаков
        model_info = {
            'Название модели': model,
            'Тип': get_model_type(model),
            'Версия': get_model_version(model),
            'Приоритет': get_model_priority(model),
            'Доступность': '✅ Работает' if working else '❌ Не работает',
            'Status Code': status_code,
            'Has Candidates': '✅ Да' if has_candidates else '❌ Нет',
            'Текстовая': '✅ Да' if is_text_model(model) else '❌ Нет',
            'Ошибка': error_msg,
            'API Version': get_api_ver(model)
        }
        
        models_data.append(model_info)
    
    # 3. Сохранение в CSV
    csv_file = f"gemini_models_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Название модели', 'Тип', 'Версия', 'Приоритет', 
            'Доступность', 'Status Code', 'Has Candidates', 
            'Текстовая', 'Ошибка', 'API Version'
        ])
        writer.writeheader()
        writer.writerows(models_data)
    
    print(f"\n💾 Результат сохранен в: {csv_file}")
    
    # 4. Открытие в Excel (Mac)
    try:
        subprocess.run(['open', csv_file])
        print(f"📊 Открыт в Excel: {csv_file}")
    except Exception as e:
        print(f"⚠️ Не удалось открыть автоматически: {e}")
        print(f"📂 Откройте файл вручную: {csv_file}")
    
    return csv_file

if __name__ == "__main__":
    analyze_models()
