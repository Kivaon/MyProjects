import requests, os

def find_first_ready_model(api_key):
    """
    ПРОЦЕДУРА 1: Поиск 'первого выжившего'.
    Возвращает (имя_модели, версия_api) или (None, None).
    """
    for ver in ["v1beta", "v1"]:
        list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
        try:
            r = requests.get(list_url, timeout=5)
            if r.status_code != 200: continue
            
            models = r.json().get('models', [])
            # Сортируем reverse=True, чтобы 2.5/2.0 были выше 1.5
            candidates = sorted([m['name'].replace('models/', '') for m in models 
                          if 'generateContent' in m.get('supportedGenerationMethods', [])], reverse=True)
            
            for m_name in candidates:
                test_url = f"https://generativelanguage.googleapis.com/{ver}/models/{m_name}:generateContent?key={api_key}"
                try:
                    # Контрольное "hi" для проверки квоты
                    res = requests.post(test_url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=3)
                    if res.status_code == 200:
                        return m_name, ver # Берем ПЕРВОГО рабочего
                except: continue
        except: continue
    return None, None

def get_ai_text(prompt, api_key):
    """
    ПРОЦЕДУРА 2: Запрос к ИИ через диспетчера.
    """
    m_name, m_ver = find_first_ready_model(api_key)
    if not m_name:
        return None, "Ни одна модель не ответила (429/Quota)"

    url = f"https://generativelanguage.googleapis.com/{m_ver}/models/{m_name}:generateContent?key={api_key}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=120)
        res = r.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text'], m_name
        return None, f"Ошибка API {m_name}: {res.get('error', {}).get('message')}"
    except Exception as e:
        return None, str(e)