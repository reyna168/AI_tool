這是我準備好的 STEP 22 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# 根據筆記本中已知的依賴套件列表，自動生成 requirements.txt
# 這裡將使用在 `7519ed5d` cell 中列出的套件。
requirements_content = """
requests==2.32.4
pandas==2.2.3
numpy
scipy
scikit-learn
plotly
yfinance
FinMind
gradio
numba
anyio
google-genai
matplotlib
seaborn
ta
"""

with open('requirements.txt', 'w') as f:
    f.write(requirements_content.strip())

print("已成功生成 requirements.txt 檔案！內容如下：")
print("----------------------------------------")
print(requirements_content.strip())
print("----------------------------------------")
print("您可以使用 `!cat requirements.txt` 命令來查看檔案內容。")

# 嘗試啟動瀏覽器自動下載 (支援 Google Colab 環境)
try:
    from google.colab import files
    print("
🚀 正在啟動瀏覽器自動下載 requirements.txt...")
    files.download('requirements.txt')
    print("📥 下載指令已送出！請檢查您電腦瀏覽器的「下載」資料夾。")
except Exception as e:
    print(f"💡 瀏覽器自動下載提示 (若未自動跳出): {e}")

print("
📂 【手動下載備用指引】：")
print("👉 您也可以隨時點擊 Colab 左側面板的「📁 檔案」圖示")
print("👉 在檔案列表中找到 requirements.txt，按右鍵點選「下載」即可存至本機電腦！")
```
