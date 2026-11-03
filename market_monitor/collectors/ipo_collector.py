from datetime import datetime, timedelta
from collectors.base_collector import BaseCollector, logger
from config import DAYS_HORIZON

class IpoCollector(BaseCollector):
    def fetch_upcoming_ipos(self):
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_FIRST"
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        
        raw_list = self.fetch_with_retry(url, cache_key="ipo_stock_first", today_str=today_str) or []
        upcoming = []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for item in raw_list:
                code = item.get("Code") or item.get("StockCode") or ""
                name = item.get("Name") or item.get("StockName") or ""
                market_type = item.get("MarketType") or "初次上市"
                
                # 日期轉換 (民國轉西元)
                raw_date = str(item.get("ListingDate") or item.get("Date") or "")
                iso_date = ""
                if len(raw_date) == 7: # 例如 1151115
                    roc_year = int(raw_date[:3])
                    iso_date = f"{roc_year + 1911}-{raw_date[3:5]}-{raw_date[5:7]}"
                elif len(raw_date) == 8:
                    iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                else:
                    iso_date = raw_date

                try:
                    price = float(item.get("IssuePrice") or 0.0)
                except ValueError:
                    price = 0.0

                if code and iso_date:
                    cursor.execute("""
                        INSERT INTO ipo_schedules (code, name, market_type, issue_price, listing_date, status, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(code, listing_date) DO UPDATE SET
                            issue_price=excluded.issue_price,
                            status=excluded.status
                    """, (code, name, market_type, price, iso_date, "即將上市", today_str))

                    # 篩選未來 14 天內即將登場的新股
                    try:
                        target_dt = datetime.strptime(iso_date, "%Y-%m-%d")
                        diff = (target_dt - today).days
                        if 0 <= diff <= DAYS_HORIZON:
                            upcoming.append({
                                "code": code,
                                "name": name,
                                "market_type": market_type,
                                "issue_price": price,
                                "listing_date": iso_date,
                                "days_left": diff
                            })
                    except Exception:
                        pass
            conn.commit()

        logger.info(f"IPO collected: {len(upcoming)} upcoming in {DAYS_HORIZON} days")
        return upcoming

