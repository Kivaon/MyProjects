import os
from datetime import datetime

# --- MANIFEST ---
VERSION = "v1.2"
DATE    = "2026-01-23"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def tbox_log(message, script_meta, level="INFO", conf=None):
    """
    Унифицированный вывод TranslateBox.
    script_meta: паспорт вызывающей процедуры {'name':..., 'version':...}
    conf: словарь конфигурации (опционально)
    """
    now = datetime.now()
    # Идентификатор вызывающей процедуры
    tag = f"[{script_meta['name']} {script_meta['version']}]"
    
    # Формируем строки вывода
    time_s = now.strftime('%H:%M:%S')
    time_f = now.strftime('%Y-%m-%d %H:%M:%S')
    
    t_msg = f"[{time_s}] {tag} [{level}] {message}"
    f_msg = f"[{time_f}] {tag} [{level}] {message}"
    
    # 1. Печать в терминал (всегда)
    print(t_msg)
    
    # 2. Попытка записи в файл (если передан конфиг)
    if conf and 'LOG_FILE' in conf:
        log_path = conf['LOG_FILE']
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f_msg + "\n")
        except Exception as e:
            # Унифицированная ошибка: используем META самой утилиты utils
            sys_tag = f"[{NAME} {VERSION}]"
            error_msg = f"!!! ОШИБКА ДОСТУПА К LOG_FILE: {e}"
            print(f"[{time_s}] {sys_tag} [SYS_ERROR] {error_msg}")