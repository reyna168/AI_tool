from datetime import datetime
from collectors.base_collector import BaseCollector, logger
from config import HIGH_YIELD_THRESHOLD, DAYS_HORIZON

class CalendarCollector(BaseCollector):
    def fetch_dividend_and_briefings(self):
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        # 1. 取得最新殖利率對照表 (BWIBBU_ALL)
        bwibbu_url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        yield_map = {}
        yield_list = self.fetch_with_retry(bwibbu_url, cache_key="yield_map", today_str=today_str) or []
        for item in yield_list:
            c = item.get("Code", "")
            try:
                y = float(item.get("DividendYield", 0.0))
                yield_map[c] = y
            except ValueError:
                pass

        # 2. 取得除權息預告表 (TWT48U_ALL)
        div_url = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"
        div_list = self.fetch_with_retry(div_url, cache_key="div_schedule", today_str=today_str) or []
        
        events = {
            "high_yield_dividends": [],
            "regular_dividends": [],
            "briefings": []
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for item in div_list:
                code = item.get("Code", "")
                name = item.get("Name", "")
                raw_date = str(item.get("Date", ""))
                
                iso_date = ""
                if len(raw_date) == 7:
                    roc_year = int(raw_date[:3])
                    iso_date = f"{roc_year + 1911}-{raw_date[3:5]}-{raw_date[5:7]}"
                elif len(raw_date) == 8:
                    iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                else:
                    iso_date = raw_date

                try:
                    cash_div = float(item.get("CashDividend") or 0.0)
                except ValueError:
                    cash_div = 0.0

                try:
                    stock_div = float(item.get("StockDividendRatio") or 0.0)
                except ValueError:
                    stock_div = 0.0

                est_yield = yield_map.get(code, 0.0)

                if code and iso_date:
                    cursor.execute("""
                        INSERT INTO corporate_events (event_type, event_date, code, name, cash_dividend, stock_dividend, est_yield, description, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(event_type, event_date, code) DO UPDATE SET
                            cash_dividend=excluded.cash_dividend,
                            stock_dividend=excluded.stock_dividend,
                            est_yield=excluded.est_yield
                    """, ("DIVIDEND", iso_date, code, name, cash_div, stock_div, est_yield, "除權除息預告", today_str))

                    try:
                        target_dt = datetime.strptime(iso_date, "%Y-%m-%d")
                        diff = (target_dt - today).days
                        if 0 <= diff <= DAYS_HORIZON:
                            event_info = {
                                "code": code,
                                "name": name,
                                "date": iso_date,
                                "cash_div": cash_div,
                                "stock_div": stock_div,
                                "est_yield": est_yield,
                                "days_left": diff
                            }
                            if est_yield >= HIGH_YIELD_THRESHOLD:
                                events["high_yield_dividends"].append(event_info)
                            else:
                                events["regular_dividends"].append(event_info)
                    except Exception:
                        pass

            conn.commit()

        logger.info(f"Dividends analyzed: {len(events['high_yield_dividends'])} high-yield items")
        return events

