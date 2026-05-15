#!/usr/bin/env python3
"""
Тестовый скрипт для создания таблицы с признаками моделей Gemini
Формат: название - доступность - квота - exception - тип - версия - доп.названия - лимиты - оценка
"""

import requests
import re
import time
from typing import Dict, List, Tuple, Any

def load_api_key():
    """Загрузка API ключа"""
    try:
        with open('_config/tconfig.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('API_KEY='):
                    return line.split('=', 1)[1].strip().split('#')[0]
    except:
        pass
    return None

def get_gemini_models(api_key):
    """Получение всех Gemini моделей"""
    all_models = []
    
    for api_v in ["v1beta", "v1"]:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_v}/models?key={api_key}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                models_data = r.json().get('models', [])
                for model in models_data:
                    if 'generateContent' in model.get('supportedGenerationMethods', []):
                        model_name = model['name'].split('/')[-1]
                        if model_name not in all_models:
                            all_models.append(model_name)
        except:
            continue
    
    return all_models

def get_model_limits(model_name, api_key):
    """Получение лимитов модели"""
    try:
        # Определяем версию API
        api_ver = "v1beta" if "preview" in model_name or "exp" in model_name else "v1"
        
        info_url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}?key={api_key}"
        r = requests.get(info_url, timeout=5)
        
        if r.status_code == 200:
            model_info = r.json()
            return {
                'input_limit': model_info.get('inputTokenLimit', 0),
                'output_limit': model_info.get('outputTokenLimit', 0),
                'api_version': api_ver
            }
    except:
        pass
    
    return {'input_limit': 0, 'output_limit': 0, 'api_version': 'unknown'}

def test_model_availability(model_name, api_key, limits):
    """Проверка доступности модели"""
    try:
        api_ver = limits['api_version']
        url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}:generateContent?key={api_key}"
        
        test_payload = {
            "contents": [{"parts": [{"text": "Translate 'Hello' to Russian"}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }
        
        r = requests.post(url, json=test_payload, timeout=10)
        
        if r.status_code == 200:
            return {'status': 'available', 'message': 'Работает'}
        elif r.status_code == 429:
            return {'status': 'quota_exhausted', 'message': 'Квота исчерпана'}
        elif r.status_code == 404:
            return {'status': 'not_found', 'message': 'Не найдена'}
        else:
            return {'status': 'error', 'message': f'Ошибка {r.status_code}'}
            
    except Exception as e:
        return {'status': 'exception', 'message': f'Исключение: {str(e)[:20]}'}

def get_model_type(model_name):
    """Определение типа модели"""
    name = model_name.lower()
    
    if "gemini" in name:
        if "flash" in name:
            return "gemini-flash"
        elif "pro" in name:
            return "gemini-pro"
        elif "nano" in name:
            return "gemini-nano"
        elif "ultra" in name:
            return "gemini-ultra"
        elif "lite" in name:
            return "gemini-lite"
        else:
            return "gemini"
    elif "gemma" in name:
        return "gemma"
    elif "imagen" in name:
        return "imagen"
    elif "nano-banana" in name:
        return "nano-banana"
    elif "lyria" in name:
        return "lyria"
    elif "deep-research" in name:
        return "deep-research"
    else:
        return "other"

def get_version_info(model_name):
    """Получение информации о версии"""
    version_match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', model_name.lower())
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3)) if version_match.group(3) else 0
        return f"{major}.{minor}.{patch}"
    return "no-version"

def get_additional_names(model_name):
    """Получение дополнительных названий"""
    name = model_name.lower()
    additional = []
    
    if "preview" in name:
        additional.append("preview")
    if "exp" in name:
        additional.append("exp")
    if "latest" in name:
        additional.append("latest")
    if "tts" in name:
        additional.append("tts")
    if "image" in name:
        additional.append("image")
    if "vision" in name:
        additional.append("vision")
    if "robotics" in name:
        additional.append("robotics")
    if "computer-use" in name:
        additional.append("computer-use")
    if "customtools" in name:
        additional.append("customtools")
    if "clip" in name:
        additional.append("clip")
    if "pro" in name:
        additional.append("pro")
    if "lite" in name:
        additional.append("lite")
    if "flash" in name:
        additional.append("flash")
    
    return ", ".join(additional) if additional else "none"

def get_exception_reason(model_name, availability, limits):
    """Причина исключения модели с детальным признаком"""
    name = model_name.lower()
    
    # 1. Проверка лимитов
    if limits['input_limit'] < 1000 or limits['output_limit'] < 1000:
        if limits['input_limit'] == 0 and limits['output_limit'] == 0:
            return f"Исключение: лимиты 0/0 (не поддерживает generateContent)"
        elif limits['input_limit'] < 1000:
            return f"Исключение: лимит входных токенов {limits['input_limit']} < 1000"
        elif limits['output_limit'] < 1000:
            return f"Исключение: лимит выходных токенов {limits['output_limit']} < 1000"
    
    # 2. Проверка доступности
    if availability['status'] == 'quota_exhausted':
        return "Исключение: квота исчерпана (429)"
    elif availability['status'] == 'not_found':
        return "Исключение: модель не найдена (404)"
    elif availability['status'] == 'error':
        return f"Исключение: ошибка API ({availability['message']})"
    elif availability['status'] == 'exception':
        return f"Исключение: исключение ({availability['message']})"
    
    # 3. Проверка на не-текстовые модели
    exclude_patterns = {
        'imagen': 'генерация изображений',
        'veo': 'генерация видео', 
        'music': 'генерация музыки',
        'speech': 'распознавание речи',
        'tts': 'синтез речи (text-to-speech)',
        'embedding': 'создание эмбеддингов',
        'aqa': 'ответы на вопросы',
        'vision': 'анализ изображений',
        'image': 'обработка изображений',
        'robotics': 'робототехника'
    }
    
    for pattern, description in exclude_patterns.items():
        if pattern in name:
            return f"Исключение: не текстовая модель ({description})"
    
    return "Доступна"

def calculate_score(model_name, availability, limits):
    """Расчет оценки модели"""
    score = 0
    
    # Базовые баллы за лимиты
    if limits['input_limit'] >= 1000000:
        score += 40
    elif limits['input_limit'] >= 100000:
        score += 30
    elif limits['input_limit'] >= 10000:
        score += 20
    elif limits['input_limit'] >= 1000:
        score += 10
    
    if limits['output_limit'] >= 8000:
        score += 20
    elif limits['output_limit'] >= 4000:
        score += 15
    elif limits['output_limit'] >= 2000:
        score += 10
    elif limits['output_limit'] >= 1000:
        score += 5
    
    # Баллы за доступность
    if availability['status'] == 'available':
        score += 30
    elif availability['status'] == 'quota_exhausted':
        score += 0
    elif availability['status'] == 'not_found':
        score += 0
    else:
        score += 5
    
    # Баллы за тип модели
    name = model_name.lower()
    if "flash" in name:
        score += 10
    elif "pro" in name:
        score += 8
    elif "nano" in name:
        score += 6
    elif "lite" in name:
        score += 5
    else:
        score += 3
    
    return score

def analyze_models_with_features():
    """Основной анализ моделей с таблицей признаков"""
    api_key = load_api_key()
    if not api_key:
        print("❌ API ключ не найден")
        return
    
    print("🔍 Анализ Gemini моделей с таблицей признаков...")
    print()
    
    # Получаем все модели
    all_models = get_gemini_models(api_key)
    print(f"📊 Всего моделей найдено: {len(all_models)}")
    
    # Собираем информацию о моделях
    model_data = []
    
    for i, model in enumerate(all_models, 1):
        print(f"🔄 Анализ модели {i}/{len(all_models)}: {model}")
        
        # Получаем информацию
        limits = get_model_limits(model, api_key)
        availability = test_model_availability(model, api_key, limits)
        
        # Формируем данные для таблицы
        data = {
            'name': model,
            'availability': availability['status'],
            'quota': f"{limits['input_limit']:,}/{limits['output_limit']:,}",
            'exception': get_exception_reason(model, availability, limits),
            'type': get_model_type(model),
            'version': get_version_info(model),
            'additional': get_additional_names(model),
            'limits': limits,
            'score': calculate_score(model, availability, limits)
        }
        
        model_data.append(data)
        
        # Небольшая задержка чтобы не превысить лимиты
        time.sleep(0.1)
    
    # Сортируем по оценке
    model_data.sort(key=lambda x: x['score'], reverse=True)
    
    # Вывод таблицы
    print("\n" + "="*200)
    print("📋 ТАБЛИЦА ПРИЗНАКОВ МОДЕЛЕЙ GEMINI")
    print("="*200)
    
    # Заголовки таблицы
    headers = [
        "№", "Название", "Доступность", "Квота", "Exception", 
        "Тип", "Версия", "Доп.названия", "Лимиты (вых/вых)", "Оценка"
    ]
    
    # Ширина колонок (увеличим для Exception)
    col_widths = [3, 35, 12, 15, 35, 15, 10, 20, 15, 6]
    
    # Вывод заголовков
    header_line = ""
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        header_line += f"{header:<{width}}"
    print(header_line)
    print("-" * sum(col_widths))
    
    # Вывод данных
    for i, data in enumerate(model_data, 1):
        row_data = [
            str(i),
            data['name'],
            data['availability'],
            data['quota'],
            data['exception'],
            data['type'],
            data['version'],
            data['additional'],
            f"{data['limits']['input_limit']:,}/{data['limits']['output_limit']:,}",
            str(data['score'])
        ]
        
        row_line = ""
        for j, (cell, width) in enumerate(zip(row_data, col_widths)):
            # Обрезаем слишком длинные ячейки
            if len(cell) > width:
                cell = cell[:width-3] + "..."
            row_line += f"{cell:<{width}}"
        print(row_line)
    
    # Статистика
    working_models = [m for m in model_data if m['availability'] == 'available']
    quota_exhausted = [m for m in model_data if m['availability'] == 'quota_exhausted']
    not_found = [m for m in model_data if m['availability'] == 'not_found']
    
    print("\n" + "="*200)
    print("📊 СТАТИСТИКА ПО ТИПАМ МОДЕЛЕЙ")
    print("="*200)
    
    # Группировка по типам
    type_stats = {}
    for data in model_data:
        model_type = data['type']
        if model_type not in type_stats:
            type_stats[model_type] = {'total': 0, 'working': 0, 'score_sum': 0}
        type_stats[model_type]['total'] += 1
        if data['availability'] == 'available':
            type_stats[model_type]['working'] += 1
        type_stats[model_type]['score_sum'] += data['score']
    
    print(f"{'Тип модели':<20} {'Всего':<8} {'Работает':<10} {'Средняя оценка':<15}")
    print("-" * 60)
    for model_type, stats in sorted(type_stats.items()):
        avg_score = stats['score_sum'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{model_type:<20} {stats['total']:<8} {stats['working']:<10} {avg_score:<15.1f}")
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего моделей: {len(model_data)}")
    print(f"   Работающих: {len(working_models)}")
    print(f"   Квота исчерпана: {len(quota_exhausted)}")
    print(f"   Не найдено: {len(not_found)}")
    
    # ТОП моделей
    print(f"\n🏆 ТОП-10 МОДЕЛЕЙ ПО ОЦЕНКЕ:")
    for i, data in enumerate(model_data[:10], 1):
        status = "✅" if data['availability'] == 'available' else "❌"
        print(f"   {i}. {status} {data['name']} - {data['score']} баллов - {data['type']} - {data['quota']}")
    
    # Анализ исключений
    print(f"\n❌ ПРИЧИНЫ ИСКЛЮЧЕНИЯ МОДЕЛЕЙ:")
    exceptions = {}
    for data in model_data:
        if data['exception'] != "Доступна":
            reason = data['exception']
            exceptions[reason] = exceptions.get(reason, 0) + 1
    
    for reason, count in sorted(exceptions.items(), key=lambda x: x[1], reverse=True):
        print(f"   {reason}: {count} моделей")

if __name__ == "__main__":
    analyze_models_with_features()
