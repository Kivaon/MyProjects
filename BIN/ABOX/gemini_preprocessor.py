#!/usr/bin/env python3
"""
Gemini Text Preprocessor - Подготовка текста для качественной озвучки
Использует Gemini для улучшения текста перед TTS
"""

import os
import sys
import google.generativeai as genai
from datetime import datetime

# Добавляем путь к TBOX utils
sys.path.append('/Users/kivaonmac/Documents/AI_Lab/BIN/TBOX')
import tbox_utils as utils

# --- ПАСПОРТ ---
VERSION = "v1.0.gemini-prep"
DATE    = "2026-02-10"
NAME    = os.path.basename(__file__)
META = {"name": NAME, "version": VERSION, "date": DATE}

class GeminiTextPreprocessor:
    def __init__(self, api_key=None):
        """Инициализация Gemini API"""
        
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            print("❌ Нужен API ключ Gemini")
            print("1. Получите ключ на: https://makersuite.google.com/app/apikey")
            print("2. Экспортируйте: export GEMINI_API_KEY='ваш_ключ'")
            return
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        print("✅ Gemini инициализирован")
    
    def prepare_hebrew_text(self, text):
        """Подготовка ивритского текста для озвучки"""
        
        prompt = f"""
        Подготовь этот ивритский текст для качественной озвучки на русском языке:
        
        ТЕКСТ:
        {text}
        
        ВЫПОЛНИ:
        1. Переведи текст на русский язык
        2. Расставь ударения во всех словах [ударная_гласная]
        3. Исправь пунктуацию для естественного чтения
        4. Добавь паузы [пауза] в логичных местах
        5. Замени сложные слова на более простые синонимы
        6. Убери сокращения и аббревиатуры
        
        ФОРМАТ ВЫВОДА:
        - Только готовый текст
        - Без комментариев
        - Ударения в квадратных скобках
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return text
    
    def prepare_russian_text(self, text):
        """Подготовка русского текста для озвучки"""
        
        prompt = f"""
        Подготовь этот русский текст для качественной озвучки:
        
        ТЕКСТ:
        {text}
        
        ВЫПОЛНИ:
        1. Расставь ударения во всех словах [ударная_гласная]
        2. Исправь пунктуацию для естественного чтения  
        3. Добавь паузы [пауза] в логичных местах
        4. Замени сложные слова на более простые синонимы
        5. Разбей длинные предложения на короткие
        6. Убери сокращения и аббревиатуры
        
        ПРАВИЛА УДАРЕНИЙ:
        - Проверяй все многосложные слова
        - Используй словарные ударения
        - В сомнительных случаях выбирай наиболее распространенный вариант
        
        ФОРМАТ ВЫВОДА:
        - Только готовый текст
        - Без комментариев
        - Ударения в квадратных скобках
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return text
    
    def process_file(self, input_file, output_file=None, language="auto"):
        """Обрабатывает файл и сохраняет результат"""
        
        try:
            # Читаем файл с учетом формата
            text = ""
            
            if input_file.endswith('.docx'):
                # Читаем Word документ
                try:
                    from docx import Document
                    doc = Document(input_file)
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                except ImportError:
                    print("❌ Нужно установить: pip install python-docx")
                    return None
            elif input_file.endswith('.rtf'):
                # Читаем RTF файл
                try:
                    from striprtf.striprtf import rtf_to_text
                    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                        rtf_content = f.read()
                    text = rtf_to_text(rtf_content)
                except ImportError:
                    # Если striprtf не установлен, используем простую очистку
                    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                        rtf_content = f.read()
                    # Убираем RTF теги
                    import re
                    text = re.sub(r'\\[a-zA-Z]+\d*', '', rtf_content)
                    text = re.sub(r'[{}]', '', text)
                    text = re.sub(r'\\[^a-zA-Z]', '', text)
            else:
                # Читаем текстовый файл
                with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            
            print(f"📝 Чтение файла: {os.path.basename(input_file)}")
            print(f"📏 Длина текста: {len(text)} символов")
            
            # Определяем язык
            if language == "auto":
                # Простая эвристика для определения языка
                hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
                russian_chars = sum(1 for c in text if 'а' <= c.lower() <= 'я')
                
                if hebrew_chars > russian_chars:
                    language = "hebrew"
                    print("🌐 Определен язык: Иврит")
                else:
                    language = "russian"
                    print("🌐 Определен язык: Русский")
            
            # Обрабатываем текст
            print("🤖 Обработка через Gemini...")
            
            if language == "hebrew":
                processed_text = self.prepare_hebrew_text(text)
            else:
                processed_text = self.prepare_russian_text(text)
            
            # Сохраняем результат
            if not output_file:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
                output_file = f"{base_name}_gemini_prepared_{timestamp}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(processed_text)
            
            print(f"✅ Сохранено: {output_file}")
            print(f"📏 Новая длина: {len(processed_text)} символов")
            
            return output_file
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return None
    
    def preview_improvements(self, original_text, processed_text):
        """Показывает разницу между оригиналом и обработкой"""
        
        print("\n" + "="*60)
        print("📊 СРАВНЕНИЕ ТЕКСТОВ")
        print("="*60)
        
        print("\n📝 ОРИГИНАЛ:")
        print("-"*40)
        print(original_text[:300] + "..." if len(original_text) > 300 else original_text)
        
        print("\n🤖 ОБРАБОТАНО GEMINI:")
        print("-"*40)
        print(processed_text[:300] + "..." if len(processed_text) > 300 else processed_text)
        
        # Статистика
        original_words = len(original_text.split())
        processed_words = len(processed_text.split())
        stress_marks = processed_text.count('[')
        
        print(f"\n📈 СТАТИСТИКА:")
        print(f"   Слов оригинал: {original_words}")
        print(f"   обработано: {processed_words}")
        print(f"   Ударений расставлено: {stress_marks}")
        print(f"   Изменено символов: {len(processed_text) - len(original_text)}")
        print("="*60)

def main():
    """Главная функция"""
    
    if len(sys.argv) < 2:
        print("Gemini Text Preprocessor - Улучшение текста для TTS")
        print("\nИспользование:")
        print("  python3 gemini_preprocessor.py файл.txt")
        print("  python3 gemini_preprocessor.py файл.txt --output=готовый.txt")
        print("  python3 gemini_preprocessor.py файл.txt --language=russian")
        print("\nПримеры:")
        print("  python3 gemini_preprocessor.py lecture.txt")
        print("  python3 gemini_preprocessor.py hebrew_text.txt --language=hebrew")
        return
    
    # Загружаем конфигурацию ABOX
    conf = utils.load_abox_config()
    
    # Инициализация
    preprocessor = GeminiTextPreprocessor()
    
    if not preprocessor.model:
        return
    
    # Парсинг аргументов
    input_file = sys.argv[1]
    output_file = None
    language = "auto"
    
    for arg in sys.argv[2:]:
        if arg.startswith('--output='):
            output_file = arg[9:]
        elif arg.startswith('--language='):
            language = arg[8:]
    
    # Проверяем файл
    if not os.path.exists(input_file):
        print(f"❌ Файл не найден: {input_file}")
        return
    
    # Обрабатываем
    result_file = preprocessor.process_file(input_file, output_file, language)
    
    if result_file and conf:
        utils.tbox_log(f"Текст обработан через Gemini: {os.path.basename(result_file)}", META, "DONE", conf)

if __name__ == "__main__":
    main()
