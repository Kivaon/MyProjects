#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TBox Translator v6.12.gpt-simple
Перевод MD-файлов с поддержкой Gemini и OpenAI GPT
"""

import os, sys, time, glob, requests, shutil, re, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from docx import Document   
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from tbox_utils import tbox_log

# Попытка импорта OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# --- MANIFEST ---
VERSION = "v6.12.gpt-simple"
DATE    = "2026-04-27"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

# Глобальные переменные для провайдеров
CURRENT_PROVIDER = "gemini"  # "gemini" или "openai"
CURRENT_MODEL = "gemini-1.5-flash"  # Будет обновлен в init_providers()

def load_tbox_config():
    """Загрузка конфигурации"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(script_dir, "_config", "tconfig.txt")
    conf = {}
    if not os.path.exists(config_path): 
        print(f"Ошибка: Конфиг не найден: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    conf[key.strip()] = val.strip()
        actual_base = conf.get('BASE_DIR', script_dir)
        for key in conf:
            if '${BASE_DIR}' in conf[key]:
                conf[key] = conf[key].replace('${BASE_DIR}', actual_base)
        return conf
    except Exception as e:
        print(f"Ошибка в load_tbox_config: {e}")
        return None

def load_prompts(conf):
    """Загрузка справочника промптов"""
    prompts_dir = conf.get('PROMPTS_DIR', 'BIN/_config')
    base_dir = conf.get('BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompts_path = os.path.join(base_dir, prompts_dir, 'prompts.md')
    prompts = {
        'TORAH': "Ты — редактор лекций Рава {author}. Переведи часть {part_num}/{total_parts} на русский.\nСТРОГО СОХРАНЯЙ РАЗМЕТКУ: '#' для заголовков и '**' для выделений.\nСтиль: возвышенный, точный.\nТЕКСТ:\n{chunk}",
        'FICTION': "Переведи художественный текст часть {part_num}/{total_parts} на русский.\nСОХРАНЯЙ стилистику и тон оригинала.\nРазметка: '#' для заголовков, '**' для выделений.\nТЕКСТ:\n{chunk}",
        'GENERIC': "Переведи текст часть {part_num}/{total_parts} на русский.\nТЕКСТ:\n{chunk}"
    }
    if os.path.exists(prompts_path):
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for block in content.split('\n---\n'):
                    if ':' in block.split('\n')[0]:
                        key = block.split('\n')[0].strip()
                        prompt = '\n'.join(block.split('\n')[1:]).strip()
                        prompts[key] = prompt
        except Exception as e:
            tbox_log(f"Ошибка загрузки промптов: {e}", META, "ERROR", conf)
    else:
        tbox_log(f"Файл промптов не найден, используем встроенные: {prompts_path}", META, "WARN", conf)
    return prompts

def get_api_ver(model_name):
    """Определяет API версию по названию модели"""
    v_match = re.search(r'(\d+)', model_name)
    v_major = int(v_match.group(1)) if v_match else 1
    if v_major >= 2 or any(x in model_name.lower() for x in ['exp', 'beta']):
        return "v1beta"
    return "v1"


def init_providers(conf, use_openai=False):
    """Инициализация провайдеров - Gemini по умолчанию, GPT если указан"""
    global CURRENT_PROVIDER, CURRENT_MODEL
    
    if use_openai:
        # Используем OpenAI GPT
        openai_key = conf.get('OPENAI_API_KEY', '').strip()
        openai_model = conf.get('MODEL_GPT', 'gpt-3.5-turbo').strip()
        
        if not OPENAI_AVAILABLE:
            print("OpenAI не установлен. Установите: pip install openai")
            return False
        
        if not openai_key:
            print("OPENAI_API_KEY не найден в конфигурации")
            return False
        
        CURRENT_PROVIDER = "openai"
        CURRENT_MODEL = openai_model
        print(f"Используем OpenAI GPT: {openai_model}")
        return True
    else:
        # Используем Gemini (по умолчанию)
        gemini_key = conf.get('API_KEY', '').strip()
        gemini_model = conf.get('MODEL_GEMINI', 'gemini-1.5-flash').strip()
        
        if not gemini_key:
            print("API_KEY не найден в конфигурации")
            return False
        
        CURRENT_PROVIDER = "gemini"
        CURRENT_MODEL = gemini_model
        print(f"Используем Gemini: {gemini_model}")
        return True


def translate_with_gemini(prompt, api_key, model):
    """Перевод через Gemini API"""
    api_ver = get_api_ver(model)
    url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model}:generateContent?key={api_key}"
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192
        }
    }
    
    response = requests.post(url, json=data, timeout=30)
    return response


def translate_with_openai(prompt, conf):
    """Перевод через OpenAI GPT API"""
    openai_key = conf.get('OPENAI_API_KEY', '').strip()
    openai_model = conf.get('MODEL_GPT', 'gpt-3.5-turbo').strip()
    
    if not OPENAI_AVAILABLE or not openai_key:
        raise Exception("OpenAI GPT недоступен")
    
    client = openai.OpenAI(api_key=openai_key)
    
    response = client.chat.completions.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": "Ты профессиональный переводчик. Переводи текст точно, сохраняя форматирование и смысл."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=8192,
        temperature=0.3
    )
    
    return response


def analyze_429_error(error_text):
    """Анализирует ошибку 429 для определения RPM или RPD"""
    error_lower = error_text.lower()
    
    # Проверка индикаторов RPD (запросов в день)
    rpd_indicators = [
        'per day', 'daily', 'day quota', 'daily quota',
        'requestsperday', 'perday', 'day limit'
    ]
    
    # Проверка индикаторов RPM (запросов в минуту)  
    rpm_indicators = [
        'per minute', 'minute', 'rpm', 'per min',
        'requestsperminute', 'minute quota', 'rate limit'
    ]
    
    if any(indicator in error_lower for indicator in rpd_indicators):
        return 'RPD'  # Дневной лимит превышен - немедленно сменить модель
    elif any(indicator in error_lower for indicator in rpm_indicators):
        return 'RPM'  # Минутный лимит превышен - можно retry с задержкой
    else:
        # По умолчанию RPM для безопасности (можно retry)
        return 'RPM'


def switch_to_openai(conf):
    """Переключение на OpenAI GPT"""
    global CURRENT_PROVIDER, CURRENT_MODEL
    
    openai_key = conf.get('OPENAI_API_KEY', '').strip()
    openai_model = conf.get('MODEL_GPT', 'gpt-3.5-turbo').strip()
    
    if not OPENAI_AVAILABLE or not openai_key:
        print("OpenAI GPT недоступен для переключения")
        return False
    
    CURRENT_PROVIDER = "openai"
    CURRENT_MODEL = openai_model
    print(f"Переключение на OpenAI GPT: {openai_model}")
    return True


def translate_md_chunk(chunk, part_num, total_parts, author, conf, prompts, prompt_code, include_original):
    """Перевод MD-текста с retry-логикой и переключением провайдеров"""
    global CURRENT_PROVIDER, CURRENT_MODEL
    
    # Получить промпт из справочника
    base_prompt = prompts.get(prompt_code, prompts.get('GENERIC', 'Переведи на русский: {chunk}'))
    
    # Подставить плейсхолдеры
    prompt = base_prompt.format(
        author=author,
        part_num=part_num,
        total_parts=total_parts,
        chunk=chunk
    )
    
    # Если include_original, добавить инструкцию о цитатах
    if include_original:
        prompt += "\n\nВКЛЮЧАЙ ОРИГИНАЛЬНЫЙ ТЕКСТ ЦИТАТ В СКОБКАХ ПОСЛЕ ПЕРЕВОДА."

    while True:
        # Маркер начала чанка с текущим провайдером
        header_marker = f"\n\n--- [PART {part_num}/{total_parts} | {CURRENT_PROVIDER.upper()}: {CURRENT_MODEL}] ---\n"
        
        # 3 попытки для текущего провайдера
        for attempt in range(3):
            try:
                if CURRENT_PROVIDER == "gemini":
                    api_key = conf.get('API_KEY', '').split('#')[0].strip()
                    response = translate_with_gemini(prompt, api_key, CURRENT_MODEL)
                    
                    if response.status_code == 200:
                        result = response.json()
                        translation = result['candidates'][0]['content']['parts'][0]['text']
                        return header_marker + translation
                    elif response.status_code == 429:
                        error_text = response.text
                        error_type = analyze_429_error(error_text)
                        
                        if error_type == 'RPD':
                            print("Gemini дневной лимит (RPD) - переключение на OpenAI")
                            # Переключаемся на OpenAI
                            if switch_to_openai(conf):
                                break  # Переключились, пробуем заново
                            else:
                                return header_marker + f"\n\n[ОШИБКА: Все провайдеры недоступны]\n[ИСХОДНИК]:\n{chunk[:300]}..."
                        else:
                            # RPM - retry с задержкой
                            if attempt < 2:
                                delay = 10 + (attempt * 5)
                                print(f"Gemini минутный лимит (RPM) - ожидание {delay}s")
                                time.sleep(delay)
                                continue
                            else:
                                # Последняя попытка - переключаем провайдер
                                if switch_to_openai(conf):
                                    break
                                else:
                                    return header_marker + f"\n\n[ОШИБКА: Все провайдеры недоступны]\n[ИСХОДНИК]:\n{chunk[:300]}..."
                    else:
                        raise Exception(f"Gemini API error {response.status_code}: {response.text}")
                
                elif CURRENT_PROVIDER == "openai":
                    response = translate_with_openai(prompt, conf)
                    translation = response.choices[0].message.content
                    return header_marker + translation
                
            except Exception as e:
                error_msg = str(e)
                print(f"Ошибка {CURRENT_PROVIDER.upper()} попытки {attempt+1}: {error_msg}")
                
                if attempt == 2:  # Последняя попытка
                    if CURRENT_PROVIDER == "gemini":
                        # Пробуем переключиться на OpenAI
                        if switch_to_openai(conf):
                            break
                        else:
                            return header_marker + f"\n\n[ОШИБКА: Все провайдеры недоступны]\n[ИСХОДНИК]:\n{chunk[:300]}..."
                    else:
                        return header_marker + f"\n\n[ОШИБКА: OpenAI недоступен]\n[ИСХОДНИК]:\n{chunk[:300]}..."
                
                # Задержка перед retry
                time.sleep(5)


def find_best_boundary(text, max_chars):
    """Находит лучшую границу для разбиения текста"""
    if len(text) <= max_chars:
        return len(text)
    
    # Ищем конец предложения
    for i in range(max_chars, max(0, max_chars-100), -1):
        if text[i] in '.!?':
            return i + 1
    
    # Ищем конец слова
    for i in range(max_chars, max(0, max_chars-50), -1):
        if text[i] == ' ':
            return i
    
    return max_chars


def main():
    """Основная функция обработки MD-файлов"""
    parser = argparse.ArgumentParser(description='Перевод MD-файлов с мульти-модельной поддержкой')
    parser.add_argument('input_file', help='MD файл для перевода')
    parser.add_argument('--provider', choices=['gemini', 'openai'], help='Принудительный выбор провайдера')
    parser.add_argument('--original', action='store_true', help='Включать оригинальный текст в перевод')
    args = parser.parse_args()
    
    conf = load_tbox_config()
    if not conf:
        print("Ошибка загрузки конфигурации")
        return
    
    # Инициализация провайдеров
    use_openai = args.provider == "openai"
    if not init_providers(conf, use_openai=use_openai):
        print("Ошибка инициализации провайдеров")
        return
    
    # Загрузка промптов
    prompts = load_prompts(conf)
    
    # Обработка файла
    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Файл не найден: {input_path}")
        return
    
    print(f"Обработка файла: {input_path}")
    print(f"Провайдер: {CURRENT_PROVIDER.upper()} - {CURRENT_MODEL}")
    
    # Чтение MD файла
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Разбиение на чанки
    max_chars = 3000
    chunks = []
    start = 0
    
    while start < len(md_content):
        end = start + max_chars
        if end >= len(md_content):
            chunks.append(md_content[start:])
            break
        
        # Ищем ближайший конец предложения/абзаца
        boundary_text = md_content[start:end]
        boundary_pos = find_best_boundary(boundary_text, max_chars)
        
        chunk = md_content[start:start + boundary_pos]
        chunks.append(chunk)
        start += boundary_pos
    
    print(f"Разбито на {len(chunks)} чанков")
    
    # Перевод чанков
    translated_chunks = []
    author = "Автор"  # Можно извлечь из имени файла или конфига
    prompt_code = "GENERIC"  # Можно определить по содержимому
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Перевод чанка {i}/{len(chunks)}...")
        translated = translate_md_chunk(chunk, i, len(chunks), author, conf, prompts, prompt_code, args.original)
        translated_chunks.append(translated)
        
        # Пауза между чанками
        if i < len(chunks):
            time.sleep(2)
    
    # Сохранение результата
    output_path = input_path.replace('.md', '_translated.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(translated_chunks))
    
    print(f"Перевод сохранен: {output_path}")


if __name__ == "__main__":
    main()
