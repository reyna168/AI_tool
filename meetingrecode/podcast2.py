import requests

api_key = "your_elevenlabs_api_key"
voice_id = "your_voice_id"

def generate_audio(text, filename="output.mp3"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, headers=headers, json=payload)
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"語音已儲存到 {filename}")

generate_audio(script)

