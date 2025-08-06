import openai

openai.api_key = "your_openai_api_key"

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "請幫我寫一篇 podcast 腳本，主題是 AI 如何改變日常生活"}]
)

script = response.choices[0].message.content
print(script)
