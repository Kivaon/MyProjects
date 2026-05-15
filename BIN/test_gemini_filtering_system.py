#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы фильтрации и приоритетов Gemini моделей
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

def basic_model_filter(model_name):
    """Этап1: Базовые фильтры"""
    name = model_name.lower()
    
    exclude_patterns = [
        "imagen", "veo", "music", "speech", "tts", "image-preview",
        "exp", "embedding", "aqa", "ultra"
    ]
    
    has_gemini = "gemini" in name
    is_excluded = any(pattern in name for pattern in exclude_patterns)
    
    return has_gemini and not is_excluded

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

def get_dynamic_model_priority(model_name):
    """Динамический приоритет на основе названия"""
    name = model_name.lower()
    
    # Парсинг версии
    version_match = re.search(r'gemini-(\d+)\.(\d+)(?:\.(\d+))?', name)
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3)) if version_match.group(3) else 0
    else:
        return (0, 0, 0, 0, 0)
    
    # Приоритет типа
    type_priority = 0
    if "flash" in name:
        type_priority = 3
    elif "pro" in name:
        type_priority = 2
    elif "nano" in name:
        type_priority = 1
    
    # Приоритет суффикса
    suffix_priority = 0
    if "preview" in name:
        suffix_priority = 1
    elif "latest" in name:
        suffix_priority = 2
    elif "lite" in name:
        suffix_priority = 0
    
    return (major, minor, patch, type_priority, suffix_priority)

def get_comprehensive_priority(model_info):
    """Комбинированный приоритет с учетом лимитов"""
    name, input_limit, output_limit = model_info
    
    base_priority = get_dynamic_model_priority(name)
    
    # Приоритет от лимитов
    limit_priority = 0
    
    if input_limit >= 1000000:
        limit_priority += 3
    elif input_limit >= 500000:
        limit_priority += 2
    elif input_limit >= 100000:
        limit_priority += 1
    
    if output_limit >= 8000:
        limit_priority += 3
    elif output_limit >= 4000:
        limit_priority += 2
    elif output_limit >= 1000:
        limit_priority += 1
    
    # Возвращаем кортеж из 6 элементов: (major, minor, patch, type, suffix, limits)
    return (base_priority[0], base_priority[1], base_priority[2], base_priority[3], base_priority[4], limit_priority)

def analyze_models():
    """Основной анализ моделей"""
    api_key = load_api_key()
    if not api_key:
        print("❌ API ключ не найден")
        return
    
    print("🔍 Анализ Gemini моделей...")
    all_models = get_gemini_models(api_key)
    print(f"📊 Всего моделей найдено: {len(all_models)}")
    
    # Этап1: Базовая фильтрация
    basic_filtered = []
    excluded_stage1 = []
    
    for model in all_models:
        if basic_model_filter(model):
            basic_filtered.append(model)
        else:
            excluded_stage1.append(model)
    
    print(f"✅ После этапа1: {len(basic_filtered)} моделей")
    print(f"❌ Исключено на этапе1: {len(excluded_stage1)} моделей")
    
    # Этап2: Проверка лимитов и доступности
    detailed_results = []
    
    for model in basic_filtered:
        limits = get_model_limits(model, api_key)
        availability = test_model_availability(model, api_key, limits)
        
        # Признаки исключения
        exclusion_reasons = []
        if limits['input_limit'] < 1000 or limits['output_limit'] < 1000:
            exclusion_reasons.append("Малые лимиты")
        if availability['status'] != 'available':
            exclusion_reasons.append(availability['message'])
        
        detailed_results.append({
            'model': model,
            'limits': limits,
            'availability': availability,
            'exclusion_reasons': exclusion_reasons,
            'priority': get_dynamic_model_priority(model)
        })
    
    # Разделение на категории
    available_models = []
    insufficient_limits = []
    quota_exhausted = []
    failed_models = []
    
    for result in detailed_results:
        if result['availability']['status'] == 'available':
            if result['limits']['input_limit'] >= 1000 and result['limits']['output_limit'] >= 1000:
                available_models.append(result)
            else:
                insufficient_limits.append(result)
        elif result['availability']['status'] == 'quota_exhausted':
            quota_exhausted.append(result)
        else:
            failed_models.append(result)
    
    # Сортировка доступных моделей по комбинированному приоритету
    available_with_priority = []
    for result in available_models:
        model_info = (result['model'], result['limits']['input_limit'], result['limits']['output_limit'])
        comprehensive_priority = get_comprehensive_priority(model_info)
        result['comprehensive_priority'] = comprehensive_priority
        available_with_priority.append(result)
    
    available_with_priority.sort(key=lambda x: x['comprehensive_priority'], reverse=True)
    
    # Вывод таблицы
    print("\n" + "="*150)
    print("📋 ПОЛНАЯ ТАБЛИЦА АНАЛИЗА МОДЕЛЕЙ")
    print("="*150)
    
    print(f"{'№':<3} {'Модель':<35} {'Признаки исключения':<25} {'Лимиты (вых/вых)':<15} {'Приоритет (версия/тип/суфф)':<25} {'Комплексный':<15} {'Статус':<15}")
    print("-" * 150)
    
    # Все модели с нумерацией - сначала отсеченные, потом доступные
    excluded_results = excluded_stage1 + insufficient_limits + quota_exhausted + failed_models
    available_results = available_with_priority
    all_results = excluded_results + available_results
    
    # Вывод отсеченных моделей
    print("\n" + "="*150)
    print("📋 ОТСЕЧЕННЫЕ МОДЕЛИ")
    print("="*150)
    
    print(f"{'№':<3} {'Модель':<35} {'Причина отсечения':<25} {'Лимиты (вых/вых)':<15} {'Приоритет':<25} {'Статус':<15}")
    print("-" * 150)
    
    for i, result in enumerate(excluded_results, 1):
        if isinstance(result, str):
            # Модели, отсеченные на этапе1
            print(f"{i:<3} {result:<35} {'Этап1: non-gemini/imagen/music/etc.':<25} {'N/A':<15} {'N/A':<25} {'❌ Отсечена':<15}")
        else:
            # Модели, отсеченные на этапе2
            model = result['model']
            reasons = ", ".join(result['exclusion_reasons']) if result['exclusion_reasons'] else "Нет"
            limits = f"{result['limits']['input_limit']:,}/{result['limits']['output_limit']:,}"
            priority = f"{result['priority'][0]}.{result['priority'][1]}.{result['priority'][2]}/{result['priority'][3]}/{result['priority'][4]}"
            status = result['availability']['message']
            
            if result['availability']['status'] == 'quota_exhausted':
                status = f"⚠️ {status}"
            else:
                status = f"❌ {status}"
            
            print(f"{i:<3} {model:<35} {reasons:<25} {limits:<15} {priority:<25} {status:<15}")
    
    # Вывод доступных моделей
    print("\n" + "="*150)
    print("📋 ДОСТУПНЫЕ МОДЕЛИ (отсортированы по приоритету)")
    print("="*150)
    
    print(f"{'№':<3} {'Модель':<35} {'Лимиты (вых/вых)':<15} {'Базовый приоритет':<25} {'Комплексный приоритет':<25} {'Статус':<15}")
    print("-" * 150)
    
    for i, result in enumerate(available_results, 1):
        model = result['model']
        limits = f"{result['limits']['input_limit']:,}/{result['limits']['output_limit']:,}"
        priority = f"{result['priority'][0]}.{result['priority'][1]}.{result['priority'][2]}/{result['priority'][3]}/{result['priority'][4]}"
        
        if 'comprehensive_priority' in result and len(result['comprehensive_priority']) >= 6:
            comp = f"{result['comprehensive_priority'][0]}.{result['comprehensive_priority'][1]}.{result['comprehensive_priority'][2]}/{result['comprehensive_priority'][3]}/{result['comprehensive_priority'][4]}/{result['comprehensive_priority'][5]}"
        else:
            comp = "N/A"
        
        status = result['availability']['message']
        
        # Цветовая маркировка статуса
        if result['availability']['status'] == 'available':
            status = f"✅ {status}"
        elif result['availability']['status'] == 'quota_exhausted':
            status = f"⚠️ {status}"
        else:
            status = f"❌ {status}"
        
        print(f"{i:<3} {model:<35} {limits:<15} {priority:<25} {comp:<25} {status:<15}")
    
    # Итоговая статистика
    print("\n" + "="*150)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*150)
    print(f"📊 Всего моделей найдено: {len(all_models)}")
    print(f"❌ Этап1 отсечено: {len(excluded_stage1)} (non-gemini, imagen, music, etc.)")
    print(f"⚠️ Этап2 отсечено: {len(insufficient_limits + quota_exhausted + failed_models)} (лимиты/квота/ошибки)")
    print(f"✅ Доступных моделей: {len(available_results)}")
    
    if available_results:
        print(f"\n🏆 ТОП-5 МОДЕЛЕЙ ПО ПРИОРИТЕТУ:")
        for i, result in enumerate(available_results[:5], 1):
            print(f"  {i}. {result['model']} - {result['limits']['input_limit']:,}/{result['limits']['output_limit']:,} токенов")
    
    # Демонстрация работы приоритетов
    print(f"\n🔍 ДЕМОНСТРАЦИЯ РАБОТЫ ПРИОРИТЕТОВ:")
    print("   Базовый приоритет: версия.модель.тип (flash=3, pro=2)")
    print("   Лимитный приоритет: входные+выходные лимиты")
    print("   Комплексный приоритет: базовый + лимитный")

if __name__ == "__main__":
    analyze_models()
