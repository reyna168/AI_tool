import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "market_data.sqlite3"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 請求中介層防護配置
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 12
REQUEST_DELAY_SECONDS = 1.0  # 請求間隔防鎖
MAX_RETRIES = 3

# 推播設定（可透過環境變數或直接配置）
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# 策略門檻
HIGH_YIELD_THRESHOLD = 5.0      # 高殖利率標註門檻 5%
CB_UNDER_PAR_THRESHOLD = 100.0  # 可轉債破百面額防守門檻
DAYS_HORIZON = 14               # 除權息/法說/新股預告視窗 (未來14天)

