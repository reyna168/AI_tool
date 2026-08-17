# Hermes Agent 保姆級教學——最安全的 AI 私人助理

## 一、Hermes 是什麼

Hermes 是由 Nous Research 團隊推出的一款 AI 助理。與 ChatGPT、Claude、OpenClaw 等工具相比，Hermes 有四個獨特優勢：

| 優勢 | 說明 |
|------|------|
| **背景獨立運作** | 可長時間在背景持續運作，透過手機 APP 隨時交辦任務 |
| **自我學習** | 每完成一項任務會自動回顧，優化下次處理方式 |
| **分層記憶系統** | 記住你的工作模式、偏好和習慣，成為真正的貼身助理 |
| **安全與穩定** | 內建審查機制，遇到刪除檔案等重要操作會先詢問授權 |

---

## 二、安裝方式比較

| 方式 | 優點 | 缺點 |
|------|------|------|
| **本機電腦** | 幾乎不花錢；被駭客入侵風險低 | 電腦關機/休眠/斷電時離線 |
| **雲端伺服器** | 24 小時穩定運作；不接觸本地私人文件 | 需付月租費 |

---

## 三、本機安裝

### 3.1 建立獨立帳號（建議）

為了安全考量，建議為 Hermes 建立一個**非管理員**的獨立使用者帳號：

**macOS**：系統設定 → 使用者與群組 → 加入使用者 → 設定帳號名稱和密碼 → 登出並登入新帳號

**Windows**：設定 → 帳戶 → 其他使用者 → 新增使用者

### 3.2 下載安裝

1. 前往 Hermes 官網，依據作業系統下載對應版本
2. 打開安裝檔，點擊 **Install Hermes**
3. 安裝完成後啟動 Hermes

### 3.3 選擇 AI 模型供應商

- **Hermes 官方訂閱**：支付月費使用其提供的模型
- **OpenAI**：若已有 ChatGPT 訂閱，可直接使用，無需額外付費
- **OpenRouter**：支援自由切換各式各樣的模型，採儲值制

選擇後，Hermes 會產生一組授權碼，複製貼到對應的授權網頁即可完成設定。

---

## 四、雲端安裝（以 Hetzner 為例）

### 4.1 購買方案

1. 進入 [Hetzner](https://www.hetzner.com) 首頁，點擊「選擇方案」
2. 選擇預設第二個選項（CPU 和 RAM 足以支援 Hermes 運行）
3. 選擇付費週期（綁月越長越划算）
4. 使用 Google 帳號登入，填寫信用卡資訊完成購買

### 4.2 初始設定

1. 選擇伺服器位置（盡量選離自己近的機房，如馬來西亞）
2. 從應用程式清單中選擇 **Hermes Agent**
3. 建立登入雲端主機的帳號和密碼
4. 系統自動安裝 Hermes

### 4.3 配置 AI 模型

在 Hetzner 後台打開 **Terminal 終端機**：

```bash
# 切換使用者
su hermes

# 進行快速設定
hermes setup
# 選擇 Quick Setup
```

選擇 AI 模型供應商（如 OpenAI），貼上授權碼，選擇模型（如 GPT-5.5）。

---

## 五、串接 Telegram

### 5.1 建立 Telegram Bot

1. 在 Telegram 搜尋 **@BotFather**
2. 輸入 `/newbot`
3. 設定機器人名稱（名稱必須以 `bot` 結尾）
4. 取得一組 Bot Token

### 5.2 綁定 Hermes

```bash
# 在 Hermes 設定頁面選擇 Telegram
# 貼上 Bot Token
```

### 5.3 設定安全防護

為了防止他人偷偷發訊息給你的 AI 助理：

1. 在 Telegram 搜尋 **@userinfobot**
2. 傳送任意訊息取得自己的用戶 ID
3. 將 ID 貼回 Hermes 設定頁面（設為 Home Channel）

### 5.4 啟動對話

```bash
# 本機安裝時
hermes gateway
```

在 Telegram 中找到你的 Bot，點擊「開始」即可對話。

---

## 六、記憶系統

Hermes 使用三個核心檔案管理記憶：

| 檔案 | 用途 |
|------|------|
| **User.md** | 你的個人檔案卡——記錄你是誰、有哪些偏好 |
| **Memory.md** | Hermes 的工作筆記本——累積經驗與心得 |
| **Persona.md** | Hermes 的角色設定——記載名稱、語氣、扮演的角色 |

### 記憶特點

- 對話量累積到一定程度時，**自動壓縮**先前的對話內容
- 輸入 `/new` 可建立全新對話，記憶仍然保留
- 可要求 Hermes 列出所有記憶、修改或刪除特定內容

### 自訂角色

例如將 Hermes 命名為「鬥鬥」，設定為「細心又溫暖的陪伴者」，這些設定記錄在 `Persona.md`。

---

## 七、切換 AI 模型（OpenRouter）

如果不喜歡月費模式，可使用 OpenRouter 彈性付費：

1. 前往 [OpenRouter](https://openrouter.ai)，使用 Google 註冊免費帳號
2. 點擊 **API Keys** → **New Key**，建立一組金鑰
3. 切換到 **Credits** 頁面，綁定信用卡並儲值（如 10 美元）
4. 回到 Hetzner 後台終端機：

```bash
su hermes
hermes model
# 選擇 OpenRouter → 貼上金鑰 → 選擇模型（如 DeepSeek）
```

---

## 八、網頁搜尋（Tavily）

Hermes 內建基礎網頁搜尋，但若需要更即時、多來源的搜尋結果，可串接 Tavily：

1. 前往 [Tavily](https://tavily.com) 註冊免費帳號
2. 取得一組 API 金鑰
3. 在終端機設定：

```bash
su hermes
hermes tools
# 選擇 4. Reconfigure → Web Search → Tavily → 貼上 API 金鑰
```

---

## 九、SubAgent（子代理）

SubAgent 可以讓 Hermes 一次派出多個分身，同時執行不同任務。

**範例**：調查三個電商平台的抽成費用和上架流程

```
→ Hermes 同時派出 3 個子代理
→ 各自調查一個平台
→ 結果匯整成 HTML 儀表板
```

---

## 十、串接 Google 服務（Gmail、日曆、Drive、Docs）

### 10.1 建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 建立新專案，命名為 **Hermes**
3. 在「程式庫」中搜尋並啟用：
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Docs API

### 10.2 建立 OAuth 憑證

1. 點擊「憑證」→「建立 OAuth 使用者端」
2. 應用程式名稱輸入 **Hermes**
3. 目標對象設為**外部**
4. 填寫聯絡電子郵件，勾選同意後建立
5. 下載 JSON 檔案

### 10.3 設定測試使用者

在「目標對象」頁面，將自己的 Google 帳號新增為測試使用者。

### 10.4 串接 Hermes

1. 將下載的 JSON 檔案上傳給 Hermes
2. Hermes 產生授權連結
3. 打開連結，點擊「繼續」並勾選全選授權
4. 若出現錯誤訊息（正常），將網址複製貼回 Hermes

### 10.5 使用範例

- 請 Hermes 找出特定郵件，並將事件登記到 Google 日曆
- 自動從 Gmail 信件中提取行程資訊

---

## 十一、排程功能（Cron Jobs）

Hermes 可以設定定時任務：

| 範例 | 設定 |
|------|------|
| 每天早上 8 點推送今日行程 | `每天 08:00` |
| 每天晚上推送 5 個日文單字 | `每天 21:00` |
| 每天凌晨 3 點備份資料 | `每天 03:00` |

可隨時查看、刪除或修改排程，也可指定使用特定 AI 模型執行特定任務。

---

## 十二、地圖與路線規劃

Hermes 內建地圖查詢功能，可以：

- 規劃大眾運輸路線
- 建議店家造訪順序
- 查詢營業時間

---

## 十三、語音模式

在 Telegram 中輸入 `/voice` 啟用語音模式：

- 按住麥克風按鈕錄音
- Hermes 以語音回覆
- 適合不方便打字的場景（如採購途中）

---

## 十四、Skills 技能系統

### 14.1 什麼是 Skill

Skill 就像一份寫好的 SOP，Hermes 照著流程直接操作，不用每次從頭摸索。

### 14.2 自建 Skill 範例

**範例 1：自動記錄到 Google Docs**
- 觸發：你交代一件事
- 流程：自動整理 → 附上日期時間 → 寫入 Google 文件

**範例 2：收據 OCR**
- 觸發：上傳收據照片到 Telegram
- 流程：裁切背景 → 文字辨識 → 填入 Google 試算表

### 14.3 內建 Skills

Hermes 內建 70+ 種 Skills，涵蓋創作、文書、軟體開發等領域。

每當 Hermes 完成一項任務，會自動將處理方式保存為 Skill，下次遇到類似任務時更快上手。

### 14.4 安裝社群 Skills

- 前往官方 Skills 目錄網站瀏覽
- 複製安裝指令
- 在 Telegram 請 Hermes 安裝
- Hermes 會自動檢查來源和安全性，若發現惡意內容會警告

---

## 十五、圖片生成

### 15.1 使用內建模型

若使用的模型本身支援生圖（如 Gemini、ChatGPT），無需額外設定。

### 15.2 使用 fal.ai

若模型不支援生圖，可串接 fal.ai：

1. 前往 [fal.ai](https://fal.ai) 註冊帳號
2. 綁定信用卡並儲值
3. 取得 API 金鑰
4. 在終端機設定：

```bash
su hermes
hermes tools
# 選擇 4. Reconfigure → Image Generation → fal.ai → 貼上金鑰
# 選擇模型（如 GPT Image 2）
```

---

## 十六、影片生成

1. 進入 `hermes tools` → **Video Generation**
2. 選擇 fal.ai → 貼上同一把金鑰
3. 選擇模型（如 Sora/Dance 2.0）
4. 在 Telegram 設定頁面啟用影片生成功能

可將商品照轉成質感細膩的商品影片。

---

## 十七、串接 Notion

### 17.1 建立 Notion 連線

1. 前往 [Notion](https://notion.so) → **New Connection**
2. 取得專屬 API 金鑰

### 17.2 設定 Hermes

```bash
su hermes
# 將 Notion 金鑰寫入設定檔
# 重啟系統使設定生效
```

### 17.3 開放頁面權限

在 Notion 設定 → 管理 → 找到 Hermes → 編輯權限 → 勾選要開放的頁面 → 儲存。

### 17.4 使用目標模式

使用「購物目標」功能，Hermes 會將大目標拆解成小任務，分回合持续推进直到完成。

---

## 十八、備份與安全

### 自動備份

設定排程在每天凌晨 3 點自動備份：

```
→ 打包所有重要資料為壓縮檔
→ 備份到 Google Cloud Storage
→ 若發生意外，從雲端取回最新備份即可恢復
```

### 防火牆

在 Hetzner 後台 → 安全分頁：

1. 建立防火牆規則
2. 設為啟用
3. 防止來自外部的惡意連線

---

## 十九、總結

| 功能 | 說明 |
|------|------|
| 背景運作 | 24 小時持續運作，隨時透過 Telegram 交辦 |
| 記憶系統 | 自動學習你的偏好和工作模式 |
| 多模型切換 | 透過 OpenRouter 彈性選擇不同 AI 模型 |
| SubAgent | 同時派出多個子代理並行處理任務 |
| Google 整合 | Gmail、日曆、Drive、Docs 一鍵串接 |
| 排程任務 | 定時自動執行指定工作 |
| Skills | 內建 70+ 技能，支援自建和社群安裝 |
| 圖片/影片生成 | 透過 fal.ai 串接多種生成模型 |
| Notion 串接 | 透過 API 金鑰整合筆記管理 |
| 自動備份 | 定時備份到雲端，防止資料遺失 |

> **安全提醒**：Hermes 強調安全優先——遇到刪除檔案等重要操作會先暫停詢問，確保你有充分的授權控制。
