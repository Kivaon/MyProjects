#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TBox TTS Enhanced - Улучшенная озвучка с AI переводом и настройками
"""

import os
import sys
import re
import asyncio
import edge_tts
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'TBOX'))
import tbox_utils as utils
from datetime import datetime

# Импорт предобработки текста
try:
    from tbox_tts_preprocessor import preprocess_tts_text
except ImportError:
    def preprocess_tts_text(text):
        return text  # Fallback если модуль не найден

# --- ПАСПОРТ ---
VERSION = "v2.0.enhanced"
DATE    = "2026-02-07"
NAME = os.path.basename(__file__)
META = {"name": NAME, "version": VERSION, "date": DATE}

# --- АЛИАС ДЛЯ СТАРОГО ИМЕНИ ---
OLD_NAME = "tbox_tts_enhanced.py"
NEW_NAME = "tbox_tts_gen.py"

# Проверяем существование старого файла
old_file = os.path.join(os.path.dirname(__file__), OLD_NAME)
if os.path.exists(old_file):
    print(f"⚠️  Обнаружен старый файл {OLD_NAME}, рекомендуется удалить его вручную")
    print(f"🔄 Автоматически переименовываю {OLD_NAME} → {NEW_NAME}")

# Переименовываем старый файл, если он существует
if os.path.exists(old_file):
    try:
        os.rename(old_file, os.path.join(os.path.dirname(__file__), NEW_NAME))
        print(f"✅ Файл переименован: {OLD_NAME} → {NEW_NAME}")
    except Exception as e:
        print(f"❌ Ошибка переименования: {e}")

# --- НАСТРОЙКИ ГОЛОСОВ ---
VOICES = {
    'female': 'ru-RU-SvetlanaNeural',
    'male': 'ru-RU-DmitryNeural',      # Мужской голос по умолчанию
    'female_warm': 'ru-RU-DariyaNeural',
    'ethalon': 'ru-RU-Ethalon',        # Эталонный голос
    'male_mature': 'ru-RU-DmitryNeural',  # Зрелый мужской голос
}

# --- НАСТРОЙКИ СКОРОСТИ ---
SPEED_RATES = {
    'slow': '0.8',      # Медленно
    'normal': '1.0',     # Нормально  
    'fast': '1.2',       # Быстро
    'very_fast': '1.5',  # Очень быстро
}

# --- НАСТРОЙКИ ПЕРЕВОДА ---
TRANSLATION_METHODS = {
    'edge': 'edge_tts',        # Бесплатный Edge TTS
    'ai_parts': 'ai_parts',     # AI по частям со склейкой
    'ai_full': 'ai_full',       # AI целиком
}

def parse_speech_command(command):
    """Парсинг команды speech [файл] [голос] [метод] [скорость]"""
    parts = command.strip().split()
    
    if len(parts) < 2:
        return None
    
    config = {
        'input_file': parts[0],
        'voice': None,
        'method': 'edge',  # по умолчанию
        'speed': 'normal'
    }
    
    # Парсинг параметров
    for part in parts[1:]:
        if part in VOICES or part.startswith('CUSTOM:'):
            config['voice'] = part
        elif part in SPEED_RATES:
            config['speed'] = part
        elif part in TRANSLATION_METHODS:
            config['method'] = part
    
    return config

async def translate_text_with_ai(text, target_lang='ru', conf=None):
    """Перевод текста с помощью AI по частям"""
    try:
        # Импортируем translator
        import tbox_translator as translator
        
        # Разбиваем на части для перевода
        max_part_length = 3000
        text_parts = []
        
        for i in range(0, len(text), max_part_length):
            text_parts.append(text[i:i+max_part_length])
        
        translated_parts = []
        
        for i, part in enumerate(text_parts, 1):
            if conf:
                utils.tbox_log(f"Перевод части {i}/{len(text_parts)}...", META, "INFO", conf)
            
            # Используем промпт GENERIC для перевода
            translated = await translator.translate_md_chunk_async(
                part, i, len(text_parts), "", conf, 
                {'GENERIC': "Переведи текст на русский:\n{chunk}"}, 
                'GENERIC', False
            )
            
            if translated:
                translated_parts.append(translated)
            else:
                translated_parts.append(part)  # Если перевод не удался, оставляем оригинал
        
        # Склеиваем переведенные части
        return ' '.join(translated_parts)
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка AI перевода: {e}", META, "ERROR", conf)
        return text  # Возвращаем оригинал при ошибке

async def translate_text_full_ai(text, target_lang='ru', conf=None):
    """Перевод текста с помощью AI целиком"""
    try:
        import tbox_translator as translator
        
        if conf:
            utils.tbox_log(f"Перевод полного текста...", META, "INFO", conf)
        
        translated = await translator.translate_md_chunk_async(
            text, 1, 1, "", conf,
            {'GENERIC': "Переведи текст на русский:\n{chunk}"},
            'GENERIC', False
        )
        
        return translated if translated else text
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка AI перевода: {e}", META, "ERROR", conf)
        return text

def split_text_for_tts(text, max_chars=4000):
    """Разбивает текст на чанки для TTS с правильной обработкой слов и пунктуации"""
    chunks = []
    current_chunk = ""
    
    # Определяем язык текста
    is_hebrew = bool(re.search(r'[\u0590-\u05FF]', text))
    
    # Очищаем текст от специальных символов и кодов
    clean_text = text
    
    # Убираем HTML/XML теги если есть
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    # Обработка знаков препинания - убираем точки совсем, добавляем пробелы к другим
    # Точки полностью убираем - TTS все равно читает их как "точка"
    clean_text = clean_text.replace('.', ' ')  # Заменяем точки на пробелы
    clean_text = re.sub(r'([,;:!?])', r' \1 ', clean_text)  # Другие знаки с пробелами
    
    # Убираем лишние пробелы и переносы строк
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Дополнительная обработка для русского языка
    if not is_hebrew:
        # Заменяем распространенные сокращения для правильного чтения
        replacements = {
            'т.д.': 'то есть',
            'т.п.': 'такое',
            'др.': 'другое',
            'пр.': 'пример',
            'см.': 'смотри',
            'т.к.': 'так как',
            'т.е.': 'то есть',
            'т.о.': 'таким образом',
        }
        
        for abbr, full in replacements.items():
            clean_text = clean_text.replace(abbr, full)
        
        # Обработка чисел и дат
        clean_text = re.sub(r'(\d{4})г\.', r'в \1 году', clean_text)
        clean_text = re.sub(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', r'\1 \2 \1 \3', clean_text)
    
    if is_hebrew:
        # Для иврита: разбиваем по словам с сохранением пунктуации
        words = re.split(r'(\s+)', clean_text)
        
        for word in words:
            if word.strip():  # Пропускаем пустые элементы
                if len(current_chunk) + len(word) <= max_chars:
                    current_chunk += word
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = word
    else:
        # Для других языков: разбиваем по предложениям для лучшей интонации
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                if len(current_chunk) + len(sentence) <= max_chars:
                    current_chunk += sentence + " "
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

async def text_to_speech_enhanced(text, output_file, voice='ru-RU-SvetlanaNeural', 
                                  method='edge', speed='normal', conf=None):
    """Улучшенное преобразование текста в речь с разными методами"""
    try:
        if conf:
            utils.tbox_log(f"Начало озвучки: {os.path.basename(output_file)}", META, "START", conf)
        
        # Предобработка текста - исправление ударений и ошибок
        processed_text = preprocess_tts_text(text)
        
        if conf:
            utils.tbox_log(f"Текст предобработан", META, "INFO", conf)
        
        # Выбор метода обработки
        if method == 'edge':
            # Просто используем Edge TTS
            pass
        elif method == 'ai_chunks':
            # AI перевод по частям
            processed_text = await translate_text_ai_chunks(processed_text, conf=conf)
        elif method == 'ai_full':
            processed_text = await translate_text_full_ai(processed_text, conf=conf)
        
        # Разбиваем на чанки для TTS
        chunks = split_text_for_tts(processed_text, max_chars=3000)
        
        # Создаем директорию
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Озвучка каждого чанка
        communicate = None
        for i, chunk in enumerate(chunks, 1):
            if conf:
                utils.tbox_log(f"Озвучка чанка {i}/{len(chunks)}...", META, "INFO", conf)
            
            chunk_file = output_file.replace('.mp3', f'_part_{i:03d}.mp3')
            
            # Применяем скорость озвучки
            communicate = edge_tts.Communicate(chunk, voice)
            if speed != 'normal':
                communicate = edge_tts.Communicate(chunk, voice, rate=SPEED_RATES[speed])
            
            await communicate.save(chunk_file)
            
            if conf:
                utils.tbox_log(f"Чанк {i} сохранен: {os.path.basename(chunk_file)}", META, "INFO", conf)
        
        # Склеиваем все части в один файл
        if len(chunks) > 1:
            if conf:
                utils.tbox_log(f"Склейка {len(chunks)} частей...", META, "INFO", conf)
            
            # Используем ffmpeg для склейки
            import subprocess
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', 
                f"concat:{'|'.join([f'part_{i:03d}.mp3' for i in range(1, len(chunks) + 1)])}",
                '-c', 'copy', output_file
            ]
            
            # Создаем временный файл со списком
            list_file = output_file.replace('.mp3', '_list.txt')
            with open(list_file, 'w') as f:
                for i in range(1, len(chunks) + 1):
                    f.write(f"file 'part_{i:03d}.mp3'\n")
            
            # Пробуем ffmpeg
            try:
                result = subprocess.run(
                    ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_file],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    # Удаляем временные файлы
                    for i in range(1, len(chunks) + 1):
                        temp_file = output_file.replace('.mp3', f'_part_{i:03d}.mp3')
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    
                    if conf:
                        utils.tbox_log(f"Склейка завершена: {os.path.basename(output_file)}", META, "DONE", conf)
                else:
                    if conf:
                        utils.tbox_log(f"Ошибка склейки: {result.stderr}", META, "ERROR", conf)
                    
            except FileNotFoundError:
                if conf:
                    utils.tbox_log("ffmpeg не найден, склейка пропущена", META, "WARN", conf)
            except Exception as e:
                if conf:
                    utils.tbox_log(f"Ошибка склейки: {e}", META, "ERROR", conf)
        else:
            # Одна часть - просто сохраняем
            communicate = edge_tts.Communicate(chunks[0], voice)
            if speed != 'normal':
                communicate = edge_tts.Communicate(chunks[0], voice, rate=SPEED_RATES[speed])
            await communicate.save(output_file)
        
        if conf:
            utils.tbox_log(f"Озвучка завершена: {os.path.basename(output_file)}", META, "DONE", conf)
        
        return True
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка озвучки: {e}", META, "ERROR", conf)
        return False

async def process_file_with_tts(input_path, output_dir=None, voice=None, 
                                  method='edge', speed='normal', conf=None):
    """Обрабатывает файл и создает озвучку с использованием путей из конфигурации"""
    try:
        # Читаем входной файл
        content = ""
        
        # Используем пути из конфигурации
        if conf:
            if not output_dir:
                output_dir = conf.get('AUDIO_DIR', '06_AUDIO')
            if not voice:
                voice = conf.get('DEFAULT_VOICE', 'ru-RU-DmitryNeural')  # Мужской голос по умолчанию
            
            # Читаем входной файл с учетом формата
            if input_path.endswith('.docx'):
                # Читаем Word документ
                from docx import Document
                doc = Document(input_path)
                for paragraph in doc.paragraphs:
                    content += paragraph.text + "\n"
            elif input_path.endswith('.rtf'):
                # Читаем RTF файл - извлекаем только текст
                try:
                    from striprtf.striprtf import rtf_to_text
                    with open(input_path, 'r', encoding='utf-8') as f:
                        rtf_content = f.read()
                    content = rtf_to_text(rtf_content)
                except ImportError:
                    # Если striprtf не установлен, используем простую очистку
                    with open(input_path, 'r', encoding='utf-8') as f:
                        rtf_content = f.read()
                    # Убираем RTF теги
                    content = re.sub(r'\\[a-zA-Z]+\d*', '', rtf_content)
                    content = re.sub(r'[{}]', '', content)
                    content = re.sub(r'\\[^a-zA-Z]', '', content)
                except Exception as e:
                    if conf:
                        utils.tbox_log(f"Ошибка чтения RTF: {e}", META, "ERROR", conf)
                    return False
            elif input_path.endswith('.md'):
                # Читаем Markdown файл
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # Читаем текстовый файл
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
        
        # Создаем выходной файл с путями из конфигурации
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        
        # Используем полный путь к выходному файлу
        if output_dir and not output_dir.startswith('/'):
            output_file = os.path.join(output_dir, f"{base_name}_tts_{timestamp}.mp3")
        else:
            # Если output_dir относительный, комбинируем с директорией скрипта
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, output_dir, f"{base_name}_tts_{timestamp}.mp3")
        
        # Озвучка с улучшенными настройками
        success = await text_to_speech_enhanced(
            content, output_file, voice, method, speed, conf
        )
        
        return success
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка обработки файла: {e}", META, "ERROR", conf)
        return False

def main():
    """Главная функция с использованием конфигурации"""
    # Загружаем конфигурацию ABOX
    conf = utils.load_abox_config()
    if not conf:
        print("КРИТИЧЕСКАЯ ОШИБКА: aconfig.txt не найден.")
        return
    
    # Получаем параметры из конфигурации или командной строки
    if len(sys.argv) >= 2:
        # Если есть аргументы командной строки, используем их
        input_file = sys.argv[1]
        
        # Дополнительные параметры
        voice = conf.get('DEFAULT_VOICE', 'ru-RU-DmitryNeural')  # Мужской голос по умолчанию
        output_dir = conf.get('AUDIO_DIR', '06_AUDIO')
        method = conf.get('DEFAULT_TTS_METHOD', 'edge')
        speed = conf.get('DEFAULT_TTS_SPEED', 'normal')
        
        # Парсинг дополнительных параметров
        for arg in sys.argv[2:]:
            if arg.startswith('--voice='):
                voice = arg[8:]  # Убираем --voice=
            elif arg.startswith('--output='):
                output_dir = arg[9:]  # Убираем --output=
            elif arg.startswith('--method='):
                method = arg[9:]  # Убираем --method=
            elif arg.startswith('--speed='):
                speed = arg[9:]  # Убираем --speed=
        
        # Логируем параметры
        if conf:
            utils.tbox_log(f"🎤 Запуск из командной строки: файл={input_file}, голос={voice}, метод={method}, скорость={speed}", META, "INFO", conf)
    
    else:
        # Если нет аргументов, используем конфигурацию по умолчанию
        input_file = conf.get('DEFAULT_INPUT_FILE', '')
        voice = conf.get('DEFAULT_VOICE', 'ru-RU-DmitryNeural')  # Мужской голос по умолчанию
        output_dir = conf.get('AUDIO_DIR', '06_AUDIO')
        method = conf.get('DEFAULT_TTS_METHOD', 'edge')
        speed = conf.get('DEFAULT_TTS_SPEED', 'normal')
        
        # Если входной файл не указан, ищем в TTS_DIR
        if not input_file:
            tts_dir = conf.get('TTS_DIR', '06_AUDIO/IN')
            if os.path.exists(tts_dir):
                # Ищем последний текстовый файл
                text_files = []
                for file in os.listdir(tts_dir):
                    if file.endswith(('.md', '.txt', '.rtf')):
                        file_path = os.path.join(tts_dir, file)
                        file_time = os.path.getmtime(file_path)
                        text_files.append((file_time, file_path, file))
                
                if text_files:
                    # Сортируем по времени и берем последний
                    text_files.sort(reverse=True)
                    input_file = text_files[0][1]  # Берем путь к последнему файлу
                    if conf:
                        utils.tbox_log(f"📁 Найден последний файл: {text_files[0][2]}", META, "INFO", conf)
        
        if conf:
            utils.tbox_log(f"🎤 Запуск из конфигурации: файл={input_file}, голос={voice}, метод={method}, скорость={speed}", META, "INFO", conf)
    
    # Проверяем существование файла
    if not input_file:
        print("❌ Ошибка: входной файл не указан")
        return
    
    if not os.path.exists(input_file):
        print(f"❌ Ошибка: файл не найден: {input_file}")
        return
    
    # Обработка файла
    asyncio.run(process_file_with_tts(
        input_file, output_dir, voice, method, speed, conf
    ))

if __name__ == "__main__":
    main()
