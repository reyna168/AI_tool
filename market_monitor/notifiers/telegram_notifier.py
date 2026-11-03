import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL
from collectors.base_collector import logger

class TelegramNotifier:
    @staticmethod
    def send_summary(data):
        vix = data.get("vix") or {}
        rates = data.get("rates") or {}
        date_str = data["date"]
        
        msg_lines = [
            f"🔔 *市場盤前晨報速覽 ({date_str})*",
            "",
            f"📈 *VIX 恐慌指標*：`{vix.get('vix_close', 'N/A')}` ({vix.get('risk_level', '')})",
            f"💵 *美台利差*：`{rates.get('rate_spread', 'N/A')}%` (10Y美債: `{rates.get('us_10y_yield', 'N/A')}%`)",
            "",
            f"🎯 *即將登場 (14天內)*：",
            f"• 新股上市/抽籤：{len(data.get('ipo', []))} 檔",
            f"• 高殖利率股 (>5%)：{len(data.get('calendar', {}).get('high_yield_dividends', []))} 檔",
            f"• 處置懲罰股票：{len(data.get('news', {}).get('punish_list', []))} 檔",
            "",
            f"👉 完整詳細日報已存檔至本地 reports/ 目錄！"
        ]
        text = "\n".join(msg_lines)

        # 1. 嘗試發送 Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                resp = requests.post(tg_url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown"
                }, timeout=10)
                if resp.status_code == 200:
                    logger.info("Telegram notification sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")

        # 2. 嘗試發送 Discord Webhook
        if DISCORD_WEBHOOK_URL:
            try:
                resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=10)
                if resp.status_code in [200, 204]:
                    logger.info("Discord notification sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send Discord message: {e}")

        return text

