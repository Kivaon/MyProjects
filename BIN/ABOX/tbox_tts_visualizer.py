#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Визуализация и управление ударениями в тексте для TTS
"""

import re
from typing import Dict, List, Tuple
from tbox_tts_preprocessor import preprocessor

class TTSVisualizer:
    """Класс для визуализации ударений и пауз в тексте"""
    
    def __init__(self):
        self.stress_char = '́'  # Ударение (U+0301)
        self.pause_chars = {
            '.': '⟨⟩',    # Длинная пауза
            '!': '⟨!⟩',    # Эмоциональная пауза
            '?': '⟨?⟩',    # Вопросительная пауза
            ',': '⟨,⟩',    # Короткая пауза
            ';': '⟨;⟩',    # Средняя пауза
            ':': '⟨:⟩',    # Пояснительная пауза
        }
        
        # Специальные символы которые НЕ читаются
        self.non_reading_chars = {
            '—': '⟨—⟩',    # Длинное тире
            '–': '⟨–⟩',    # Среднее тире
            '-': '⟨-⟩',    # Короткое тире
            '...': '⟨...⟩', # Многоточие
            '…': '⟨…⟩',    # Многоточие
        }
    
    def add_stress_marks_visual(self, text: str) -> str:
        """Добавляет визуальные ударения в текст"""
        words = text.split()
        result_words = []
        
        for word in words:
            # Очищаем слово от пунктуации
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Проверяем в словаре ударений
            if clean_word in preprocessor.stress_dict:
                stressed_word = preprocessor.stress_dict[clean_word]
                # Находим позицию ударения
                stress_pos = stressed_word.find(self.stress_char)
                
                if stress_pos != -1:
                    # Восстанавливаем пунктуацию
                    prefix = re.match(r'^[^\w]*', word).group()
                    suffix = re.search(r'[^\w]*$', word).group()
                    clean_base = re.sub(r'[^\w]', '', word)
                    
                    # Добавляем визуальное ударение
                    if stress_pos < len(clean_base):
                        visual_word = (prefix + 
                                      clean_base[:stress_pos+1] + 
                                      '↑' + 
                                      clean_base[stress_pos+1:] + 
                                      suffix)
                    else:
                        visual_word = word
                else:
                    visual_word = word
            else:
                visual_word = word
            
            result_words.append(visual_word)
        
        return ' '.join(result_words)
    
    def add_pause_visualization(self, text: str) -> str:
        """Добавляет визуализацию пауз"""
        result = text
        
        # Заменяем знаки препинания на визуальные
        for char, visual in self.pause_chars.items():
            result = result.replace(char, f' {visual} ')
        
        # Обрабатываем специальные символы
        for char, visual in self.non_reading_chars.items():
            result = result.replace(char, f' {visual} ')
        
        # Убираем лишние пробелы
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def visualize_full_text(self, text: str) -> str:
        """Полная визуализация текста с ударениями и паузами"""
        # 1. Добавляем ударения
        text = self.add_stress_marks_visual(text)
        
        # 2. Добавляем паузы
        text = self.add_pause_visualization(text)
        
        return text
    
    def show_stress_dictionary(self, words: List[str] = None) -> None:
        """Показывает словарь ударений"""
        if words:
            # Показываем только указанные слова
            for word in words:
                clean_word = word.lower()
                if clean_word in preprocessor.stress_dict:
                    print(f"{word} → {preprocessor.stress_dict[clean_word]}")
                else:
                    print(f"{word} → (нет в словаре)")
        else:
            # Показываем весь словарь
            print("📚 Словарь ударений:")
            print("-" * 40)
            for word, stressed in sorted(preprocessor.stress_dict.items()):
                print(f"{word:15} → {stressed}")
    
    def add_word_to_dictionary(self, word: str, stressed_word: str) -> None:
        """Добавляет слово в словарь ударений"""
        clean_word = word.lower()
        preprocessor.stress_dict[clean_word] = stressed_word
        print(f"✅ Добавлено: {word} → {stressed_word}")
    
    def find_common_errors(self, text: str) -> List[Tuple[str, str]]:
        """Находит частые ошибки в тексте"""
        errors = []
        
        # Проверяем слова без ударений
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            if word in preprocessor.stress_dict:
                errors.append((word, preprocessor.stress_dict[word]))
        
        # Проверяем специальные символы
        for char, visual in self.non_reading_chars.items():
            if char in text:
                errors.append((char, f"не читать → {visual}"))
        
        return errors
    
    def generate_training_text(self) -> str:
        """Генерирует текст для тренировки эталонного голоса"""
        training_words = []
        
        # Берем слова из словаря ударений
        for word, stressed in list(preprocessor.stress_dict.items())[:50]:
            training_words.append(word)
        
        # Создаем предложения
        sentences = [
            "Менеджер позвонит и скажет, что каталог готов.",
            "Свекла и торты на столе.",
            "Бухгалтер проверит документы и кассу.",
            "Компас показывает на север.",
            "Красивее всего смотрится статуя в музее.",
        ]
        
        # Добавляем слова из словаря
        for i in range(0, len(training_words), 5):
            chunk = training_words[i:i+5]
            sentences.append(". ".join(chunk) + ".")
        
        return "\n\n".join(sentences)

def main():
    """Демонстрация работы визуализатора"""
    visualizer = TTSVisualizer()
    
    # Тестовый текст
    test_text = """
    Менеджер позвонит и скажет, что каталог готов. 
    Свекла и торты — на столе. 
    Красивее всего смотрится статуя в музее... 
    Что-ли он придет?
    """
    
    print("🎤 TTS Визуализатор")
    print("=" * 50)
    
    print("\n📝 Оригинальный текст:")
    print(test_text.strip())
    
    print("\n🎯 Визуализация с ударениями и паузами:")
    visualized = visualizer.visualize_full_text(test_text)
    print(visualized)
    
    print("\n🔍 Найденные ошибки:")
    errors = visualizer.find_common_errors(test_text)
    for error, correction in errors:
        print(f"  {error} → {correction}")
    
    print("\n📚 Пример словаря (первые 10 слов):")
    sample_words = ['менеджер', 'каталог', 'свекла', 'торты', 'красивее']
    visualizer.show_stress_dictionary(sample_words)
    
    print("\n🎓 Текст для тренировки:")
    training = visualizer.generate_training_text()
    print(training[:300] + "...")

if __name__ == "__main__":
    main()
