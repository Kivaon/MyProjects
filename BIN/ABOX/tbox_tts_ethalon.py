#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Создание эталонного голоса из примеров для TBox TTS
"""

import os
import json
import subprocess
from datetime import datetime

def create_ethalon_voice(voice_name="ethalon", output_dir=None, language="hebrew"):
    """Создает эталонный голос из примеров в директории"""
    
    # Загружаем конфигурацию
    import tbox_utils as utils
    conf = utils.load_abox_config()
    
    # Используем пути из конфигурации
    if conf:
        if not output_dir:
            output_dir = conf.get('ETHALON_DIR', '06_AUDIO/VOICE')
    
    # Пути
    ethalon_config = os.path.join(output_dir, "metadata", f"{voice_name}_voice.json")
    ethalon_model = os.path.join(output_dir, f"{voice_name}.onnx")
    
    # Создаем директории
    os.makedirs(os.path.join(output_dir, "metadata"), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🎤 Создание эталонного голоса: {voice_name} ({language})")
    
    # 2. Выбираем примеры в зависимости от языка
    if language == "russian":
        examples = [
            # Буквы
            {"text": "А", "description": "А"},
            {"text": "Б", "description": "Бэ"},
            {"text": "В", "description": "Вэ"},
            {"text": "Г", "description": "Гэ"},
            {"text": "Д", "description": "Дэ"},
            {"text": "Е", "description": "Е"},
            {"text": "Ё", "description": "Ё"},
            {"text": "Ж", "description": "Жэ"},
            {"text": "З", "description": "Зэ"},
            {"text": "И", "description": "И"},
            {"text": "Й", "description": "Й"},
            {"text": "К", "description": "Ка"},
            {"text": "Л", "description": "Эл"},
            {"text": "М", "description": "Эм"},
            {"text": "Н", "description": "Эн"},
            {"text": "О", "description": "О"},
            {"text": "П", "description": "Пэ"},
            {"text": "Р", "description": "Эр"},
            {"text": "С", "description": "Эс"},
            {"text": "Т", "description": "Тэ"},
            {"text": "У", "description": "У"},
            {"text": "Ф", "description": "Эф"},
            {"text": "Х", "description": "Ха"},
            {"text": "Ц", "description": "Цэ"},
            {"text": "Ч", "description": "Чэ"},
            {"text": "Ш", "description": "Ша"},
            {"text": "Щ", "description": "Ща"},
            {"text": "Ъ", "description": "Твёрдый знак"},
            {"text": "Ы", "description": "Ы"},
            {"text": "Ь", "description": "Мягкий знак"},
            {"text": "Э", "description": "Э"},
            {"text": "Ю", "description": "Ю"},
            
            # Гласные
            {"text": "а", "description": "а"},
            {"text": "о", "description": "о"},
            {"text": "у", "description": "у"},
            {"text": "ы", "description": "ы"},
            {"text": "э", "description": "э"},
            
            # Сочетания
            {"text": "Привет", "description": "Приветствие"},
            {"text": "Спасибо", "description": "Благодарность"},
            {"text": "Здравствуйте", "description": "Формальное приветствие"},
        ]
        display_name = "Эталонный голос (русский)"
        gender = "neutral"
        age = "adult"
        description = "Стандартизированное произношение русского языка"
        
    elif language == "hebrew":
        examples = [
            # Буквы
            {"text": "א", "description": "Алеф"},
            {"text": "ב", "description": "Бет"},
            {"text": "ג", "description": "Гимель"},
            {"text": "ד", "description": "Далет"},
            {"text": "ה", "description": "Гей"},
            {"text": "ו", "description": "Вав"},
            {"text": "ז", "description": "Заин"},
            {"text": "ט", "description": "Тет"},
            {"text": "י", "description": "Йуд"},
            {"text": "כ", "description": "Ламед"},
            {"text": "מ", "description": "Мем"},
            {"text": "נ", "description": "Нун"},
            {"text": "ס", "description": "Самех"},
            {"text": "ע", "description": "Аин"},
            {"text": "פ", "description": "Пэ"},
            {"text": "צ", "description": "Цади"},
            {"text": "ק", "description": "Куф"},
            {"text": "ר", "description": "Реш"},
            {"text": "ש", "description": "Шин"},
            {"text": "ת", "description": "Тав"},
            
            # Гласные
            {"text": "אָ", "description": "Камац"},
            {"text": "אֹ", "description": "Хатаф"},
            {"text": "אִ", "description": "Хирик"},
            {"text": "אֶ", "description": "Цади"},
            {"text": "אַ", "description": "Патах"},
            {"text": "אָ", "description": "Камац с огласовкой"},
            
            # Сочетания
            {"text": "שלום", "description": "Шалом"},
            {"text": "תודה", "description": "Тода"},
            {"text": "ברכה", "description": "Баруха"},
            {"text": "אמן", "description": "Амин"},
            {"text": "תודה", "description": "Тода"},
            {"text": "מצוות", "description": "Командование"},
            {"text": "לימוש", "description": "Изучение"},
            {"text": "עבודה", "description": "Работа"},
            {"text": "משפח", "description": "Семья"},
            {"text": "תורה", "description": "Тора"},
            {"text": "מצוות", "description": "Командование"},
            {"text": "לימוש", "description": "Изучение"},
        ]
        display_name = "Эталонный голос (иврит)"
        gender = "neutral"
        age = "adult"
        description = "Стандартизированное произношение иврита"
    
    else:
        print(f"❌ Неподдерживаемый язык: {language}")
        return
    
    # 3. Создаем конфигурацию эталонного голоса
    ethalon_config_data = {
        "name": voice_name,
        "display_name": display_name,
        "language": language,
        "gender": gender,
        "age": age,
        "description": description,
        "created": datetime.now().isoformat(),
        "examples_count": len(examples),
        "examples": examples
    }
    
    # Сохраняем конфигурацию
    with open(ethalon_config, 'w', encoding='utf-8') as f:
        json.dump(ethalon_config_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Конфигурация сохранена: {ethalon_config}")
    
    # 4. Создаем обучающие данные для edge-tts
    training_script = f"""
#!/bin/bash
# Создание эталонного голоса: {voice_name} ({language})

echo "🎤 Создание эталонного голоса: {voice_name}"

# Создаем временный файл с примерами
TEMP_EXAMPLES="/tmp/ethalon_examples.txt"
cat > "$TEMP_EXAMPLES" << 'EOF'
"""
    
    # Добавляем примеры в скрипт
    for i, example in enumerate(examples, 1):
        training_script += f'echo "Пример {i}: {example["text"]} ({example["description"]})"\n'
    
    training_script += f"""
# Создаем эталонный голос
edge-tts --create-voice "{voice_name}" --training-data "$TEMP_EXAMPLES" --voice-output "{ethalon_model}"

echo "✅ Эталонный голос создан: {voice_name}"
echo "📁 Модель: {ethalon_model}"
echo "⚙️ Конфигурация: {ethalon_config}"
echo ""
echo "🔄 Для использования в TBox:"
echo "python3 tbox_tts_enhanced.py speech ваш_файл.md {voice_name}"
echo ""
echo "📋 Примеры произношения ({language}):"
"""
    
    # Добавляем примеры в скрипт
    for i, example in enumerate(examples, 1):
        training_script += f' {i}. {example["text"]} - {example["description"]}\n'
    
    training_script += """
EOF

# Запускаем создание голоса
bash "$TEMP_EXAMPLES"
"""
    
    # Сохраняем скрипт
    script_path = os.path.join(output_dir, f"create_{voice_name}.sh")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(training_script)
    
    print(f"✅ Скрипт создан: {script_path}")
    
    # 5. Автоматически запускаем создание голоса
    try:
        result = subprocess.run(
            ['bash', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ Эталонный голос '{voice_name}' успешно создан!")
            print(f"📁 Модель: {ethalon_model}")
            print(f"⚙️ Конфигурация: {ethalon_config}")
            
            # Проверяем что файлы создались
            if os.path.exists(ethalon_model) and os.path.exists(ethalon_config):
                print("🎉 Готово к использованию!")
            else:
                print("⚠️ Файлы не найдены после создания")
        else:
            print(f"❌ Ошибка создания голоса: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰️ Превышено время создания голоса (5 минут)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    """Главная функция"""
    import argparse
    
    # Загружаем конфигурацию
    import tbox_utils as utils
    conf = utils.load_abox_config()
    
    parser = argparse.ArgumentParser(description="Создание эталонного голоса из примеров")
    parser.add_argument("--name", default="ethalon", help="Название голоса (по умолчанию: ethalon)")
    parser.add_argument("--output", help="Директория для сохранения (из config.txt)")
    parser.add_argument("--language", default="hebrew", choices=["russian", "hebrew"], help="Язык голоса")
    
    args = parser.parse_args()
    
    # Используем пути из конфигурации
    output_dir = args.output
    if not output_dir and conf:
        output_dir = conf.get('ETHALON_DIR', '06_AUDIO/VOICE')
    
    print(f"🎤 TBox Ethalon Voice Creator")
    print(f"📁 Голос: {args.name}")
    print(f"🌐 Язык: {args.language}")
    print(f"📂 Выход: {output_dir}")
    
    create_ethalon_voice(args.name, output_dir, args.language)

if __name__ == "__main__":
    main()
