"""
Минимальный умный алгоритм чанкования
"""

def minimal_smart_chunking(text, max_chars=10000, buffer_size=150):
    """
    Минимальный алгоритм:
    1. Берем большой чанк max_chars
    2. Берем граничный чанк-буфер buffer_size
    3. Ищем по порядку: .!? → ,:;- → пробел
    4. Режем по найденной позиции
    """
    chunks = []
    pos = 0
    
    while pos < len(text):
        # Шаг 1: Берем большой чанк max_chars
        chunk_end = min(pos + max_chars, len(text))
        
        # Если не последний чанк, ищем умную границу
        if chunk_end < len(text):
            # Шаг 2: Берем граничный чанк-буфер
            boundary = find_boundary_minimal(text, pos, chunk_end, buffer_size, max_chars)
            if boundary:
                chunk_end = boundary
        
        # Извлекаем чанк
        chunk_text = text[pos:chunk_end]
        
        if chunk_text.strip():
            chunks.append(chunk_text)
        
        # Двигаемся к следующей границе
        pos = chunk_end
    
    return chunks

def find_boundary_minimal(text, start_pos, end_pos, buffer_size, max_chars):
    """
    Ищем границу по минимальной логике:
    а) .!?
    б) ,:;-
    в) пробел
    """
    # Шаг 2: Берем граничный чанк-буфер (последние buffer_size символов)
    buffer_start = max(start_pos, end_pos - buffer_size)
    buffer_end = end_pos
    buffer_text = text[buffer_start:buffer_end]
    
    # а) Ищем первую точку/воскл/вопрос (.!?)
    for i, char in enumerate(buffer_text):
        actual_pos = buffer_start + i
        if char in '.!?':
            # Проверяем минимальный размер чанка
            chunk_size = (actual_pos + 1) - start_pos
            min_size = max_chars * 0.3
            if chunk_size >= min_size:
                return actual_pos + 1  # Режем после знака
    
    # б) Если нет .!? - ищем запятую/тире/двоеточие (,:;-)
    for i, char in enumerate(buffer_text):
        actual_pos = buffer_start + i
        if char in ',;:—-':
            # Проверяем минимальный размер чанка
            chunk_size = actual_pos - start_pos
            min_size = max_chars * 0.3
            if chunk_size >= min_size:
                return actual_pos
    
    # в) Если нет ,:;- - ищем пробел
    for i, char in enumerate(buffer_text):
        actual_pos = buffer_start + i
        if char == ' ':
            # Проверяем минимальный размер чанка
            chunk_size = actual_pos - start_pos
            min_size = max_chars * 0.3
            if chunk_size >= min_size:
                return actual_pos
    
    # Если ничего не найдено - жесткий разрез
    return end_pos

def test_minimal_smart_chunking():
    """
    Тестируем минимальный алгоритм
    """
    print("🧪 ТЕСТ МИНИМАЛЬНОГО УМНОГО АЛГОРИТМА")
    print("🔍 Логика: .!? → ,:;- → пробел")
    print("="*60)
    
    # Тестовый текст
    text = "Это первое предложение. Это второе предложение! Это третье предложение? Это четвертое предложение, с запятой. Это пятое предложение: с двоеточием. Это шестое предложение-с тире. Это седьмое предложение. Это восьмое предложение. Это девятое предложение. Это десятое предложение. Это одиннадцатое предложение. Это двенадцатое предложение."
    
    print(f"📝 Текст: {text}")
    print(f"📏 max_chars: 60")
    print(f"📏 buffer_size: 20")
    
    chunks = minimal_smart_chunking(text, 60, 20)
    
    print(f"\n📊 Результат: {len(chunks)} чанков")
    for i, chunk in enumerate(chunks, 1):
        print(f"   Чанк {i}: '{chunk}' ({len(chunk)} символов)")
    
    # Проверка полноты
    reconstructed = ''.join(chunks)
    print(f"\n✅ Проверка: {'✅' if reconstructed == text else '❌'}")

if __name__ == "__main__":
    test_minimal_smart_chunking()
