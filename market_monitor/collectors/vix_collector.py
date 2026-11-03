from datetime import datetime
from collectors.base_collector import BaseCollector, logger

class VixCollector(BaseCollector):
    def fetch_vix(self):
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=5d"
        today_str = datetime.now().strftime("%Y-%m-%d")
        data = self.fetch_with_retry(url, cache_key="vix_latest", today_str=today_str)
        
        if not data or "chart" not in data or not data["chart"].get("result"):
            logger.error("Failed to parse VIX from Yahoo Finance")
            return None

        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        current_price = meta.get("regularMarketPrice") or 0.0
        prev_close = meta.get("chartPreviousClose") or current_price

        change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0

        if current_price < 15:
            risk_level = "🟢 低波動 (市場情緒平和樂觀)"
        elif current_price < 25:
            risk_level = "🟡 常態震盪 (正常交易區間)"
        elif current_price < 35:
            risk_level = "🟠 警戒升溫 (避險恐慌情緒升高)"
        else:
            risk_level = "🔴 極度恐慌 (全球市場劇烈動盪)"

        record = {
            "date": today_str,
            "vix_close": round(current_price, 2),
            "vix_change_pct": round(change_pct, 2),
            "risk_level": risk_level,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 寫入資料庫
        with self.db.get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO vix_history (date, vix_close, vix_change_pct, risk_level, updated_at)
                VALUES (:date, :vix_close, :vix_change_pct, :risk_level, :updated_at)
                ON CONFLICT(date) DO UPDATE SET
                    vix_close=excluded.vix_close,
                    vix_change_pct=excluded.vix_change_pct,
                    risk_level=excluded.risk_level,
                    updated_at=excluded.updated_at
            """, record)
            conn.commit()

        logger.info(f"VIX collected: {record['vix_close']} ({record['risk_level']})")
        return record

