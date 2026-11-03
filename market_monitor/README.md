# 每日市場盤前情報與宏觀指標自動監控系統 (Market Monitor)

本專案為自動化監控與盤前情報萃取系統，專為關注**台股市場、可轉債（CB）策略與全球宏觀指標**的投資者設計。

---

## 🌟 核心涵蓋維度

1. **VIX 恐慌指標**：CBOE 前日收盤價、5 日變動與風險燈號評級（🟢 低波動、🟡 常態、🟠 警戒、🔴 極度恐慌）。
2. **可轉債 (CB) 精選**：全量資料儲存入庫，自動過濾「負溢價套利機會」與「百元面額以下低檔防守標的」。
3. **即將上市櫃股票 (IPO)**：未來 14 天內即將掛牌、公開申購之新股名單與承銷價。
4. **除權除息與法說會行事曆**：未來 14 天內除權息日程，高亮標註**現金殖利率 > 5%** 之高息標的。
5. **特別訊息與監管名單**：盤後處置股票（分盤撮合、預收款券）與注意股票名單。
6. **台美利率與利差**：聯準會基準利率、台灣央行重貼現率、10 年期美債殖利率與利差走勢解讀。

---

## 📂 專案架構

```text
market_monitor/
├── collectors/                # 資料採集器 (防鎖節流 + 指數退避重試)
│   ├── base_collector.py      # 通用請求中介層與快取機制
│   ├── vix_collector.py       # VIX 恐慌指數採集
│   ├── cb_collector.py        # 可轉債每日行情與溢價率計算
│   ├── ipo_collector.py       # 新股初次上市櫃行事曆
│   ├── calendar_collector.py  # 除權息預告與高殖利率標註
│   ├── news_collector.py      # 處置股與注意股特別訊息
│   └── rates_collector.py     # 台美利差與美債 10 年期殖利率
├── storage/
│   └── database.py            # SQLite 本地關聯式資料庫 (自動建表與快取管理)
├── analyzers/
│   └── evaluator.py           # 數據綜合分析與晨報亮點生成
├── notifiers/
│   ├── markdown_notifier.py   # Markdown 日報產生器 (存放於 reports/)
│   └── telegram_notifier.py   # Telegram Bot / Discord Webhook 推播
├── reports/                   # 每日產出的 Markdown 晨報
├── config.py                  # 系統設定參數與門檻值
├── main.py                    # 主程式入口 (支援即時執行與排程模式)
└── README.md
```

---

## 🚀 快速上手

### 1. 立即執行一次採集並產生晨報

```bash
cd f:\skill_test\market_monitor
python main.py --now
```

產出結果將自動存放於 `reports/morning_report_YYYY-MM-DD.md`。

### 2. 啟動每日 07:30 定時排程常駐

```bash
python main.py --schedule
```

### 3. 配置推播通知（選填）

若欲將晨報推送到 Telegram 或 Discord，可於系統環境變數中設定：
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DISCORD_WEBHOOK_URL`

