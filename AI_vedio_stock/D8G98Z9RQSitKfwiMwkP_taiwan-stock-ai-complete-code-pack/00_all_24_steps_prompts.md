# 用 AI 打造台股看盤+盯盤系統 | 24 步驟一鏡到底完整詠唱詞庫
> 本檔案彙整自 MasterTalks Vibe Coding 實戰指南，包含 STEP 1 至 STEP 24 全部結構化 Prompt。

---

## STEP 1：啟動環境與套件安裝
- **分類**：環境與資料
- **說明**：在 Colab 準備好所有分析套件，並強制升級 UI 框架避免版本衝突。

### 詠唱詞（貼給 Gemini）：

```text
我正在 Colab 開發台股分析系統。請給我一段指令來安裝套件：requests, pandas, numpy, plotly, yfinance, scikit-learn, FinMind, 以及 gradio。

【防呆要求】：為了避免後續出現 asyncio 的版本衝突錯誤，請務必在 pip 指令中加上 `--upgrade gradio anyio`，且使用 `-q` 參數進行靜默安裝。

【金鑰安檢機制】：請撰寫一段 Python 程式碼，使用 `google.colab.userdata` 嘗試讀取名為 'GEMINI_API_KEY' 與 'FINMIND_TOKEN' 的金鑰。若讀取成功請印出打勾符號，若無請友善提醒。

安裝完成後，請印出「✅ 基礎環境與金鑰已準備好，開始 Vibe Coding！」
```

---

## STEP 2：下載台積電三年數據
- **分類**：環境與資料
- **說明**：我們先用 yfinance 下載台積電三年日線資料，作為後續分析的基石。

### 詠唱詞（貼給 Gemini）：

```text
請幫我寫 Python 程式碼：
1. 匯入 yfinance 與 pandas。
2. 下載 '2330.TW' 近三年的歷史資料 (period='3y') 並存入變數 `df`。
3. 直接印出資料總筆數與最後五筆數據讓我確認。
```

---

## STEP 3：穩健清洗：多層索引處理
- **分類**：環境與資料
- **說明**：確保不論 yfinance 回傳什麼結構，都能避開地雷，統一轉換為標準格式。

### 詠唱詞（貼給 Gemini）：

```text
yfinance 最近經常回傳帶有多層索引的格式，會導致後續程式碼崩潰！

請寫一個最穩健的 `fix_col_names` 函式來處理變數 `df`：

1. 判斷如果 `df.columns` 是 MultiIndex，提取出第一層 `col[0].lower()`；若非 MultiIndex，直接將欄位轉小寫。
2. 清除 `columns.name = None`。
3. 【優先採用還原權息】：若存在 'adj close'，請用它覆寫 'close' 並捨棄原 'adj close'；若只有 'adj close'，更名為 'close'。
4. 過濾欄位：只保留存在於 ['open', 'high', 'low', 'close', 'volume'] 的集合中。
5. 執行：`df = fix_col_names(df)` 並印出 tail(5)。
```

---

## STEP 4：專業 K 線與分價量表
- **分類**：技術分析
- **說明**：利用 Plotly 繪製互動式的 Candlestick 圖表，並加入橫向分價量表辨識支撐壓力。

### 詠唱詞（貼給 Gemini）：

```text
這是一項進階的視覺化任務！我們要在同一個畫面上，左邊畫 K 線，右邊畫「橫向的分價量表」。請【嚴格遵守邏輯】：

1. 【計算分價量表】：
- 將 df['low'].min() 到 df['high'].max() 切割為 50 個等距的價格區間 (price_bins)。
- 使用 np.searchsorted 將每根 K 線的 df['volume'] 累加到其 df['close'] 所屬的區間中。
- 計算每個區間的中心點 (midpoints) 作為 Y 軸坐標。

2. 【建立雙列子圖】：
- 使用 `make_subplots(rows=1, cols=2, column_widths=[0.8, 0.2], shared_yaxes=True, horizontal_spacing=0.01)` 建立左右並排畫布。

3. 【繪製圖表】：
- 列 1 放 `go.Candlestick`。
- 列 2 放 `go.Bar`，設定 x=區間成交量, y=區間中心點，加上 `orientation='h'` 繪製橫向長條圖，顏色設為 rgba(150,150,150,0.5)。

4. 將主標題設定為「2330 台積電三年歷史走勢與分價量表」，使用 template='plotly_white'。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 5：MA 五線譜與交叉訊號
- **分類**：技術分析
- **說明**：計算並繪製均線通道，並自動標示出 MA5 與 MA20 的黃金交叉與死亡交叉點。

### 詠唱詞（貼給 Gemini）：

```text
請利用 `df` 繪製「均線五線譜」並加上買賣訊號標示：

1. 計算 5, 20, 60, 120, 240 日均線。
2. 【尋找交叉點】：請比較 MA5 與 MA20。
- 當 MA5 向上穿過 MA20 時，標記為「黃金交叉」。
- 當 MA5 向下穿過 MA20 時，標記為「死亡交叉」。
3. 【繪製圖表】：在同一個 plotly 圖表中繪製收盤價與這五條均線。
4. 【疊加訊號】：將黃金交叉點以「向上的綠色三角形」標示在收盤價位置；死亡交叉點以「向下的紅色三角形」標示。
5. 命名為「台積電均線五線譜與交叉訊號分析」。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 6：RSI 相對強弱指標
- **分類**：技術分析
- **說明**：加入 RSI 指標圖，透過 30 與 70 基準線，一眼看出超買或超賣訊號。

### 詠唱詞（貼給 Gemini）：

```text
請在一個圖表中使用 subplots (雙層)：
1. 上方繪製股價與之前計算的均線。
2. 下方計算並繪製 RSI(14) 指標，並標註 30 與 70 的水平基準線。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 7：MACD 動能指標
- **分類**：技術分析
- **說明**：加入 MACD 指標，透過快慢線與柱狀體，掌握多空動能的轉換。

### 詠唱詞（貼給 Gemini）：

```text
請將剛才的圖表擴充為三個 subplots (三層)：
1. 上方保留股價與 MA。
2. 中間保留 RSI(14)。
3. 下方計算並繪製 MACD，包含快線、慢線以及柱狀體。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 8：布林通道 (Bollinger Bands)
- **分類**：技術分析
- **說明**：加入布林通道分析，一眼看穿股價波動區間與突破訊號。

### 詠唱詞（貼給 Gemini）：

```text
請利用 `df` 計算並繪製布林通道：
1. 計算 20 日移動平均線 (中軌)。
2. 計算上下 2 倍標準差的軌道 (上軌與下軌)。
3. 使用 plotly 將收盤價與三條軌道畫在同一張圖上，並將上下軌之間的區域填色 (fill='tonexty')。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 9：抓取營收與毛利 (財報)
- **分類**：籌碼與基本面
- **說明**：分析落後指標的第一步：營收成長性與獲利能力。

### 詠唱詞（貼給 Gemini）：

```text
請利用 yfinance 抓取 '2330.TW' 的「季度營收」與「毛利率」數據：
1. 取得 Income Statement (損益表)。
2. 提取最近三年的季度 Revenue 與 Gross Profit。
3. 繪製營收與毛利率的長條圖與折線圖。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 10：外資與投信動向 (真實籌碼)
- **分類**：籌碼與基本面
- **說明**：利用 FinMind 獲取真實三大法人進出數據，免註冊直接抓！

### 詠唱詞（貼給 Gemini）：

```text
這是一項重要的真實籌碼分析！由於 FinMind API 的結構處理需要非常精確，請【完全依照邏輯】撰寫程式碼：

1. 【API 參數】：設定 start_date 為 df.index.min()，end_date 為 df.index.max()。
2. 【獲取數據】：使用 requests 呼叫 https://api.finmindtrade.com/api/v4/data (參數: dataset='TaiwanStockInstitutionalInvestorsBuySell', data_id='2330', timeout=10)。
3. 【資料處理】：將回傳的 json 轉為 DataFrame，日期設為 index。
4. 【篩選與計算】：篩選 name 為 'Foreign_Investor' 與 'Investment_Trust'。計算淨買賣超 net_buy_sell = buy - sell。
5. 【Pivot】：將 name 轉為欄位，並計算累積買賣超 (.cumsum())。
6. 【對齊股價】：與 df[['close']] 進行 Left Merge。使用 .ffill() 填補非交易日，空值補 0。
7. 【視覺化】：建立雙層 plotly 子圖，上方為收盤價，下方為兩條法人累計買賣超折線。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 11：融資融券與散戶動態
- **分類**：籌碼與基本面
- **說明**：掌握散戶籌碼！縮短抓取區間以防卡死，遇限制自動啟動模擬數據。

### 詠唱詞（貼給 Gemini）：

```text
分析散戶融資融券。為避免程式卡死，請【完全依照邏輯】撰寫：

1. 【API 參數】：【只抓取最近一年的數據】！設定 `end_date = df.index.max()`，`start_date = end_date - pd.Timedelta(days=365)`。
2. 【防卡死呼叫】：【絕對禁止】使用 DataLoader。改用 `requests.get` 呼叫 `https://api.finmindtrade.com/api/v4/data`，參數：dataset='TaiwanStockMarginPurchaseShortSale', data_id='2330'。【務必加上 timeout=10】。
3. 【權限防護網】：若 requests 發生 Timeout 或錯誤，請印出警告並自動用 `numpy` 生成模擬數據讓課程繼續。
4. 【特徵工程】：將數據與 `df` Left Merge。針對合併產生的缺失值，使用 `.ffill()` 向前填補，最前面 NaN 補 0。
5. 【進階指標計算】：利用融券餘額除以融資餘額，計算「券資比」，處理除以零錯誤 (inf)。
6. 【視覺化】：建立三層子圖。在上方股價圖中，畫出融資餘額的 90% (籌碼混亂區，紅色背景) 與 10% (籌碼安定區，綠色背景)。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 12：ATR 波動幅度與停損策略
- **分類**：技術分析
- **說明**：計算真實波動幅度，幫助量化策略設定合理的停損點。

### 詠唱詞（貼給 Gemini）：

```text
我們來計算真實波動幅度 (ATR)：
1. 根據 `df` 的 high, low, close 計算每日 True Range (TR)。
2. 計算 14 日平滑平均得到 ATR 欄位。
3. 將收盤價與 ATR 繪製為雙層子圖。並印出說明：「當 ATR 處於高檔時，代表近期股價震盪劇烈，程式交易應相應放寬停損點。」

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 13：落後指標綜合熱力圖
- **分類**：籌碼與基本面
- **說明**：將上述財報、籌碼指標進行相關性分析，找出誰最影響股價。

### 詠唱詞（貼給 Gemini）：

```text
請整合目前的變數：
1. 建立一個包含股價、營收、外資買賣、融資餘額的 Correlation (相關性) 矩陣。請將欄位名稱改為英文以避免中文字體顯示問題。
2. 使用 Seaborn 繪製熱力圖 (Heatmap)。
3. 告訴我哪一個「落後指標」與台積電股價相關性最高。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 14：進階領先籌碼 (期貨與借券)
- **分類**：籌碼與基本面
- **說明**：抓取外資期貨空單與借券賣出餘額，從衍生性商品提前洞察現貨市場的變盤訊號。

### 詠唱詞（貼給 Gemini）：

```text
抓取進階領先籌碼：「外資期貨動向」與「借券賣出餘額」。請依照邏輯撰寫：

1. 【時間範圍】：設定 start_date 為最近一年。
2. 【獲取台指期法人數據】：呼叫 FinMind (dataset='TaiwanFuturesInstitutionalInvestors', data_id='TX', timeout=10)。篩選 institutional_investors == '外資'，計算淨未平倉口數：Foreign_TX_Net_OI = long - short。轉為 Series。
3. 【獲取借券賣出餘額】：呼叫 FinMind (dataset='TaiwanStockSecuritiesLending', data_id='2330', timeout=10)。以 date 為群組 groupby.sum()，提取 volume 作為 sell_balance。
4. 【防呆備援機制】：用 try-except 包覆 requests，若失敗，請使用 np.random 生成模擬的時間序列數據。
5. 【資料對齊】：將兩欄合併至 df，使用 .ffill().fillna(0) 填補空值。
6. 【Plotly 視覺化】：繪製 3 列子圖。Row 1 收盤價；Row 2 Foreign_TX_Net_OI (大於0用綠色，小於0用紅色)；Row 3 sell_balance (折線下方填色)。
7. 觀念輸出：print 出：「當外資期貨淨空單增加，且借券賣出攀升時，通常是法人正在避險佈局的先行訊號！」

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 15：AI 特徵工程與標籤定義
- **分類**：AI 量化模型
- **說明**：將市場行為翻譯成 AI 能懂的特徵，並建立預測目標。

### 詠唱詞（貼給 Gemini）：

```text
把股市轉成數學語言！請進行特徵工程：
1. 建立 `ml_df = df.copy()`。
2. 構建技術特徵：20日乖離率(Bias_20)、日報酬率(Daily_Return)、RSI。
3. 構建領先特徵：將剛才的外資期貨淨未平倉與借券賣出餘額加入特徵矩陣。
4. 標籤工程：使用 `shift(-1)` 將隔日收盤價大於今日收盤價標記為 1 (漲)，否則為 0 (Target)。
5. 清除 NaN 後，計算並印出 Target=0 與 Target=1 時的各特徵平均值，進行多空訊號探勘。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 16：訓練 AI 模型 (破解勝率迷思)
- **分類**：AI 量化模型
- **說明**：用基礎特徵訓練隨機森林，見證 50% 擲硬幣勝率的第一課。

### 詠唱詞（貼給 Gemini）：

```text
請訓練機器學習模型：
1. 匯入 sklearn 的 train_test_split 與 RandomForestClassifier。
2. 將 `ml_df` 的特徵設為 X，Target 設為 y。設定 test_size=0.2 且【禁止洗牌 (shuffle=False)】避免未來數據洩漏。
3. 訓練模型並印出準確度 (Accuracy)。
4. 【觀念輸出】：請在程式碼最後 print，告訴學員：「若勝率在 50% 左右，代表僅依賴公開的基礎技術指標跟擲硬幣無異。我們必須引入籌碼與複合特徵來榨出超額報酬！」

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 17：建構 20+ 複合特徵矩陣
- **分類**：AI 量化模型
- **說明**：火力全開！加入 Lag 特徵、跨市場與真實籌碼，建立多維度的 AI 預測特徵庫。

### 詠唱詞（貼給 Gemini）：

```text
建立包含 20+ 特徵的 `mega_df`：
1. 加入動能特徵：1d/3d/5d 報酬率、MACD 柱狀體。
2. 波動率與型態：布林通道寬度 (BB_Width)、正規化 ATR。
3. 【跨市場特徵】：使用 yfinance 加入費城半導體指數 (^SOX)、美國10年期公債殖利率 (^TNX) 與 VIX 恐慌指數 (^VIX) 的變動率。
4. 【Lead-Lag 領先特徵】：針對期貨未平倉與借券餘額，生成平移特徵 (如 `shift(5)` 代表一週前的數據)，讓 AI 學習領先籌碼的影響。
5. 清理 NaN 後，重新訓練隨機森林模型 (n_estimators=200)。
6. 使用 plotly 繪製「特徵重要性 (Feature Importance) 橫向長條圖」，讓我們看見 AI 是依據什麼指標做決策的！

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 18：純粹 Pandas 向量化回測
- **分類**：AI 量化模型
- **說明**：不依賴臃腫框架！使用原生 Pandas 進行向量化回測，計算加入手續費後的真實策略績效。

### 詠唱詞（貼給 Gemini）：

```text
我們將放棄龐大的外部回測套件，改用純粹的 Pandas 進行「向量化回測 (Vectorized Backtesting)」，套件越少越好、執行速度更快！

請依照以下邏輯撰寫程式碼：

1. 【準備資料】：建立 `backtest_df = pd.DataFrame(index=X_test_mega.index)`，加入欄位 `Daily_Return` (取自 `mega_df_cleaned_final` 同期數據)。
2. 【載入訊號】：將測試集預測結果 `y_pred_mega` 存入 `backtest_df['Signal']`。
3. 【計算策略報酬】：因為是今天判斷訊號、明天持有，部位狀態為 `backtest_df['Signal'].shift(1)`。計算 `Strategy_Return = backtest_df['Signal'].shift(1) * backtest_df['Daily_Return']`。
4. 【加入摩擦成本】：找出進出場點！計算訊號變化 `Trade_Action = backtest_df['Signal'].diff().abs()`。假設單邊手續費與滑價總和為 0.3% (0.003)，將發生交易當天的策略報酬扣除 `Trade_Action * 0.003 * 100`。
5. 【累積報酬】：將報酬率轉為乘數 (1 + 報酬率/100) 後，使用 `.cumprod()` 計算「買進持有 (Buy & Hold)」與「AI 策略」的累積淨值曲線。
6. 使用 plotly 繪製這兩條淨值曲線的對比圖，並 print 出兩者最終的累積總報酬率。

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 19：構建量化分析腳本 (自動化)
- **分類**：部署與自動化
- **說明**：將上述所有散落的邏輯封裝成一個優雅的 Python 類別。

### 詠唱詞（貼給 Gemini）：

```text
請將前面「環境與資料」、「技術分析」、「籌碼與基本面」以及「AI 量化模型」這四個階段所撰寫的資料獲取、特徵工程、AI 預測等核心邏輯，整合成一個名為 `StockAnalyzer` 的優雅 Python 類別。

【核心要求】：
1. 請提供 `fetch_data` (負責下載與清理資料)、`engineer_features` (負責計算技術指標與複合特徵)、`run_ai_analysis` (負責模型訓練與預測) 等方法，讓程式碼結構清晰且可被重複呼叫。
2. 確保類別內的邏輯與我們之前步驟中所撰寫的完全一致，不遺漏任何重要的指標或特徵。

【重要指令】：類別寫完後，請務必在最下方，加上「實例化並執行」該類別的測試語法（例如 `analyzer = StockAnalyzer('2330.TW')` ），讓學員按下執行就能直接看到自動化分析的結果！
```

---

## STEP 20：Gemini 3.5 智能盤勢解析
- **分類**：部署與自動化
- **說明**：不只看數據！串接gemini-3.5-flash，讓 AI 幫你寫出專業的盤後分析報告。

### 詠唱詞（貼給 Gemini）：

```text
# STEP 20: Gemini 3.5 智能盤勢解析

請幫我撰寫一段 Python，使用最新 `google-genai` SDK 呼叫 Gemini 進行盤勢分析：

1. 開頭加入 `!pip install -q google-genai`。
2. 從前面的 `mega_df` 取出最後 3 筆資料，轉換成字串格式作為 input。
3. 請依照 Google 官方最新寫法串接，加上 try-except 防呆：

```python
from google import genai
from google.colab import userdata

api_key = userdata.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    system_instruction="你是一位資深量化分析師。請根據提供的數據，撰寫一段 150 字以內的「多空盤勢解析與操作建議」。",
    input=你的數據字串變數
)
print(interaction.output_text)
```

4. 請輸出完整可執行的程式碼，絕對不要引入 Gradio！
```

---

## STEP 21：專業級面板 (Blocks 排版與雷達)
- **分類**：部署與自動化
- **說明**：使用 Gradio Blocks 打造極致穩定、免依賴前置變數的「台股 AI 綜合量化分析面板」：內建短中長均線矩陣、乖離率、RSI、MACD、布林通道、ATR 波動停損與自選股雷達。

### 詠唱詞（貼給 Gemini）：

```text
# STEP 21: 專業級面板 (Blocks 排版與雷達)

請幫我使用 Gradio Blocks 打造一個極其穩定且漂亮的「台股 AI 綜合量化分析面板」：

1. 【防崩潰模組與引入】：
import gradio as gr
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

2. 【核心分析函數 `analyze_stock`】：
- 接收 ticker (股票代號) 與 period (區間)。
- 使用 `yf.download` 下載資料，並具備強健的多層索引 (MultiIndex) 欄位自動清洗機制。
- 計算 MA5, MA10, MA20, MA60, MA120, MA240 (短中長均線矩陣)、20日乖離率 (Bias 20)、1d/3d/5d 累積報酬率、RSI(14)、MACD (DIF/DEM/柱狀體)、布林通道帶寬 (BB Width) 與 ATR(14) 動態停損建議。
- 透過 Plotly 繪製 4 層專業圖表 (K線+MA+布林通道、RSI、MACD、成交量與均量)。
- 產出全方位多空指標診斷矩陣表與文字解析總評。
- 必須加上 try-except，若下載失敗回傳空圖並在文字欄位提示錯誤原因，確保面板絕不崩潰！

3. 【自選股雷達函數 `scan_watchlist`】：
- 接收以逗號分隔的股票代號字串 (如 "2330, 2317, 2454, 2303, 2308, 3231, 2603")。
- 迴圈抓取最新收盤價、漲跌幅、20日均線位置、乖離率與 RSI，產出包含「股票代號、最新收盤價、單日漲跌幅、MA20(月線)、20日乖離率、RSI(14)、多空評定」的結構化 DataFrame。

4. 【Gradio Blocks 現代化 UI】：
- 使用 `gr.Blocks(theme=gr.themes.Soft())`。
- 頂部設定大標題：「📈 台股 AI 綜合量化量能觀測儀表板」。
- 佈局採用 `gr.Tabs()` 分為兩個獨立頁籤：
  - Tab 1: 「📊 單檔技術與模型透視」(包含代號下拉/輸入、區間選擇、啟動按鈕、4層 Plotly 圖表、文字解析框、指標診斷矩陣表)。
  - Tab 2: 「🎯 智慧自選股雷達」(包含多股輸入區、批次掃描按鈕、結構化表格)。
- 綁定按鈕的 `.click()` 事件，並提供 `concurrency_limit`

【🔥 重要指令：絕對嚴禁建立新檔案 (NO ARTIFACTS)】：
1. 請直接在對話框中輸出程式碼區塊。絕對不要建立新的檔案或元件。
2. 保持在目前的對話串中，必須引用之前定義過的變數與數據。

【Vibe Coding 守則】：
1. 請將此步驟所需的所有 import 直接包含在程式碼區塊內，確保可直接貼入新儲存格運行。

【註解要求】：
1. 第一行為：`# STEP 21: 專業級面板 (Blocks 排版與雷達)`。
2. 註解請精要專業，解釋目的。
```

---

## STEP 22：自動建立 requirements.txt 依賴檔
- **分類**：部署與自動化
- **說明**：一鍵自動生成 requirements.txt 依賴清單檔案，支援 Colab 檔案面板右鍵或程式碼一鍵自動下載，為 Hugging Face 雲端部署做好準備！

### 詠唱詞（貼給 Gemini）：

```text
請幫我撰寫一段 Python 程式碼，在 Google Colab 中【自動建立 requirements.txt 依賴檔】並提供【一鍵下載到電腦】的功能，為後續部署到 Hugging Face Spaces 做準備：

1. 【自動建立 requirements.txt 檔案】：
- 使用 Python 檔案寫入方式，自動在當前專案根目錄建立 `requirements.txt`。
- 清單內包含專案運行所需的所有核心依賴庫：
  * gradio>=4.0.0
  * yfinance>=0.2.38
  * pandas>=2.0.0
  * numpy>=1.24.0
  * plotly>=5.18.0
  * requests>=2.31.0
  * google-genai>=0.1.1
  * scikit-learn>=1.3.0
  * xgboost>=2.0.0

2. 【自動檢核與列印內容】：
- 寫入完成後自動讀取並印出 `requirements.txt` 的內容與絕對路徑，確保依賴清單完整無誤。

3. 【提供雙軌便捷下載引導】：
- 【方式 A：程式碼一鍵自動下載至電腦】：使用 `from google.colab import files; files.download('requirements.txt')` 觸發瀏覽器下載。
- 【方式 B：Colab 面板手動下載引導】：印出友善指引，說明可點擊 Colab 左側面板的「📁 檔案」圖示找到 `requirements.txt`，按右鍵選擇「下載」。

4. 請輸出完整可直接在 Colab 執行的 Python 程式碼，並附帶執行成功提示！

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 23：分析程式碼重構為模組化 stock.py
- **分類**：部署與自動化
- **說明**：將 StockAnalyzer 類別與 Gradio 分析儀表板提取重構為獨立的 stock.py 檔案，支援 Colab 一鍵自動下載或檔案面板手動下載，完美接軌 Hugging Face 部署！

### 詠唱詞（貼給 Gemini）：

```text
請幫我撰寫一段 Python 程式碼，在 Google Colab 中【將分析程式碼重構為模組化的 stock.py 檔案】並提供【一鍵自動下載至電腦】的功能：

1. 【模組化封裝 stock.py】：
- 使用 Python 檔案寫入方式（或 `%%writefile stock.py`），將完整的 `StockAnalyzer` 分析核心類別與 Gradio Blocks 應用程式重構成乾淨、模組化的 `stock.py`。
- 程式內整合：
  * yfinance 穩定下載與多層欄位清洗機制 (`_fix_col_names`)
  * MA5/MA20 均線、乖離率、布林通道與 MACD/RSI 指標計算
  * Plotly 專業 K 線走勢圖繪製
  * 自選股雷達批次掃描功能 (`scan_watchlist`)
  * 完整的 Gradio Blocks 介面與啟動入口 (`app.launch()`)

2. 【自動檢核與檔案生成】：
- 自動在 Colab 根目錄生成 `stock.py`，印出檔案絕對路徑與模組結構說明，確保程式碼結構完整。

3. 【提供雙軌便捷下載引導】：
- 【方式 A：程式碼一鍵自動下載至電腦】：執行 `from google.colab import files; files.download('stock.py')` 直接觸發瀏覽器下載。
- 【方式 B：Colab 面板手動下載引導】：印出清晰指引，說明可點擊 Colab 左側面板「📁 檔案」圖示找到 `stock.py`，按右鍵點選「下載」。

4. 請輸出完整可直接在 Colab 執行的 Python 程式碼，執行後能立即產出並下載 stock.py！

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

## STEP 24：線上網站部署 (Colab 股市工具一鍵變 Web App)
- **分類**：部署與自動化
- **說明**：免架設伺服器、免寫網頁前端，本步驟直接在 Hugging Face Space 網頁上操作（不需再貼回 Colab！），包含安全設定 FinMind Token 與 Gemini API Key 密鑰。

### 詠唱詞（貼給 Gemini）：

```text
這一步是最後的雲端發布！【本步驟已不需再回 Colab 執行任何程式碼】，請直接在 Hugging Face Spaces 網站上完成部署與密鑰設定。

請提供一份清晰、專業的 Hugging Face Spaces 完整建置與安全設定指南：

1. 【確認電腦已下載兩大核心檔案 (來自 STEP 22 & 23)】：
- 📄 requirements.txt (相依套件清單)
- 🐍 app.py 或 stock.py (Gradio 分析與雷達主程式，若為 stock.py 建議直接更名為 app.py 作為預設進入點)

2. 【建立 Hugging Face Space 雲端容器】：
- 登入 Hugging Face (huggingface.co) -> 點選右上角頭像 -> "+ New Space"。
- 設定參數：
  * Space name：輸入自訂名稱 (如 `taiwan-stock-ai-dashboard`)
  * Select the Space SDK：選擇 **Gradio**
  * Space hardware：選擇 **CPU Basic (Free - 2 vCPU, 16GB RAM)** 免費規格
  * Space visibility：選擇 **Public** (公開分享) 或 **Private** (個人私有)
- 點擊 "Create Space" 建立容器專案。

3. 【檔案上傳 (拖曳即部署)】：
- 切換至頂部 **"Files"** 頁籤 -> 點選 **"+ Add file"** -> **"Upload files"**。
- 將電腦中的 `requirements.txt` 與 `app.py` 拖曳上傳，點擊 **"Commit changes to main"**。

4. 【🔑 重點教學：在 Settings 中安全配置 FinMind Token 與 Gemini API Key】：
- 切換至 Space 頂部 **"Settings"** (設定) 頁籤。
- 向下滾動找到 **"Variables and secrets"** 區塊。
- 點擊 **"New secret"**，依序新增以下兩組安全密鑰 (嚴禁直接寫死在程式碼中，Hugging Face 會以加密環境變數注入)：
  * Secret 1：
    - Name: `GEMINI_API_KEY`
    - Value: 填入您的 Google Gemini API Key (支援 AI 智能策略解析)
  * Secret 2：
    - Name: `FINMIND_TOKEN`
    - Value: 填入您的 FinMind API Token (支援台股法人籌碼與融資融券真實數據)
- 點擊 "Save" 儲存，密鑰將安全生效且不會對外公開！

5. 【自動建置監控與成果檢驗】：
- 切換回 **"App"** 頁籤，上方狀態顯示 🟡 **Building**，點擊可即時展開 Build Logs 觀察 Docker 容器安裝套件流程。
- 當狀態轉為 🟢 **Running** (綠燈) 時，即代表台股 AI 盯盤系統已永久上線！
- 取得專屬網址與全螢幕獨立 Direct URL，支援手機/平板隨時加入主畫面看盤！

【🤖 AI 助教解析】：
在產出程式碼之前，請你先以「資深量化分析師」的口吻，針對本步驟即將計算的指標或處理的數據，在對話框中直接給予我約 50 字的專業觀念提醒，讓我一邊寫程式一邊學投資！
```

---

