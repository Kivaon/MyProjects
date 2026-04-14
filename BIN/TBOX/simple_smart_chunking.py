"""
Простой умный алгоритм чанкования по вашей логике
"""

def simple_smart_chunking(text, max_chars=10000, buffer_size=150):
    """
    Простой умный алгоритм:
    1. Берем большой чанк max_chars
    2. Берем граничный чанк-буфер buffer_size
    3. Находим в буфере по приоритету
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
            boundary = find_boundary_in_buffer(text, pos, chunk_end, buffer_size, max_chars)
            if boundary:
                chunk_end = boundary
        
        # Извлекаем чанк
        chunk_text = text[pos:chunk_end]
        
        if chunk_text.strip():
            chunks.append(chunk_text)
        
        # Двигаемся к следующей границе
        pos = chunk_end
    
    return chunks

def find_boundary_in_buffer(text, start_pos, end_pos, buffer_size, max_chars):
    """
    Находим границу в граничном чанке-буфере
    """
    # Шаг 2: Берем граничный чанк-буфер (последние 150 символов)
    buffer_start = max(start_pos, end_pos - buffer_size)
    buffer_end = end_pos
    buffer_text = text[buffer_start:buffer_end]
    
    # Шаг 3: Находим в буфере по приоритету в одном цикле
    
    # Ищем все знаки препинания в буфере
    candidates = []
    
    for i, char in enumerate(buffer_text):
        actual_pos = buffer_start + i
        
        # 1. Точка/воскл/вопрос
        if char in '.!?':
            candidates.append((actual_pos, 'sentence', 1))
        # 2. Другие знаки
        elif char in ',;:—-':
            candidates.append((actual_pos, 'punctuation', 2))
        # 3. Пробел
        elif char == ' ':
            candidates.append((actual_pos, 'word', 3))
    
    if not candidates:
        return end_pos
    
    # Сортируем по приоритету (чем меньше, тем выше приоритет)
    candidates.sort(key=lambda x: x[2])
    
    # Шаг 4: Режем по первому кандидату
    best_candidate = candidates[0]
    boundary_pos = best_candidate[0]
    boundary_type = best_candidate[1]
    
    # Для предложений режем после знака
    if boundary_type == 'sentence':
        boundary_pos += 1
    
    # Проверяем минимальный размер чанка
    chunk_size = boundary_pos - start_pos
    min_size = max_chars * 0.3
    
    if chunk_size < min_size:
        return end_pos
    
    return boundary_pos

def test_simple_smart_chunking():
    """
    Тестируем простой умный алгоритм
    """
    print("🧪 ТЕСТ ПРОСТОГО УМНОГО АЛГОРИТМА")
    print("🔍 Ваша логика: большой чанк + буфер + приоритеты")
    print("="*60)
    
    # Тестовый текст
    text = "Это первое предложение. Это второе предложение! Это третье предложение? Это четвертое предложение, с запятой. Это пятое предложение: с двоеточием. Это шестое предложение-с тире. Это седьмое предложение. Это восьмое предложение. Это девятое предложение. Это десятое предложение. Это одиннадцатое предложение. Это двенадцатое предложение."
    
    print(f"📝 Текст: {text}")
    print(f"📏 max_chars: 60")
    print(f"📏 buffer_size: 20")
    
    chunks = simple_smart_chunking(text, 60, 20)
    
    print(f"\n📊 Результат: {len(chunks)} чанков")
    for i, chunk in enumerate(chunks, 1):
        print(f"   Чанк {i}: '{chunk}' ({len(chunk)} символов)")
    
    # Проверка полноты
    reconstructed = ''.join(chunks)
    print(f"\n✅ Проверка: {'✅' if reconstructed == text else '❌'}")

if __name__ == "__main__":
    test_simple_smart_chunking()
