import os, requests, configparser

def get_key():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.txt")
    config = configparser.ConfigParser()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config.read_string('[DEFAULT]\n' + f.read())
        return config['DEFAULT'].get('API_KEY', '').split('#')[0].strip()
    except: return None

def check_health():
    key = get_key()
    if not key:
        print("[-] ОШИБКА: API_KEY не найден в config.txt")
        return

    print(f"--- ДИАГНОСТИКА GEMINI API ---")
    print(f"Ключ: {key[:8]}...{key[-4:]}")
    
    # Проверяем обе ветки API
    for ver in ["v1", "v1beta"]:
        url = f"https://generativelanguage.googleapis.com/{ver}/models?key={key}"
        print(f"\n[Ветка {ver.upper()}]:")
        
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                models = r.json().get('models', [])
                # Фильтруем только текстовые модели
                gen_models = [m['name'].replace('models/', '') for m in models 
                              if 'generateContent' in m.get('supportedGenerationMethods', [])]
                
                for m in gen_models:
                    # Тестовый запрос (ping) для каждой модели
                    t_url = f"https://generativelanguage.googleapis.com/{ver}/models/{m}:generateContent?key={key}"
                    try:
                        tr = requests.post(t_url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=5)
                        if tr.status_code == 200:
                            status = "✅ OK"
                        elif tr.status_code == 429:
                            reason = "Quota Full" if "limit" not in tr.text else "LIMIT 0 (Wait 24h)"
                            status = f"❌ 429 ({reason})"
                        else:
                            status = f"⚠️ {tr.status_code}"
                        
                        print(f"  - {m:<35} | {status}")
                    except:
                        print(f"  - {m:<35} | 🔌 Network Error")
            else:
                print(f"  [!] Ошибка ветки: {r.status_code}")
        except Exception as e:
            print(f"  [!] Ошибка соединения: {e}")

if __name__ == "__main__":
    check_health()