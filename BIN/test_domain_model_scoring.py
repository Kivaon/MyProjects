#!/usr/bin/env python3
"""
Тестовый скрипт для доменной системы оценки моделей Gemini
Формат оценки: MAJOR.MINOR.PATCH.TYPE.STABILITY.AVAILABILITY
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

def parse_version_from_name(model_name):
    """Парсинг версии из названия модели"""
    version_match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', model_name.lower())
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3)) if version_match.group(3) else 0
        return (major, minor, patch)
    return (0, 0, 0)  # Если версии нет

def get_model_type_score(model_name):
    """Оценка типа модели"""
    name = model_name.lower()
    
    if "flash" in name:
        return 9  # Лучшие для быстрых задач
    elif "pro" in name:
        return 8  # Качественные модели
    elif "nano" in name:
        return 7  # Легкие модели
    elif "ultra" in name:
        return 6  # Сверхмощные
    elif "lite" in name:
        return 5  # Облегченные
    elif "vision" in name or "image" in name:
        return 4  # Визуальные
    elif "embedding" in name:
        return 3  # Встраивания
    elif "tts" in name or "speech" in name:
        return 2  # Голосовые
    else:
        return 1  # Базовые

def get_stability_score(model_name):
    """Оценка стабильности модели"""
    name = model_name.lower()
    
    if "exp" in name:
        return 1  # Экспериментальные
    elif "preview" in name:
        return 3  # Превью
    elif "latest" in name:
        return 7  # Последние стабильные
    elif "001" in name or "002" in name:
        return 5  # Ранние релизы
    else:
        return 9  # Стабильные релизы

def get_availability_score(model_name, api_key, limits):
    """Оценка реальной работоспособности"""
    try:
        availability = test_model_availability(model_name, api_key, limits)
        
        if availability['status'] == 'available':
            return 9  # Полностью работает
        elif availability['status'] == 'quota_exhausted':
            return 0  # Квота исчерпана
        elif availability['status'] == 'not_found':
            return 0  # Не найдена
        elif availability['status'] == 'error':
            return 2  # Ошибки
        else:
            return 3  # Проблемы
    except:
        return 0

def get_domain_model_score(model_name, api_key):
    """
    Формирование доменной оценки модели
    Формат: MAJOR.MINOR.PATCH.TYPE.STABILITY.AVAILABILITY
    """
    # 1. Получаем лимиты
    limits = get_model_limits(model_name, api_key)
    
    # 2. Проверяем минимальные лимиты
    if limits['input_limit'] < 1000 or limits['output_limit'] < 1000:
        return {
            'domain_score': '0.0.0.0.0.0',
            'reason': 'Недостаточные лимиты',
            'limits': limits,
            'components': {}
        }
    
    # 3. Парсим версию
    major, minor, patch = parse_version_from_name(model_name)
    
    # 4. Оцениваем тип
    type_score = get_model_type_score(model_name)
    
    # 5. Оцениваем стабильность
    stability_score = get_stability_score(model_name)
    
    # 6. Проверяем работоспособность
    availability_score = get_availability_score(model_name, api_key, limits)
    
    # 7. Формируем доменную оценку
    domain_score = f"{major}.{minor}.{patch}.{type_score}.{stability_score}.{availability_score}"
    
    return {
        'domain_score': domain_score,
        'components': {
            'version': (major, minor, patch),
            'type': type_score,
            'stability': stability_score,
            'availability': availability_score
        },
        'limits': limits,
        'reason': 'Доменная оценка'
    }

def parse_domain_score(domain_score):
    """Парсинг доменной оценки в кортеж для сортировки"""
    try:
        parts = domain_score.split('.')
        return tuple(int(part) for part in parts)
    except:
        return (0, 0, 0, 0, 0, 0)

def analyze_models_with_domain_scoring():
    """Основной анализ моделей с доменной системой оценки"""
    api_key = load_api_key()
    if not api_key:
        print("❌ API ключ не найден")
        return
    
    print("🔍 Анализ Gemini моделей с доменной системой оценки...")
    print("📊 Формат оценки: MAJOR.MINOR.PATCH.TYPE.STABILITY.AVAILABILITY")
    print()
    
    # Получаем все модели
    all_models = get_gemini_models(api_key)
    print(f"📊 Всего моделей найдено: {len(all_models)}")
    
    # Оцениваем все модели
    model_scores = []
    
    for i, model in enumerate(all_models, 1):
        print(f"🔄 Анализ модели {i}/{len(all_models)}: {model}")
        
        score_data = get_domain_model_score(model, api_key)
        score_data['model'] = model
        model_scores.append(score_data)
        
        # Небольшая задержка чтобы не превысить лимиты
        time.sleep(0.1)
    
    # Сортируем по доменной оценке
    model_scores.sort(key=lambda x: parse_domain_score(x['domain_score']), reverse=True)
    
    # Разделяем на категории
    working_models = [m for m in model_scores if m['components'].get('availability') == 9]
    quota_exhausted = [m for m in model_scores if m['components'].get('availability') == 0 and 'quota' in m.get('reason', '').lower()]
    not_found = [m for m in model_scores if m['components'].get('availability') == 0 and 'не найдена' in m.get('reason', '').lower()]
    insufficient_limits = [m for m in model_scores if 'Недостаточные лимиты' in m.get('reason', '')]
    other_errors = [m for m in model_scores if m not in working_models and m not in quota_exhausted and m not in not_found and m not in insufficient_limits]
    
    # Вывод таблицы
    print("\n" + "="*180)
    print("📋 ДОМЕННАЯ ОЦЕНКА ВСЕХ МОДЕЛЕЙ")
    print("="*180)
    
    print(f"{'№':<3} {'Модель':<35} {'Доменная оценка':<20} {'Компоненты (версия/тип/стаб/доступ)':<35} {'Лимиты (вых/вых)':<15} {'Статус':<15}")
    print("-" * 180)
    
    for i, model_data in enumerate(model_scores, 1):
        model = model_data['model']
        domain_score = model_data['domain_score']
        components = model_data['components']
        limits = model_data['limits']
        
        # Компоненты оценки
        if 'version' in components and len(components['version']) >= 3:
            comp_str = f"{components['version'][0]}.{components['version'][1]}.{components['version'][2]}/{components.get('type', 0)}/{components.get('stability', 0)}/{components.get('availability', 0)}"
        else:
            comp_str = "N/A"
        
        # Лимиты
        limits_str = f"{limits['input_limit']:,}/{limits['output_limit']:,}"
        
        # Статус
        if components.get('availability') == 9:
            status = "✅ Работает"
        elif components.get('availability') == 0:
            status = f"❌ {model_data['reason']}"
        else:
            status = f"⚠️ {model_data['reason']}"
        
        print(f"{i:<3} {model:<35} {domain_score:<20} {comp_str:<35} {limits_str:<15} {status:<15}")
    
    # Итоговая статистика
    print("\n" + "="*180)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*180)
    print(f"📊 Всего моделей проанализировано: {len(model_scores)}")
    print(f"✅ Работающих моделей: {len(working_models)}")
    print(f"⚠️ Квота исчерпана: {len(quota_exhausted)}")
    print(f"❌ Не найдено: {len(not_found)}")
    print(f"❌ Недостаточные лимиты: {len(insufficient_limits)}")
    print(f"❌ Другие ошибки: {len(other_errors)}")
    
    if working_models:
        print(f"\n🏆 ТОП-10 РАБОТАЮЩИХ МОДЕЛЕЙ ПО ДОМЕННОЙ ОЦЕНКЕ:")
        for i, model_data in enumerate(working_models[:10], 1):
            model = model_data['model']
            domain_score = model_data['domain_score']
            limits = model_data['limits']
            print(f"  {i}. {model} - {domain_score} - {limits['input_limit']:,}/{limits['output_limit']:,} токенов")
    
    # Анализ доменных оценок
    print(f"\n🔍 АНАЛИЗ ДОМЕННЫХ ОЦЕНОК:")
    print("   📈 Формат: MAJOR.MINOR.PATCH.TYPE.STABILITY.AVAILABILITY")
    print("   🎯 TYPE: flash=9, pro=8, nano=7, ultra=6, lite=5, vision=4, embedding=3, tts=2, базовые=1")
    print("   🛡️ STABILITY: stable=9, latest=7, early=5, preview=3, exp=1")
    print("   ✅ AVAILABILITY: works=9, problems=3, error=2, exhausted/not_found=0")
    
    # Примеры лучших моделей
    print(f"\n💡 ПРИМЕРЫ ЛУЧШИХ ОЦЕНОК:")
    examples = [
        ("gemini-3.1-flash-lite-preview", "3.1.2.9.3.9"),
        ("gemini-2.5-pro", "2.5.0.8.9.0"),
        ("imagen-3.0-generate-001", "3.0.1.4.5.9")
    ]
    
    for model, expected_score in examples:
        found = next((m for m in model_scores if m['model'] == model), None)
        if found:
            print(f"   📊 {model}: {found['domain_score']} (ожидалось: {expected_score})")

if __name__ == "__main__":
    analyze_models_with_domain_scoring()
