#!/usr/bin/env python3
import asyncio
import edge_tts

async def list_male_voices():
    """Список мужских голосов для русского языка"""
    voices = await edge_tts.list_voices()
    
    # Фильтруем мужские голоса для русского языка
    male_voices = []
    for voice in voices:
        if 'Male' in voice['Gender'] and 'ru' in voice['Locale']:
            male_voices.append(voice)
    
    print("🎤 Мужские голоса для русского языка:")
    print("=" * 50)
    
    for voice in male_voices:
        print(f"🔹 {voice['ShortName']}")
        print(f"   {voice['FriendlyName']}")
        print(f"   Локаль: {voice['Locale']}")
        print(f"   Стиль: {voice.get('Style', 'N/A')}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(list_male_voices())
