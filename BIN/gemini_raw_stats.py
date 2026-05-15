#!/usr/bin/env python3
"""
Скрипт для выгрузки 'голой' статистики по моделям Gemini
Без оценок - только реальные данные из API
"""

import requests
import re
import time
import json
from typing import Dict, List, Any

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
    """Получение всех Gemini моделей из API"""
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
        except Exception as e:
            print(f"Ошибка при получении моделей из {api_v}: {e}")
            continue
    
    return all_models

def get_model_info_from_api(model_name, api_key):
    """Получение детальной информации о модели из API"""
    try:
        # Определяем версию API
        api_ver = "v1beta" if "preview" in model_name or "exp" in model_name else "v1"
        
        info_url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}?key={api_key}"
        r = requests.get(info_url, timeout=5)
        
        if r.status_code == 200:
            model_info = r.json()
            return {
                'api_version': api_ver,
                'display_name': model_info.get('displayName', ''),
                'description': model_info.get('description', ''),
                'input_limit': model_info.get('inputTokenLimit', 0),
                'output_limit': model_info.get('outputTokenLimit', 0),
                'temperature_supported': 'temperature' in model_info.get('supportedGenerationMethods', []),
                'top_k_supported': 'topK' in model_info.get('supportedGenerationMethods', []),
                'top_p_supported': 'topP' in model_info.get('supportedGenerationMethods', []),
                'max_output_tokens': model_info.get('maxOutputTokens', 0),
                'base_model_id': model_info.get('baseModelId', ''),
                'version': model_info.get('version', ''),
                'name': model_info.get('name', ''),
                'tuned_model_source': model_info.get('tunedModelSource', {}),
                'supported_generation_methods': model_info.get('supportedGenerationMethods', []),
                'safety_settings': model_info.get('safetySettings', []),
                'routing_header': model_info.get('routingHeader', {}),
                'time_created': model_info.get('timeCreated', ''),
                'time_updated': model_info.get('timeUpdated', ''),
                'state': model_info.get('state', ''),
                'publisher_model': model_info.get('publisherModel', ''),
                'usage_context': model_info.get('usageContext', '')
            }
    except Exception as e:
        print(f"Ошибка при получении информации о модели {model_name}: {e}")
    
    return {
        'api_version': 'unknown',
        'display_name': '',
        'description': '',
        'input_limit': 0,
        'output_limit': 0,
        'temperature_supported': False,
        'top_k_supported': False,
        'top_p_supported': False,
        'max_output_tokens': 0,
        'base_model_id': '',
        'version': '',
        'name': '',
        'tuned_model_source': {},
        'supported_generation_methods': [],
        'safety_settings': [],
        'routing_header': {},
        'time_created': '',
        'time_updated': '',
        'state': '',
        'publisher_model': '',
        'usage_context': ''
    }

def test_model_availability(model_name, api_key, api_version):
    """Проверка доступности модели через тестовый запрос"""
    try:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
        
        test_payload = {
            "contents": [{"parts": [{"text": "Test"}]}],
            "generationConfig": {"maxOutputTokens": 5}
        }
        
        r = requests.post(url, json=test_payload, timeout=10)
        
        result = {
            'status_code': r.status_code,
            'available': r.status_code == 200,
            'error_type': None,
            'error_message': '',
            'response_time_ms': None
        }
        
        if r.status_code == 200:
            result['error_type'] = 'success'
            result['error_message'] = 'Available'
        elif r.status_code == 429:
            result['error_type'] = 'quota_exhausted'
            result['error_message'] = 'Rate limit exceeded'
        elif r.status_code == 404:
            result['error_type'] = 'not_found'
            result['error_message'] = 'Model not found'
        elif r.status_code == 401:
            result['error_type'] = 'unauthorized'
            result['error_message'] = 'Unauthorized'
        elif r.status_code == 400:
            result['error_type'] = 'bad_request'
            result['error_message'] = f'Bad request: {r.text[:100]}'
        elif r.status_code in [500, 503]:
            result['error_type'] = 'server_error'
            result['error_message'] = f'Server error: {r.status_code}'
        else:
            result['error_type'] = 'unknown_error'
            result['error_message'] = f'Unknown error: {r.status_code}'
            
        return result
            
    except requests.exceptions.Timeout:
        return {
            'status_code': None,
            'available': False,
            'error_type': 'timeout',
            'error_message': 'Request timeout',
            'response_time_ms': None
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'status_code': None,
            'available': False,
            'error_type': 'connection_error',
            'error_message': f'Connection error: {str(e)[:50]}',
            'response_time_ms': None
        }
    except Exception as e:
        return {
            'status_code': None,
            'available': False,
            'error_type': 'exception',
            'error_message': f'Exception: {str(e)[:50]}',
            'response_time_ms': None
        }

def parse_model_features(model_name):
    """Парсинг признаков из названия модели"""
    name = model_name.lower()
    
    features = {
        'has_preview': 'preview' in name,
        'has_exp': 'exp' in name,
        'has_latest': 'latest' in name,
        'has_flash': 'flash' in name,
        'has_pro': 'pro' in name,
        'has_lite': 'lite' in name,
        'has_nano': 'nano' in name,
        'has_ultra': 'ultra' in name,
        'has_vision': 'vision' in name,
        'has_image': 'image' in name,
        'has_embedding': 'embedding' in name,
        'has_tts': 'tts' in name,
        'has_speech': 'speech' in name,
        'has_robotics': 'robotics' in name,
        'has_computer_use': 'computer-use' in name,
        'has_customtools': 'customtools' in name,
        'has_clip': 'clip' in name,
        'has_music': 'music' in name,
        'has_video': 'veo' in name,
        'has_gemma': 'gemma' in name,
        'has_lyria': 'lyria' in name,
        'has_imagen': 'imagen' in name,
        'has_deep_research': 'deep-research' in name,
        'has_nano_banana': 'nano-banana' in name
    }
    
    # Определяем основной тип
    if features['has_gemma']:
        features['primary_type'] = 'gemma'
    elif features['has_imagen']:
        features['primary_type'] = 'imagen'
    elif features['has_lyria']:
        features['primary_type'] = 'lyria'
    elif features['has_deep_research']:
        features['primary_type'] = 'deep-research'
    elif features['has_nano_banana']:
        features['primary_type'] = 'nano-banana'
    elif 'gemini' in name:
        if features['has_flash']:
            features['primary_type'] = 'gemini-flash'
        elif features['has_pro']:
            features['primary_type'] = 'gemini-pro'
        elif features['has_nano']:
            features['primary_type'] = 'gemini-nano'
        elif features['has_ultra']:
            features['primary_type'] = 'gemini-ultra'
        elif features['has_lite']:
            features['primary_type'] = 'gemini-lite'
        else:
            features['primary_type'] = 'gemini'
    else:
        features['primary_type'] = 'other'
    
    # Парсим версию
    version_match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', name)
    if version_match:
        features['version_major'] = int(version_match.group(1))
        features['version_minor'] = int(version_match.group(2))
        features['version_patch'] = int(version_match.group(3)) if version_match.group(3) else 0
        features['version_string'] = f"{features['version_major']}.{features['version_minor']}.{features['version_patch']}"
    else:
        features['version_major'] = 0
        features['version_minor'] = 0
        features['version_patch'] = 0
        features['version_string'] = 'no-version'
    
    # Собираем все признаки в строку
    feature_tags = []
    for tag, has_feature in features.items():
        if has_feature and tag.startswith('has_'):
            feature_tags.append(tag[4:])  # Убираем префикс 'has_'
    
    features['feature_tags'] = ', '.join(feature_tags)
    
    return features

def collect_raw_model_stats():
    """Сбор 'голой' статистики по моделям"""
    api_key = load_api_key()
    if not api_key:
        print("❌ API ключ не найден")
        return []
    
    print("🔍 Сбор 'голой' статистики по моделям Gemini...")
    print("⚠️  Без оценок - только реальные данные из API")
    print()
    
    # Получаем все модели
    all_models = get_gemini_models(api_key)
    print(f"📊 Всего моделей найдено: {len(all_models)}")
    
    # Собираем статистику
    model_stats = []
    
    for i, model in enumerate(all_models, 1):
        print(f"🔄 Анализ модели {i}/{len(all_models)}: {model}")
        
        # Получаем информацию из API
        api_info = get_model_info_from_api(model, api_key)
        
        # Проверяем доступность
        availability = test_model_availability(model, api_key, api_info['api_version'])
        
        # Парсим признаки из названия
        features = parse_model_features(model)
        
        # Собираем полную статистику
        stats = {
            'model_name': model,
            'api_info': api_info,
            'availability': availability,
            'features': features,
            'raw_response': {
                'api_info_status': 'success' if api_info['input_limit'] > 0 else 'no_limits',
                'test_status': availability['error_type'],
                'full_api_response': api_info,
                'full_test_response': availability
            }
        }
        
        model_stats.append(stats)
        
        # Небольшая задержка чтобы не превысить лимиты
        time.sleep(0.1)
    
    return model_stats

def export_to_csv(model_stats, filename='gemini_raw_stats.csv'):
    """Экспорт статистики в CSV"""
    import csv
    
    # Определяем все возможные поля
    fieldnames = [
        'model_name',
        'api_version',
        'display_name',
        'description',
        'input_limit',
        'output_limit',
        'max_output_tokens',
        'temperature_supported',
        'top_k_supported',
        'top_p_supported',
        'base_model_id',
        'version',
        'state',
        'publisher_model',
        'usage_context',
        'primary_type',
        'version_string',
        'version_major',
        'version_minor',
        'version_patch',
        'feature_tags',
        'has_preview',
        'has_exp',
        'has_latest',
        'has_flash',
        'has_pro',
        'has_lite',
        'has_nano',
        'has_ultra',
        'has_vision',
        'has_image',
        'has_embedding',
        'has_tts',
        'has_speech',
        'has_robotics',
        'has_computer_use',
        'has_customtools',
        'has_clip',
        'has_music',
        'has_video',
        'has_gemma',
        'has_lyria',
        'has_imagen',
        'has_deep_research',
        'has_nano_banana',
        'available',
        'status_code',
        'error_type',
        'error_message',
        'time_created',
        'time_updated'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for stats in model_stats:
            api_info = stats['api_info']
            availability = stats['availability']
            features = stats['features']
            
            row = {
                'model_name': stats['model_name'],
                'api_version': api_info['api_version'],
                'display_name': api_info['display_name'],
                'description': api_info['description'],
                'input_limit': api_info['input_limit'],
                'output_limit': api_info['output_limit'],
                'max_output_tokens': api_info['max_output_tokens'],
                'temperature_supported': api_info['temperature_supported'],
                'top_k_supported': api_info['top_k_supported'],
                'top_p_supported': api_info['top_p_supported'],
                'base_model_id': api_info['base_model_id'],
                'version': api_info['version'],
                'state': api_info['state'],
                'publisher_model': api_info['publisher_model'],
                'usage_context': api_info['usage_context'],
                'primary_type': features['primary_type'],
                'version_string': features['version_string'],
                'version_major': features['version_major'],
                'version_minor': features['version_minor'],
                'version_patch': features['version_patch'],
                'feature_tags': features['feature_tags'],
                'has_preview': features['has_preview'],
                'has_exp': features['has_exp'],
                'has_latest': features['has_latest'],
                'has_flash': features['has_flash'],
                'has_pro': features['has_pro'],
                'has_lite': features['has_lite'],
                'has_nano': features['has_nano'],
                'has_ultra': features['has_ultra'],
                'has_vision': features['has_vision'],
                'has_image': features['has_image'],
                'has_embedding': features['has_embedding'],
                'has_tts': features['has_tts'],
                'has_speech': features['has_speech'],
                'has_robotics': features['has_robotics'],
                'has_computer_use': features['has_computer_use'],
                'has_customtools': features['has_customtools'],
                'has_clip': features['has_clip'],
                'has_music': features['has_music'],
                'has_video': features['has_video'],
                'has_gemma': features['has_gemma'],
                'has_lyria': features['has_lyria'],
                'has_imagen': features['has_imagen'],
                'has_deep_research': features['has_deep_research'],
                'has_nano_banana': features['has_nano_banana'],
                'available': availability['available'],
                'status_code': availability['status_code'],
                'error_type': availability['error_type'],
                'error_message': availability['error_message'],
                'time_created': api_info['time_created'],
                'time_updated': api_info['time_updated']
            }
            
            writer.writerow(row)
    
    print(f"📊 Статистика экспортирована в {filename}")

def export_to_json(model_stats, filename='gemini_raw_stats.json'):
    """Экспорт статистики в JSON"""
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(model_stats, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"📊 Полная статистика экспортирована в {filename}")

def print_summary_stats(model_stats):
    """Вывод сводной статистики"""
    print("\n" + "="*80)
    print("📊 СВОДНАЯ СТАТИСТИКА ПО МОДЕЛЯМ")
    print("="*80)
    
    total = len(model_stats)
    available = sum(1 for s in model_stats if s['availability']['available'])
    quota_exhausted = sum(1 for s in model_stats if s['availability']['error_type'] == 'quota_exhausted')
    not_found = sum(1 for s in model_stats if s['availability']['error_type'] == 'not_found')
    server_error = sum(1 for s in model_stats if s['availability']['error_type'] == 'server_error')
    timeout = sum(1 for s in model_stats if s['availability']['error_type'] == 'timeout')
    
    print(f"📈 Всего моделей: {total}")
    print(f"✅ Доступно: {available} ({available/total*100:.1f}%)")
    print(f"⚠️  Квота исчерпана: {quota_exhausted} ({quota_exhausted/total*100:.1f}%)")
    print(f"❌ Не найдено: {not_found} ({not_found/total*100:.1f}%)")
    print(f"🔥 Ошибка сервера: {server_error} ({server_error/total*100:.1f}%)")
    print(f"⏰ Таймаут: {timeout} ({timeout/total*100:.1f}%)")
    
    # Статистика по типам
    type_stats = {}
    for stats in model_stats:
        model_type = stats['features']['primary_type']
        if model_type not in type_stats:
            type_stats[model_type] = {'total': 0, 'available': 0}
        type_stats[model_type]['total'] += 1
        if stats['availability']['available']:
            type_stats[model_type]['available'] += 1
    
    print(f"\n📋 СТАТИСТИКА ПО ТИПАМ:")
    for model_type, counts in sorted(type_stats.items()):
        print(f"   {model_type}: {counts['available']}/{counts['total']} доступно")
    
    # Статистика по лимитам
    limit_stats = {}
    for stats in model_stats:
        limits = stats['api_info']['input_limit']
        if limits == 0:
            category = '0 токенов'
        elif limits < 10000:
            category = '< 10K токенов'
        elif limits < 100000:
            category = '10K-100K токенов'
        elif limits < 1000000:
            category = '100K-1M токенов'
        else:
            category = '> 1M токенов'
        
        limit_stats[category] = limit_stats.get(category, 0) + 1
    
    print(f"\n💾 СТАТИСТИКА ПО ЛИМИТАМ ВХОДА:")
    for category, count in sorted(limit_stats.items()):
        print(f"   {category}: {count} моделей")

if __name__ == "__main__":
    # Собираем статистику
    model_stats = collect_raw_model_stats()
    
    if model_stats:
        # Выводим сводную статистику
        print_summary_stats(model_stats)
        
        # Экспортируем в CSV
        export_to_csv(model_stats)
        
        # Экспортируем в JSON
        export_to_json(model_stats)
        
        print(f"\n🎯 Готово! 'Голая' статистика собрана без оценок")
        print(f"📁 Файлы созданы:")
        print(f"   - gemini_raw_stats.csv (таблица)")
        print(f"   - gemini_raw_stats.json (полные данные)")
    else:
        print("❌ Не удалось собрать статистику")
