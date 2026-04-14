#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест установки OCR библиотек
"""

def test_ocr_setup():
    print("🔍 Проверка установки OCR библиотек...\n")
    
    # 1. Проверка Python библиотек
    try:
        import pytesseract
        print("✅ pytesseract установлен")
        print(f"   Версия: {pytesseract.__version__}")
    except ImportError:
        print("❌ pytesseract НЕ установлен")
        print("   Установите: pip install pytesseract")
    
    try:
        from PIL import Image
        print("✅ Pillow (PIL) установлен")
        print(f"   Версия: {Image.__version__}")
    except ImportError:
        print("❌ Pillow НЕ установлен")
        print("   Установите: pip install pillow")
    
    try:
        import cv2
        print("✅ OpenCV установлен")
        print(f"   Версия: {cv2.__version__}")
    except ImportError:
        print("⚠️  OpenCV НЕ установлен (опционально)")
        print("   Установите: pip install opencv-python")
    
    # 2. Проверка системного Tesseract
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Tesseract установлен")
            print(f"   {result.stdout.split()[1]} {result.stdout.split()[2]}")
        else:
            print("❌ Tesseract НЕ работает")
    except FileNotFoundError:
        print("❌ Tesseract НЕ установлен в системе")
        print("   macOS: brew install tesseract")
        print("   Linux: sudo apt-get install tesseract-ocr")
    except Exception as e:
        print(f"❌ Ошибка проверки Tesseract: {e}")
    
    # 3. Проверка языков
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--list-langs'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            langs = result.stdout.strip().split('\n')[1:]  # Пропускаем первую строку
            print(f"✅ Доступно языков: {len(langs)}")
            
            # Проверка нужных языков
            needed_langs = ['eng', 'rus', 'heb', 'chi_sim', 'chi_tra']
            available = [lang for lang in needed_langs if lang in langs]
            missing = [lang for lang in needed_langs if lang not in langs]
            
            if available:
                print(f"   ✅ Доступны нужные языки: {', '.join(available)}")
            if missing:
                print(f"   ❌ Отсутствуют языки: {', '.join(missing)}")
                print("      macOS: brew install tesseract-lang")
                print("      Linux: sudo apt-get install tesseract-ocr-heb tesseract-ocr-rus tesseract-ocr-chi-sim tesseract-ocr-chi-tra")
        else:
            print("❌ Не удалось получить список языков")
    except Exception as e:
        print(f"❌ Ошибка проверки языков: {e}")
    
    print("\n🎯 Готово к тестированию!")

if __name__ == "__main__":
    test_ocr_setup()
