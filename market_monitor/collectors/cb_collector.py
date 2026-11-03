from datetime import datetime
from collectors.base_collector import BaseCollector, logger
from config import CB_UNDER_PAR_THRESHOLD

class CbCollector(BaseCollector):
    def fetch_cb_data(self):
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        # 1. 取得現股市價對照表 (TWSE STOCK_DAY_ALL)
        stock_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        stock_raw = self.fetch_with_retry(stock_url, cache_key="stock_prices", today_str=today_str) or []
        price_map = {}
        for s in stock_raw:
            try:
                price_map[s["Code"]] = float(s.get("ClosingPrice") or 0.0)
            except (ValueError, TypeError):
                pass

        # 2. 取得台灣上市櫃可轉債發行與轉換條款全量清單 (TPEx bond_ISSBD5_data)
        cb_url = "https://www.tpex.org.tw/openapi/v1/bond_ISSBD5_data"
        raw_list = self.fetch_with_retry(cb_url, cache_key="cb_issbd5_full", today_str=today_str) or []

        highlighted = {
            "itm_expiring": [],     # ★ 核心新增：即將到期且現股價錢站上轉換價 (價內轉換誘因)
            "negative_premium": [], # 負折溢價/套利
            "under_par": [],        # 破百元防守型
            "mature_soon": []       # 接近到期
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for item in raw_list:
                bond_code = str(item.get("BondCode", "")).strip()
                bond_name = item.get("ShortName") or item.get("IssuerName") or ""
                issuer = str(item.get("IssuerCode", "")).strip()
                mat_date_str = str(item.get("MaturityDate", "")).strip()

                try:
                    conv_price = float(item.get("Conversion/ExchangePriceAtIssuance") or 0.0)
                except (ValueError, TypeError):
                    conv_price = 0.0

                stock_price = price_map.get(issuer, 0.0)

                # 到期日解析與天數計算
                days_left = 9999
                formatted_mat_date = ""
                if len(mat_date_str) == 8:
                    try:
                        mat_dt = datetime.strptime(mat_date_str, "%Y%m%d")
                        formatted_mat_date = mat_dt.strftime("%Y-%m-%d")
                        days_left = (mat_dt - today).days
                    except Exception:
                        pass

                # 計算平價 (Parity)
                parity = (stock_price / conv_price * 100) if conv_price > 0 else 0.0

                features = []

                # ★ 核心判斷：現股站上轉換價 (stock_price >= conv_price) 且 1 年內即將到期 (days_left <= 365)
                if conv_price > 0 and stock_price >= conv_price and 0 <= days_left <= 365:
                    itm_pct = round((stock_price - conv_price) / conv_price * 100, 2)
                    features.append("到期價內站上轉換價")
                    highlighted["itm_expiring"].append({
                        "bond_code": bond_code,
                        "name": bond_name,
                        "issuer": issuer,
                        "stock_price": stock_price,
                        "conv_price": conv_price,
                        "maturity_date": formatted_mat_date,
                        "days_left": days_left,
                        "itm_pct": itm_pct
                    })

                # 記錄資料庫
                feature_str = ",".join(features)
                if bond_code:
                    cursor.execute("""
                        INSERT INTO cb_records (date, bond_code, bond_name, close_price, premium_rate, conversion_price, stock_price, features)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date, bond_code) DO UPDATE SET
                            conversion_price=excluded.conversion_price,
                            stock_price=excluded.stock_price,
                            features=excluded.features
                    """, (today_str, bond_code, bond_name, parity, 0.0, conv_price, stock_price, feature_str))

            conn.commit()

        # 依到期剩餘天數由小到大排序 (即將到期者排在最前面)
        highlighted["itm_expiring"].sort(key=lambda x: x["days_left"])

        logger.info(f"CB processed: {len(raw_list)} items, {len(highlighted['itm_expiring'])} ITM expiring bonds found")
        return highlighted
