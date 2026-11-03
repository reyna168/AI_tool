這是我準備好的 STEP 20 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 20: Gemini 3.5 智能盤勢解析 - 備用救援程式碼
!pip install -q google-genai

import pandas as pd
from google import genai
from google.colab import userdata

try:
    api_key = userdata.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未設定，請在 Colab 秘密鍵 (Secrets) 中加入！")
    
    client = genai.Client(api_key=api_key)
    
    recent_data = df.tail(3)[['open', 'high', 'low', 'close', 'volume']].to_string()
    
    prompt = f"以下是台股 2330 台積電近三日交易數據：\n{recent_data}\n請身為資深量化分析師，給予 150 字以內的多空解析與操作觀點。"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    print("🤖 【Gemini 智能盤後解析】:")
    print(response.text)
except Exception as e:
    print(f"⚠️ Gemini 呼叫提示: {e}")
```
