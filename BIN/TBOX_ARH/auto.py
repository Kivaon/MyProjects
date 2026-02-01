import sys, subprocess, os

# v1.1 - 2026-01-19
# Фикс: Автоматический переход в папку проекта

def run_cmd(cmd_list):
    """Запуск скриптов через python3"""
    try:
        print(f"\n>>> ЗАПУСК: {' '.join(cmd_list)}")
        # Используем абсолютный путь к интерпретатору и скрипту
        subprocess.run(["python3"] + cmd_list, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"!!! ОШИБКА при выполнении: {cmd_list[0]}")
        return False

def main():
    # --- МАГИЯ ПУТЕЙ ---
    # Определяем, где лежит сам auto.py (это ~/Documents/AI_Lab/)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    # Прыгаем в эту папку, чтобы все относительные пути (./) работали верно
    os.chdir(project_dir)
    # -------------------

    if len(sys.argv) < 2:
        print("\n[ АВТОМАТЫ ЛАБОРАТОРИИ 2.0 ]")
        print("Использование:")
        print("  auto -yt [ID] [-s] [-pub]")
        print("  auto -pdf [имя] [-s] [-pub]")
        print("  auto -ocr [-s] [-pub]")
        return

    mode = sys.argv[1]
    args = sys.argv[2:]
    
    do_pub = "-pub" in args
    include_source = "-s" in args
    
    clean_args = [a for a in args if a not in ("-pub", "-s")]
    search_val = clean_args[0] if clean_args else ""

    # 1. ЭКСТРАКЦИЯ
    success = False
    if mode == "-yt":
        if not search_val:
            print("Ошибка: Для YouTube нужен ID.")
            return
        success = run_cmd(["extract_yt.py", search_val])
    elif mode == "-pdf":
        success = run_cmd(["extract_pdf.py"] + ([search_val] if search_val else []))
    elif mode == "-ocr":
        success = run_cmd(["ocr_scanner.py"])

    if not success: return

    # 2. ПЕРЕВОД
    trans_cmd = ["translator.py"]
    if include_source: trans_cmd.append("-s")
    
    if run_cmd(trans_cmd):
        # 3. ПАБЛИШЕР
        if do_pub:
            run_cmd(["publisher.py"])
            print("\n✅ ЦИКЛ ЗАВЕРШЕН! Проверь папку FINAL")
        else:
            print("\n✅ ГОТОВО! Перевод в DOC2PUB")

if __name__ == "__main__":
    main()