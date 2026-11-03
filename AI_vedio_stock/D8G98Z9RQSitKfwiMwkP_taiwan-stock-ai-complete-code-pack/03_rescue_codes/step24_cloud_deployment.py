這是我準備好的 STEP 24「線上網站部署 (Colab 股市工具一鍵變 Web App)」雲端發布指南與應急說明。

⚠️ **【重要觀念說明】：本步驟【完全不需要再回到 Colab 貼上或執行任何程式碼】！**
因為在 STEP 22 (requirements.txt) 與 STEP 23 (stock.py) 您已經透過自動下載或檔案面板將這兩個檔案儲存至您的電腦。STEP 24 的所有操作均直接在 **Hugging Face 官方網站** 上進行。

---

### 🌐 【Hugging Face Spaces 部署 4 步全流程】

#### 1️⃣ 建立 Gradio Space
- 前往 [huggingface.co](https://huggingface.co/) 註冊/登入 ➔ 點右上角頭像 ➔ **「+ New Space」**。
- **Space name**: 輸入自訂專案名（如 `taiwan-stock-dashboard`）。
- **Space SDK**: 選擇 👉 **`Gradio`**。
- **Space hardware**: 選擇 👉 **`CPU Basic (Free)`**。
- 點擊頁面底部的 **「Create Space」**。

#### 2️⃣ 上傳 requirements.txt 與 app.py
- 進入 Space 頁面，點選頂部 **「Files」** 頁籤 ➔ 點選 **「+ Add file」** ➔ **「Upload files」**。
- 將電腦下載好的 `requirements.txt` 與 `stock.py` 拖曳上傳。
  *(💡 小秘訣：若檔案名為 stock.py，建議直接在電腦上重新命名為 `app.py` 後再上傳，Hugging Face 會自動視為預設進入點)*
- 點擊 **「Commit changes to main」**。

#### 3️⃣ 🔑 安全設定 FinMind Token 與 Gemini API Key (絕對不外洩)
若您的系統有使用到法人籌碼/借券數據或 Gemini AI 策略解析：
- 切換至 Space 頂部的 **「Settings」** (設定) 頁籤。
- 往下滑找到 **「Variables and secrets」** 區塊。
- 點擊 **「New secret」** 分別新增兩筆密鑰：
  * **密鑰一 (Gemini AI)**：
    - Name: `GEMINI_API_KEY`
    - Value: 填入您的 Google Gemini API Key
  * **密鑰二 (FinMind 台股籌碼)**：
    - Name: `FINMIND_TOKEN`
    - Value: 填入您的 FinMind API Token
- 點擊 **「Save」** 儲存。平台會以加密環境變數自動注入容器，程式碼即可透過 `os.environ.get('KEY')` 安全讀取！

#### 4️⃣ 自動建置 (Build) 與上線營運
- 切換回 **「App」** 頁籤，上方狀態會顯示 🟡 **Building**。
- 點擊可展開 Build Logs 查看套件安裝進度。
- 當狀態變為 🟢 **Running** (綠燈) 時，您的台股量化盯盤系統就正式在雲端上線囉！
- 複製 Space 網址即可分享給好友或在手機瀏覽器中隨時看盤！
