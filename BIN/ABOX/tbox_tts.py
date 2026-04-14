import os, sys, re, asyncio, json
from datetime import datetime
import edge_tts
import tbox_utils as utils
from docx import Document

# --- ПАСПОРТ ---
VERSION = "v1.0.edge-tts"
DATE    = "2026-02-01"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION, "date": DATE}

# --- НАСТРОЙКИ ГОЛОСОВ ---
VOICES = {
    'female': 'ru-RU-SvetlanaNeural',
    'male': 'ru-RU-DmitryNeural',
    'female_warm': 'ru-RU-DariyaNeural'
}

# --- КАСТОМНЫЕ ГОЛОСА ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_VOICES_DIR = os.path.join(SCRIPT_DIR, 'voice_models')
CUSTOM_VOICE_CONFIG = os.path.join(CUSTOM_VOICES_DIR, 'metadata', 'voices_index.json')

def load_custom_voices():
    """Загружает реестр кастомных голосов"""
    if not os.path.exists(CUSTOM_VOICE_CONFIG):
        return {}
    
    try:
        with open(CUSTOM_VOICE_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def get_available_voices():
    """Возвращает все доступные голоса (стандартные + кастомные)"""
    voices = VOICES.copy()
    custom_voices = load_custom_voices()
    
    # Добавляем кастомные голоса
    for voice_id, voice_data in custom_voices.items():
        if voice_data.get('model_path') and os.path.exists(voice_data['model_path']):
            voices[voice_id] = f"CUSTOM:{voice_id}"
    
    return voices

async def text_to_speech(text, output_file, voice='ru-RU-SvetlanaNeural', conf=None):
    """Преобразование текста в речь с помощью Edge TTS"""
    try:
        if conf:
            utils.tbox_log(f"Начало озвучки: {os.path.basename(output_file)}", META, "START", conf)
            utils.tbox_log(f"Голос: {voice}", META, "INFO", conf)
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
        if conf:
            utils.tbox_log(f"Озвучка завершена: {os.path.basename(output_file)}", META, "DONE", conf)
        
        return True
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка озвучки: {e}", META, "ERROR", conf)
        return False

def split_text_for_tts(text, max_chars=4000):
    """Разбивает текст на чанки для TTS (ограничение Edge TTS)"""
    chunks = []
    current_chunk = ""
    
    # Разбиваем по предложениям
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

async def process_file_with_tts(input_path, output_dir, voice='ru-RU-SvetlanaNeural', conf=None):
    """Обрабатывает файл и создает озвучку"""
    try:
        # Читаем входной файл
        content = ""
        
        if input_path.endswith('.docx'):
            # Читаем Word документ
            doc = Document(input_path)
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
        else:
            # Читаем текстовый файл
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Извлекаем чистый текст (убираем markdown)
        clean_text = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)  # заголовки
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)  # жирный текст
        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)  # курсив
        clean_text = re.sub(r'<[^>]+>', '', clean_text)  # HTML теги
        clean_text = re.sub(r'\n\n+', '. ', clean_text)  # множественные переносы
        clean_text = clean_text.strip()
        
        if not clean_text:
            if conf:
                utils.tbox_log("Файл пуст или не содержит текста", META, "WARNING", conf)
            return False
        
        # Разбиваем на чанки
        chunks = split_text_for_tts(clean_text)
        if conf:
            utils.tbox_log(f"Текст разбит на {len(chunks)} частей", META, "INFO", conf)
        
        # Создаем выходной файл
        base_name = os.path.basename(input_path).replace('.txt', '').replace('.md', '').replace('.docx', '')
        output_file = os.path.join(output_dir, f"{base_name}_tts.mp3")
        
        # Если один чанк - сразу озвучиваем
        if len(chunks) == 1:
            return await text_to_speech(clean_text, output_file, voice, conf)
        
        # Если много чанков - озвучиваем по частям и склеиваем
        temp_files = []
        try:
            for i, chunk in enumerate(chunks):
                if conf:
                    utils.tbox_log(f"Озвучка части {i+1}/{len(chunks)}", META, "INFO", conf)
                
                temp_file = os.path.join(output_dir, f"temp_{i}_{base_name}.mp3")
                temp_files.append(temp_file)
                
                success = await text_to_speech(chunk, temp_file, voice, conf)
                if not success:
                    return False
                
                # Небольшая пауза между запросами
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
            
            # Склеиваем все файлы (простая реализация)
            if conf:
                utils.tbox_log("Склеивание аудиофайлов...", META, "INFO", conf)
            
            # Для простоты - пока возвращаем первый файл
            # TODO: реализовать склеивание MP3 файлов
            if temp_files:
                import shutil
                shutil.copy2(temp_files[0], output_file)
                
                # Удаляем временные файлы
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            return True
            
        except Exception as e:
            # Очистка временных файлов при ошибке
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise e
            
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка обработки файла: {e}", META, "ERROR", conf)
        return False

def find_target_file(user_arg, conf):
    """Поиск целевого файла"""
    TXT_DIR = conf.get('TXT_RAW', '02_TXT/TXT')
    MD_DIR = conf.get('MD_DIR', '02_TXT/MD')
    DOC_DIR = conf.get('DOC_DIR', '03_DOC')
    
    if user_arg:
        if os.path.exists(user_arg):
            return os.path.abspath(user_arg)
        else:
            # Поиск по имени в директориях
            for directory in [TXT_DIR, MD_DIR, DOC_DIR]:
                if os.path.exists(directory):
                    files = [f for f in os.listdir(directory) 
                            if user_arg.lower() in f.lower() 
                            and f.endswith(('.txt', '.md', '.docx'))]
                    if files:
                        return os.path.join(directory, max(files, key=os.path.getmtime))
    else:
        # Автопилот: самый свежий файл
        for directory in [DOC_DIR, MD_DIR, TXT_DIR]:
            if os.path.exists(directory):
                files = [os.path.join(directory, f) for f in os.listdir(directory) 
                        if f.endswith(('.txt', '.md', '.docx'))]
                if files:
                    return max(files, key=os.path.getmtime)
    
    return None

async def main():
    """Главная функция"""
    # 1. Загрузка конфигурации
    user_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Проверяем флаги
    voice = 'ru-RU-SvetlanaNeural'  # по умолчанию женский голос
    if user_arg and user_arg.startswith('--'):
        if user_arg == '--male':
            voice = VOICES['male']
            user_arg = sys.argv[2] if len(sys.argv) > 2 else None
        elif user_arg == '--female':
            voice = VOICES['female']
            user_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    CONF = utils.load_abox_config()
    if not CONF:
        print("Ошибка: aconfig.txt не найден.")
        return
    
    # 2. Поиск файла
    target_path = find_target_file(user_arg, CONF)
    if not target_path:
        utils.tbox_log("Текстовый файл не найден.", META, "ERROR", CONF)
        return
    
    # 3. Подготовка выходной директории
    AUDIO_DIR = CONF.get('AUDIO_DIR', '06_AUDIO')
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # 4. Обработка
    utils.tbox_log(f"Старт TTS: {os.path.basename(target_path)}", META, "START", CONF)
    
    success = await process_file_with_tts(target_path, AUDIO_DIR, voice, CONF)
    
    if success:
        base_name = os.path.basename(target_path).replace('.txt', '').replace('.md', '').replace('.docx', '')
        output_file = os.path.join(AUDIO_DIR, f"{base_name}_tts.mp3")
        utils.tbox_log(f"Готово: {os.path.basename(output_file)}", META, "DONE", CONF)
    else:
        utils.tbox_log("Озвучка не удалась", META, "ERROR", CONF)

if __name__ == "__main__":
    asyncio.run(main())
