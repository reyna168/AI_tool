# 台股 AI 看盤+盯盤系統：完整程式碼與資源總包

本壓縮包收錄「用 AI 打造台股看盤+盯盤系統 | Vibe Coding 實戰指南」之所有核心程式碼與資源：

## 目錄結構
- 📁 01_v6_full_market_platform/ : 推薦之 v6 全市場掃描 + 深度分析平台（免 Gradio，支援 Render / 本地執行）
  - main.py (FastAPI 後端 API)
  - stock.py (台股量化技術分析與選股核心)
  - index.html (前端即時互動戰情室 UI)
  - requirements.txt (Python 依賴套件清單)
  - Dockerfile (容器化部署配置)
  - README.md
- 📁 02_step24_huggingface_deploy/ : STEP 24 Hugging Face Spaces 專用部署包
  - app.py (Gradio / 互動介面進入點)
  - requirements.txt
- 📁 03_rescue_codes/ : 各步驟備用救援程式碼 (Python)
  - step11_margin_trading.py
  - step13_institutional_investors.py
  - step14_financial_fundamentals.py
  - step16_multi_indicators.py
  - step17_scoring_model.py
  - step18_backtesting_engine.py
  - step19_interactive_dashboard.py
  - step20_auto_alert_notification.py
  - step21_gemini_ai_analysis.py
  - step22_morning_briefing.py
  - step23_full_market_screener.py
  - step24_cloud_deployment.py
- 📄 00_all_24_steps_prompts.md : 全部 24 步驟完整詠唱詞（一鏡到底）

祝您開發順利！
