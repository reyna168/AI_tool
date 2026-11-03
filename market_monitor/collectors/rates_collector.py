from datetime import datetime
from collectors.base_collector import BaseCollector, logger

class RatesCollector(BaseCollector):
    def fetch_rates_and_spread(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 抓取美債 10 年期殖利率 (^TNX)
        tnx_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?interval=1d&range=5d"
        tnx_data = self.fetch_with_retry(tnx_url, cache_key="tnx_yield", today_str=today_str)
        
        us_10y = 4.50
        if tnx_data and "chart" in tnx_data and tnx_data["chart"].get("result"):
            meta = tnx_data["chart"]["result"][0].get("meta", {})
            us_10y = meta.get("regularMarketPrice") or 4.50

        # 2. 基準利率數據（聯準會 Fed Rate vs 台灣央行重貼現率）
        # 目前聯準會基準利率區間約 4.50% ~ 4.75%，台灣央行重貼現率為 2.00%
        us_fed_rate = 4.50
        tw_central_rate = 2.00
        rate_spread = round(us_fed_rate - tw_central_rate, 2)

        if rate_spread > 2.0:
            trend_comment = "美台利差維持高檔倒掛 (>2%)，外幣定存吸引力強，台幣面臨防禦性匯率波動"
        else:
            trend_comment = "利差逐步收斂，資金回流新興市場潛力增加"

        record = {
            "date": today_str,
            "us_fed_rate": us_fed_rate,
            "tw_central_rate": tw_central_rate,
            "us_10y_yield": round(us_10y, 2),
            "rate_spread": rate_spread,
            "trend_comment": trend_comment,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with self.db.get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO interest_rates (date, us_fed_rate, tw_central_rate, us_10y_yield, rate_spread, trend_comment, updated_at)
                VALUES (:date, :us_fed_rate, :tw_central_rate, :us_10y_yield, :rate_spread, :trend_comment, :updated_at)
                ON CONFLICT(date) DO UPDATE SET
                    us_fed_rate=excluded.us_fed_rate,
                    tw_central_rate=excluded.tw_central_rate,
                    us_10y_yield=excluded.us_10y_yield,
                    rate_spread=excluded.rate_spread,
                    trend_comment=excluded.trend_comment,
                    updated_at=excluded.updated_at
            """, record)
            conn.commit()

        logger.info(f"Rates collected: US 10Y {record['us_10y_yield']}%, Spread {record['rate_spread']}%")
        return record

