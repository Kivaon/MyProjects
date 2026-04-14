#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ИИ для расстановки знаков препинания в тексте
"""

import re
import asyncio
from typing import Dict, List

class PunctuationAI:
    """ИИ для расстановки знаков препинания"""
    
    def __init__(self):
        # Правила расстановки знаков препинания
        self.punctuation_rules = {
            # Конец предложений
            'sentence_endings': {
                'patterns': [
                    r'\b(?:и|а|но|да|но|или|либо|тоже|также|еще|пока|пока что|когда|где|куда|откуда|почему|зачем|как|какой|какая|какое|какие|чей|чья|чьё|чьи|сколько|кто|что|который|которая|которое|которые)\s+[а-яё]+\s*$',
                    r'\b(?:менеджер|директор|бухгалтер|инженер|разработчик|аналитик|дизайнер|программист|специалист|эксперт|консультант)\s+[а-яё]+\s*$',
                    r'\b(?:нужно|надо|должен|должна|должно|должны|следует|требуется|необходимо|важно|срочно|немедленно)\s+[а-яё]+\s*$',
                ],
                'punctuation': '.',
            },
            
            # Запятые в сложных предложениях
            'commas_complex': {
                'patterns': [
                    r'\b(?:и|а|но|да|но|или|либо|тоже|также|еще|пока|пока что)\s+',
                    r'\b(?:когда|где|куда|откуда|почему|зачем|как|какой|какая|какое|какие|чей|чья|чьё|чьи|сколько|кто|что|который|которая|которое|которые)\s+',
                    r'\b(?:потому что|так как|поскольку|из-за того что|вследствие того что|благодаря тому что|несмотря на то что)\s+',
                ],
                'punctuation': ',',
            },
            
            # Запятые при перечислениях
            'commas_list': {
                'patterns': [
                    r'([а-яё]+),\s*([а-яё]+),\s*([а-яё]+)',
                    r'([а-яё]+)\s+и\s+([а-яё]+)\s+и\s+([а-яё]+)',
                ],
                'punctuation': ',',
            },
            
            # Вопросительные знаки
            'question_marks': {
                'patterns': [
                    r'\b(?:кто|что|где|когда|куда|откуда|почему|зачем|как|какой|какая|какое|какие|чей|чья|чьё|чьи|сколько|когда|как|ли|неужели|правда|верно)\s*[а-яё]*\s*$',
                ],
                'punctuation': '?',
            },
            
            # Восклицательные знаки
            'exclamation_marks': {
                'patterns': [
                    r'\b(?:срочно|немедленно|быстро|немедленно|важно|внимание|опасно|стоп|прекрати|хватит)\s*[а-яё]*\s*$',
                    r'\b(?:отлично|прекрасно|замечательно|великолепно|превосходно|удивительно|потрясающе)\s*[а-яё]*\s*$',
                ],
                'punctuation': '!',
            },
            
            # Двоеточия
            'colons': {
                'patterns': [
                    r'\b(?:например|таким образом|вот|следует|итак|итак)\s*$',
                    r'\b(?:это|это значит|это означает|это говорит)\s*$',
                ],
                'punctuation': ':',
            },
            
            # Точки с запятой
            'semicolons': {
                'patterns': [
                    r'([а-яё]+\s+[а-яё]+\s+[а-яё]+),\s*([а-яё]+\s+[а-яё]+\s+[а-яё]+)',
                ],
                'punctuation': ';',
            },
        }
        
        # Слова-индикаторы для расстановки знаков
        self.indicator_words = {
            'question': ['кто', 'что', 'где', 'когда', 'куда', 'откуда', 'почему', 'зачем', 'как', 'какой', 'какая', 'какое', 'какие', 'чей', 'чья', 'чьё', 'чьи', 'сколько', 'ли', 'неужели', 'правда', 'верно'],
            'exclamation': ['срочно', 'немедленно', 'быстро', 'важно', 'внимание', 'опасно', 'стоп', 'прекрати', 'хватит', 'отлично', 'прекрасно', 'замечательно', 'великолепно', 'превосходно', 'удивительно', 'потрясающе'],
            'colon': ['например', 'таким образом', 'вот', 'следует', 'итак', 'это', 'это значит', 'это означает', 'это говорит'],
            'comma': ['и', 'а', 'но', 'да', 'или', 'либо', 'тоже', 'также', 'еще', 'пока', 'когда', 'где', 'куда', 'откуда', 'почему', 'зачем', 'как', 'который', 'которая', 'которое', 'которые', 'потому что', 'так как', 'поскольку', 'из-за того что'],
        }
    
    def add_punctuation(self, text: str) -> str:
        """Добавляет знаки препинания в текст"""
        
        # Разбиваем текст на предложения
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        punctuated_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Очищаем от существующих знаков препинания
            clean_sentence = re.sub(r'[.!?,:;]', '', sentence.strip())
            
            # Определяем тип предложения и добавляем соответствующий знак
            punctuated_sentence = self._process_sentence(clean_sentence)
            punctuated_sentences.append(punctuated_sentence)
        
        return ' '.join(punctuated_sentences)
    
    def _process_sentence(self, sentence: str) -> str:
        """Обрабатывает отдельное предложение"""
        
        # Проверяем на вопрос
        if self._is_question(sentence):
            return sentence + '?'
        
        # Проверяем на восклицание
        elif self._is_exclamation(sentence):
            return sentence + '!'
        
        # Проверяем на перечисление
        elif self._is_list(sentence):
            return self._add_list_commas(sentence) + '.'
        
        # Проверяем на сложное предложение
        elif self._is_complex(sentence):
            return self._add_complex_commas(sentence) + '.'
        
        # Обычное предложение
        else:
            return sentence + '.'
    
    def _is_question(self, sentence: str) -> bool:
        """Проверяет, является ли предложение вопросительным"""
        words = sentence.lower().split()
        
        # Проверяем наличие вопросительных слов
        for word in words:
            if word in self.indicator_words['question']:
                return True
        
        # Проверяем по паттернам
        for pattern in self.punctuation_rules['question_marks']['patterns']:
            if re.search(pattern, sentence.lower()):
                return True
        
        return False
    
    def _is_exclamation(self, sentence: str) -> bool:
        """Проверяет, является ли предложение восклицательным"""
        words = sentence.lower().split()
        
        # Проверяем наличие восклицательных слов
        for word in words:
            if word in self.indicator_words['exclamation']:
                return True
        
        # Проверяем по паттернам
        for pattern in self.punctuation_rules['exclamation_marks']['patterns']:
            if re.search(pattern, sentence.lower()):
                return True
        
        return False
    
    def _is_list(self, sentence: str) -> bool:
        """Проверяет, является ли предложение перечислением"""
        # Ищем перечисления через запятые
        if re.search(r'[а-яё]+,\s*[а-яё]+,\s*[а-яё]+', sentence):
            return True
        
        # Ищем перечисления через "и"
        if re.search(r'[а-яё]+\s+и\s+[а-яё]+\s+и\s+[а-яё]+', sentence):
            return True
        
        return False
    
    def _is_complex(self, sentence: str) -> bool:
        """Проверяет, является ли предложение сложным"""
        words = sentence.lower().split()
        
        # Проверяем наличие союзов
        for word in words:
            if word in self.indicator_words['comma']:
                return True
        
        return False
    
    def _add_list_commas(self, sentence: str) -> str:
        """Добавляет запятые в перечислениях"""
        # Заменяем "и" на запятые, кроме последней
        words = sentence.split()
        
        # Находим индексы "и"
        and_indices = [i for i, word in enumerate(words) if word.lower() == 'и']
        
        # Если есть несколько "и", заменяем на запятые
        if len(and_indices) > 1:
            for i in and_indices[:-1]:
                words[i] = ','
        
        return ' '.join(words)
    
    def _add_complex_commas(self, sentence: str) -> str:
        """Добавляет запятые в сложных предложениях"""
        words = sentence.split()
        
        # Ищем союзы и добавляем запятые
        for i, word in enumerate(words):
            if word.lower() in self.indicator_words['comma']:
                # Добавляем запятую перед союзом (если не в начале)
                if i > 0:
                    words[i-1] += ','
                    break
        
        return ' '.join(words)
    
    def smart_punctuation(self, text: str) -> str:
        """Умная расстановка знаков препинания с контекстным анализом"""
        
        # Разбиваем на абзацы
        paragraphs = text.split('\n')
        
        result_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                result_paragraphs.append('')
                continue
            
            # Разбиваем на предложения
            sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
            
            processed_sentences = []
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                
                # Анализируем контекст
                processed = self._analyze_context(sentence.strip())
                processed_sentences.append(processed)
            
            result_paragraphs.append(' '.join(processed_sentences))
        
        return '\n'.join(result_paragraphs)
    
    def _analyze_context(self, sentence: str) -> str:
        """Анализирует контекст предложения"""
        
        # Проверяем на начало диалога
        if sentence.startswith(('-', '"', '«')):
            return self._process_dialogue(sentence)
        
        # Проверяем на перечисление
        elif re.search(r'\d+\.', sentence):
            return self._process_numbered_list(sentence)
        
        # Обычная обработка
        else:
            return self._process_sentence(sentence)
    
    def _process_dialogue(self, sentence: str) -> str:
        """Обрабатывает диалог"""
        # Если начинается с тире, это реплика
        if sentence.startswith('-'):
            content = sentence[1:].strip()
            return f"- {self._process_sentence(content)}"
        
        # Если в кавычках, это прямая речь
        elif '"' in sentence or '«' in sentence:
            # Находим кавычки
            if '"' in sentence:
                parts = sentence.split('"')
                if len(parts) >= 3:
                    # Прямая речь в кавычках
                    speech = parts[1]
                    rest = '"'.join(parts[2:])
                    return f'"{self._process_sentence(speech)}"{rest}'
            
            elif '«' in sentence and '»' in sentence:
                parts = sentence.split('«')
                if len(parts) >= 2:
                    inner = parts[1].split('»')[0]
                    rest = parts[1].split('»')[1] if '»' in parts[1] else ''
                    return f'«{self._process_sentence(inner)}»{rest}'
        
        return self._process_sentence(sentence)
    
    def _process_numbered_list(self, sentence: str) -> str:
        """Обрабатывает нумерованные списки"""
        # Если начинается с цифры, это пункт списка
        match = re.match(r'(\d+)\.\s*(.*)', sentence)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"{number}. {self._process_sentence(content)}"
        
        return self._process_sentence(sentence)

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ИИ для расстановки знаков препинания")
    parser.add_argument("file", nargs='?', help="Файл для обработки")
    parser.add_argument("--text", help="Текст для обработки")
    parser.add_argument("--output", help="Выходной файл")
    
    args = parser.parse_args()
    
    ai = PunctuationAI()
    
    if args.text:
        # Обрабатываем текст из аргумента
        result = ai.smart_punctuation(args.text)
        print("Оригинал:")
        print(args.text)
        print("\nС знаками препинания:")
        print(result)
    
    elif args.file:
        # Обрабатываем файл
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            result = ai.smart_punctuation(text)
            
            # Выводим результат
            print("Оригинал:")
            print(text)
            print("\nС знаками препинания:")
            print(result)
            
            # Сохраняем в файл
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"\nСохранено: {args.output}")
            else:
                # Автоматически создаем выходной файл
                output_file = args.file.replace('.', '_punctuated.')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"\nСохранено: {output_file}")
        
        except Exception as e:
            print(f"Ошибка: {e}")
    
    else:
        print("🤖 ИИ ДЛЯ РАССТАНОВКИ ЗНАКОВ ПРЕПИНАНИЯ")
        print("=" * 40)
        print("Использование:")
        print("  python3 tbox_punctuation_ai.py --text 'текст без знаков'")
        print("  python3 tbox_punctuation_ai.py file.txt")
        print("  python3 tbox_punctuation_ai.py file.txt --output result.txt")
        print("\nПример:")
        print('  python3 tbox_punctuation_ai.py --text "менеджер звонит клиенту когда он придет"')

if __name__ == "__main__":
    main()
