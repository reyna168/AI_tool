# 台股與宏觀市場每日盤前情報系統

依訪談定案規格實作：Python 3 + SQLite，每日 07:30 彙整 VIX、台美利差、可轉債精選、新股、除權息/法說、特別訊息，
存成 `reports/YYYY-MM-DD.md` 並推播 Telegram / Discord。

## 安裝與執行
```bash
pip install -r requirements.txt
copy .env.example .env          # 填 Telegram / Discord（可略過，僅產生本機 .md）
python main.py --now --no-push  # 第一次先試跑，看日報最底部的「執行警告」
python main.py --now            # 立即執行並推播
python main.py --schedule       # 常駐，每天 07:30（config.yaml 可改）
python -m unittest discover tests   # 離線單元測試
```
Windows 也可改用「工作排程器」每天 07:30 執行 `python main.py --now`，比常駐更穩。

## 第一次使用必做（重要）
1. **填 `config.yaml` 的 `tw_rates`**（央行重貼現率、台灣 10Y 公債殖利率、as_of）。台灣利率沒有穩定免費 API，故手動維護；未填則利差欄位顯示「—」並出現警告。
2. **確認可轉債端點**：預設會用 swagger 自動探索 TPEx OpenAPI 中的「可轉債」端點。
   若日報警告 CB 失敗或欄位錯位：
   ```bash
   python main.py --discover 可轉債
   ```
   把正確端點填入 `config.yaml` 的 `cb.sources`，欄位名稱不同時用 `cb.field_map` 覆寫。
3. 若 TWSE 出現 SSL 憑證錯誤（Python 3.13 常見），升級 `certifi` 或暫時設 `http.ssl_verify: false`。

## 架構
```
main.py          入口（--now / --schedule / --discover / --only）
core/            http.py（節流 1~2 秒 + 指數退避 3 次 + 當日 SQLite 快取）、util.py
collectors/      vix / rates / cb / ipo / calendar（除權息+法說）/ notices，彼此獨立，失敗只記警告
storage/db.py    SQLite：series、cb_quotes、events、announcements、http_cache
analyzers/       signals（VIX 燈號、利差、殖利率）、cb_screen（四類精選）、notice_filter、report
notifiers/       markdown（日報）、push（Telegram / Discord）
```

## 已知限制（請知悉）
- 本專案在無外網沙箱中完成，**僅以模擬資料做過離線測試**；各官方端點的真實欄位未在線上驗證。
  端點或欄位改版時只需調整對應 collector 或 `config.yaml`，其他模組不受影響。
- 除權息「殖利率」為 **單次** 除權息價值 ÷ 除權息前收盤價；遇「權息」併行時含股票股利，屬估算上限，並非年化殖利率。
- 可轉債溢價率 = CB 價 ÷（股價 ÷ 轉換價 × 100）− 1，股價取自當日收盤行情；缺股價或轉換價者不計算。
- 溢價歷史百分位需累積約 20 個交易日資料後才會出現。
- 法說會 / 重大訊息 / 注意 / 處置的部分端點路徑為已知路徑加 swagger 關鍵字探索備援，未必百分之百命中。
- 資訊整理工具，非投資建議。
