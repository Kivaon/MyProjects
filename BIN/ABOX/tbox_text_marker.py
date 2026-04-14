#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой маркер текста - подчеркивает проблемные места
"""

import os
import re
from typing import Dict

class TextMarker:
    def __init__(self):
        # Словарь ударений
        self.stress_dict = {
            'звонит': 'звОнит', 'стоит': 'стОит', 'торты': 'тОрты', 
            'свекла': 'свёкла', 'каталог': 'каталОг',
        }
        
        # Неоднозначные слова
        self.ambiguous = {
            'стоит': ['стОит', 'стоИт'],
            'стали': ['стАли', 'сталИ'],
        }
        
        # Иностранные термины
        self.foreign = {
            'ai': 'ай', 'AI': 'ай',
            'api': 'апи', 'API': 'апи',
            'frontend': 'фронтенд', 'Frontend': 'фронтенд',
            'backend': 'бэкенд', 'Backend': 'бэкенд',
            'database': 'база данных', 'Database': 'база данных',
            'machine': 'машин', 'Machine': 'машин',
            'learning': 'лёрнинг', 'Learning': 'лёрнинг',
            'endpoint': 'эндпоинт', 'Endpoint': 'эндпоинт',
        }
    
    def mark_text(self, text: str) -> str:
        """Помечает текст подчеркиванием только неоднозначных слов"""
        words = text.split()
        result = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Проверяем неоднозначные слова (главное!)
            if clean_word in self.ambiguous:
                variants = ', '.join(self.ambiguous[clean_word])
                result.append(f"_{word}_({variants})_")
            
            # Проверяем ударения (только если есть в словаре)
            elif clean_word in self.stress_dict:
                stressed = self.stress_dict[clean_word]
                # Находим большую букву (ударение)
                for i, char in enumerate(stressed):
                    if char.isupper() and char.isalpha():
                        # Помечаем подчеркиванием
                        marked = stressed[:i] + '_' + stressed[i] + '_' + stressed[i+1:]
                        result.append(marked)
                        break
                else:
                    result.append(word)
            
            # Проверяем иностранные термины
            elif clean_word in self.foreign:
                translation = self.foreign[clean_word]
                result.append(f"_{word}_({translation})_")
            
            # Все остальные слова - оставляем как есть (без пометок!)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def process_file(self, file_path: str) -> str:
        """Обрабатывает файл"""
        try:
            if file_path.endswith('.docx'):
                from docx import Document
                doc = Document(file_path)
                text = '\n'.join([p.text for p in doc.paragraphs])
            elif file_path.endswith('.rtf'):
                from striprtf.striprtf import rtf_to_text
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = rtf_to_text(f.read())
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return self.mark_text(text)
        except Exception as e:
            return f"Ошибка: {e}"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Маркер текста")
    parser.add_argument("file", nargs='?', help="Файл для обработки")
    parser.add_argument("--dir", default="/Users/kivaonmac/Documents/AI_Lab/06_AUDIO/IN", help="Директория")
    
    args = parser.parse_args()
    
    marker = TextMarker()
    
    # Определяем файл
    if args.file:
        file_path = args.file
    else:
        # Последний файл в директории
        if os.path.exists(args.dir):
            files = []
            for f in os.listdir(args.dir):
                if f.endswith(('.txt', '.rtf', '.docx')):
                    fp = os.path.join(args.dir, f)
                    files.append((os.path.getmtime(fp), fp, f))
            
            if files:
                files.sort(reverse=True)
                file_path = files[0][1]
                print(f"Файл: {files[0][2]}")
            else:
                print("Файлы не найдены")
                return
        else:
            print("Директория не найдена")
            return
    
    # Обрабатываем
    marked_text = marker.process_file(file_path)
    print("Результат:")
    print(marked_text)
    
    # Сохраняем переработанный файл с вопросами
    if file_path.endswith('.docx'):
        processed_file = file_path.replace('.docx', '_marked.txt')
    elif file_path.endswith('.rtf'):
        processed_file = file_path.replace('.rtf', '_marked.txt')
    else:
        processed_file = file_path.replace('.', '_marked.')
    
    with open(processed_file, 'w', encoding='utf-8') as f:
        f.write(marked_text)
    
    print(f"Сохранено: {processed_file}")

if __name__ == "__main__":
    main()
