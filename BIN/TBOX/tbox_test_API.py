import os, sys, requests, configparser
from tbox_utils import tbox_log

# --- MANIFEST ---
VERSION = "v1.4"
DATE    = "2026-01-23"
NAME    = os.path.basename(__file__)
META    = {"name": NAME, "version": VERSION}

def load_tbox_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir_actual = os.path.dirname(script_dir)
    config_path = os.path.join(base_dir_actual, "_config/tconfig.txt")
    conf = {}
    if not os.path.exists(config_path): return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    conf[key.strip()] = val.strip()
        return conf
    except: return None

def check_health():
    CONF = load_tbox_config()
    if not CONF or 'API_KEY' not in CONF:
        tbox_log("API_KEY не найден!", META, "ERROR")
        return

    key = CONF.get('API_KEY').split('#')[0].strip()
    tbox_log(f"Запуск диагностики. Ключ: {key[:4]}***{key[-4:]}", META, "START", CONF)

    working_models = [] # Сюда собираем "хорошее"

    for ver in ["v1", "v1beta"]:
        url = f"https://generativelanguage.googleapis.com/{ver}/models?key={key}"
        print(f"\n--- [ Ветка {ver.upper()} ] ---")
        
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue

            models = r.json().get('models', [])
            gen_models = [m['name'].replace('models/', '') for m in models 
                          if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            for m in sorted(gen_models):
                t_url = f"https://generativelanguage.googleapis.com/{ver}/models/{m}:generateContent?key={key}"
                try:
                    payload = {"contents": [{"parts": [{"text": "hi"}]}]}
                    tr = requests.post(t_url, json=payload, timeout=7)
                    
                    if tr.status_code == 200:
                        status = "✅ ONLINE"
                        working_models.append(f"{m} ({ver})") # Сохраняем успех
                    elif tr.status_code == 429:
                        status = "❌ 429 (QUOTA)"
                    else:
                        status = f"⚠️ {tr.status_code}"
                    
                    print(f"  - {m:<35} | {status}")
                except:
                    print(f"  - {m:<35} | 🔌 TIMEOUT")

        except Exception as e:
            tbox_log(f"Ошибка соединения {ver}: {e}", META, "ERROR", CONF)

    # --- ФИНАЛЬНЫЙ СВОДНЫЙ ОТЧЕТ ---
    print("\n" + "="*50)
    print(f"🏆 ЗОЛОТОЙ СПИСОК ДОСТУПНЫХ МОДЕЛЕЙ (TBox {VERSION})")
    print("="*50)
    
    if working_models:
        # Убираем дубли (если модель есть и в v1, и в v1beta)
        unique_working = sorted(list(set(working_models)))
        for i, m in enumerate(unique_working, 1):
            print(f"{i}. {m}")
        
        tbox_log(f"Диагностика завершена. Найдено моделей: {len(unique_working)}", META, "DONE", CONF)
    else:
        print("[-] НЕТ ДОСТУПНЫХ МОДЕЛЕЙ. Проверьте лимиты или ключ.")
        tbox_log("Ключ не прошел проверку ни по одной модели.", META, "ERROR", CONF)

if __name__ == "__main__":
    check_health()