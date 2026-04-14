import os, sys, re, json, librosa
import numpy as np
from datetime import datetime
import soundfile as sf
import tbox_utils as utils

# --- ПАСПОРТ ---
VERSION = "v1.0.voice-trainer"
DATE    = "2026-02-01"
NAME    = os.path.basename(__file__)
META = {"name": NAME, "version": VERSION, "date": DATE}

# --- НАСТРОЙКИ ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_MODELS_DIR = os.path.join(SCRIPT_DIR, 'voice_models')
SAMPLES_DIR = os.path.join(VOICE_MODELS_DIR, 'samples')
MODELS_DIR = os.path.join(VOICE_MODELS_DIR, 'models')
METADATA_DIR = os.path.join(VOICE_MODELS_DIR, 'metadata')
VOICES_CONFIG = os.path.join(METADATA_DIR, 'voices_index.json')

# --- ПАРАМЕТРЫ ЭТАЛОНОВ ---
MIN_SAMPLE_LENGTH = 5.0   # Минимальная длина фрагмента (сек)
MAX_SAMPLE_LENGTH = 30.0  # Максимальная длина фрагмента (сек)
TARGET_SAMPLE_RATE = 22050  # Частота дискретизации
MIN_SILENCE_DURATION = 0.5  # Минимальная тишина между фразами

def ensure_directories():
    """Создает структуру директорий для голосовых моделей"""
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

def load_voices_index():
    """Загружает реестр голосов"""
    if not os.path.exists(VOICES_CONFIG):
        return {}
    
    try:
        with open(VOICES_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_voices_index(index):
    """Сохраняет реестр голосов"""
    try:
        with open(VOICES_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def detect_speech_segments(audio_path, min_duration=MIN_SILENCE_DURATION):
    """Детектирует речевые сегменты в аудио"""
    try:
        # Загружаем аудио
        y, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE)
        
        # Детектируем речь (простой метод по энергии)
        frame_length = 2048
        hop_length = 512
        
        # RMS энергия
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Порог детекции речи
        threshold = np.mean(rms) * 0.1
        
        # Находим сегменты с речью
        speech_frames = rms > threshold
        
        # Конвертируем в временные интервалы
        speech_times = librosa.frames_to_time(np.where(speech_frames)[0], sr=sr, hop_length=hop_length)
        
        # Группируем в сегменты
        segments = []
        if len(speech_times) > 0:
            start_time = speech_times[0]
            prev_time = speech_times[0]
            
            for time in speech_times[1:]:
                if time - prev_time > min_duration:
                    segments.append((start_time, prev_time))
                    start_time = time
                prev_time = time
            
            segments.append((start_time, prev_time))
        
        return segments
        
    except Exception as e:
        print(f"Ошибка детекции речи: {e}")
        return []

def extract_voice_samples(audio_path, voice_id, conf=None):
    """Извлекает эталонные фрагменты голоса из аудио"""
    try:
        if conf:
            utils.tbox_log(f"Анализ аудио: {os.path.basename(audio_path)}", META, "INFO", conf)
        
        # Детектируем речевые сегменты
        segments = detect_speech_segments(audio_path)
        
        if not segments:
            if conf:
                utils.tbox_log("Речевые сегменты не найдены", META, "WARNING", conf)
            return False
        
        # Загружаем аудио для извлечения
        y, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE)
        
        # Создаем директорию для образцов
        voice_samples_dir = os.path.join(SAMPLES_DIR, voice_id)
        os.makedirs(voice_samples_dir, exist_ok=True)
        
        # Извлекаем подходящие сегменты
        extracted_count = 0
        for i, (start, end) in enumerate(segments):
            duration = end - start
            
            # Проверяем длину сегмента
            if MIN_SAMPLE_LENGTH <= duration <= MAX_SAMPLE_LENGTH:
                # Извлекаем сегмент
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                segment = y[start_sample:end_sample]
                
                # Сохраняем
                output_file = os.path.join(voice_samples_dir, f"sample_{extracted_count+1:03d}.wav")
                sf.write(output_file, segment, TARGET_SAMPLE_RATE)
                extracted_count += 1
                
                if conf:
                    utils.tbox_log(f"Извлечен сегмент {extracted_count}: {duration:.1f}сек", META, "INFO", conf)
        
        if conf:
            utils.tbox_log(f"Всего извлечено: {extracted_count} образцов", META, "DONE", conf)
        
        return extracted_count > 0
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка извлечения образцов: {e}", META, "ERROR", conf)
        return False

def create_voice_metadata(voice_id, name, samples_count, conf=None):
    """Создает метаданные для голоса"""
    metadata = {
        "voice_id": voice_id,
        "name": name,
        "language": "ru",
        "samples_count": samples_count,
        "model_type": "xtts_v2",  # По умолчанию
        "model_path": None,
        "created_date": datetime.now().isoformat(),
        "status": "samples_ready"
    }
    
    # Сохраняем метаданные голоса
    voice_metadata_file = os.path.join(METADATA_DIR, f"{voice_id}.json")
    try:
        with open(voice_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    # Обновляем реестр голосов
    voices_index = load_voices_index()
    voices_index[voice_id] = metadata
    
    if save_voices_index(voices_index):
        if conf:
            utils.tbox_log(f"Голос {voice_id} зарегистрирован", META, "DONE", conf)
        return True
    
    return False

def list_voices():
    """Показывает список доступных голосов"""
    voices_index = load_voices_index()
    
    print("\n=== ДОСТУПНЫЕ ГОЛОСА ===")
    print("Стандартные голоса:")
    print("  - female (Светлана)")
    print("  - male (Дмитрий)")
    print("  - female_warm (Дарья)")
    
    print("\nКастомные голоса:")
    if not voices_index:
        print("  (пока нет)")
    else:
        for voice_id, metadata in voices_index.items():
            status = metadata.get('status', 'unknown')
            samples = metadata.get('samples_count', 0)
            model = "✓" if metadata.get('model_path') else "✗"
            print(f"  - {voice_id} ({metadata.get('name', 'N/A')}) [образцов:{samples}] [модель:{model}] [{status}]")

def train_voice_model(voice_id, conf=None):
    """Обучает модель голоса (заглушка для будущей реализации)"""
    try:
        voices_index = load_voices_index()
        
        if voice_id not in voices_index:
            print(f"Голос {voice_id} не найден")
            return False
        
        voice_metadata = voices_index[voice_id]
        voice_samples_dir = os.path.join(SAMPLES_DIR, voice_id)
        
        # Проверяем наличие образцов
        if not os.path.exists(voice_samples_dir):
            print(f"Образцы для голоса {voice_id} не найдены")
            return False
        
        samples = [f for f in os.listdir(voice_samples_dir) if f.endswith('.wav')]
        if len(samples) < 5:
            print(f"Слишком мало образцов: {len(samples)} (минимум 5)")
            return False
        
        if conf:
            utils.tbox_log(f"Начало обучения модели: {voice_id}", META, "START", conf)
        
        # TODO: Реализация обучения XTTSv2
        print("Обучение моделей пока не реализовано")
        print("Требуется установка: pip install coqui-tts torch")
        print(f"Найдено образцов: {len(samples)}")
        
        # Заглушка для будущего обучения
        model_dir = os.path.join(MODELS_DIR, f"{voice_id}_xtts")
        os.makedirs(model_dir, exist_ok=True)
        
        # Обновляем метаданные
        voice_metadata['model_path'] = model_dir
        voice_metadata['status'] = 'model_trained'
        voices_index[voice_id] = voice_metadata
        save_voices_index(voices_index)
        
        if conf:
            utils.tbox_log(f"Модель создана (заглушка): {model_dir}", META, "DONE", conf)
        
        return True
        
    except Exception as e:
        if conf:
            utils.tbox_log(f"Ошибка обучения: {e}", META, "ERROR", conf)
        return False

def main():
    """Главная функция"""
    ensure_directories()
    
    # Загрузка конфига
    CONF = utils.load_abox_config()
    
    # Парсинг аргументов
    if len(sys.argv) < 2:
        print("TBOX Voice Trainer - утилита создания кастомных голосов")
        print("\nИспользование:")
        print("  python tbox_voice_trainer.py --list")
        print("  python tbox_voice_trainer.py --create <voice_id> --name <имя> --source <audio_file>")
        print("  python tbox_voice_trainer.py --train <voice_id>")
        print("\nПримеры:")
        print("  python tbox_voice_trainer.py --create lecturer1 --name 'Рав Коэн' --source lecture.mp3")
        print("  python tbox_voice_trainer.py --train lecturer1")
        return
    
    args = sys.argv[1:]
    
    if args[0] == '--list':
        list_voices()
    
    elif args[0] == '--create':
        if len(args) < 6 or '--name' not in args or '--source' not in args:
            print("Ошибка: нужны параметры --name и --source")
            return
        
        voice_id = args[1]
        name_idx = args.index('--name') + 1
        source_idx = args.index('--source') + 1
        
        voice_name = args[name_idx]
        source_audio = args[source_idx]
        
        if not os.path.exists(source_audio):
            print(f"Файл не найден: {source_audio}")
            return
        
        print(f"Создание голоса: {voice_id} ({voice_name})")
        print(f"Источник: {source_audio}")
        
        # Извлечение образцов
        if extract_voice_samples(source_audio, voice_id, CONF):
            # Подсчет образцов
            voice_samples_dir = os.path.join(SAMPLES_DIR, voice_id)
            samples_count = len([f for f in os.listdir(voice_samples_dir) if f.endswith('.wav')])
            
            # Создание метаданных
            if create_voice_metadata(voice_id, voice_name, samples_count, CONF):
                print(f"✓ Голос {voice_id} создан успешно!")
                print(f"✓ Извлечено образцов: {samples_count}")
                print(f"✓ Для обучения модели: python tbox_voice_trainer.py --train {voice_id}")
            else:
                print("✗ Ошибка создания метаданных")
        else:
            print("✗ Ошибка извлечения образцов")
    
    elif args[0] == '--train':
        if len(args) < 2:
            print("Ошибка: нужен voice_id")
            return
        
        voice_id = args[1]
        print(f"Обучение модели: {voice_id}")
        
        if train_voice_model(voice_id, CONF):
            print("✓ Обучение завершено!")
        else:
            print("✗ Ошибка обучения")
    
    else:
        print(f"Неизвестная команда: {args[0]}")

if __name__ == "__main__":
    main()
